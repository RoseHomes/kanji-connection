# Structured content pipeline

คู่มือสำหรับการเตรียมหมวดและ JLPT N5–N1 บน revision `0003` อยู่ใน
[คู่มือนำเข้าเนื้อหาการเรียน (ภาษาไทย)](LEARNING_CONTENT_IMPORT_TH.md)

## Active editorial working edition

When the final v2 overlay is available locally, `scripts/build_book.py` builds
the corrected working edition under `private/editorial-working` and preserves
the extraction and earlier audit outputs. See [local editorial preview](EDITORIAL_PREVIEW.md)
for the active build, guarded synchronization and protected preview commands.
The source-extraction pipeline below describes the historical baseline; its
insert-only rehearsal and reports do not update the working database.

## Original extraction and baseline pipeline

Use the immutable source directory private/kanji-connection-extracted/. It
contains 30 chapter JSON files, the matching aggregate, extraction report and
text for all 243 source PDF pages. Never modify, move or regenerate those files.

The source/reference inputs are intentionally absent from a public clone. Only
maintainers with separately authorized private inputs can run the complete book
pipeline. The credential-free sample remains available without them. From the
project root:

```powershell
.\.venv\Scripts\python.exe scripts/build_book.py
.\.venv\Scripts\python.exe scripts/rehearse_book_import.py
.\.venv\Scripts\python.exe scripts/report_book.py
.\.venv\Scripts\python.exe -m pytest -q backend/tests/test_book_pipeline.py
```

The build reads JSON, validates strict Pydantic models, checks
aggregate/report/page consistency and prepares an insert-only plan against the
existing 16-table schema. There is no PDF parser, renderer, OCR or font recovery
dependency. Source page text is preserved in chapter sections; ancillary page
text remains in the canonical book. No book content is imported, published or
embedded in frontend bundles by these commands.

Outputs are private/json-content/book.json, verification.json,
import-bundle.json and import-rehearsal.json. Only schemas, counts and audit
metadata are public files. File SHA-256 digests, JSON pointers and source PDF
page numbers identify every record. The source JSON's missing diagram cores,
review status and wording are preserved exactly.

Dictionary evidence is optional and explicitly reported as unavailable when
snapshots are absent. `scripts/fetch_content_references.py` explicitly fetches
KANJIDIC2 and JMdict from EDRDG into private/dictionaries/. Existing snapshots
are retained and digest-checked; remove both a snapshot and its metadata
deliberately to choose a newer upstream version. Rebuild all evidence after a
reference update. No network access occurs during a build.

Dictionary sources: James William Breen / Electronic Dictionary Research and
Development Group, [KANJIDIC2 and JMdict](https://www.edrdg.org/pub/Nihongo/),
[CC BY-SA 4.0](https://www.edrdg.org/edrdg/licence.html). Attribution, digests
and URLs accompany verification. A supplementary
[禾／のぎ check](https://www.kanjipedia.jp/kanji/0000635400) from the earlier
audit is retained explicitly. Dictionary membership does not independently
approve Thai translations, usage context, component names or etymology. Derived
data remains private pending reuse/attribution review; PDF text and artwork have
separate reuse rights.

The Python importer receives a caller-owned SQLAlchemy session and never commits
or creates an engine. It preflights all operations, rejects user
tables/publication/duplicate keys/oversize strings, resolves foreign keys and
inserts only missing natural keys. Existing values remain unchanged; differences
are returned as conflicts. The guarded PostgreSQL caller is now
`scripts/import_private_book.py`: its default mode is read-only. It requires the
exact verified source/overlay/bundle hashes, revision 0002, a matching schema
snapshot and empty application tables. The explicit
`--commit-authorized-private-import` flag is only for an owner-authorized
import. It owns a serializable transaction, advisory/table locks, rollback and
pre/postcommit checks. It refuses changed data rather than guessing whether
another edition is compatible. The old sample seeder is separate and must not be
used to import the book.

The complete rehearsal enables foreign keys in disposable in-memory SQLite,
inserts all prepared rows twice and rolls back. Tests verify editorial
preservation, full rollback, source fidelity, page boundaries, answer alignment,
reference integrity and unsafe-plan rejection. Private-source tests skip when
the source is absent in CI; synthetic schema validation and the existing
application tests still run. PostgreSQL execution is not claimed by the local
rehearsal.

See [content audit](../reports/CONTENT_AUDIT.md) and
[seed validation](../reports/SEED_VALIDATION.md) for exact counts and remaining
editorial work. The private staging import was verified on 2026-11-16. See
[private import report](../reports/LIVE_PRIVATE_IMPORT_REPORT.md) for actual
execution results. This is not authorization for future imports, publication,
migrations, deployment or Git push.

## Edition-bound editorial layer (2026-11-16)

`content/editorial-corrections.json` is separate from the protected dataset.
Pydantic validates it; a complete source-manifest hash and expected original
values prevent applying corrections to a different edition. The current sense
correction only removes an unsupported alias already contrasted with a valid
source gloss. Original source values and correction evidence remain in
provenance and corrected section records. No source Book card, word, page or
file is rewritten. No chapter approval is inferred.

`app.editorial.prepare_editorial` creates contextual reading annotations,
dictionary supplements for all supporting glyphs, source-pair views for the two
coreless diagrams and manual comparison rubrics. Supporting records remain
non-teaching, private and without invented Thai meanings. Four component
comparisons use typed endpoints in section JSON; no Kanji-only foreign key or
component-position relationship is invented.

Explicit optional reference fetching:

```powershell
.\.venv\Scripts\python.exe scripts/fetch_editorial_references.py
```

This downloads four official Japan Foundation Japanese-Thai XLSX lists to
ignored private/editorial-references/. Existing snapshots are digest-checked,
never replaced. The standard-library XLSX reader excludes phonetic/ruby metadata
from visible text. Only canonical/whitespace-equivalent Thai strings count as
exact matches; substring matches and alternate translations do not trigger
approval. Nonmatching meanings retain reference rows for sense review. Missing
snapshots yield uncovered checks. Japan Foundation materials remain private
verification references with attribution; they are not redistributed as teaching
content.

Private outputs now also include editorial.json and audit-dispositions.json.
Every original audit ID retains its classification, evidence and scoped
disposition; a supporting-field mapping resolution does not mean its absent
teaching card or Thai gloss was supplied. The original baseline is retained in
private/editorial/initial-audit.json. The report rejects a rehearsal whose exact
bundle hash differs from the current plan.

`app.comparison_scoring.assess_comparison` returns unanswered for blanks and
needs_manual_review with score=null for nonblank C responses. Exact source
quotations may be recognized as evidence but never receive automatic credit.
Twenty-three rubrics have target-specific source tips; seven have only pair/note
references. Teacher approval, Thai semantic review, mnemonic-claim review and
visual review are still open. These pure assessment helpers are not publication
or teacher-grading endpoints. Existing database editorial values remain
preserved as conflicts; the guarded remote caller aborts rather than committing
any conflict.

## Documentation regeneration compatibility

The unchanged generators write legacy paths docs/ERD.md, docs/CONTENT_AUDIT.md
and docs/SEED_VALIDATION.md. Those paths are compatibility pointers to
categorized documents. Regeneration can overwrite the pointers and reintroduce
historical narration, chapter titles and source-derived JSON metadata. Review
output locally and reconcile it with the canonical reports before publication.
Changing generator output paths is a future code change; this documentation-only
reorganization does not modify those tools. See the
[publication checklist](PUBLICATION.md) and
[cleanup report](../reports/DOCUMENTATION_REVIEW.md).
