import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Base, KanjiRecord, LessonKanji, LessonRecord
from app.seed import seed


@pytest.fixture
def engine():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def test_seed_idempotent_and_not_published(engine):
    with Session(engine) as session:
        seed(session)
        session.commit()
        seed(session)
        session.commit()
        assert session.scalar(select(func.count()).select_from(KanjiRecord)) == 3
        assert session.scalar(select(func.count()).select_from(LessonRecord)) == 30
        assert session.scalar(select(func.count()).select_from(LessonKanji)) == 3
        assert set(session.scalars(select(LessonRecord.status))) == {"needs_review"}


def test_rollback_leaves_no_seed_records(engine):
    with Session(engine) as session:
        seed(session)
        session.rollback()
        assert session.scalar(select(func.count()).select_from(KanjiRecord)) == 0


def test_foreign_key_and_single_glyph_constraints(engine):
    with Session(engine) as session:
        session.add(LessonKanji(lesson_id=999, kanji_id=999, position=0))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        session.add(KanjiRecord(character="彼女", meaning_th="test", readings={}, source={}))
        with pytest.raises(IntegrityError):
            session.commit()
