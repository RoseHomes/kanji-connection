import pytest
from alembic import command
from sqlalchemy import text
from test_migrations import config


def test_plain_postgres_without_supabase_auth_stays_deny_all(db_engine):
    if db_engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL-only migration branch")
    with db_engine.begin() as connection:
        cfg = config()
        cfg.attributes["connection"] = connection
        command.downgrade(cfg, "0001")
        connection.execute(text("DROP SCHEMA auth CASCADE"))
        command.upgrade(cfg, "head")
        assert (
            connection.scalar(text("SELECT count(*) FROM pg_policies WHERE schemaname='public'"))
            == 0
        )
        assert connection.scalar(
            text("SELECT relrowsecurity FROM pg_class WHERE oid='user_progress'::regclass")
        )
