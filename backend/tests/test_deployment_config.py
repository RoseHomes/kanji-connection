"""Deployment-only guards; synthetic configuration, no network or live Auth/data."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.auth import Identity
from app.config import Settings
from app.learning import Learning
from app.main import create_app


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
