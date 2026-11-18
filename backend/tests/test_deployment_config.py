"""Deployment-only guards; synthetic configuration, no network or live Auth/data."""

import ast
import sys
from pathlib import Path
from uuid import uuid4

import pytest
import tomllib
from fastapi.testclient import TestClient
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from pydantic import ValidationError

from app.auth import Identity
from app.config import Settings
from app.learning import Learning
from app.main import create_app


def test_deployed_pyproject_dependencies_match_runtime_requirements():
    backend = Path(__file__).resolve().parents[1]
    project = tomllib.loads((backend / "pyproject.toml").read_text("utf-8"))["project"]

    def normalized(line):
        req = Requirement(line)
        return (
            canonicalize_name(req.name),
            frozenset(req.extras),
            str(req.specifier),
            str(req.marker) if req.marker else None,
        )

    deployed = {normalized(line) for line in project["dependencies"]}
    requirements = {
        normalized(line.strip())
        for line in (backend / "requirements.txt").read_text("utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert deployed and deployed == requirements
    assert len(deployed) == len(project["dependencies"])
    assert (backend / ".python-version").read_text().strip() in SpecifierSet(
        project["requires-python"]
    )
    assert "binary" in next(extras for name, extras, _, _ in deployed if name == "psycopg")
    assert "crypto" in next(extras for name, extras, _, _ in deployed if name == "pyjwt")


def test_application_third_party_imports_have_direct_runtime_dependencies():
    backend = Path(__file__).resolve().parents[1]
    project = tomllib.loads((backend / "pyproject.toml").read_text("utf-8"))["project"]
    declared = {canonicalize_name(Requirement(line).name) for line in project["dependencies"]}
    imported = set()
    for file in [backend / "index.py", *sorted((backend / "app").glob("*.py"))]:
        for node in ast.walk(ast.parse(file.read_text("utf-8"))):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module.split(".")[0])
    aliases = {"jwt": "pyjwt"}
    third_party = imported - sys.stdlib_module_names - {"app"}
    assert third_party
    assert {aliases.get(name, canonicalize_name(name)) for name in third_party} <= declared


def hosted(**changes):
    return Settings(
        _env_file=None,
        **{
            "vercel": True,
            "content_source": "database",
            "expose_samples": False,
            "database_url": "postgresql+psycopg://fixture:fixture@pooler.example.test:6543/postgres",
            "supabase_url": "https://auth.example.test",
            "cors_origins": ["https://frontend.example.test"],
            "enable_user_writes": False,
            "development_user_ids": [],
            **changes,
        },
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"development_user_ids": [uuid4()]},
        {"expose_samples": True},
        {"content_source": "sample"},
        {
            "migration_database_url": "postgresql+psycopg://fixture:fixture@pooler.example.test:5432/postgres"
        },
        {"database_url": None},
        {"supabase_url": None},
        {"cors_origins": []},
        {"cors_origins": ["http://localhost:5173"]},
        {"cors_origins": ["https://:fixture@frontend.example.test"]},
        {"cors_origins": ["https://127.0.0.2"]},
        {"supabase_url": "https://YOUR_PROJECT_REF.supabase.co"},
        {"database_url": "postgresql+psycopg://fixture:fixture@pooler.example.test:5432/postgres"},
    ],
)
def test_hosted_config_fails_closed(changes):
    with pytest.raises(ValidationError):
        hosted(**changes)


def test_guard_detects_vercel_environment_without_loading_local_credentials(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    values = hosted().model_dump(exclude={"vercel"})
    assert Settings(_env_file=None, **values).vercel is True


def test_hosted_development_access_stays_disabled_even_after_unsafe_model_copy():
    owner = uuid4()
    copied = hosted().model_copy(update={"development_user_ids": [owner]})
    assert Learning(None, copied, Identity(owner)).private is False
    with pytest.raises(ValueError, match="no development allowlist"):
        create_app(copied)


def test_exact_frontend_cors_preflight_handles_bearer_headers_without_database():
    app = create_app(hosted())
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/me/dashboard",
            headers={
                "Origin": "https://frontend.example.test",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "https://frontend.example.test"
        assert "access-control-allow-credentials" not in response.headers
        denied = client.options(
            "/api/v1/me/dashboard",
            headers={
                "Origin": "https://unapproved.example.test",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert denied.status_code == 400
        assert "access-control-allow-origin" not in denied.headers
        assert client.get("/api/v1/health").json()["account_writes_enabled"] is False
