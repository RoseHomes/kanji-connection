# Learning schema review

Migration 0001 supplied only kanjis, lessons, placements and sections. It could
not represent the complete required domain. Migration 0002 and the current ORM
now cover these foundations:

| Feature                                    | Storage and constraints                                                                                    |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| Single characters                          | kanjis, single-glyph check, unique character, nullable strokes/JLPT estimate                               |
| Readings                                   | kanji_readings with on/kun/other, order/notes and unique reading per kind; legacy JSON retained            |
| Components                                 | components and positioned kanji_components; components are separate from full glyphs                       |
| Visual/phonetic/mnemonic/history relations | typed kanji_relations, source/target FKs, direction, distinct-target check, provenance                     |
| Compound words                             | vocabularies, unique written form/reading; ordered vocabulary_kanjis supports repeated glyphs              |
| Curriculum and recurrence                  | lessons, lesson_kanjis, lesson_vocabularies; unique chapter/slug, explicit ordering                        |
| Sections and mnemonics/examples            | ordered lesson_sections with structured JSON blocks/provenance and editorial/access flags                  |
| Licensed diagrams                          | visual_assets with stable key, path, license, editorial state and source metadata                          |
| Exercises/answers                          | quiz_questions with stable per-lesson key, options, private answer key and provenance                      |
| Account lesson progress                    | user_progress keyed by owner UUID and lesson, 0–100 check, timestamps, version                             |
| Score attempts and retries                 | quiz_attempts with owner and unique submission UUID for retry idempotency                                  |
| Spaced reviews                             | review_items with exactly one kanji/vocabulary target, per-owner uniqueness, due index and schedule bounds |
| Editorial/private/premium protection       | checked statuses/access tiers; catalog-visible default false; RLS enabled                                  |

These are schema capabilities; the current application implements authenticated
learning, server grading/scheduling, version-conflict handling and explicit
guest sync. The strict book validation schema and insert-only pipeline are
implemented separately. Teacher grading, editorial approval, licensed artwork
and hosted production verification remain outside the completed scope. JLPT
fields are estimates, not an official level list. See
[current status](../reports/IMPLEMENTATION_STATUS.md),
[account behavior](../guides/AUTH_AND_PROGRESS.md) and
[content audit](../reports/CONTENT_AUDIT.md).

Existing migration-0001 records are preserved, get private access defaults, and
are not silently enriched or promoted by the insert-only seed. Normalized
readings are preferred when present; legacy JSON readings remain readable for
reviewed records during transition. Curated backfill/publication requires a
separately reviewed import, not ad hoc seed updates.

Public SQL APIs and local PostgreSQL migration upgrade/downgrade/upgrades are
integration-tested. Metadata drift checking ignores only the three deliberate
FKs into external auth.users. The generated ERD matches ORM metadata; tests
compare migrations with that metadata.
