"""Edition-bound private staging import. Default is read-only; explicit opt-in commits."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.book_bundle import Bundle
from app.book_import import apply_bundle
from app.config import Settings
from app.database import create_database_engine
from app.json_content import SOURCE_RELATIVE, load_dataset
from app.models import Base

EXPECTED = {
    "source_sha256": "f9e5f7cf05b96a4962245057a300a7fee5ddde38603a34ca7c406afde460cae9",
    "bundle_sha256": "92cf49d38857ee52a9a03d160700223eecbfa6425d75de198d5be3334a9ccd2e",
    "editorial_layer_sha256": "6bd2e5ab59b695677be20a6cf6e68edd806d036822f992e812f282d1ba552f11",
}
FOLDER = ROOT / "private/live-book-import"
TABLES = {t.name: t for t in Base.metadata.sorted_tables}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def verify_sources():
    bundle = Bundle.model_validate_json(
        (ROOT / "private/json-content/import-bundle.json").read_bytes()
    )
    book = load_dataset(ROOT / SOURCE_RELATIVE)
    actual = {
        "source_sha256": hashlib.sha256(
            json.dumps(book.source_files, sort_keys=True).encode()
        ).hexdigest(),
        "bundle_sha256": hashlib.sha256(bundle.model_dump_json().encode()).hexdigest(),
        "editorial_layer_sha256": hashlib.sha256(
            (ROOT / "content/editorial-corrections.json").read_bytes()
        ).hexdigest(),
    }
    require(
        actual == EXPECTED,
        "Source, bundle or editorial hash differs from verified plan",
    )
    require(bundle.source_sha256 == actual["source_sha256"], "Bundle source mismatch")
    require(
        bundle.editorial_layer_sha256 == actual["editorial_layer_sha256"],
        "Overlay mismatch",
    )
    rehearsal = json.loads(
        (ROOT / "private/json-content/import-rehearsal.json").read_bytes()
    )
    require(all(rehearsal[k] == v for k, v in EXPECTED.items()), "Stale rehearsal")
    require(
        len(bundle.operations) == 2941 and len(book.chapters) == 30,
        "Plan count mismatch",
    )
    require(not bundle.publication_approved, "Publication forbidden")
    return bundle, rehearsal["counts"], actual


def schema_check(connection):
    require(
        connection.scalar(text("SELECT version_num FROM public.alembic_version"))
        == "0002",
        "Live revision differs from 0002",
    )
    queries = json.loads(
        (ROOT / "private/database-review/inspection-queries.json").read_bytes()
    )
    baseline = json.loads(
        (ROOT / "private/database-review/schema-after-committed.json").read_bytes()
    )
    snapshot = {}
    for key in ["relations", "columns", "constraints", "indexes", "policies"]:

        def relevant(row):
            # Include sequences and unexpected new public objects in the comparison.
            return row.get("schema") == "public"

        rows = [
            dict(r)
            for r in connection.execute(text(queries[key])).mappings()
            if relevant(r)
        ]
        old = [r for r in baseline[key] if relevant(r)]
        if key == "relations":
            rows = [{k: v for k, v in r.items() if k != "oid"} for r in rows]
            old = [{k: v for k, v in r.items() if k != "oid"} for r in old]
        require(rows == old, f"Live application schema differs: {key}")
        snapshot[key] = rows
    triggers = (
        connection.execute(
            text(
                "SELECT event_object_table,trigger_name FROM information_schema.triggers "
                "WHERE event_object_schema='public'"
            )
        )
        .mappings()
        .all()
    )
    require(
        not any(r["event_object_table"] in TABLES for r in triggers),
        "Unexpected application trigger",
    )
    for role in ["anon", "authenticated"]:
        exposed = connection.scalar(
            text(
                "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname='public' AND c.relname=ANY(:tables) "
                "AND (has_table_privilege(:role,c.oid,'SELECT') "
                "OR has_table_privilege(:role,c.oid,'INSERT') "
                "OR has_table_privilege(:role,c.oid,'UPDATE') "
                "OR has_table_privilege(:role,c.oid,'DELETE') "
                "OR has_table_privilege(:role,c.oid,'TRUNCATE'))"
            ),
            {"tables": [*TABLES, "alembic_version"], "role": role},
        )
        require(exposed == 0, "Unexpected direct client application privileges")
    return snapshot


def counts(connection):
    return {
        name: connection.scalar(select(func.count()).select_from(t))
        for name, t in TABLES.items()
    }


def private_check(connection):
    for name, table in TABLES.items():
        for field in ["status", "review_status"]:
            if field in table.c:
                require(
                    connection.scalar(
                        select(func.count())
                        .select_from(table)
                        .where(table.c[field] != "needs_review")
                    )
                    == 0,
                    f"Non-review content in {name}",
                )
        if "access_tier" in table.c:
            require(
                connection.scalar(
                    select(func.count())
                    .select_from(table)
                    .where(table.c.access_tier != "private")
                )
                == 0,
                f"Non-private content in {name}",
            )
    require(
        connection.scalar(
            text("SELECT count(*) FROM public.lessons WHERE catalog_visible")
        )
        == 0,
        "Visible lesson catalog",
    )


def foreign_key_check(connection):
    checked = 0
    for table in TABLES.values():
        for fk in table.foreign_keys:
            parent = fk.column
            orphan = (
                select(func.count())
                .select_from(table.outerjoin(parent.table, fk.parent == parent))
                .where(fk.parent.is_not(None), parent.is_(None))
            )
            require(connection.scalar(orphan) == 0, "Orphan foreign key")
            checked += 1
    # Actual owner FKs reference Supabase auth.users and are checked separately by PostgreSQL.
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit-authorized-private-import", action="store_true")
    args = parser.parse_args()
    bundle, expected_counts, hashes = verify_sources()
    FOLDER.mkdir(parents=True, exist_ok=True)
    engine = create_database_engine(Settings())
    report = {
        "hashes": hashes,
        "revision": "0002",
        "operations": len(bundle.operations),
        "chapters": 30,
        "publication_approved": False,
        "committed": False,
    }
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                connection.execute(text("SET LOCAL statement_timeout='60s'"))
                report["schema"] = schema_check(connection)
                report["before_counts"] = counts(connection)
                # This verified plan was approved against empty application tables.
                # Reject changed data instead of guessing compatibility or preserving mixed editions.
                require(
                    not any(report["before_counts"].values()),
                    "Application tables no longer empty; stop",
                )
            (FOLDER / "preflight.json").write_text(
                json.dumps(report, indent=2) + "\n", encoding="utf-8"
            )
            if not args.commit_authorized_private_import:
                print(
                    json.dumps(
                        {
                            "read_only_preflight_passed": True,
                            "hashes": hashes,
                            "all_application_tables_empty": True,
                            "operations": 2941,
                        }
                    )
                )
                return
            # One controlled transaction; table locks also stop noncooperating writers.
            with connection.begin():
                connection.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
                connection.execute(text("SET LOCAL lock_timeout='5s'"))
                connection.execute(text("SET LOCAL statement_timeout='60s'"))
                connection.execute(text("SET LOCAL search_path=public,pg_catalog"))
                connection.execute(text("SELECT pg_advisory_xact_lock(17171701)"))
                connection.execute(
                    text(
                        "LOCK TABLE "
                        + ",".join('public."' + n + '"' for n in sorted(TABLES))
                        + " IN SHARE ROW EXCLUSIVE MODE"
                    )
                )
                schema_check(connection)
                require(
                    not any(counts(connection).values()),
                    "Concurrent application change; stop",
                )
                verify_sources()
                session = Session(
                    bind=connection, join_transaction_mode="rollback_only"
                )
                try:
                    first = apply_bundle(session, bundle)
                    require(
                        not first["conflicts"] and not first["skipped"],
                        "Import conflict",
                    )
                    session.flush()
                    require(
                        counts(connection) == expected_counts,
                        "Precommit count mismatch",
                    )
                    private_check(connection)
                    report["foreign_keys_checked"] = foreign_key_check(connection)
                    second = apply_bundle(session, bundle)
                    require(
                        not second["inserted"] and not second["conflicts"],
                        "Duplicate protection failed",
                    )
                    report["inserted"] = first["inserted"]
                    report["repeat_import_inserted"] = sum(second["inserted"].values())
                    report["editorial_flags_retained"] = len(bundle.unresolved_issues)
                finally:
                    session.close()
            report["committed"] = True
            # Persist outcome before postcommit checks; never automatically retry this command.
            (FOLDER / "result.json").write_text(
                json.dumps(report, indent=2) + "\n", encoding="utf-8"
            )
        with engine.connect() as fresh, fresh.begin():
            fresh.execute(text("SET TRANSACTION READ ONLY"))
            schema_check(fresh)
            report["after_counts"] = counts(fresh)
            require(
                report["after_counts"] == expected_counts, "Postcommit count mismatch"
            )
            private_check(fresh)
            foreign_key_check(fresh)
            report["postcommit_verified"] = True
        (FOLDER / "result.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps({k: v for k, v in report.items() if k != "schema"}))
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - CLI boundary must redact all driver failures
        # Never serialize driver messages/SQL parameters, credentials or source content.
        print(
            json.dumps(
                {
                    "stopped": True,
                    "error_type": type(exc).__name__,
                    "reason": str(exc)
                    if type(exc) is RuntimeError
                    else "Inspect locally; details suppressed",
                }
            )
        )
        raise SystemExit(1) from None
