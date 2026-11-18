from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class KanjiRecord(Base):
    __tablename__ = "kanjis"
    __table_args__ = (CheckConstraint("length(character) = 1", name="single_character"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    character: Mapped[str] = mapped_column(String(1), unique=True)
    meaning_th: Mapped[str] = mapped_column(String(500))
    readings: Mapped[dict] = mapped_column(JSON)
    review_status: Mapped[str] = mapped_column(String(30), default="needs_review")
    source: Mapped[dict] = mapped_column(JSON)
    romaji: Mapped[str] = mapped_column(String(100), default="", server_default="")
    strokes: Mapped[int | None] = mapped_column(Integer)
    jlpt_estimate: Mapped[int | None] = mapped_column(Integer)
    note_th: Mapped[str] = mapped_column(String(2000), default="", server_default="")
    access_tier: Mapped[str] = mapped_column(
        String(20), default="private", server_default="private"
    )


class LessonRecord(Base):
    __tablename__ = "lessons"
    __table_args__ = (CheckConstraint("chapter BETWEEN 1 AND 30", name="chapter_range"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    chapter: Mapped[int] = mapped_column(Integer, unique=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    title_th: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(30), default="needs_review", index=True)
    summary_th: Mapped[str] = mapped_column(String(1000), default="", server_default="")
    anchors: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    # Metadata may be displayed without making private lesson contents available.
    catalog_visible: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    introduction_th: Mapped[str] = mapped_column(String(4000), default="", server_default="")
    provenance: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    access_tier: Mapped[str] = mapped_column(
        String(20), default="private", server_default="private"
    )


class Component(Base):
    __tablename__ = "components"
    id: Mapped[int] = mapped_column(primary_key=True)
    glyph: Mapped[str] = mapped_column(String(20), unique=True)
    label_th: Mapped[str] = mapped_column(String(200))
    classification: Mapped[str] = mapped_column(String(30))
    source: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="needs_review")


class KanjiComponent(Base):
    __tablename__ = "kanji_components"
    kanji_id: Mapped[int] = mapped_column(ForeignKey("kanjis.id"), primary_key=True)
    component_id: Mapped[int] = mapped_column(ForeignKey("components.id"), primary_key=True)
    position: Mapped[str] = mapped_column(String(30), primary_key=True)
    explanation_th: Mapped[str] = mapped_column(String(2000))


class KanjiRelation(Base):
    __tablename__ = "kanji_relations"
    __table_args__ = (
        UniqueConstraint("source_id", "target_id", "relation_type"),
        CheckConstraint("source_id <> target_id", name="relation_distinct_glyphs"),
        CheckConstraint(
            "relation_type IN ('visual_similarity', 'same_component', "
            "'mnemonic', 'historical_etymology', 'phonetic')",
            name="relation_kind",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("kanjis.id"), index=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("kanjis.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(30))
    directed: Mapped[bool] = mapped_column(Boolean, default=False)
    explanation_th: Mapped[str] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(String(30), default="needs_review")
    provenance: Mapped[dict] = mapped_column(JSON)


class Vocabulary(Base):
    __tablename__ = "vocabularies"
    __table_args__ = (UniqueConstraint("written_form", "reading"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    written_form: Mapped[str] = mapped_column(String(150), index=True)
    reading: Mapped[str] = mapped_column(String(200), index=True)
    meaning_th: Mapped[str] = mapped_column(String(1000))
    romaji: Mapped[str] = mapped_column(String(300), default="")
    usage_notes: Mapped[str] = mapped_column(String(2000), default="")
    status: Mapped[str] = mapped_column(String(30), default="needs_review")
    provenance: Mapped[dict] = mapped_column(JSON)
    access_tier: Mapped[str] = mapped_column(String(20), default="private")


class VocabularyKanji(Base):
    __tablename__ = "vocabulary_kanjis"
    vocabulary_id: Mapped[int] = mapped_column(ForeignKey("vocabularies.id"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    kanji_id: Mapped[int] = mapped_column(ForeignKey("kanjis.id"), index=True)


class LessonVocabulary(Base):
    __tablename__ = "lesson_vocabularies"
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), primary_key=True)
    vocabulary_id: Mapped[int] = mapped_column(ForeignKey("vocabularies.id"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer)


class VisualAsset(Base):
    __tablename__ = "visual_assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_key: Mapped[str] = mapped_column(String(200), unique=True)
    path: Mapped[str] = mapped_column(String(500))
    description_th: Mapped[str] = mapped_column(String(1000))
    license: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(30), default="needs_review")
    provenance: Mapped[dict] = mapped_column(JSON)


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    __table_args__ = (UniqueConstraint("lesson_id", "stable_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), index=True)
    stable_key: Mapped[str] = mapped_column(String(100))
    question_type: Mapped[str] = mapped_column(String(40))
    prompt: Mapped[dict] = mapped_column(JSON)
    options: Mapped[list] = mapped_column(JSON)
    answer_key: Mapped[dict] = mapped_column(JSON)
    explanation_th: Mapped[str] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(String(30), default="needs_review")
    provenance: Mapped[dict] = mapped_column(JSON)


class UserProgress(Base):
    __tablename__ = "user_progress"
    __table_args__ = (CheckConstraint("progress BETWEEN 0 AND 100", name="progress_range"),)
    # Supabase JWT sub UUID. Migration adds auth.users FK only on Supabase.
    owner_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), primary_key=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now().astimezone()
    )
    version: Mapped[int] = mapped_column(Integer, default=1)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (UniqueConstraint("owner_id", "submission_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    submission_id: Mapped[UUID] = mapped_column(Uuid)
    question_id: Mapped[int] = mapped_column(ForeignKey("quiz_questions.id"))
    selected_answer: Mapped[dict] = mapped_column(JSON)
    correct: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReviewItem(Base):
    __tablename__ = "review_items"
    __table_args__ = (
        CheckConstraint(
            "(kanji_id IS NOT NULL AND vocabulary_id IS NULL) OR "
            "(kanji_id IS NULL AND vocabulary_id IS NOT NULL)",
            name="one_review_target",
        ),
        CheckConstraint(
            "interval_days BETWEEN 0 AND 90 AND lapses >= 0 AND reviews >= 0",
            name="review_schedule_bounds",
        ),
        UniqueConstraint("owner_id", "kanji_id"),
        UniqueConstraint("owner_id", "vocabulary_id"),
        Index("ix_review_owner_due", "owner_id", "due_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(Uuid)
    kanji_id: Mapped[int | None] = mapped_column(ForeignKey("kanjis.id"))
    vocabulary_id: Mapped[int | None] = mapped_column(ForeignKey("vocabularies.id"))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    interval_days: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    reviews: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)


class LessonKanji(Base):
    __tablename__ = "lesson_kanjis"
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), primary_key=True)
    kanji_id: Mapped[int] = mapped_column(ForeignKey("kanjis.id"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer)


class LessonSection(Base):
    __tablename__ = "lesson_sections"
    __table_args__ = (UniqueConstraint("lesson_id", "position"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(40))
    blocks: Mapped[list] = mapped_column(JSON)
    provenance: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="needs_review")
    access_tier: Mapped[str] = mapped_column(
        String(20), default="private", server_default="private"
    )


class KanjiReading(Base):
    __tablename__ = "kanji_readings"
    __table_args__ = (
        UniqueConstraint("kanji_id", "reading", "kind"),
        CheckConstraint("kind IN ('on', 'kun', 'other')", name="reading_kind"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    kanji_id: Mapped[int] = mapped_column(ForeignKey("kanjis.id"), index=True)
    reading: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(10))
    position: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str] = mapped_column(String(1000), default="")


# Shared editorial constraints are explicit in the generated migration as well.
for _model, _field in [
    (KanjiRecord, "review_status"),
    (LessonRecord, "status"),
    (Component, "status"),
    (Vocabulary, "status"),
    (KanjiRelation, "status"),
    (LessonSection, "status"),
    (VisualAsset, "status"),
    (QuizQuestion, "status"),
]:
    _model.__table__.append_constraint(
        CheckConstraint(
            f"{_field} IN ('draft', 'needs_review', 'verified', 'published', 'sample')",
            name=f"ck_{_model.__tablename__}_status",
        )
    )

for _model in [KanjiRecord, LessonRecord, Vocabulary, LessonSection]:
    _model.__table__.append_constraint(
        CheckConstraint(
            "access_tier IN ('private', 'free', 'premium')",
            name=f"ck_{_model.__tablename__}_access",
        )
    )
