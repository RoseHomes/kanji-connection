"""Content foundation only. No accounts or user state yet."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade():
    op.create_table(
        "kanjis",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("character", sa.String(1), nullable=False, unique=True),
        sa.Column("meaning_th", sa.String(500), nullable=False),
        sa.Column("readings", sa.JSON(), nullable=False),
        sa.Column("review_status", sa.String(30), nullable=False),
        sa.Column("source", sa.JSON(), nullable=False),
        sa.CheckConstraint("length(character) = 1", name="single_character"),
    )
    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chapter", sa.Integer(), nullable=False, unique=True),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("title_th", sa.String(300), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.CheckConstraint("chapter BETWEEN 1 AND 30", name="chapter_range"),
    )
    op.create_index("ix_lessons_status", "lessons", ["status"])
    op.create_table(
        "lesson_kanjis",
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id"), primary_key=True),
        sa.Column("kanji_id", sa.Integer(), sa.ForeignKey("kanjis.id"), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    op.create_table(
        "lesson_sections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("blocks", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.UniqueConstraint("lesson_id", "position"),
    )
    op.create_index("ix_lesson_sections_lesson_id", "lesson_sections", ["lesson_id"])
    # Deny anonymous Data API access even if an owner runs this migration.
    if op.get_context().dialect.name == "postgresql":
        for table in ["kanjis", "lessons", "lesson_kanjis", "lesson_sections"]:
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade():
    for table in ["lesson_sections", "lesson_kanjis", "lessons", "kanjis"]:
        op.drop_table(table)
