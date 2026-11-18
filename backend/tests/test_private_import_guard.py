"""Offline safety checks for the explicitly authorized staging-import caller."""

import importlib
import importlib.util
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "private_import_guard", ROOT / "scripts/import_private_book.py"
)
caller = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(caller)


@pytest.mark.parametrize("field", ["source_sha256", "bundle_sha256", "editorial_layer_sha256"])
def test_hash_discrepancy_stops_before_connection(monkeypatch, field):
    if not (ROOT / "private/kanji-connection-extracted").exists():
        pytest.skip("Private source absent")
    monkeypatch.setitem(caller.EXPECTED, field, "changed-plan")
    engine = Mock(side_effect=AssertionError("A mismatch must not open a connection"))
    monkeypatch.setattr(caller, "create_database_engine", engine)
    monkeypatch.setattr(
        sys, "argv", ["import_private_book.py", "--commit-authorized-private-import"]
    )
    with pytest.raises(RuntimeError, match="hash differs"):
        caller.main()
    engine.assert_not_called()


def test_revision_discrepancy_stops_before_import():
    connection = Mock()
    connection.scalar.return_value = "0003"
    with pytest.raises(RuntimeError, match="revision differs"):
        caller.schema_check(connection)
    connection.execute.assert_not_called()


def test_learning_harness_restricts_writes_without_touching_database(monkeypatch):
    from fastapi.testclient import TestClient

    from app.config import Settings

    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    harness = importlib.import_module("verify_private_learning")
    plan = {
        "owner_id": "00000000-0000-0000-0000-000000000001",
        "slug": "chapter-01",
        "character": "X",
        "questions": [
            {
                "key": "chapter-01:q-001",
                "answer": "source-answer",
                "submission_id": "00000000-0000-0000-0000-000000000002",
            }
        ],
    }
    settings = Settings(_env_file=None, database_url=None, supabase_url=None)
    with TestClient(harness.restricted_app(settings, plan)) as client:
        assert client.post("/api/v1/me/sync/apply", json={}).status_code == 403
        assert client.put("/api/v1/me/progress/other", json={}).status_code == 403
        assert (
            client.post(
                "/api/v1/me/attempts/chapter-01:q-001",
                json={
                    "answer": "unplanned-answer",
                    "submission_id": plan["questions"][0]["submission_id"],
                },
            ).status_code
            == 403
        )
        # Correctly scoped bodies still require the real verified actor; no auth bypass.
        assert (
            client.put(
                "/api/v1/me/progress/chapter-01", json={"progress": 50, "expected_version": 0}
            ).status_code
            == 401
        )
