import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import StaticPool

from app.models import Base


@pytest.fixture(params=["sqlite", "postgresql"])
def db_engine(request):
    if request.param == "sqlite":
        engine = create_engine(
            "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
        )

        @event.listens_for(engine, "connect")
        def constraints(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(engine)
        yield engine
        engine.dispose()
        return
    raw = os.environ.get("TEST_DATABASE_URL")
    if not raw:
        pytest.skip("Set TEST_DATABASE_URL for isolated local PostgreSQL integration tests")
    url = make_url(raw)
    if (
        url.host != "127.0.0.1"
        or url.database != "kanji_test"
        or url.drivername != "postgresql+psycopg"
        or url.query
    ):
        pytest.fail("Refusing tests outside loopback database kanji_test")
    engine = create_engine(url, hide_parameters=True)
    # This explicitly validated disposable test database is the only reset target.
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        connection.execute(text("DROP SCHEMA IF EXISTS auth CASCADE"))
        connection.execute(text("CREATE SCHEMA auth"))
        connection.execute(text("CREATE TABLE auth.users (id uuid PRIMARY KEY)"))
        connection.execute(
            text("""CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE
            AS $$ SELECT nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$""")
        )
        connection.execute(
            text("""DO $$ BEGIN IF NOT EXISTS (
            SELECT FROM pg_roles WHERE rolname='authenticated') THEN
            CREATE ROLE authenticated NOLOGIN; END IF; END $$""")
        )
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        config.set_main_option(
            "script_location", str(Path(__file__).resolve().parents[1] / "migrations")
        )
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        command.upgrade(config, "head")  # Revision tracking prevents duplicate DDL.
    yield engine
    engine.dispose()
