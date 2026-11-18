from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text


def config():
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    return config


def test_online_migration_refuses_without_opt_in(monkeypatch):
    import app.database

    def forbidden(*args, **kwargs):
        raise AssertionError("Should not construct a remote engine")

    monkeypatch.setattr(app.database, "create_database_engine", forbidden)
    with pytest.raises(RuntimeError, match="Remote database writes are disabled"):
        command.upgrade(config(), "head")


def test_migration_upgrade_downgrade_and_metadata_alignment(db_engine):
    if db_engine.dialect.name != "postgresql":
        pytest.skip("Alembic migration targets PostgreSQL")
    with db_engine.begin() as connection:
        cfg = config()
        cfg.attributes["connection"] = connection
        command.check(cfg)
        command.downgrade(cfg, "0001")
        connection.execute(
            text(
                "INSERT INTO kanjis(character,meaning_th,readings,review_status,source) "
                "VALUES ('木','EXISTING_ROW','{}','needs_review','{}')"
            )
        )
        command.upgrade(cfg, "head")
        row = connection.execute(
            text("SELECT meaning_th,access_tier FROM kanjis WHERE character='木'")
        ).one()
        assert row == ("EXISTING_ROW", "private")
        command.upgrade(cfg, "head")
        assert connection.scalar(text("SELECT count(*) FROM kanjis")) == 1
        command.check(cfg)
        indexes = inspect(connection).get_indexes("review_items")
        assert "ix_review_owner_due" in {i["name"] for i in indexes}


def test_offline_migration_generates_postgres_sql_without_connection(tmp_path):
    import io

    buffer = io.StringIO()
    cfg = config()
    cfg.output_buffer = buffer
    command.upgrade(cfg, "head", sql=True)
    sql = buffer.getvalue()
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY owner_scope" in sql
    assert "CREATE TABLE user_progress" in sql
    assert "ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY" in sql
    assert "REVOKE ALL PRIVILEGES ON TABLE public.%I FROM PUBLIC" in sql
