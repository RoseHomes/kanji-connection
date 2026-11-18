"""Validate/apply a private bundle only to disposable in-memory SQLite. No remote mode."""

import hashlib
import json
import sys
from pathlib import Path

from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.book_bundle import Bundle
from app.book_import import apply_bundle
from app.models import Base


def main():
    bundle = Bundle.model_validate_json(
        (ROOT / "private/json-content/import-bundle.json").read_text("utf-8")
    )
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def constraints(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        first = apply_bundle(session, bundle)
        counts = {
            table.name: session.scalar(select(func.count()).select_from(table))
            for table in Base.metadata.sorted_tables
        }
        second = apply_bundle(session, bundle)
        if second["inserted"] or second["conflicts"]:
            raise RuntimeError("Idempotency check failed")
        session.rollback()
        if any(
            session.scalar(select(func.count()).select_from(table))
            for table in Base.metadata.sorted_tables
        ):
            raise RuntimeError("Rollback check failed")
    engine.dispose()
    result = {
        "mode": "in_memory_sqlite_only",
        "source_sha256": bundle.source_sha256,
        "bundle_sha256": hashlib.sha256(bundle.model_dump_json().encode()).hexdigest(),
        "editorial_layer_sha256": bundle.editorial_layer_sha256,
        "counts": counts,
        "idempotent": True,
        "rolled_back": True,
        "publication_approved": False,
        "supabase_writes": 0,
        "issues": len(bundle.unresolved_issues),
        "editorial_gaps": len(bundle.gaps),
        "inserted_in_scratch": sum(first["inserted"].values()),
    }
    (ROOT / "private/json-content/import-rehearsal.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
