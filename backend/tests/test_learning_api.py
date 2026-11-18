"""Learning flows run against disposable SQLite / guarded local PostgreSQL only."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.auth import Identity, optional_identity
from app.config import Settings
from app.main import create_app
from app.models import LessonRecord, QuizAttempt, QuizQuestion, ReviewItem, UserProgress
from app.seed import seed

A = UUID("11111111-1111-4111-8111-111111111111")
B = UUID("22222222-2222-4222-8222-222222222222")


@pytest.fixture
def learning_client(db_engine):
    with Session(db_engine) as db, db.begin():
        if db_engine.dialect.name == "postgresql":
            for owner in (A, B):
                db.execute(text("INSERT INTO auth.users(id) VALUES (:id)"), {"id": owner})
        seed(db, include_samples=True)
        lesson = db.scalar(select(LessonRecord).where(LessonRecord.chapter == 2))
        private = db.scalar(select(LessonRecord).where(LessonRecord.chapter == 1))
        for parent, key, kind, status, answer in [
            (lesson, "q-01", "kanji_reading", "sample", {"kind": "sample", "text": "き"}),
            (
                lesson,
                "comparison-c",
                "comparison",
                "sample",
                {"kind": "reference_only", "text": "SOURCE REFERENCE"},
            ),
            (
                private,
                "private-q",
                "reading",
                "needs_review",
                {"kind": "explicit_source", "text": "PRIVATE_SECRET"},
            ),
        ]:
            db.add(
                QuizQuestion(
                    lesson_id=parent.id,
                    stable_key=key,
                    question_type=kind,
                    prompt={"text": "木"},
                    options=[],
                    answer_key=answer,
                    explanation_th="",
                    status=status,
                    provenance={"secret": "never public"},
                )
            )
    settings = Settings(
        _env_file=None, content_source="database", expose_samples=True, enable_user_writes=True
    )
    app = create_app(settings, db_engine)
    owner = {"id": A}
    app.dependency_overrides[optional_identity] = lambda: (
        Identity(owner["id"]) if owner["id"] else None
    )
    with TestClient(app) as client:
        yield client, owner, db_engine, app


def test_owner_scoping_versions_and_server_scheduling(learning_client):
    client, owner, engine, _ = learning_client
    result = client.put(
        "/api/v1/me/progress/chapter-02", json={"progress": 100, "expected_version": 0}
    )
    assert result.status_code == 200 and result.json()["version"] == 1
    assert (
        client.put(
            "/api/v1/me/progress/chapter-02", json={"progress": 0, "expected_version": 0}
        ).status_code
        == 409
    )
    first = client.put("/api/v1/me/reviews/木", json={"knew": True, "expected_version": 0}).json()
    assert first["interval"] == 1 and first["reviews"] == 1
    assert (
        client.put("/api/v1/me/reviews/木", json={"knew": True, "expected_version": 0}).status_code
        == 409
    )
    second = client.put("/api/v1/me/reviews/木", json={"knew": True, "expected_version": 1}).json()
    assert second["interval"] == 2 and second["reviews"] == 2
    lapse = client.put("/api/v1/me/reviews/木", json={"knew": False, "expected_version": 2}).json()
    assert lapse["interval"] == 1 and lapse["lapses"] == 1
    with Session(engine) as db, db.begin():
        r = db.scalar(select(ReviewItem).where(ReviewItem.owner_id == A))
        r.interval_days = 80
    assert (
        client.put("/api/v1/me/reviews/木", json={"knew": True, "expected_version": 3}).json()[
            "interval"
        ]
        == 90
    )
    owner["id"] = B
    dash = client.get("/api/v1/me/dashboard").json()
    assert dash["lessons"] == [] and dash["cards"] == {}
    assert (
        client.put(
            "/api/v1/me/progress/chapter-02", json={"progress": 100, "expected_version": 1}
        ).status_code
        == 409
    )


def test_questions_hide_keys_and_grade_without_trusting_client_scores(learning_client):
    client, owner, engine, _ = learning_client
    questions = client.get("/api/v1/learning/questions/chapter-02")
    assert questions.status_code == 200
    assert "answer_key" not in questions.text and "never public" not in questions.text
    payload = {"submission_id": str(uuid4()), "answer": "き"}
    url = "/api/v1/me/attempts/chapter-02:q-01"
    assert client.post(url, json=payload).json()["correct"] is True
    assert client.post(url, json=payload).status_code == 200
    assert client.post(url, json={**payload, "answer": "wrong"}).status_code == 409
    assert client.post(url, json={**payload, "score": 100}).status_code == 422
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(QuizAttempt)) == 1
    manual = client.post(
        "/api/v1/me/attempts/chapter-02:comparison-c",
        json={"submission_id": str(uuid4()), "answer": "source description"},
    ).json()
    assert manual["correct"] is None
    stats = client.get("/api/v1/me/dashboard").json()["quiz"]
    assert stats["correct"] == 1 and stats["graded"] == 1 and stats["pending"] == 1
    owner["id"] = B
    assert client.get("/api/v1/me/dashboard").json()["quiz"]["graded"] == 0


def test_private_content_is_allowlisted_not_merely_logged_in(learning_client):
    client, owner, _, app = learning_client
    assert client.get("/api/v1/learning/questions/chapter-01").status_code == 404
    app.state.settings.development_user_ids = [A]
    assert client.get("/api/v1/learning/questions/chapter-01").status_code == 200
    owner["id"] = B
    assert client.get("/api/v1/learning/questions/chapter-01").status_code == 404
    owner["id"] = None
    assert client.get("/api/v1/learning/questions/chapter-01").status_code == 404
    assert client.get("/api/v1/me/dashboard").status_code == 401


def test_guest_sync_requires_complete_choices_and_detects_stale_cloud(learning_client):
    client, _, engine, _ = learning_client
    client.put("/api/v1/me/reviews/木", json={"knew": True, "expected_version": 0})
    guest = {
        "cards": {
            "木": {
                "interval": 8,
                "due": (datetime.now(timezone.utc) + timedelta(days=8)).isoformat(),
                "reviews": 4,
                "lapses": 0,
            }
        },
        "lessons": {"chapter-02": 100},
        "attempts": [
            {"submission_id": str(uuid4()), "question_key": "chapter-02:q-01", "answer": "き"}
        ],
    }
    preview = client.post("/api/v1/me/sync/preview", json=guest).json()
    assert len(preview["rows"]) == 3
    assert (
        client.post(
            "/api/v1/me/sync/apply",
            json={"guest": guest, "snapshot": preview["snapshot"], "choices": {}},
        ).status_code
        == 422
    )
    choices = {r["key"]: "guest" for r in preview["rows"]}
    client.put("/api/v1/me/reviews/木", json={"knew": True, "expected_version": 1})
    stale = client.post(
        "/api/v1/me/sync/apply",
        json={"guest": guest, "snapshot": preview["snapshot"], "choices": choices},
    )
    assert stale.status_code == 409
    fresh = client.post("/api/v1/me/sync/preview", json=guest).json()
    assert (
        client.post(
            "/api/v1/me/sync/apply",
            json={"guest": guest, "snapshot": fresh["snapshot"], "choices": choices},
        ).status_code
        == 200
    )
    dash = client.get("/api/v1/me/dashboard").json()
    assert dash["cards"]["木"]["reviews"] == 4 and dash["cards"]["木"]["interval"] == 8
    assert dash["quiz"]["correct"] == 1 and dash["lessons"][0]["progress"] == 100
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(QuizAttempt)) == 1


def test_keep_cloud_and_unknown_source_preserve_existing_records(learning_client):
    client, _, _, _ = learning_client
    client.put("/api/v1/me/progress/chapter-02", json={"progress": 70, "expected_version": 0})
    guest = {"cards": {}, "lessons": {"chapter-02": 100, "chapter-01": 100}, "attempts": []}
    preview = client.post("/api/v1/me/sync/preview", json=guest).json()
    assert preview["unavailable"] == ["lesson:chapter-01"]
    assert (
        client.post(
            "/api/v1/me/sync/apply",
            json={
                "guest": guest,
                "snapshot": preview["snapshot"],
                "choices": {"lesson:chapter-02": "cloud"},
            },
        ).status_code
        == 200
    )
    assert client.get("/api/v1/me/dashboard").json()["lessons"][0]["progress"] == 70


def test_live_write_switch_and_request_validation(learning_client):
    client, _, engine, app = learning_client
    assert (
        client.put(
            "/api/v1/me/progress/chapter-02",
            json={"progress": 101, "expected_version": 0, "owner_id": str(B)},
        ).status_code
        == 422
    )
    app.state.settings.enable_user_writes = False
    assert client.post("/api/v1/me/sync/preview", json={"cards": {}}).status_code == 200
    assert (
        client.put(
            "/api/v1/me/progress/chapter-02", json={"progress": 100, "expected_version": 0}
        ).status_code
        == 503
    )
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(UserProgress)) == 0


def test_commit_failure_returns_error_before_success_response(learning_client, monkeypatch):
    client, _, engine, _ = learning_client

    def fail_commit(session):
        raise OperationalError("commit", {}, RuntimeError("unavailable"))

    with monkeypatch.context() as scoped:
        scoped.setattr(Session, "commit", fail_commit)
        response = client.put(
            "/api/v1/me/progress/chapter-02", json={"progress": 100, "expected_version": 0}
        )
    assert response.status_code == 503
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(UserProgress)) == 0
