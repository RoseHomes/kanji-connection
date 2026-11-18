"""Local configuration; validation never opens a network connection."""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore", hide_input_in_errors=True)
    content_source: Literal["sample", "database"] = "sample"
    database_url: SecretStr | None = None
    migration_database_url: SecretStr | None = None
    database_sslmode: Literal["require", "verify-full"] = "require"
    database_sslrootcert: str | None = None
    database_connect_timeout: int = Field(10, ge=1, le=30)
    database_statement_timeout_ms: int = Field(5000, ge=100, le=60000)
    database_pool_timeout: int = Field(5, ge=1, le=30)
    expose_samples: bool = False
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    supabase_url: str | None = None
    supabase_jwt_audience: str = "authenticated"
    supabase_publishable_key: SecretStr | None = None
    enable_user_writes: bool = False
    development_user_ids: list[UUID] = []
    vercel: bool = False

    def require_hosted_safety(self):
        """Vercel Preview and Production both deny development content access."""
        if not self.vercel:
            return
        if self.content_source != "database" or self.expose_samples or self.development_user_ids:
            raise ValueError(
                "Hosted deployments require database mode, no samples and no development allowlist"
            )
        if self.migration_database_url:
            raise ValueError("Migration credentials must not be configured on hosted runtimes")
        if not self.database_url or not self.supabase_url or not self.cors_origins:
            raise ValueError(
                "Hosted deployments require database, Auth origin and explicit CORS origins"
            )
        url = make_url(self.database_url.get_secret_value())
        import re

        for value in [self.database_url.get_secret_value(), self.supabase_url, *self.cors_origins]:
            if re.search(
                r"YOUR_|REPLACE_|PROJECT_REF|EXACT_POOLER_HOST|URL_ENCODED_PASSWORD",
                value,
                re.IGNORECASE,
            ):
                raise ValueError("Replace production template placeholders before deployment")
        if url.port != 6543:
            raise ValueError(
                "Hosted DATABASE_URL must use the Supabase transaction pooler on port 6543"
            )
        from urllib.parse import urlsplit

        for origin in [self.supabase_url, *self.cors_origins]:
            host = urlsplit(origin).hostname or ""
            if (
                not origin.startswith("https://")
                or host in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
                or host.startswith("127.")
                or host.endswith(".localhost")
            ):
                raise ValueError(
                    "Hosted Auth/CORS configuration requires HTTPS origins without loopback hosts"
                )

    @model_validator(mode="after")
    def hosted_safety(self):
        self.require_hosted_safety()
        return self

    @field_validator("supabase_publishable_key")
    @classmethod
    def public_auth_key(cls, value):
        if value is None:
            return value
        import jwt

        key = value.get_secret_value()
        if key.startswith("sb_publishable_"):
            return value
        try:
            if jwt.decode(key, options={"verify_signature": False}).get("role") == "anon":
                return value
        except jwt.PyJWTError:
            pass
        raise ValueError("Use a public publishable/anon key, never a server secret")

    @field_validator("supabase_url")
    @classmethod
    def auth_origin(cls, value):
        if value is None:
            return value
        from urllib.parse import urlsplit

        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            raise ValueError("SUPABASE_URL must be an exact HTTPS project origin")
        return value.rstrip("/")

    @field_validator("database_url", "migration_database_url")
    @classmethod
    def valid_database_url(cls, value: SecretStr | None):
        if value is None:
            return value
        try:
            url = make_url(value.get_secret_value())
            valid = (
                url.drivername == "postgresql+psycopg"
                and url.host
                and url.database
                and url.username
                and url.password
                and url.port in (None, 5432, 6543)
            )
        except (ArgumentError, ValueError, TypeError):
            valid = False
        if not valid:
            raise ValueError(
                "Use a complete postgresql+psycopg URL; encode reserved password characters"
            )
        return value

    @field_validator("cors_origins")
    @classmethod
    def exact_origins(cls, values: list[str]):
        from urllib.parse import urlsplit

        for value in values:
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or "*" in value
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username is not None
                or parsed.password is not None
            ):
                raise ValueError("CORS_ORIGINS must contain exact HTTP(S) origins without paths")
        return values


@lru_cache
def get_settings() -> Settings:
    return Settings()


if __name__ == "__main__":
    # str(ValidationError) is safe with hide_input_in_errors; never print a settings dump.
    try:
        settings = get_settings()
        print(
            f"Configuration valid; content_source={settings.content_source}; "
            f"database_url_set={settings.database_url is not None}; no connection attempted"
        )
    except ValueError:
        raise SystemExit(
            "Configuration invalid. Check URL format, bounds and exact CORS origins locally."
        )
