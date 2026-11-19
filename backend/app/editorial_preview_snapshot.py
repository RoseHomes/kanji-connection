"""Verified private preview mirror, with database-enforced read-only connections.

Only the loopback preview launcher imports this module. Production uses its
existing Supabase connection and authorization paths, unchanged.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, event, insert, text

from .book_bundle import Bundle
from .content_revision import digest
from .database import create_database_engine
from .editorial_sync import TABLES, prepare_updates, snapshot
from .models import Base

ROOT = Path(__file__).resolve().parents[2]


def readonly_engine(path):
    # URI mode=ro prevents a future accidental write even outside read_session.
    engine = create_engine(
        f"sqlite:///file:{path.as_posix()}?mode=ro&uri=true",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def query_only(connection, record):
        connection.execute("PRAGMA query_only=ON")

    return engine


def materialize_snapshot(data, folder):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ("working-" + digest(data)[:16] + ".sqlite3")
    if not path.exists():
        temporary = folder / ("building-" + uuid4().hex + ".sqlite3")
        writer = create_engine("sqlite:///" + temporary.as_posix())
        try:
            Base.metadata.create_all(writer)
            with writer.begin() as connection:
                for name, table in TABLES.items():
                    if data[name]:
                        connection.execute(insert(table), data[name])
        finally:
            writer.dispose()
        temporary.replace(path)
    engine = readonly_engine(path)
    try:
        with engine.connect() as connection:
            if digest(snapshot(connection)) != digest(data):
                raise ValueError("Local preview snapshot differs from verified Supabase data")
    except Exception:
        engine.dispose()
        raise
    return engine


def create_verified_preview_engine(settings):
    if settings.vercel:
        raise ValueError("Local snapshots are forbidden on hosted runtimes")
    manifest = json.loads((ROOT / "private/editorial-working/manifest.json").read_bytes())
    revision = manifest["revision_id"]
    receipt = json.loads((ROOT / f"private/editorial-sync/{revision}/committed.json").read_bytes())
    bundle = Bundle.model_validate_json(
        (ROOT / "private/editorial-working/working-bundle.json").read_bytes()
    )
    if digest(bundle.model_dump()) != manifest["bundle_sha256"]:
        raise ValueError("Working bundle failed its recorded digest")
    remote = create_database_engine(settings)
    try:
        with remote.connect() as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            data = snapshot(connection)
            connection.rollback()
    finally:
        remote.dispose()
    if digest(data) != receipt["after_sha256"]:
        raise ValueError("Supabase changed since the synchronized working edition; preview refused")
    if prepare_updates(data, bundle, revision)["operations"]:
        raise ValueError("Source and Supabase projections differ; preview refused")
    folder = ROOT / "private/editorial-preview/snapshots"
    engine = materialize_snapshot(data, folder)
    (folder / "verification.json").write_text(
        json.dumps(
            {
                "revision_id": revision,
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "snapshot_sha256": digest(data),
                "bundle_sha256": manifest["bundle_sha256"],
                "rows": {name: len(rows) for name, rows in data.items()},
                "supabase_writes": 0,
                "source_projection_changes": 0,
                "database_enforced_read_only": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        "Verified Supabase and working edition; local snapshot is database-enforced read-only.",
        flush=True,
    )
    return engine
