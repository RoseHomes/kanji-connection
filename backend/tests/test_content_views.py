"""Focused UI presentation/visibility tests with synthetic in-memory data only."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import Identity, optional_identity
from app.config import Settings
from app.main import create_app
from app.models import Base, KanjiRecord, LessonKanji, LessonRecord, LessonSection


def identity_provider(value):
    def provide():
        return value

    return provide


@pytest.fixture
def presentation():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    owner = uuid4()
    settings = Settings(
        _env_file=None,
        content_source="database",
        development_user_ids=[owner],
        enable_user_writes=False,
    )
    with Session(engine) as db, db.begin():
        lesson = LessonRecord(
            chapter=2,
            slug="chapter-02",
            title_th="Private fixture",
            status="needs_review",
            anchors=["木"],
            catalog_visible=False,
        )
        db.add(lesson)
        for character in ["木", "林", "森"]:
            row = KanjiRecord(
                character=character,
                meaning_th="fixture",
                readings={"kun": ["き"], "on": []},
                review_status="needs_review",
                source={"kind": "supporting_printed_glyph"} if character == "森" else {},
            )
            db.add(row)
            db.flush()
            if character != "森":
                db.add(LessonKanji(lesson_id=lesson.id, kanji_id=row.id, position=row.id))
        db.add(
            LessonSection(
                lesson_id=lesson.id,
                position=0,
                kind="exercises",
                status="needs_review",
                access_tier="private",
                provenance={"pdf_pages": [24]},
                blocks=[
                    {
                        "exercises": [
                            {"number": 1, "prompt": "fixture", "answer": "secret answer"}
                        ],
                        "answers": ["secret answer"],
                        "answer_c_note": "secret note",
                    },
                    {"kind": "source_page_text", "text": "raw answer key"},
                ],
            )
        )
    app = create_app(settings, engine)
    with TestClient(app) as client:
        yield app, client, owner
    engine.dispose()


def test_private_views_remain_empty_or_denied_without_allowlist(presentation):
    app, client, _ = presentation
    for identity in [None, Identity(uuid4())]:
        app.dependency_overrides[optional_identity] = identity_provider(identity)
        assert client.get("/api/v1/learning/catalog").json() == []
        assert client.get("/api/v1/learning/kanjis").json() == []
        assert client.get("/api/v1/learning/compare?characters=木,林").status_code == 404
        assert client.get("/api/v1/learning/lesson/chapter-02").status_code == 404


def test_private_catalog_search_pagination_and_comparison_preserve_status(presentation):
    app, client, owner = presentation
    app.dependency_overrides[optional_identity] = lambda: Identity(owner)
    catalog = client.get("/api/v1/learning/catalog").json()
    assert catalog[0]["status"] == "needs_review" and catalog[0]["private_development"]
    assert catalog[0]["available_count"] == 2  # Actual links, not one preview anchor.
    assert client.get("/api/v1/learning/catalog?part=6").json() == []
    assert client.get("/api/v1/learning/catalog?q=missing").json() == []
    assert len(client.get("/api/v1/learning/kanjis").json()) == 2  # Supporting-only excluded.
    assert len(client.get("/api/v1/learning/kanjis?offset=1&limit=1").json()) == 1
    assert len(client.get("/api/v1/learning/kanjis?q=き").json()) == 2
    compared = client.get("/api/v1/learning/compare?characters=林,木").json()
    assert [c["character"] for c in compared] == ["林", "木"]
    assert all(c["review_status"] == "needs_review" for c in compared)
    review_cards = client.get("/api/v1/me/review-cards").json()
    assert len(review_cards) == 2 and all(c["private_development"] for c in review_cards)
    assert client.get("/api/v1/learning/compare?characters=木").status_code == 422
    assert client.get("/api/v1/lessons").json() == []  # Public behavior unchanged.


def test_lesson_sections_hide_provenance_without_answer_leaks_or_source_mutation(presentation):
    app, client, owner = presentation
    app.dependency_overrides[optional_identity] = lambda: Identity(owner)
    response = client.get("/api/v1/learning/lesson/chapter-02")
    assert response.status_code == 200
    section = response.json()["sections"][0]
    assert "pdf_pages" not in section and "provenance" not in response.json()
    assert "id" not in response.json()
    assert len(section["blocks"]) == 1 and "answer" not in response.text
    with Session(app.state.engine) as db:
        assert db.query(LessonSection).one().blocks[0]["answers"] == ["secret answer"]
    assert client.get("/api/v1/health").json()["account_writes_enabled"] is False
