"""Lazy engines and request-scoped sessions. No migrations/seeding at startup."""

from fastapi import HTTPException, Request
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from .config import Settings, get_settings


def create_database_engine(settings: Settings | None = None, *, migration: bool = False) -> Engine:
    settings = settings or get_settings()
    secret = settings.migration_database_url if migration else settings.database_url
    if secret is None:
        raise RuntimeError(
            "Configure MIGRATION_DATABASE_URL" if migration else "Configure DATABASE_URL"
        )
    args = {
        "prepare_threshold": None,
        "connect_timeout": settings.database_connect_timeout,
        "sslmode": settings.database_sslmode,
    }
    if settings.database_sslrootcert:
        args["sslrootcert"] = settings.database_sslrootcert
    options = (
        {"poolclass": NullPool}
        if migration
        else {
            "pool_size": 1,
            "max_overflow": 0,
            "pool_timeout": settings.database_pool_timeout,
            "pool_pre_ping": True,
            "pool_recycle": 300,
        }
    )
    return create_engine(
        secret.get_secret_value(), connect_args=args, hide_parameters=True, echo=False, **options
    )


def read_session(request: Request):
    settings = request.app.state.settings
    if settings.content_source == "sample":
        yield None
        return
    engine = request.app.state.engine
    if engine is None:
        raise HTTPException(503, "Database is not configured")
    with Session(engine, autoflush=False, expire_on_commit=False) as session:
        try:
            # Public routes cannot write even if a future repository accidentally does so.
            if engine.dialect.name == "postgresql":
                session.execute(text("SET TRANSACTION READ ONLY"))
                session.execute(
                    text("SELECT set_config('statement_timeout', :timeout, true)"),
                    {"timeout": str(settings.database_statement_timeout_ms)},
                )
            yield session
        finally:
            session.rollback()


def require_write_authorization(authorized: bool):
    if not authorized:
        raise RuntimeError(
            "Remote database writes are disabled. Explicit owner authorization and "
            "the allow_remote_write opt-in are required before any connection."
        )
