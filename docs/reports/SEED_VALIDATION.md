# Seed validation - editorial overlay

JSON and source records remain immutable. The separate editorial layer produces
private/needs_review operational records, with original values, dictionary
supplements, correction IDs and evidence retained. Nothing is published or
catalog-visible.

On 2026-11-16, the owner authorized this unchanged edition as private staging.
The live PostgreSQL import committed all 2,941 rows and a fresh connection
verified the exact table counts below, private visibility, revision 0002 and
foreign keys. The second import pass added zero rows with zero conflicts. All
four editorial flags remain; no chapter was approved. See
[the live report](LIVE_PRIVATE_IMPORT_REPORT.md) for execution and learning test
evidence. No migration, deployment or Git push occurred. The JSON block below is
the earlier **local rehearsal**, retained as historical evidence rather than a
live-write counter.

Full local rehearsal: 2941 prepared rows, two passes with foreign keys enabled,
zero duplicate inserts and complete rollback. There are 4 broad editorial
blockers and zero approved chapters.

| Existing table      | Planned rows |
| ------------------- | -----------: |
| components          |            3 |
| kanji_components    |            0 |
| kanji_readings      |          480 |
| kanji_relations     |          240 |
| kanjis              |          358 |
| lesson_kanjis       |          420 |
| lesson_sections     |          210 |
| lesson_vocabularies |          240 |
| lessons             |           30 |
| quiz_attempts       |            0 |
| quiz_questions      |          450 |
| review_items        |            0 |
| user_progress       |            0 |
| visual_assets       |            0 |
| vocabularies        |          197 |
| vocabulary_kanjis   |          313 |

Source coverage is unchanged: 313 teaching Kanji plus 45 supporting glyphs, 197
vocabulary pairs/240 placements, 420 numbered questions/answers and 30
reference-only C notes. Supporting reference readings are additional reference
metadata, not new teaching cards. Existing editorial changes remain untouched;
the importer reports differing fields as conflicts. All user-owned tables
receive zero rows.

```json
{
  "mode": "in_memory_sqlite_only",
  "source_sha256": "f9e5f7cf05b96a4962245057a300a7fee5ddde38603a34ca7c406afde460cae9",
  "bundle_sha256": "92cf49d38857ee52a9a03d160700223eecbfa6425d75de198d5be3334a9ccd2e",
  "editorial_layer_sha256": "6bd2e5ab59b695677be20a6cf6e68edd806d036822f992e812f282d1ba552f11",
  "counts": {
    "components": 3,
    "kanjis": 358,
    "lessons": 30,
    "visual_assets": 0,
    "vocabularies": 197,
    "kanji_components": 0,
    "kanji_readings": 480,
    "kanji_relations": 240,
    "lesson_kanjis": 420,
    "lesson_sections": 210,
    "lesson_vocabularies": 240,
    "quiz_questions": 450,
    "review_items": 0,
    "user_progress": 0,
    "vocabulary_kanjis": 313,
    "quiz_attempts": 0
  },
  "idempotent": true,
  "rolled_back": true,
  "publication_approved": false,
  "supabase_writes": 0,
  "issues": 4,
  "editorial_gaps": 0,
  "inserted_in_scratch": 2941
}
```

Rehearsal records the exact bundle hash and editorial-layer hash; reports reject
stale rehearsal evidence. Tests cover complete-plan foreign keys, repeat import,
rollback, existing editorial values, correction guards, original-data integrity,
typed diagram endpoints, Thai reference parsing and manual scoring.
PostgreSQL-specific execution is not claimed by this SQLite rehearsal. The owner
explicitly accepted private staging with the remaining editorial scope open.
`scripts/import_private_book.py` performed the authorized
transaction/advisory/table locking, exact hash/schema guards and commit. Its
default mode is read-only; future remote writes require separate authorization,
and rerunning against populated tables is refused.
