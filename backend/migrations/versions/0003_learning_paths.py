"""Add category and JLPT learning paths without migrating book data."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


TABLES = (
    "example_sentences",
    "jlpt_reference_releases",
    "jlpt_assignments",
    "learning_paths",
    "learning_units",
    "learning_path_items",
)


def upgrade():
    op.create_table(
        "example_sentences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("text_ja", sa.String(length=500), nullable=False),
        sa.Column("reading", sa.String(length=400), server_default="", nullable=False),
        sa.Column("meaning_th", sa.Text(), nullable=False),
        sa.Column("usage_notes_th", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("access_tier", sa.String(length=20), server_default="private", nullable=False),
        sa.Column("provenance", sa.JSON(), server_default="{}", nullable=False),
        sa.CheckConstraint(
            "access_tier IN ('private', 'free', 'premium')", name="ck_example_sentences_access"
        ),
        sa.CheckConstraint(
            "status <> 'published' OR (length(trim(text_ja)) > 0 AND length(trim(meaning_th)) > 0)",
            name="ck_sentences_published_text",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'needs_review', 'verified', 'published', 'sample')",
            name="ck_example_sentences_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("text_ja", "reading"),
    )
    op.create_table(
        "jlpt_reference_releases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_key", sa.String(length=80), nullable=False),
        sa.Column("version", sa.String(length=120), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("license", sa.String(length=120), nullable=False),
        sa.Column("attribution", sa.Text(), nullable=False),
        sa.Column("manifest_sha256", sa.String(length=64), nullable=False),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.CheckConstraint("manifest_sha256 ~ '^[0-9a-f]{64}$'", name="ck_jlpt_manifest_hash"),
        sa.CheckConstraint(
            "length(trim(source_key)) > 0 AND length(trim(version)) > 0 AND length(trim(source_url)) > 0 AND length(trim(license)) > 0 AND length(trim(attribution)) > 0",
            name="ck_jlpt_release_metadata",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key", "version"),
    )
    op.create_table(
        "jlpt_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("release_id", sa.Integer(), nullable=False),
        sa.Column("reference_key", sa.String(length=200), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("kanji_id", sa.Integer(), nullable=True),
        sa.Column("vocabulary_id", sa.Integer(), nullable=True),
        sa.Column("match_provenance", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "(kanji_id IS NOT NULL) <> (vocabulary_id IS NOT NULL)",
            name="ck_jlpt_assignment_target",
        ),
        sa.CheckConstraint("level BETWEEN 1 AND 5", name="ck_jlpt_assignment_level"),
        sa.ForeignKeyConstraint(
            ["kanji_id"],
            ["kanjis.id"],
        ),
        sa.ForeignKeyConstraint(
            ["release_id"],
            ["jlpt_reference_releases.id"],
        ),
        sa.ForeignKeyConstraint(
            ["vocabulary_id"],
            ["vocabularies.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("release_id", "reference_key"),
    )
    op.create_index(
        "ix_jlpt_assignments_kanji_id",
        "jlpt_assignments",
        ["kanji_id", "release_id"],
        unique=False,
        postgresql_where=sa.text("kanji_id IS NOT NULL"),
        sqlite_where=sa.text("kanji_id IS NOT NULL"),
    )
    op.create_index(
        "ix_jlpt_assignments_release_level",
        "jlpt_assignments",
        ["release_id", "level"],
        unique=False,
    )
    op.create_index(
        "ix_jlpt_assignments_vocabulary_id",
        "jlpt_assignments",
        ["vocabulary_id", "release_id"],
        unique=False,
        postgresql_where=sa.text("vocabulary_id IS NOT NULL"),
        sqlite_where=sa.text("vocabulary_id IS NOT NULL"),
    )
    op.create_index(
        "uq_jlpt_assignments_kanji_id",
        "jlpt_assignments",
        ["release_id", "level", "kanji_id"],
        unique=True,
        postgresql_where=sa.text("kanji_id IS NOT NULL"),
        sqlite_where=sa.text("kanji_id IS NOT NULL"),
    )
    op.create_index(
        "uq_jlpt_assignments_vocabulary_id",
        "jlpt_assignments",
        ["release_id", "level", "vocabulary_id"],
        unique=True,
        postgresql_where=sa.text("vocabulary_id IS NOT NULL"),
        sqlite_where=sa.text("vocabulary_id IS NOT NULL"),
    )
    op.create_table(
        "learning_paths",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("title_th", sa.String(length=300), nullable=False),
        sa.Column("summary_th", sa.Text(), server_default="", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("access_tier", sa.String(length=20), server_default="private", nullable=False),
        sa.Column("jlpt_level", sa.Integer(), nullable=True),
        sa.Column("jlpt_release_id", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "(kind = 'category' AND jlpt_level IS NULL AND jlpt_release_id IS NULL) OR (kind = 'jlpt' AND jlpt_level IS NOT NULL AND jlpt_level BETWEEN 1 AND 5 AND jlpt_release_id IS NOT NULL)",
            name="ck_learning_path_kind_level",
        ),
        sa.CheckConstraint(
            "access_tier IN ('private', 'free', 'premium')", name="ck_learning_paths_access"
        ),
        sa.CheckConstraint("slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="ck_learning_path_slug"),
        sa.CheckConstraint(
            "status IN ('draft', 'needs_review', 'verified', 'published', 'sample')",
            name="ck_learning_paths_status",
        ),
        sa.CheckConstraint("sort_order >= 0", name="ck_learning_path_order"),
        sa.ForeignKeyConstraint(
            ["jlpt_release_id"],
            ["jlpt_reference_releases.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kind", "slug"),
    )
    op.create_index(
        "ix_learning_paths_jlpt_release", "learning_paths", ["jlpt_release_id"], unique=False
    )
    op.create_index(
        "ix_learning_paths_visible_order",
        "learning_paths",
        ["kind", "status", "access_tier", "sort_order", "id"],
        unique=False,
    )
    op.create_index(
        "uq_learning_paths_jlpt_level",
        "learning_paths",
        ["jlpt_level"],
        unique=True,
        postgresql_where=sa.text("kind = 'jlpt'"),
        sqlite_where=sa.text("kind = 'jlpt'"),
    )
    op.create_table(
        "learning_units",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("path_id", sa.Integer(), nullable=False),
        sa.Column("unit_key", sa.String(length=80), nullable=False),
        sa.Column("title_th", sa.String(length=300), nullable=False),
        sa.Column("intro_th", sa.Text(), server_default="", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'needs_review', 'verified', 'published', 'sample')",
            name="ck_learning_units_status",
        ),
        sa.CheckConstraint("unit_key ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="ck_learning_unit_key"),
        sa.CheckConstraint("sort_order >= 0", name="ck_learning_unit_order"),
        sa.ForeignKeyConstraint(
            ["path_id"],
            ["learning_paths.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("path_id", "id"),
        sa.UniqueConstraint("path_id", "unit_key"),
    )
    op.create_index(
        "ix_learning_units_visible_order",
        "learning_units",
        ["path_id", "status", "sort_order", "id"],
        unique=False,
    )
    op.create_table(
        "learning_path_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("path_id", sa.Integer(), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=True),
        sa.Column("kanji_id", sa.Integer(), nullable=True),
        sa.Column("vocabulary_id", sa.Integer(), nullable=True),
        sa.Column("sentence_id", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("context_note_th", sa.Text(), server_default="", nullable=False),
        sa.CheckConstraint(
            "CASE WHEN kanji_id IS NULL THEN 0 ELSE 1 END + CASE WHEN vocabulary_id IS NULL THEN 0 ELSE 1 END + CASE WHEN sentence_id IS NULL THEN 0 ELSE 1 END = 1",
            name="ck_learning_path_item_target",
        ),
        sa.CheckConstraint(
            "NOT required OR unit_id IS NOT NULL", name="ck_learning_path_item_required"
        ),
        sa.CheckConstraint("sort_order >= 0", name="ck_learning_path_item_order"),
        sa.ForeignKeyConstraint(
            ["kanji_id"],
            ["kanjis.id"],
        ),
        sa.ForeignKeyConstraint(
            ["path_id", "unit_id"],
            ["learning_units.path_id", "learning_units.id"],
        ),
        sa.ForeignKeyConstraint(
            ["path_id"],
            ["learning_paths.id"],
        ),
        sa.ForeignKeyConstraint(
            ["sentence_id"],
            ["example_sentences.id"],
        ),
        sa.ForeignKeyConstraint(
            ["vocabulary_id"],
            ["vocabularies.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_learning_path_items_kanji_id",
        "learning_path_items",
        ["kanji_id", "path_id"],
        unique=False,
        postgresql_where=sa.text("kanji_id IS NOT NULL"),
        sqlite_where=sa.text("kanji_id IS NOT NULL"),
    )
    op.create_index(
        "ix_learning_path_items_order",
        "learning_path_items",
        ["path_id", "unit_id", "sort_order", "id"],
        unique=False,
    )
    op.create_index(
        "ix_learning_path_items_sentence_id",
        "learning_path_items",
        ["sentence_id", "path_id"],
        unique=False,
        postgresql_where=sa.text("sentence_id IS NOT NULL"),
        sqlite_where=sa.text("sentence_id IS NOT NULL"),
    )
    op.create_index(
        "ix_learning_path_items_vocabulary_id",
        "learning_path_items",
        ["vocabulary_id", "path_id"],
        unique=False,
        postgresql_where=sa.text("vocabulary_id IS NOT NULL"),
        sqlite_where=sa.text("vocabulary_id IS NOT NULL"),
    )
    op.create_index(
        "uq_learning_path_items_kanji_id",
        "learning_path_items",
        ["path_id", "kanji_id"],
        unique=True,
        postgresql_where=sa.text("kanji_id IS NOT NULL"),
        sqlite_where=sa.text("kanji_id IS NOT NULL"),
    )
    op.create_index(
        "uq_learning_path_items_sentence_id",
        "learning_path_items",
        ["path_id", "sentence_id"],
        unique=True,
        postgresql_where=sa.text("sentence_id IS NOT NULL"),
        sqlite_where=sa.text("sentence_id IS NOT NULL"),
    )
    op.create_index(
        "uq_learning_path_items_vocabulary_id",
        "learning_path_items",
        ["path_id", "vocabulary_id"],
        unique=True,
        postgresql_where=sa.text("vocabulary_id IS NOT NULL"),
        sqlite_where=sa.text("vocabulary_id IS NOT NULL"),
    )

    if op.get_context().dialect.name == "postgresql":
        for table in TABLES:
            op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"REVOKE ALL PRIVILEGES ON TABLE public.{table} FROM PUBLIC")
            op.execute(f"REVOKE ALL PRIVILEGES ON SEQUENCE public.{table}_id_seq FROM PUBLIC")
            op.execute(f"""
                DO $$ BEGIN
                    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'anon') THEN
                        REVOKE ALL PRIVILEGES ON TABLE public.{table} FROM anon;
                        REVOKE ALL PRIVILEGES ON SEQUENCE public.{table}_id_seq FROM anon;
                    END IF;
                    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticated') THEN
                        REVOKE ALL PRIVILEGES ON TABLE public.{table} FROM authenticated;
                        REVOKE ALL PRIVILEGES ON SEQUENCE public.{table}_id_seq FROM authenticated;
                    END IF;
                END $$;
            """)


def downgrade():
    for table in reversed(TABLES):
        op.drop_table(table)
