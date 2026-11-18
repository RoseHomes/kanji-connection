"""Full existing book, signed sessions and persistence, exclusively in-memory."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.book_bundle import Bundle
from app.book_import import apply_bundle
from app.config import Settings
from app.main import create_app
from app.models import Base, LessonRecord, QuizQuestion


def test_all_450_structured_questions_through_signed_owner_apis():
    path = Path(__file__).resolve().parents[2] / "private/json-content/import-bundle.json"
    if not path.exists():
        pytest.skip("Private prepared book unavailable")
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def constraints(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    owner = uuid4()
    settings = Settings(
        _env_file=None,
        content_source="database",
        enable_user_writes=True,
        supabase_url="https://fixture.example.test",
        development_user_ids=[owner],
    )
    with Session(engine) as db, db.begin():
        apply_bundle(db, Bundle.model_validate_json(path.read_bytes()))
    key = ec.generate_private_key(ec.SECP256R1())

    def headers(subject):
        token = jwt.encode(
            {
                "sub": str(subject),
                "role": "authenticated",
                "aud": "authenticated",
                "iss": settings.supabase_url + "/auth/v1",
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
            },
            key,
            algorithm="ES256",
            headers={"kid": "fixture"},
        )
        return {"Authorization": "Bearer " + token}

    app = create_app(settings, engine)
    app.state.jwks_client = SimpleNamespace(
        get_signing_key_from_jwt=lambda token: SimpleNamespace(key=key.public_key())
    )
    with TestClient(app) as client:
        assert client.get("/api/v1/learning/lessons").json() == []
        assert client.get("/api/v1/learning/lesson/chapter-01").status_code == 404
        assert client.get("/api/v1/learning/lessons", headers=headers(uuid4())).json() == []
        authorization = headers(owner)
        lessons = client.get("/api/v1/learning/lessons", headers=authorization).json()
        detail = client.get("/api/v1/learning/lesson/chapter-01", headers=authorization)
        assert detail.status_code == 200 and len(detail.json()["kanjis"]) == 14
        assert detail.json()["private_development"] is True and "answer_key" not in detail.text
        assert len(lessons) == 30 and all(l["private_development"] for l in lessons)
        for lesson in lessons:
            slug = lesson["slug"]
            response = client.get("/api/v1/learning/questions/" + slug, headers=authorization)
            assert response.status_code == 200 and len(response.json()) == 15
            assert "answer_key" not in response.text and "provenance" not in response.text
            with Session(engine) as db:
                parent = db.scalar(select(LessonRecord).where(LessonRecord.slug == slug))
                questions = list(
                    db.scalars(select(QuizQuestion).where(QuizQuestion.lesson_id == parent.id))
                )
                for q in questions:
                    result = client.post(
                        "/api/v1/me/attempts/" + slug + ":" + q.stable_key,
                        headers=authorization,
                        json={
                            "submission_id": str(uuid4()),
                            "answer": q.answer_key.get("text") or "Source-grounded manual response",
                        },
                    )
                    assert result.status_code == 200, result.text
                    assert result.json()["correct"] is (
                        None if q.answer_key["kind"] == "reference_only" else True
                    )
            assert (
                client.put(
                    "/api/v1/me/progress/" + slug,
                    headers=authorization,
                    json={"progress": 100, "expected_version": 0},
                ).status_code
                == 200
            )
        dashboard = client.get("/api/v1/me/dashboard", headers=authorization).json()
        assert len(dashboard["lessons"]) == 30
        assert (
            dashboard["quiz"]["correct"] == 420
            and dashboard["quiz"]["graded"] == 420
            and dashboard["quiz"]["pending"] == 30
        )
        cards = client.get("/api/v1/me/review-cards", headers=authorization).json()
        assert len(cards) == 313  # supporting-only records are not teaching flashcards
        assert (
            client.put(
                "/api/v1/me/reviews/木",
                headers=authorization,
                json={"knew": True, "expected_version": 0},
            ).json()["interval"]
            == 1
        )
        other = client.get("/api/v1/me/dashboard", headers=headers(uuid4())).json()
        assert other["quiz"]["graded"] == 0 and other["lessons"] == [] and other["cards"] == {}
    engine.dispose()
