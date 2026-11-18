import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.main import create_app
from app.models import (
    KanjiReading,
    KanjiRecord,
    LessonRecord,
    LessonSection,
    ReviewItem,
    UserProgress,
    Vocabulary,
    VocabularyKanji,
)
from app.seed import seed


@pytest.fixture
def db_client(db_engine):
    with Session(db_engine) as session, session.begin():
        seed(session, include_samples=True)
        for character, state, access in [("人", "draft", "free"), ("本", "published", "premium")]:
            session.add(
                KanjiRecord(
                    character=character,
                    meaning_th="PRIVATE_FIXTURE",
                    readings={},
                    source={"secret": "must-never-leak"},
                    review_status=state,
                    access_tier=access,
                )
            )
        lesson = session.scalar(select(LessonRecord).where(LessonRecord.chapter == 2))
        lesson.title_th = "DB lesson from stored row"
        lesson.provenance = {**lesson.provenance, "secret": "private-path"}
        session.add_all(
            [
                LessonSection(
                    lesson_id=lesson.id,
                    position=0,
                    kind="text",
                    blocks=[{"text": "PUBLIC_BLOCK"}],
                    provenance={"secret": "private"},
                    status="sample",
                    access_tier="free",
                ),
                LessonSection(
                    lesson_id=lesson.id,
                    position=1,
                    kind="text",
                    blocks=[{"text": "PRIVATE_BLOCK"}],
                    provenance={},
                    status="draft",
                    access_tier="free",
                ),
                LessonSection(
                    lesson_id=lesson.id,
                    position=2,
                    kind="text",
                    blocks=[{"text": "PREMIUM_BLOCK"}],
                    provenance={},
                    status="published",
                    access_tier="premium",
                ),
            ]
        )
        wood = session.scalar(select(KanjiRecord).where(KanjiRecord.character == "木"))
        for state, access, form in [
            ("sample", "free", "木"),
            ("draft", "free", "PRIVATE_WORD"),
            ("published", "premium", "PREMIUM_WORD"),
        ]:
            vocab = Vocabulary(
                written_form=form,
                reading="test",
                meaning_th="test fixture",
                status=state,
                access_tier=access,
                provenance={},
            )
            session.add(vocab)
            session.flush()
            session.add(VocabularyKanji(vocabulary_id=vocab.id, position=0, kanji_id=wood.id))
    with TestClient(
        create_app(
            Settings(_env_file=None, content_source="database", expose_samples=True),
            engine=db_engine,
        )
    ) as client:
        yield client


def test_database_api_reads_stored_content_and_filters_private(db_client):
    body = db_client.get("/api/v1/lessons/chapter-02").json()
    assert body["title_th"] == "DB lesson from stored row"
    assert len(body["kanjis"]) == 3
    assert body["sections"] == [
        {"kind": "text", "blocks": [{"text": "PUBLIC_BLOCK"}], "pdf_pages": []}
    ]
    assert "PRIVATE" not in str(body) and "secret" not in str(body)
    assert "PREMIUM" not in str(body)
    assert db_client.get("/api/v1/kanjis/人").status_code == 404
    assert db_client.get("/api/v1/kanjis/本").status_code == 404
    assert db_client.get("/api/v1/compare?characters=木,本").status_code == 404
    assert len(db_client.get("/api/v1/kanjis/木/vocabulary").json()) == 1


def test_database_search_filters_order_and_literal_wildcards(db_client):
    for q, expected in [("ต้นไม้", "木"), ("はやし", "林"), ("mori", "森")]:
        assert db_client.get("/api/v1/search", params={"q": q}).json()[0]["character"] == expected
    assert len(db_client.get("/api/v1/kanjis?q=木").json()) == 3
    assert db_client.get("/api/v1/kanjis?q=%25").json() == []
    assert db_client.get("/api/v1/kanjis?q=_").json() == []
    assert db_client.get("/api/v1/lessons?part=2").json() == []
    assert len(db_client.get("/api/v1/lessons?q=森").json()) == 1
    assert db_client.get("/api/v1/lessons?limit=2&offset=1").json() == []
    assert [k["character"] for k in db_client.get("/api/v1/compare?characters=森,木").json()] == [
        "森",
        "木",
    ]
    assert db_client.get("/api/v1/kanjis/木/relations").json()["related"] == ["林", "森"]


def test_samples_require_opt_in_and_published_free_content_is_readable(db_client, db_engine):
    with Session(db_engine) as session, session.begin():
        wood = session.scalar(select(KanjiRecord).where(KanjiRecord.character == "木"))
        wood.review_status = "published"
    with TestClient(
        create_app(Settings(_env_file=None, content_source="database"), engine=db_engine)
    ) as client:
        assert [k["character"] for k in client.get("/api/v1/kanjis").json()] == ["木"]
        assert client.get("/api/v1/lessons/chapter-02").status_code == 404


