"""Synthetic, isolated public-learning boundaries. Never connects to Supabase."""

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import Identity, optional_identity
from app.config import Settings
from app.main import create_app
from app.models import (
    Base,
    KanjiRecord,
    LessonKanji,
    LessonRecord,
    LessonSection,
    QuizAttempt,
    QuizQuestion,
    ReviewItem,
    UserProgress,
)


@pytest.fixture
def public_app():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db, db.begin():
        for chapter, status, access, visible in [
            (1, "published", "free", True),
            (2, "needs_review", "private", True),
            (3, "published", "premium", True),
            (4, "published", "free", False),
            (5, "sample", "free", True),
        ]:
            db.add(
                LessonRecord(
                    id=chapter,
                    chapter=chapter,
                    slug=f"chapter-{chapter:02}",
                    title_th=f"SYNTHETIC LESSON {chapter}",
                    status=status,
                    access_tier=access,
                    catalog_visible=visible,
                )
            )
        for index, char, status, access in [
            (1, "木", "published", "free"),
            (2, "林", "needs_review", "private"),
            (3, "森", "published", "premium"),
        ]:
            db.add(
                KanjiRecord(
                    id=index,
                    character=char,
                    meaning_th="SYNTHETIC GLOSS",
                    readings={},
                    source={},
                    review_status=status,
                    access_tier=access,
                )
            )
        db.flush()
        db.add_all([LessonKanji(lesson_id=1, kanji_id=i, position=i) for i in [1, 2, 3]])
        db.add(
            LessonSection(
                lesson_id=1,
                position=1,
                kind="exercises",
                status="published",
                access_tier="free",
                provenance={},
                blocks=[
                    {"kind": "source_page_text", "text": "RAW_INTERNAL_TEXT"},
                    {
                        "exercises": [
                            {
                                "number": 1,
                                "prompt": "SYNTHETIC PROMPT",
                                "answer": "HIDDEN_UNTIL_CHECK",
                            }
                        ],
                        "answers": ["HIDDEN_UNTIL_CHECK"],
                    },
                ],
            )
        )
        for parent, status, key in [
            (1, "published", "q-01"),
            (1, "needs_review", "q-private"),
            (2, "published", "q-01"),
            (4, "published", "q-01"),
        ]:
            db.add(
                QuizQuestion(
                    lesson_id=parent,
                    stable_key=key,
                    question_type="reading",
                    prompt={"text": "SYNTHETIC QUESTION"},
                    options=[],
                    answer_key={"kind": "explicit_source", "text": "synthetic-answer"},
                    explanation_th="",
                    status=status,
                    provenance={},
                )
            )
    app = create_app(
        Settings(_env_file=None, content_source="database", enable_user_writes=False), engine
    )
    with TestClient(app) as client:
        yield client, app, engine
    engine.dispose()


def test_only_published_free_visible_lessons_and_cards_are_public(public_app):
    client, _, _ = public_app
    for path in ["/lessons", "/learning/catalog", "/learning/lessons"]:
        response = client.get("/api/v1" + path)
        assert response.status_code == 200
        assert [item["slug"] for item in response.json()] == ["chapter-01"]
    assert [item["character"] for item in client.get("/api/v1/learning/kanjis").json()] == ["木"]
    assert [
        item["character"]
        for item in client.get("/api/v1/learning/lesson/chapter-01").json()["kanjis"]
    ] == ["木"]
    for path in ["/lessons/chapter-01", "/learning/lesson/chapter-01"]:
        body = client.get("/api/v1" + path).text
        assert "RAW_INTERNAL_TEXT" not in body and "HIDDEN_UNTIL_CHECK" not in body
    assert [q["key"] for q in client.get("/api/v1/learning/questions/chapter-01").json()] == [
        "chapter-01:q-01"
    ]


@pytest.mark.parametrize("authenticated", [False, True])
def test_signin_does_not_unlock_unpublished_or_hidden_content(public_app, authenticated):
    client, app, _ = public_app
    if authenticated:
        app.dependency_overrides[optional_identity] = lambda: Identity(
            UUID("00000000-0000-0000-0000-000000000001")
        )
    for slug in ["chapter-02", "chapter-03", "chapter-04", "chapter-05"]:
        for prefix in ["/learning/lesson/", "/learning/questions/", "/lessons/"]:
            assert client.get("/api/v1" + prefix + slug).status_code == 404
    for char in ["林", "森"]:
        assert client.get("/api/v1/kanjis/" + char).status_code == 404
    assert (
        client.post(
            "/api/v1/learning/check/chapter-01:q-private",
            json={"answer": "test", "submission_id": "00000000-0000-0000-0000-000000000001"},
        ).status_code
        == 404
    )


def test_public_grading_never_persists_and_personal_routes_remain_protected(public_app):
    client, app, engine = public_app
    body = {"answer": "synthetic-answer", "submission_id": "00000000-0000-0000-0000-000000000001"}
    result = client.post("/api/v1/learning/check/chapter-01:q-01", json=body)
    assert result.status_code == 200 and result.json()["correct"] is True
    assert result.json()["persisted"] is False
    assert client.get("/api/v1/me/dashboard").status_code == 401
    assert client.get("/api/v1/me/review-cards").status_code == 401
    assert client.post("/api/v1/me/attempts/chapter-01:q-01", json=body).status_code == 401
    app.dependency_overrides[optional_identity] = lambda: Identity(
        UUID("00000000-0000-0000-0000-000000000001")
    )
    assert client.post("/api/v1/me/attempts/chapter-01:q-01", json=body).status_code == 503
    assert (
        client.put(
            "/api/v1/me/progress/chapter-01", json={"progress": 100, "expected_version": 0}
        ).status_code
        == 503
    )
    with Session(engine) as db:
        for model in [QuizAttempt, ReviewItem, UserProgress]:
            assert db.scalar(select(func.count()).select_from(model)) == 0
