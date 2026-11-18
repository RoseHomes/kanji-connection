from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from sqlalchemy.exc import OperationalError

from app.config import Settings
from app.database import create_database_engine, require_write_authorization
from app.main import create_app


def test_env_example_validates_offline():
    example = Path(__file__).resolve().parents[1] / ".env.example"
    settings = Settings(_env_file=example)
    assert settings.content_source == "database"
    assert settings.expose_samples is False
    assert settings.database_url and settings.migration_database_url
    assert "URL_ENCODED_PASSWORD" not in repr(settings)


@pytest.mark.parametrize(
    "url", ["invalid-secret", "sqlite:///secret.db", "postgresql+psycopg://missing"]
)
def test_bad_urls_fail_without_secret_echo(url):
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None, database_url=url)
    assert url not in str(exc.value)


def test_pool_configuration_is_lazy_and_serverless_sized(monkeypatch):
    from app import database

    captured = {}

    def factory(url, **kwargs):
        captured.update(kwargs)
        return "engine-without-connection"

    monkeypatch.setattr(database, "create_engine", factory)
    result = create_database_engine(
        Settings(
            _env_file=None,
            database_url=SecretStr("postgresql+psycopg://user:password@example.test:6543/postgres"),
        )
    )
    assert result == "engine-without-connection"
    assert captured["pool_size"] == 1 and captured["max_overflow"] == 0
    assert captured["connect_args"]["prepare_threshold"] is None
    assert captured["connect_args"]["sslmode"] == "require"
    assert captured["hide_parameters"] is True


def test_database_mode_fails_closed_without_credentials():
    with TestClient(create_app(Settings(_env_file=None, content_source="database"))) as client:
        assert client.get("/api/v1/health").json()["database"] == "not_configured"
        assert client.get("/api/v1/lessons").status_code == 503
        assert client.get("/api/v1/kanjis").status_code == 503


def test_db_error_response_redacts_details_and_never_falls_back(monkeypatch):
    from app.database import read_session
    from app.repository import DatabaseRepository

    app = create_app(Settings(_env_file=None, content_source="database"))
    app.dependency_overrides[read_session] = lambda: None

    def fail(*args, **kwargs):
        raise OperationalError("SELECT private", {}, Exception("password=supersecret"))

    monkeypatch.setattr(DatabaseRepository, "lessons", fail)
    with TestClient(app) as client:
        response = client.get("/api/v1/lessons")
        assert response.status_code == 503
        assert "supersecret" not in response.text and "SELECT" not in response.text
        assert response.json()["error"]["code"] == "database_unavailable"


def test_remote_writes_require_explicit_opt_in():
    with pytest.raises(RuntimeError, match="Remote database writes are disabled"):
        require_write_authorization(False)


@pytest.mark.parametrize(
    "origin", ["*", "https://example.com/lesson", "https://example.com/", "not-an-origin"]
)
def test_cors_requires_exact_origin(origin):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins=[origin])