def test_seed_preserves_editorial_changes_and_rolls_back(db_engine):
    with Session(db_engine) as session, session.begin():
        seed(session)
        lesson = session.scalar(select(LessonRecord).where(LessonRecord.chapter == 2))
        lesson.title_th = "EDITORIAL TITLE"
        lesson.status = "verified"
    with Session(db_engine) as session, session.begin():
        seed(session, include_samples=True)
        lesson = session.scalar(select(LessonRecord).where(LessonRecord.chapter == 2))
        assert lesson.title_th == "EDITORIAL TITLE" and lesson.status == "verified"
        assert session.scalar(select(func.count()).select_from(KanjiRecord)) == 3
        assert session.scalar(select(func.count()).select_from(KanjiReading)) == 8
    with Session(db_engine) as session:
        record = session.scalar(select(KanjiRecord).where(KanjiRecord.character == "木"))
        record.meaning_th = "rollback"
        session.flush()
        session.rollback()
        assert session.get(KanjiRecord, record.id).meaning_th != "rollback"


def test_batched_queries_do_not_grow_with_character_count(db_client, db_engine):
    statements = []

    def before(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(db_engine, "before_cursor_execute", before)
    try:
        db_client.get("/api/v1/kanjis?limit=1")
        single = len(statements)
        statements.clear()
        db_client.get("/api/v1/kanjis?limit=30")
        assert len(statements) == single
    finally:
        event.remove(db_engine, "before_cursor_execute", before)


def test_progress_and_review_constraints(db_client, db_engine):
    from datetime import datetime, timezone
    from uuid import UUID

    owner = UUID("11111111-1111-1111-1111-111111111111")
    with Session(db_engine) as session:
        lesson_id = session.scalar(select(LessonRecord.id).limit(1))
        session.add(UserProgress(owner_id=owner, lesson_id=lesson_id, progress=101))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
        session.add(ReviewItem(owner_id=owner, due_at=datetime.now(timezone.utc)))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


def test_postgres_rls_policies_and_read_only_requests(db_client, db_engine):
    if db_engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL-only RLS/transaction checks")
    from uuid import UUID

    owner = UUID("11111111-1111-1111-1111-111111111111")
    other = UUID("22222222-2222-2222-2222-222222222222")
    with db_engine.begin() as connection:
        assert connection.scalar(
            text(
                "SELECT bool_and(relrowsecurity) FROM pg_class "
                "WHERE relnamespace='public'::regnamespace AND relkind='r' "
                "AND relname<>'alembic_version'"
            )
        )
        connection.execute(
            text("INSERT INTO auth.users(id) VALUES (:a),(:b)"), {"a": owner, "b": other}
        )
        connection.execute(
            text(
                "INSERT INTO user_progress(owner_id,lesson_id,progress,updated_at,version) "
                "SELECT :owner,id,20,now(),1 FROM lessons WHERE chapter=2"
            ),
            {"owner": owner},
        )
        connection.execute(text("GRANT USAGE ON SCHEMA public,auth TO authenticated"))
        connection.execute(
            text("GRANT SELECT,INSERT,UPDATE,DELETE ON user_progress TO authenticated")
        )
        connection.execute(text("GRANT SELECT ON kanjis TO authenticated"))
        connection.execute(text("SET LOCAL ROLE authenticated"))
        connection.execute(
            text("SELECT set_config('request.jwt.claim.sub',:owner,true)"), {"owner": str(other)}
        )
        assert connection.scalar(text("SELECT count(*) FROM user_progress")) == 0
        assert connection.scalar(text("SELECT count(*) FROM kanjis")) == 0
        connection.execute(
            text("SELECT set_config('request.jwt.claim.sub',:owner,true)"), {"owner": str(owner)}
        )
        assert connection.scalar(text("SELECT count(*) FROM user_progress")) == 1
        with pytest.raises(DBAPIError), connection.begin_nested():
            connection.execute(text("UPDATE user_progress SET owner_id=:other"), {"other": other})
        with pytest.raises(DBAPIError), connection.begin_nested():
            connection.execute(
                text(
                    "INSERT INTO user_progress(owner_id,lesson_id,progress,updated_at,version) "
                    "SELECT :other,lesson_id,10,now(),1 FROM user_progress"
                ),
                {"other": other},
            )
    # Inspect the actual API transaction to prove its READ ONLY setting, not a mock.
    readonly = []

    def check(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("SELECT kanjis."):
            raw = connection.connection.driver_connection
            with raw.cursor() as c:
                c.execute("SHOW transaction_read_only")
                readonly.append(c.fetchone()[0])

    event.listen(db_engine, "before_cursor_execute", check)
    try:
        assert db_client.get("/api/v1/kanjis").status_code == 200
        assert readonly and set(readonly) == {"on"}
    finally:
        event.remove(db_engine, "before_cursor_execute", check)
