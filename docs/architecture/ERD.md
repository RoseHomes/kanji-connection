# Learning database ERD

Generated from SQLAlchemy metadata with the
[schema generator](../../scripts/write_erd.py). Migration alignment is tested
with Alembic against isolated PostgreSQL.

The unchanged generator writes the legacy docs/ERD.md compatibility path. Review
and reconcile its output with this canonical diagram; see
[generator maintenance](../guides/PUBLICATION.md#documentation-generators).

```mermaid
erDiagram
  components ||--o{ kanji_components : component_id
  kanjis ||--o{ kanji_components : kanji_id
  kanjis ||--o{ kanji_readings : kanji_id
  kanjis ||--o{ kanji_relations : source_id
  kanjis ||--o{ kanji_relations : target_id
  kanjis ||--o{ lesson_kanjis : kanji_id
  lessons ||--o{ lesson_kanjis : lesson_id
  lessons ||--o{ lesson_sections : lesson_id
  lessons ||--o{ lesson_vocabularies : lesson_id
  vocabularies ||--o{ lesson_vocabularies : vocabulary_id
  lessons ||--o{ quiz_questions : lesson_id
  kanjis ||--o{ review_items : kanji_id
  vocabularies ||--o{ review_items : vocabulary_id
  lessons ||--o{ user_progress : lesson_id
  kanjis ||--o{ vocabulary_kanjis : kanji_id
  vocabularies ||--o{ vocabulary_kanjis : vocabulary_id
  quiz_questions ||--o{ quiz_attempts : question_id
  components {
    integer id PK
    string glyph UK
    string label_th
    string classification
    json source
    string status
  }
  kanjis {
    integer id PK
    string character UK
    string meaning_th
    json readings
    string review_status
    json source
    string romaji
    integer strokes
    integer jlpt_estimate
    string note_th
    string access_tier
  }
  lessons {
    integer id PK
    integer chapter UK
    string slug UK
    string title_th
    string status
    string summary_th
    json anchors
    boolean catalog_visible
    string introduction_th
    json provenance
    string access_tier
  }
  visual_assets {
    integer id PK
    string asset_key UK
    string path
    string description_th
    string license
    string status
    json provenance
  }
  vocabularies {
    integer id PK
    string written_form
    string reading
    string meaning_th
    string romaji
    string usage_notes
    string status
    json provenance
    string access_tier
  }
  kanji_components {
    integer kanji_id PK,FK
    integer component_id PK,FK
    string position PK
    string explanation_th
  }
  kanji_readings {
    integer id PK
    integer kanji_id FK
    string reading
    string kind
    integer position
    string notes
  }
  kanji_relations {
    integer id PK
    integer source_id FK
    integer target_id FK
    string relation_type
    boolean directed
    string explanation_th
    string status
    json provenance
  }
  lesson_kanjis {
    integer lesson_id PK,FK
    integer kanji_id PK,FK
    integer position
  }
  lesson_sections {
    integer id PK
    integer lesson_id FK
    integer position
    string kind
    json blocks
    json provenance
    string status
    string access_tier
  }
  lesson_vocabularies {
    integer lesson_id PK,FK
    integer vocabulary_id PK,FK
    integer position
  }
  quiz_questions {
    integer id PK
    integer lesson_id FK
    string stable_key
    string question_type
    json prompt
    json options
    json answer_key
    string explanation_th
    string status
    json provenance
  }
  review_items {
    integer id PK
    uuid owner_id
    integer kanji_id FK
    integer vocabulary_id FK
    datetime due_at
    integer interval_days
    integer lapses
    integer reviews
    integer version
  }
  user_progress {
    uuid owner_id PK
    integer lesson_id PK,FK
    integer progress
    datetime completed_at
    datetime updated_at
    integer version
  }
  vocabulary_kanjis {
    integer vocabulary_id PK,FK
    integer position PK
    integer kanji_id FK
  }
  quiz_attempts {
    integer id PK
    uuid owner_id
    uuid submission_id
    integer question_id FK
    json selected_answer
    boolean correct
    datetime created_at
  }
```

Supabase-only migration constraints additionally reference auth.users(id) for
user_progress, review_items and quiz_attempts. That external schema is not owned
by this application's ORM metadata.
