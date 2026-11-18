# Frontend readiness review - 2026-11-16

Implemented and inspected against the existing private Supabase book using the
existing dedicated development account. This review did not repeat imports, Auth
verification, quiz scoring/persistence integration or learning-progress
integration tests.

## Actual issues and fixes

| Observed issue                                                                                                                                                                 | Change and evidence                                                                                                                                                                                                                                                                 |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Stored lesson sections were not returned by the learning endpoint or rendered by the page.                                                                                     | Added read-only section presentation and a table of contents. All 30 lessons now render their seven sections: 210 sections, 420 teaching-card occurrences and 240 vocabulary placements.                                                                                            |
| Catalog, explorer and comparison used public-only endpoints, appearing empty to an allowlisted developer.                                                                      | Added authenticated optional-user presentation routes that grant private visibility only through the existing development UUID allowlist. Public/ordinary-account results remain filtered. Query caches include the account identity.                                               |
| No vocabulary furigana or source page labels were displayed.                                                                                                                   | Source word/reading pairs use semantic group ruby with Japanese language tags. Thai meanings and PDF page references are visible. Whole source readings are preserved; no per-character alignment or missing reading is invented.                                                   |
| Shared Kanji rows select a first-source gloss, losing 27 lesson-specific meaning variants across 23 glyphs when reused as lesson cards.                                        | Lesson cards now display the existing section occurrence's Thai gloss; explorer/shared records remain unchanged. This is source-context selection, not a new translation or editorial correction.                                                                                   |
| Four card occurrences have existing contextual-reading annotations; placing their source reading over the bare glyph would misrepresent a compound segment or incomplete stem. | These four cards show the stored source reading, separate reading index and existing editorial scope note. No standalone ruby is invented; original word examples remain visible. Five focused live read-only card checks passed (four annotations and one differing lesson gloss). |
| Comparison/mnemonic section data were invisible.                                                                                                                               | Rendered existing pairs, core/related nodes, memory tips and typed component labels. Chapters 2 and 4 explicitly retain their absent cores and use existing source pairs. A visible note distinguishes mnemonics from verified historical etymology.                                |
| A straightforward section response could expose answer keys and duplicate raw page text.                                                                                       | The presentation adapter removes raw extraction blocks and exercise answers/answer notes from the response without changing stored records. Prompts lead to the existing interactive quiz. Synthetic tests verify stored originals remain unchanged.                                |
| Home feature cards extended to 331px in a 320px viewport.                                                                                                                      | Fixed grid-child minimum sizing and responsive glyph size/spacing. Corrected views fit the viewport. A before image is retained privately.                                                                                                                                          |
| Read-only staging still offered active save/submit/review/sync controls that would fail.                                                                                       | Health exposes a nonsecret write-capability boolean. A read-only notice disables those controls without silently falling back to guest saves. Reading, question inspection and flashcard reveal remain available.                                                                   |
| Empty flashcard results claimed a completed review; explorer always described three samples.                                                                                   | Added distinct inaccessible/empty, no-due-review and no-search-match messages. Removed hardcoded sample-count claims and added explorer pagination beyond 30 cards.                                                                                                                 |
| Catalog notice contradicted clickable private staging lessons.                                                                                                                 | Private lesson/card/comparison/quiz/review views retain visible review/private labels; public catalog copy does not imply staging content is published.                                                                                                                             |
| Comparison selection was limited to tree samples, with an unconditional tree explanation.                                                                                      | Added validated 2-4-character input and URL selection. The tree note appears only for that set; browser Back restores the form selection. Missing readings/components/strokes are shown as missing rather than invented.                                                            |
| Dependent pending queries could hide an actual error indefinitely.                                                                                                             | Error states take priority over loading; lesson/dashboard surface health errors, retries recover, and no guest save occurs after a health failure. Network/404 messages are localized and the backend-port instruction was removed.                                                 |
| Home linked directly to a private lesson; route transitions kept the old scroll/focus.                                                                                         | Home leads to accessible catalog choices. Route changes reset scroll, focus main content and update the title. Section anchors and quiz links work.                                                                                                                                 |
| Small mobile input/control sizing and mixed-script fallbacks were inconsistent.                                                                                                | Mobile search uses 16px text; navigation/filter/section links have at least 44px targets. Thai/Japanese font fallbacks, textarea focus/font, section layouts and review badges follow the existing palette.                                                                         |

