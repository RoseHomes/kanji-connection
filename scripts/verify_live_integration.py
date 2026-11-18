"""Read-only live integration verification. Never prints keys, tokens, URLs or SQL errors."""

import json
import subprocess
import sys
from pathlib import Path

import httpx
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import Settings
from app.database import create_database_engine
from app.models import Base


def frontend(mode):
    script = "import {loadEnv} from 'vite'; const e=loadEnv(process.argv[1],'.','VITE_'); process.stdout.write(JSON.stringify({url:e.VITE_SUPABASE_URL,key:e.VITE_SUPABASE_PUBLISHABLE_KEY,api:e.VITE_API_URL}));"
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script, mode],
        cwd=ROOT / "frontend",
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        return None
    return json.loads(result.stdout)


def request(url, headers=None):
    try:
        response = httpx.get(url, headers=headers, timeout=15, follow_redirects=False)
        return response, {"http_status": response.status_code}
    except httpx.HTTPError as exc:
        return None, {"network_error": type(exc).__name__}


def main():
    report = {
        "read_only": True,
        "accounts_created": 0,
        "emails_requested": 0,
        "database_writes": 0,
    }
    try:
        settings = Settings()
    except ValueError as exc:
        fields = (
            sorted({str(e["loc"][0]) for e in exc.errors(include_input=False)})
            if hasattr(exc, "errors")
            else []
        )
        print(json.dumps({"configuration_valid": False, "invalid_fields": fields}))
        return
    report["backend_configuration"] = {
        "valid": True,
        "auth_origin_set": bool(settings.supabase_url),
        "legacy_public_key_set": bool(settings.supabase_publishable_key),
        "account_writes_enabled": settings.enable_user_writes,
        "database_mode": settings.content_source == "database",
    }
    configs = {mode: frontend(mode) for mode in ["development", "production"]}
    report["frontend_configuration"] = {
        mode: {
            "loaded": bool(value),
            "auth_origin_set": bool(value and value.get("url")),
            "public_key_set": bool(value and value.get("key")),
            "same_project_as_backend": bool(
                value and value.get("url", "").rstrip("/") == settings.supabase_url
            ),
            "uses_local_api_proxy": bool(value and not value.get("api")),
        }
        for mode, value in configs.items()
    }
    public = (configs["development"] or {}).get("key")
    if settings.supabase_url:
        response, status = request(
            settings.supabase_url + "/auth/v1/health",
            {"apikey": public} if public else None,
        )
        report["auth_health"] = status
        response, status = request(
            settings.supabase_url + "/auth/v1/.well-known/jwks.json"
        )
        if response is not None and response.status_code == 200:
            keys = response.json().get("keys", [])
            status.update(
                public_key_count=len(keys),
                algorithms=sorted({k.get("alg", "unspecified") for k in keys}),
                supported_signing_keys=any(
                    k.get("alg") in {"ES256", "RS256"} for k in keys
                ),
            )
        report["backend_jwks"] = status
        report["frontend_auth"] = {}
        for mode, config in configs.items():
            if not config or not config.get("url") or not config.get("key"):
                continue
            for origin in settings.cors_origins:
                response, status = request(
                    config["url"].rstrip("/") + "/auth/v1/settings",
                    {"apikey": config["key"], "Origin": origin},
                )
                if response is not None and response.status_code == 200:
                    value = response.json()
                    allowed = response.headers.get("access-control-allow-origin")
                    status.update(
                        email_provider_enabled=value.get("external", {}).get("email"),
                        email_autoconfirm=value.get("mailer_autoconfirm"),
                        signup_disabled=value.get("disable_signup"),
                        browser_cors_allowed=allowed in {"*", origin},
                    )
                report["frontend_auth"][
                    mode + (" loopback" if "127.0.0.1" in origin else " local")
                ] = status
        if settings.supabase_publishable_key:
            response, status = request(
                settings.supabase_url + "/auth/v1/settings",
                {"apikey": settings.supabase_publishable_key.get_secret_value()},
            )
            report["backend_public_key"] = status
    if settings.database_url:
        engine = create_database_engine(settings)
        try:
            with engine.connect() as connection:
                tx = connection.begin()
                try:
                    connection.execute(text("SET TRANSACTION READ ONLY"))
                    connection.execute(text("SET LOCAL statement_timeout = '10000ms'"))
                    inspector = inspect(connection)
                    actual = set(inspector.get_table_names(schema="public"))
                    missing_tables = sorted(set(Base.metadata.tables) - actual)
                    missing_columns = {}
                    short_columns = {}
                    missing_uniques = {}
                    missing_fks = {}
                    counts = {}
                    for name, table in Base.metadata.tables.items():
                        if name not in actual:
                            continue
                        columns = {
                            c["name"]: c
                            for c in inspector.get_columns(name, schema="public")
                        }
                        absent = sorted({c.name for c in table.columns} - set(columns))
                        if absent:
                            missing_columns[name] = absent
                        for c in table.columns:
                            target = getattr(c.type, "length", None)
                            actual_length = getattr(
                                columns.get(c.name, {}).get("type"), "length", None
                            )
                            if target and actual_length and actual_length < target:
                                short_columns[f"{name}.{c.name}"] = True
                        unique = {
                            tuple(
                                inspector.get_pk_constraint(name, schema="public")[
                                    "constrained_columns"
                                ]
                            )
                        }
                        unique |= {
                            tuple(u["column_names"])
                            for u in inspector.get_unique_constraints(
                                name, schema="public"
                            )
                        }
                        expected = {
                            tuple(c.name for c in constraint.columns)
                            for constraint in table.constraints
                            if constraint.__class__.__name__
                            in {"UniqueConstraint", "PrimaryKeyConstraint"}
                        }
                        if expected - unique:
                            missing_uniques[name] = [list(u) for u in expected - unique]
                        fks = inspector.get_foreign_keys(name, schema="public")
                        expected_fk = {
                            tuple(c.name for c in fk.columns)
                            for fk in table.foreign_key_constraints
                        }
                        actual_fk = {tuple(fk["constrained_columns"]) for fk in fks}
                        if expected_fk - actual_fk:
                            missing_fks[name] = [
                                list(fk) for fk in expected_fk - actual_fk
                            ]
                        counts[name] = connection.scalar(
                            text(f'SELECT count(*) FROM public."{name}"')
                        )
                    revision = (
                        connection.scalar(
                            text("SELECT version_num FROM public.alembic_version")
                        )
                        if "alembic_version" in actual
                        else None
                    )
                    rls = dict(
                        connection.execute(
                            text(
                                "SELECT c.relname,c.relrowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r'"
                            )
                        ).all()
                    )
                    owner_policies = connection.scalar(
                        text(
                            "SELECT count(*) FROM pg_policies WHERE schemaname='public' AND policyname='owner_scope' AND tablename IN ('user_progress','review_items','quiz_attempts')"
                        )
                    )
                    report["database"] = {
                        "connected": True,
                        "transaction_read_only": connection.scalar(
                            text("SHOW transaction_read_only")
                        )
                        == "on",
                        "alembic_revision": revision,
                        "application_tables_found": len(
                            set(Base.metadata.tables) & actual
                        ),
                        "missing_tables": missing_tables,
                        "missing_columns": missing_columns,
                        "undersized_columns": short_columns,
                        "missing_unique_constraints": missing_uniques,
                        "missing_foreign_keys": missing_fks,
                        "all_application_rls_enabled": all(
                            rls.get(t, False) for t in Base.metadata.tables
                        ),
                        "owner_policy_count": owner_policies,
                        "counts": counts,
                    }
                finally:
                    tx.rollback()
        except SQLAlchemyError as exc:
            code = getattr(getattr(exc, "orig", None), "sqlstate", None)
            report["database"] = {
                "connected": False,
                "error_type": type(exc).__name__,
                "sqlstate": code,
            }
        finally:
            engine.dispose()
    folder = ROOT / "private/live-verification"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "read-only-integration.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report))


if __name__ == "__main__":
    main()
