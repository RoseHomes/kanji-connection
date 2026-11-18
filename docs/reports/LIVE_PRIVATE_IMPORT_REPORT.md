# Private staging import and learning integration - 2026-11-16

The complete private staging import committed successfully; fresh-connection
verification passed. Learning integration and guarded cleanup also passed.
Imported content remains in place. The owner cancelled the temporary seven-row
fixture and authorized the existing unchanged complete book edition as private
staging, plus scoped account-learning verification.

Read-only preflight passed: Alembic revision `0002`, complete public schema
snapshot, RLS/policies/client privilege denials, no application triggers and 16
empty application tables. All 65 protected source files passed structured
validation and the edition manifest check.

| Verified input             | SHA-256                                                          |
| -------------------------- | ---------------------------------------------------------------- |
| Source manifest            | f9e5f7cf05b96a4962245057a300a7fee5ddde38603a34ca7c406afde460cae9 |
| Canonical import bundle    | 92cf49d38857ee52a9a03d160700223eecbfa6425d75de198d5be3334a9ccd2e |
| Editorial correction layer | 6bd2e5ab59b695677be20a6cf6e68edd806d036822f992e812f282d1ba552f11 |

The guarded importer owns one serializable PostgreSQL transaction,
transaction-scoped advisory lock `17171701`, application table locks,
five-second lock and sixty-second statement timeouts. It rechecks schema/data
after locking, applies the existing insert-only pipeline, verifies counts,
foreign keys, private statuses and zero inserts/conflicts on a second pass
before commit, then checks committed data from a fresh connection. Any failure
before commit rolls back. No migration, publication, managed-table DML,
deployment or push.

Private evidence is stored in ignored `private/live-book-import/`. Credentials,
tokens, passwords, extracted text and account identifiers are excluded from this
report.

## Committed book inventory

| Table               |      Rows |
| ------------------- | --------: |
| lessons             |        30 |
| kanjis              |       358 |
| vocabularies        |       197 |
| components          |         3 |
| kanji_readings      |       480 |
| kanji_relations     |       240 |
| lesson_kanjis       |       420 |
| lesson_sections     |       210 |
| lesson_vocabularies |       240 |
| quiz_questions      |       450 |
| vocabulary_kanjis   |       313 |
| kanji_components    |         0 |
| visual_assets       |         0 |
| **Total book rows** | **2,941** |

The import inserted zero user-owned rows. The 358 glyphs comprise 313 teaching
Kanji and 45 supporting glyphs. Questions comprise 420 numbered exercises with
explicit source answers and 30 reference-only comparison questions. All lessons
are private/needs_review with catalog_visible=false; zero chapters are
editorially approved. All four editorial flags remain intact. The second
importer pass inserted zero rows with zero conflicts. Seventeen ORM foreign keys
had zero orphans; PostgreSQL also enforces the three owner foreign keys
referencing auth.users. Application schema remains at revision 0002.

## Actual live learning results

The loopback-only harness used the existing dedicated account and the imported
chapter 1, its source questions and an imported teaching Kanji. Development
visibility was restricted to that UUID in the process; the normal environment
and protected source/overlay were not changed. Mutation routes were restricted
to the selected lesson, card and two fixed submission UUIDs with source answers.
No temporary content or second Auth account was created.

| Check                                           | Actual result                                                                                |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Private development catalog                     | All 30 chapters accessible to the dedicated account                                          |
| Anonymous public lessons/Kanji/learning catalog | Empty; private lesson 404 and owner dashboard 401                                            |
| Lesson progress                                 | API 50%/version 1, then lesson UI 100%/version 2                                             |
| Numbered quiz                                   | Source answer submitted through UI; graded correct and persisted                             |
| Comparison quiz                                 | Source reference submitted through UI; pending manual review, excluded from score            |
| Duplicate submission                            | Existing result returned; one row per fixed submission UUID                                  |
| Flashcard                                       | UI reveal and successful review; one day, then API review extended to two days               |
| Stale progress/review versions                  | Both rejected with HTTP 409                                                                  |
| Dashboard                                       | UI and API show completed lesson, schedule, one graded/correct answer and one pending answer |
| Browser restart                                 | The saved progress, schedule and quiz results remained available                             |
| Separate database connection                    | Committed progress 100%, two-day interval and quiz aggregates verified                       |
| Alternate-owner service probe                   | Equal private-content visibility, zero progress/cards/quiz results for synthetic other owner |
| Book preservation                               | Complete content-row fingerprint identical before/after learning test and cleanup            |

The alternate-owner probe used a synthetic query identity only, with no Auth
row/token. It verifies server ownership predicates, not an actual second-account
HTTP/JWT scenario. The service check used a privileged connection;
anonymous/authenticated direct table privileges remain denied, and all owner
policies remain unchanged. No claim of privileged-query RLS enforcement is made.
No completed Auth regression suite was repeated; ordinary account session use
was only a prerequisite to the learning test.

The first browser harness run waited for an account-page button after the
application had correctly redirected to the dashboard. This caused a harness
timeout before any progress write. The wait was corrected and the
already-established session reused; all feature checks then passed. Initial
diagnostic evidence is retained privately. No application or Supabase
configuration error was found.

Cleanup took the owner advisory lock and progress-table locks, checked record
identities, targets and expected values, and deleted **two quiz_attempts, one
review_items and one user_progress row**. A fresh read-only transaction verified
zero rows in all three owner tables, unchanged 2,941-row book inventory,
unchanged content fingerprint, private status, valid foreign keys and unchanged
schema. The dedicated Auth account is retained. Both temporary local servers
were stopped; no persistent write enablement was configured.

## Focused checks and remaining scope

- Six existing importer safety cases passed (foreign keys/idempotency, rollback,
  unsafe-plan guards).
- Five focused caller/harness tests passed (source/bundle/editorial hash
  mismatch before connection, revision mismatch, route/submission restrictions
  with verified identity still required).
- Ruff lint/format checks passed for changed Python; browser harness
  syntax/format checks passed.
- The existing full Auth/backend/frontend/browser suites were not rerun. No
  frontend application code or dependencies changed, so unrelated builds/type
  checks were not repeated.
- A pre-existing Starlette/httpx test-client deprecation warning remains; no
  focused test failed.

Four editorial requirements remain open: Thai semantic/context review,
mnemonic/etymology claim review, visual adaptation/reuse review and teacher
approval of comparison rubrics. No content is approved or published. Normal
account writes remain disabled; the scoped test authorization does not activate
an ongoing public/staging service or authorize future imports, migrations,
deployment or Git pushes.

Private operational artifacts and the record ledger are retained outside the
public repository.