## Inspection and focused checks

- Microsoft Edge / Playwright, headless, with real imported private content.
- 50 responsive route checks: home, catalog, explorer, comparison, lesson, quiz,
  review, dashboard, account and not-found at 320, 390, 768, 1024 and 1440px.
- All 30 imported lesson pages inspected at 390px: seven sections, fourteen
  teaching cards, eight vocabulary placements per lesson, no horizontal
  overflow/replacement characters, and coreless diagrams exactly in chapters 2
  and 4.
- Visual inspection of mobile vocabulary ruby/Thai meanings, source-based
  core/coreless diagrams, cards and tablet catalog screenshots. This is a
  rendering review, not new linguistic/editorial approval or a reconstruction of
  book artwork.
- Six additional browser state scenarios passed: filter clearing/private notice,
  arbitrary comparison and Back, read-only lesson/table of contents, simulated
  503 and retry recovery, empty reviews, and desktop read-only review/quiz
  controls.
- Home-to-catalog-to-lesson-to-quiz navigation and the 30-lesson quiz selector
  passed.
- Final 320px control check: document width 320px, search font 16px,
  filter/navigation target heights 44px. Added badges and notices do not
  introduce overflow.
- Eighteen focused Vitest cases across lesson sections, presentation states,
  lesson, quiz and dashboard passed. Three new synthetic in-memory backend
  presentation cases passed (visibility, searches/pagination, safe sections and
  unchanged source records).
- Changed-file ESLint, Ruff, formatting, TypeScript and production Vite build
  passed. Existing Starlette/httpx test-client deprecation warning remains; no
  focused test failed. Full previously completed Auth/persistence/database
  suites were not rerun.

Private evidence: `private/ui-review/review.json`, `states.json`,
`navigation.json`, `mobile-controls.json`, `integrity.json` and screenshots.
These contain private book views and remain excluded from Git and frontend
bundles. No screenshots are published. `context-results.json` records the five
additional contextual-card checks.

## Read-only access and remaining limits

`scripts/preview_private_book.py` loads the existing dedicated account UUID
locally and binds only to 127.0.0.1. Its process-only allowlist uses existing
authorization behavior; normal backend/.env remains unchanged. Every database
transaction starts READ ONLY, all HTTP mutations are denied, and the browser
review also blocks application mutations. Actual browser application-write
requests: **zero**. Account session use was a prerequisite to private
inspection, with no signup, confirmation, Auth assertions or account changes.

The 65 protected source files and editorial correction layer still match the
verified source/overlay hashes. No schema, source JSON, editorial correction,
content record, publication flag, RLS policy or production setting was changed.
No deployment or push.

All book content remains private/needs_review. The four existing editorial
requirements remain separate and open. Physical iOS/Android devices,
Safari/Firefox and a full assistive technology audit have not been tested; do
not interpret Edge viewport checks as those tests. The preview is read-only and
normal account writes remain disabled. Existing integration results are not
repeated or expanded into production approval by this review.

## Reproduce the scoped review locally

With the existing backend/.env, dedicated-account state/password protection and
frontend configuration already in place, start the read-only preview and Vite in
separate terminals:

```powershell
.\.venv\Scripts\python.exe scripts/preview_private_book.py
# Separate terminal, frontend directory:
npm run dev
```

Then from the root run either `node scripts/review_private_ui.mjs` for the
route/lesson review, or `node scripts/review_private_ui.mjs --states-only` for
the focused state checks. These are private read-only UI inspections, not import
or progress-integration commands.
