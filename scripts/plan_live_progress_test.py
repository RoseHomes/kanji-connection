"""Prepare a seven-row plan and rehearse locally. No live-write mode exists."""

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.auth import Identity
from app.catalog import SAMPLES
from app.config import Settings
from app.learning import Learning
from app.models import (
    Base,
    KanjiRecord,
    LessonKanji,
    LessonRecord,
    QuizAttempt,
    QuizQuestion,
    ReviewItem,
    UserProgress,
)


def main():
    folder = ROOT / "private/live-progress-plan"
    preflight = json.loads((folder / "preflight.json").read_text("utf-8"))
    auth = json.loads((ROOT / "private/live-auth-test/state.json").read_text("utf-8"))
    assert preflight["read_only"] and preflight["revision"] == "0002"
    assert all(v == 0 for v in preflight["counts"].values())
    assert (
        preflight["dedicated_account_exists"]
        and preflight["dedicated_account_matches"]
        and preflight["dedicated_account_confirmed"]
    )
    assert not preflight["account_writes_enabled"]
    path = folder / "plan.json"
    if path.exists():
        plan = json.loads(path.read_text("utf-8"))
        assert not plan.get("cancelled"), (
            "Temporary fixture plan was cancelled by the owner"
        )
        assert plan["owner_id"] == auth["user_id"]
    else:
        run = str(uuid4())
        slug = "integration-progress-" + run[:8]
        marker = {
            "kind": "isolated_progress_fixture",
            "run_id": run,
            "book_content": False,
        }
        sample = SAMPLES[0]
        plan = {
            "schema_version": 1,
            "approved": False,
            "live_writes_executed": False,
            "run_id": run,
            "owner_id": auth["user_id"],
            "slug": slug,
            "submission_id": str(uuid4()),
            "comparison_owner_id": str(uuid4()),
            "created_at": datetime.now(UTC).isoformat(),
            "fixture_rows": [
                {
                    "table": "lessons",
                    "values": {
                        "chapter": 2,
                        "slug": slug,
                        "title_th": "Private integration fixture - independent sample",
                        "summary_th": "Temporary persistence test; not book content.",
                        "introduction_th": "One independent sample only.",
                        "anchors": [sample.character],
                        "catalog_visible": False,
                        "status": "needs_review",
                        "access_tier": "private",
                        "provenance": marker,
                    },
                },
                {
                    "table": "kanjis",
                    "values": {
                        "character": sample.character,
                        "meaning_th": sample.meaning_th,
                        "readings": {"on": sample.onyomi, "kun": sample.kunyomi},
                        "romaji": sample.romaji,
                        "strokes": sample.strokes,
                        "jlpt_estimate": None,
                        "note_th": "Independent test fixture only.",
                        "review_status": "needs_review",
                        "access_tier": "private",
                        "source": {**marker, "url": sample.source_url},
                    },
                },
                {
                    "table": "lesson_kanjis",
                    "values": {
                        "lesson_id": "@lesson.id",
                        "kanji_id": "@kanji.id",
                        "position": 0,
                    },
                },
                {
                    "table": "quiz_questions",
                    "values": {
                        "lesson_id": "@lesson.id",
                        "stable_key": "read-ki",
                        "question_type": "kanji_reading",
                        "prompt": {
                            "text": "Write the independent sample reading (romaji: ki) for "
                            + sample.character
                            + " in hiragana."
                        },
                        "options": [],
                        "answer_key": {"kind": "sample", "text": sample.kunyomi[0]},
                        "explanation_th": "Independent reading sample; not a book question.",
                        "status": "needs_review",
                        "provenance": {**marker, "url": sample.source_url},
                    },
                },
            ],
            "owned_rows": [
                {
                    "table": "user_progress",
                    "identity": {
                        "owner_id": "@test_account",
                        "lesson_id": "@lesson.id",
                    },
                    "create": {
                        "progress": 50,
                        "version": 1,
                        "completed_at": None,
                        "updated_at": "@server_time",
                    },
                    "update_once": {
                        "progress": 100,
                        "version": 2,
                        "completed_at": "@server_time",
                        "updated_at": "@server_time",
                    },
                },
                {
                    "table": "review_items",
                    "identity": {
                        "owner_id": "@test_account",
                        "kanji_id": "@kanji.id",
                        "vocabulary_id": None,
                    },
                    "create": {
                        "interval_days": 1,
                        "reviews": 1,
                        "lapses": 0,
                        "version": 1,
                        "due_at": "@first_server_time_plus_1_day",
                    },
                    "update_once": {
                        "interval_days": 2,
                        "reviews": 2,
                        "lapses": 0,
                        "version": 2,
                        "due_at": "@second_server_time_plus_2_days",
                    },
                },
                {
                    "table": "quiz_attempts",
                    "identity": {
                        "owner_id": "@test_account",
                        "submission_id": "@planned_submission",
                        "question_id": "@question.id",
                    },
                    "create": {
                        "correct": True,
                        "selected_answer": {
                            "answer": sample.kunyomi[0],
                            "grade_status": "graded",
                            "result": {
                                "correct": True,
                                "status": "graded",
                                "expected": sample.kunyomi[0],
                                "explanation": "Independent reading sample; not a book question.",
                            },
                        },
                        "created_at": "@server_time",
                    },
                    "update_once": None,
                },
            ],
            "create_counts": {
                "lessons": 1,
                "kanjis": 1,
                "lesson_kanjis": 1,
                "quiz_questions": 1,
                "user_progress": 1,
                "review_items": 1,
                "quiz_attempts": 1,
            },
            "update_counts": {"user_progress": 1, "review_items": 1},
            "cleanup_counts": {
                "quiz_attempts": 1,
                "review_items": 1,
                "user_progress": 1,
                "lesson_kanjis": 1,
                "quiz_questions": 1,
                "kanjis": 1,
                "lessons": 1,
            },
            "all_other_tables": {"created": 0, "updated": 0, "deleted": 0},
            "account_cleanup": "retain account; no account deletion or reset",
            "cleanup_scope": "captured primary keys + exact run marker + owner/submission references; no cascade, truncate, reset or broad deletes",
        }
        path.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    # This rehearsal cannot be redirected to PostgreSQL: the engine URL is literal.
    engine = create_engine("sqlite:///:memory:")
    assert engine.dialect.name == "sqlite"

    @event.listens_for(engine, "connect")
    def constraints(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    mapping = {
        "lessons": LessonRecord,
        "kanjis": KanjiRecord,
        "lesson_kanjis": LessonKanji,
        "quiz_questions": QuizQuestion,
    }
    ids = {}
    rows = []
    with Session(engine) as db, db.begin():
        for row in plan["fixture_rows"]:
            values = {
                key: ids[value]
                if isinstance(value, str) and value.startswith("@")
                else value
                for key, value in row["values"].items()
            }
            record = mapping[row["table"]](**values)
            db.add(record)
            db.flush()
            rows.append(record)
            if row["table"] == "lessons":
                ids["@lesson.id"] = record.id
            if row["table"] == "kanjis":
                ids["@kanji.id"] = record.id
            if row["table"] == "quiz_questions":
                ids["@question.id"] = record.id
    owner = UUID(plan["owner_id"])
    other = UUID(plan["comparison_owner_id"])
    settings = Settings(
        _env_file=None, content_source="database", development_user_ids=[owner, other]
    )
    with Session(engine) as db, db.begin():
        service = Learning(db, settings, Identity(owner))
        assert service.progress(plan["slug"], 50, 0) == {"progress": 50, "version": 1}
        assert service.progress(plan["slug"], 100, 1) == {"progress": 100, "version": 2}
        first = service.review(SAMPLES[0].character, True, 0)
        second = service.review(SAMPLES[0].character, True, 1)
        assert (
            first["interval"] == 1
            and second["interval"] == 2
            and second["version"] == 2
        )
        qkey = plan["slug"] + ":read-ki"
        submission = UUID(plan["submission_id"])
        assert (
            service.attempt(qkey, submission, SAMPLES[0].kunyomi[0])["correct"] is True
        )
        assert (
            service.attempt(qkey, submission, SAMPLES[0].kunyomi[0])["correct"] is True
        )
        for operation in [
            lambda: service.progress(plan["slug"], 0, 0),
            lambda: service.review(SAMPLES[0].character, False, 0),
        ]:
            try:
                operation()
            except HTTPException as exc:
                assert exc.status_code == 409
            else:
                raise AssertionError("Stale version accepted")
    with Session(engine) as fresh:
        owner_view = Learning(fresh, settings, Identity(owner)).dashboard()
        assert (
            owner_view["lessons"][0]["progress"] == 100
            and owner_view["lessons"][0]["version"] == 2
        )
        assert owner_view["cards"][SAMPLES[0].character]["reviews"] == 2
        assert owner_view["quiz"]["correct"] == owner_view["quiz"]["graded"] == 1
        other_service = Learning(fresh, settings, Identity(other))
        assert (
            other_service.lesson(plan["slug"]) is not None
        )  # same content visibility; isolates owner filtering
        other_view = other_service.dashboard()
        assert (
            other_view["lessons"] == []
            and other_view["cards"] == {}
            and other_view["quiz"]["graded"] == 0
        )
        counts = {
            table.name: fresh.scalar(select(func.count()).select_from(table))
            for table in Base.metadata.sorted_tables
        }
        assert sum(counts.values()) == 7
    with Session(engine) as db, db.begin():
        for model in [
            QuizAttempt,
            ReviewItem,
            UserProgress,
            LessonKanji,
            QuizQuestion,
            KanjiRecord,
            LessonRecord,
        ]:
            record = db.scalar(select(model))
            assert record is not None
            # In this isolated rehearsal every table has exactly one test row.
            db.delete(record)
            db.flush()
    with Session(engine) as fresh:
        assert all(
            fresh.scalar(select(func.count()).select_from(table)) == 0
            for table in Base.metadata.sorted_tables
        )
    engine.dispose()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    report = {
        "mode": "in_memory_sqlite_only",
        "plan_sha256": digest,
        "created_counts": {k: v for k, v in counts.items() if v},
        "updated_rows": 2,
        "duplicate_attempt_added_rows": 0,
        "stale_updates_rejected": True,
        "new_database_session_persistence_passed": True,
        "alternate_owner_filter_passed": True,
        "seven_row_cleanup_passed": True,
        "live_postgresql_writes": 0,
        "authentication_tests_repeated": False,
    }
    (folder / "local-rehearsal.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"run_id": plan["run_id"], "slug": plan["slug"], **report}))


if __name__ == "__main__":
    main()
