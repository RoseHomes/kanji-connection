# Local editorial working edition

The final working revision covers all 30 chapters without publishing them. Its
private revision file is `private/editorial-revisions/2026-11-19-final-v2.json`.
The immutable extraction remains in `private/kanji-connection-extracted`.

Build with the existing entry point:

```powershell
.\.venv\Scripts\python.exe scripts/build_book.py
```

When the final revision is present, this produces the effective strict Book,
teaching metadata, verification results and working bundle in
`private/editorial-working`. It checks the extraction manifest and every
expected original value. Earlier files in `private/json-content` remain
historical audit artifacts; they are not the active working edition. Builds
never connect to a database or apply content changes.

Run the separate local backend and frontend in two terminals:

```powershell
.\.venv\Scripts\python.exe scripts/serve_editorial_preview.py --local-snapshot
```

```powershell
cd frontend
npm run dev:editorial
```

Open `private/editorial-preview/Open Kanji Editorial Preview.url` in the local
browser. It authorizes that browser for `http://127.0.0.1:5174` using an HttpOnly,
SameSite=Strict cookie. The session lasts eight hours; restarting the backend
generates a new local shortcut. No Supabase login is needed or refreshed in
this frontend mode. Keep the shortcut and session file private.

`--local-snapshot` reads Supabase in a read-only transaction, compares the complete
educational snapshot with the synchronized edition receipt, verifies that the
structured bundle requires zero further changes, and serves an exact private
SQLite mirror. SQLite URI `mode=ro` and `PRAGMA query_only` reject writes. Startup
fails if Supabase or the working bundle has drifted. Verification and the mirror
stay in `private/editorial-preview/snapshots`. This avoids remote round trips for
every quiz answer. Omit the flag only to inspect live read-only Supabase directly.

The backend binds only to `127.0.0.1:8001`, rejects remote clients, unexpected
hosts/origins and unauthenticated requests, and refuses hosted deployment.
It is never mounted in the production application. All database sessions are
read-only. Stateless answer checks are allowed; account and content write
routes are unavailable. The frontend restricts filesystem serving to its own
directory and denies private files. Normal production access checks remain
unchanged.

Cards distinguish component names, character readings and full words with
okurigana. Optional vocabulary is expandable and marked separately; supplementary
characters have their own panel. Chapters 27 and 29 include sourced phrases and
sentences. Original manual comparison rubrics remain internal and are never
automatically graded. The learner quiz now has 15 objective choices per chapter:
seven meaning/recognition items, seven whole-word reading items and one new shape
item derived from the reviewed rubric. Stable option IDs are checked server-side;
answers, results and retries stay within the current session without account
writes. Thai editorial concerns and prior proposals remain internal
metadata rather than learner-facing approval gates.

Build the additive MCQ audit and dictionary reading exclusion map after building
the working edition, using the pinned dictionaries already in `private/`:

```powershell
.\.venv\Scripts\python.exe scripts/build_learning_presentation.py
```

This writes only `private/learning-presentation`. It preserves the working bundle
and source files and never connects to Supabase. Public lesson authorization is
checked before constructing any objective question presentation. Learner section
responses whitelist educational fields and omit PDF pages, filenames, evidence,
original answer keys and editorial rubrics.

The database update command is separate from building and previewing:

```powershell
.\.venv\Scripts\python.exe scripts/sync_editorial_working.py verify
```

The completed update has a guarded baseline, plan, rollback rehearsal, commit
receipt and fresh-connection verification under
`private/editorial-sync/2026-11-19-final-v2`. `apply` refuses to repeat a committed
revision. A later content revision needs a new reviewed baseline and revision ID;
do not overwrite these receipts or use the insert-only importer for updates.
The updater only permits specific educational columns, locks and compares the
complete expected private snapshot, verifies the resulting projection before
commit and preserves publication/review/access fields. User tables are outside
its allowlist.

Visual evidence can be regenerated while both servers run:

```powershell
.\.venv\Scripts\python.exe scripts/capture_hybrid_baseline.py
node scripts/verify_hybrid_learning.mjs
```

Lessons now default to Guided Learning: introduction, four ordered Kanji groups,
vocabulary/use, supported comparisons, an optional checkpoint and chapter review.
Full Lesson remains a complete compact reference with expandable details. Stage,
mode and focused card use shareable URLs; visits and position are stored only in
the current tab's session storage. They are not account progress or mastery.
Old `#lesson-section-N` bookmarks map to the corresponding Full Lesson section.
Comparison, Explorer and quiz return links preserve lesson context. Official
question IDs, options and scoring are unchanged; checkpoints reuse two existing
items and never add to the 15-question chapter quiz.

Shared Radix Select pickers replace the comparison and Explorer native dropdowns
and provide chapter switching. They use portalled lists, collision handling,
keyboard/typeahead navigation and focus restoration. On phones, Kanji tiles allow
one-card focus or the complete small group. The persistent lesson bar supplies
previous/next, mode switching and an outline; it replaces the global bottom tabs
within lessons so two navigation bars do not cover the learning surface.

The new browser run checks all 30 chapters in both modes at 1440, 820, 390 and
320px; all 420 card occurrences and five sentences; all 94 comparison choices;
official quiz results/retries; history, refresh, return paths, keyboard, touch,
reduced motion and WCAG axe scans. Baselines and evidence are stored under
`private/hybrid-learning`; `--resume` retains completed checks after an interruption.
The earlier redesign evidence remains in `private/ui-ux-redesign`. Nothing in this
workflow enables production account writes, publishes content, commits, pushes
or deploys the application.
