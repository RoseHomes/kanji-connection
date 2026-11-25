from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
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


class ExampleSentence(Base):
    __tablename__ = "example_sentences"
    __table_args__ = (
        UniqueConstraint("text_ja", "reading"),
        CheckConstraint(
            "status <> 'published' OR (length(trim(text_ja)) > 0 AND length(trim(meaning_th)) > 0)",
            name="ck_sentences_published_text",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    text_ja: Mapped[str] = mapped_column(String(500))
    reading: Mapped[str] = mapped_column(String(400), server_default="")
    meaning_th: Mapped[str] = mapped_column(Text)
    usage_notes_th: Mapped[str] = mapped_column(Text, server_default="")
    status: Mapped[str] = mapped_column(String(30), server_default="draft")
    access_tier: Mapped[str] = mapped_column(String(20), server_default="private")
    provenance: Mapped[dict] = mapped_column(JSON, server_default="{}")


class JLPTReferenceRelease(Base):
    __tablename__ = "jlpt_reference_releases"
    __table_args__ = (
        UniqueConstraint("source_key", "version"),
        CheckConstraint(
            "length(trim(source_key)) > 0 AND length(trim(version)) > 0 "
            "AND length(trim(source_url)) > 0 AND length(trim(license)) > 0 "
            "AND length(trim(attribution)) > 0",
            name="ck_jlpt_release_metadata",
        ),
        CheckConstraint("manifest_sha256 ~ '^[0-9a-f]{64}$'", name="ck_jlpt_manifest_hash").ddl_if(
            dialect="postgresql"
        ),
        CheckConstraint(
            "length(manifest_sha256) = 64 AND manifest_sha256 NOT GLOB '*[^0-9a-f]*'",
            name="ck_jlpt_manifest_hash_sqlite",
        ).ddl_if(dialect="sqlite"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    source_key: Mapped[str] = mapped_column(String(80))
    version: Mapped[str] = mapped_column(String(120))
    source_url: Mapped[str] = mapped_column(String(500))
    license: Mapped[str] = mapped_column(String(120))
    attribution: Mapped[str] = mapped_column(Text)
    manifest_sha256: Mapped[str] = mapped_column(String(64))
    manifest: Mapped[dict] = mapped_column(JSON)


class JLPTAssignment(Base):
    __tablename__ = "jlpt_assignments"
    __table_args__ = (
        UniqueConstraint("release_id", "reference_key"),
        CheckConstraint("level BETWEEN 1 AND 5", name="ck_jlpt_assignment_level"),
        CheckConstraint(
            "(kanji_id IS NOT NULL) <> (vocabulary_id IS NOT NULL)",
            name="ck_jlpt_assignment_target",
        ),
        Index("ix_jlpt_assignments_release_level", "release_id", "level"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    release_id: Mapped[int] = mapped_column(ForeignKey("jlpt_reference_releases.id"))
    reference_key: Mapped[str] = mapped_column(String(200))
    level: Mapped[int] = mapped_column(Integer)
    kanji_id: Mapped[int | None] = mapped_column(ForeignKey("kanjis.id"))
    vocabulary_id: Mapped[int | None] = mapped_column(ForeignKey("vocabularies.id"))
    match_provenance: Mapped[dict] = mapped_column(JSON)


def _slug_constraints(column, name):
    return (
        CheckConstraint(f"{column} ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name=name).ddl_if(
            dialect="postgresql"
        ),
        CheckConstraint(
            f"length({column}) BETWEEN 1 AND 80 AND {column} NOT GLOB '*[^a-z0-9-]*' "
            f"AND {column} NOT GLOB '-*' AND {column} NOT GLOB '*-' "
            f"AND {column} NOT GLOB '*--*'",
            name=f"{name}_sqlite",
        ).ddl_if(dialect="sqlite"),
    )


class LearningPath(Base):
    __tablename__ = "learning_paths"
    __table_args__ = (
        UniqueConstraint("kind", "slug"),
        *_slug_constraints("slug", "ck_learning_path_slug"),
        CheckConstraint(
            "(kind = 'category' AND jlpt_level IS NULL AND jlpt_release_id IS NULL) "
            "OR (kind = 'jlpt' AND jlpt_level IS NOT NULL AND jlpt_level BETWEEN 1 AND 5 "
            "AND jlpt_release_id IS NOT NULL)",
            name="ck_learning_path_kind_level",
        ),
        CheckConstraint("sort_order >= 0", name="ck_learning_path_order"),
        Index(
            "ix_learning_paths_visible_order", "kind", "status", "access_tier", "sort_order", "id"
        ),
        Index("ix_learning_paths_jlpt_release", "jlpt_release_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))
    slug: Mapped[str] = mapped_column(String(80))
    title_th: Mapped[str] = mapped_column(String(300))
    summary_th: Mapped[str] = mapped_column(Text, server_default="")
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    status: Mapped[str] = mapped_column(String(30), server_default="draft")
    access_tier: Mapped[str] = mapped_column(String(20), server_default="private")
    jlpt_level: Mapped[int | None] = mapped_column(Integer)
    jlpt_release_id: Mapped[int | None] = mapped_column(ForeignKey("jlpt_reference_releases.id"))


class LearningUnit(Base):
    __tablename__ = "learning_units"
    __table_args__ = (
        UniqueConstraint("path_id", "unit_key"),
        UniqueConstraint("path_id", "id"),
        *_slug_constraints("unit_key", "ck_learning_unit_key"),
        CheckConstraint("sort_order >= 0", name="ck_learning_unit_order"),
        Index("ix_learning_units_visible_order", "path_id", "status", "sort_order", "id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    path_id: Mapped[int] = mapped_column(ForeignKey("learning_paths.id"))
    unit_key: Mapped[str] = mapped_column(String(80))
    title_th: Mapped[str] = mapped_column(String(300))
    intro_th: Mapped[str] = mapped_column(Text, server_default="")
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    status: Mapped[str] = mapped_column(String(30), server_default="draft")


class LearningPathItem(Base):
    __tablename__ = "learning_path_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["path_id", "unit_id"], ["learning_units.path_id", "learning_units.id"]
        ),
        CheckConstraint(
            "CASE WHEN kanji_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN vocabulary_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN sentence_id IS NULL THEN 0 ELSE 1 END = 1",
            name="ck_learning_path_item_target",
        ),
        CheckConstraint("sort_order >= 0", name="ck_learning_path_item_order"),
        CheckConstraint(
            "NOT required OR unit_id IS NOT NULL", name="ck_learning_path_item_required"
        ),
        Index("ix_learning_path_items_order", "path_id", "unit_id", "sort_order", "id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    path_id: Mapped[int] = mapped_column(ForeignKey("learning_paths.id"))
    unit_id: Mapped[int | None] = mapped_column(Integer)
    kanji_id: Mapped[int | None] = mapped_column(ForeignKey("kanjis.id"))
    vocabulary_id: Mapped[int | None] = mapped_column(ForeignKey("vocabularies.id"))
    sentence_id: Mapped[int | None] = mapped_column(ForeignKey("example_sentences.id"))
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    required: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    context_note_th: Mapped[str] = mapped_column(Text, server_default="")


for _table, _scope, _targets in [
    (JLPTAssignment, ("release_id", "level"), ("kanji_id", "vocabulary_id")),
    (LearningPathItem, ("path_id",), ("kanji_id", "vocabulary_id", "sentence_id")),
]:
    for _target in _targets:
        _predicate = text(f"{_target} IS NOT NULL")
        _prefix = "jlpt_assignments" if _table is JLPTAssignment else "learning_path_items"
        Index(
            f"uq_{_prefix}_{_target}",
            *(_table.__table__.c[c] for c in (*_scope, _target)),
            unique=True,
            postgresql_where=_predicate,
            sqlite_where=_predicate,
        )
        Index(
            f"ix_{_prefix}_{_target}",
            _table.__table__.c[_target],
            _table.__table__.c[_scope[0]],
            postgresql_where=_predicate,
            sqlite_where=_predicate,
        )

_jlpt_path = text("kind = 'jlpt'")
Index(
    "uq_learning_paths_jlpt_level",
    LearningPath.jlpt_level,
    unique=True,
    postgresql_where=_jlpt_path,
    sqlite_where=_jlpt_path,
)


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
    (ExampleSentence, "status"),
    (LearningPath, "status"),
    (LearningUnit, "status"),
]:
    _model.__table__.append_constraint(
        CheckConstraint(
            f"{_field} IN ('draft', 'needs_review', 'verified', 'published', 'sample')",
            name=f"ck_{_model.__tablename__}_status",
        )
    )

for _model in [KanjiRecord, LessonRecord, Vocabulary, LessonSection, ExampleSentence, LearningPath]:
    _model.__table__.append_constraint(
        CheckConstraint(
            "access_tier IN ('private', 'free', 'premium')",
            name=f"ck_{_model.__tablename__}_access",
        )
    )
