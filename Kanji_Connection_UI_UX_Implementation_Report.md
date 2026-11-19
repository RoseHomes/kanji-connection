# Kanji Connection — UI/UX implementation

Implemented the Modern Japanese Playful redesign over the existing **2026-11-19-final-v2** working edition. All 30 chapters remain private and are available in the protected local preview. Learners can browse, compare, answer questions, see explanations, review results and retry mistakes without typing Japanese or Thai answers.

## Open the working preview

Both local servers are running. Open [the private preview shortcut](private/editorial-preview/Open%20Kanji%20Editorial%20Preview.url); it authorizes the browser at **http://127.0.0.1:5174**. Opening the site directly without that authorization does not grant access. The HttpOnly, SameSite=Strict session expires after eight hours.

To restart, use two terminals from the project root:

```powershell
.\.venv\Scripts\python.exe scripts/serve_editorial_preview.py --local-snapshot
```

```powershell
cd frontend
npm run dev:editorial
```

The backend binds to 127.0.0.1:8001. Snapshot startup reads Supabase in a read-only transaction and verifies the complete educational snapshot against the synchronized receipt and structured bundle. It refuses drift. The private SQLite mirror enforces read-only connections with URI `mode=ro` and `PRAGMA query_only`; it enables fast local answer checking without changing production access controls.

## Actual implementation

| Files / area | Implemented behavior |
|---|---|
| `frontend/src/styles.css`, `ui.tsx`, `main.tsx`, `motion-features.ts` | Warm paper palette, coral/green/yellow accents, Thai/Japanese typography, shared cards/buttons/forms, responsive navigation, touch targets, focus states, page transitions, lazy Motion features and reduced-motion support. |
| `pages/Home.tsx`, `Catalog.tsx` | Interactive hero using authorized Kanji, useful chapter groups, chapter cards, honest loading/error/empty states and clear learning actions. |
| `pages/Lesson.tsx`, `lesson-sections.tsx`, `study-content.tsx`, `components.tsx` | Readable single-page lessons, 420 card occurrences, scoped readings, meaningful mnemonics, optional vocabulary, supplementary panels, supported comparison networks, five verified sentences in chapters 27/29 and practice links. |
| `pages/Compare.tsx`, `presentation-types.ts` | **94 curated groups**: 90 existing source pairs, two 大 / 犬 / 太 groups and two 休 / 体 groups drawn from reviewed cards. Clickable categories and selectors, responsive tables, mobile pair focus, accessible change announcements and mobile scrolling to the selected comparison. No text-entry field. |
| `pages/Explorer.tsx`, `KanjiDetail.tsx` | Category/chapter browsing, optional search, pagination, clear readings and vocabulary, and related-character tiles with adequate touch targets. |
| `pages/Quiz.tsx` | Native radio choices, explicit checking, progress, correct/incorrect feedback, explanations, focused next questions, results, full answer review, wrong-only retry and full retry. No free-text exercise or persistence request. |
| Account / progress / review screens | Shared redesigned visual system, responsive forms/cards, preserved account gates and read-only controls; no invented progress or enabled writes. |
| `backend/app/learning_presentation.py`, `learning_routes.py`, `learning_schema.py` | Authorized, stateless objective presentations and stable option IDs. New `/learning/comparison-groups`, `/learning/practice/{slug}` and `/learning/practice/{slug}/{question_id}/check` endpoints. Invalid options, forged scores and free-text submissions are rejected. |
| `content_views.py`, `schemas.py`, `editorial_preview.py` | Positive educational-field serialization, including nested diagrams. Learner responses omit PDF pages, filenames, database row IDs, raw extraction, revision evidence, original answer keys and manual rubrics. |
| `editorial_preview_snapshot.py`, `scripts/serve_editorial_preview.py` | Verified, private, database-enforced read-only local mirror. The preview factory is never mounted in the production application. |
| `scripts/build_learning_presentation.py` | Additive private MCQ audit and pinned dictionary reading-exclusion map; no extraction, working-source or Supabase updates. |

Motion covers route/section entry, hero selections, comparison changes, quiz transitions, feedback, progress and completion. CSS supplies card hover, button press and focus feedback. Reduced-motion mode removes movement and preserves functionality. Motion features load separately: **49.10 kB raw / 18.85 kB gzip**; the measured main build chunk is approximately **285 kB raw / 91 kB gzip**.

## Exact exercise conversion

| Preserved source | Learner presentation | Count |
|---|---|---:|
| 210 meaning items | 120 meaning-choice + 90 glyph-recognition items | 210 |
| 210 reading items | Whole-word reading choices; accepted variants excluded from distractors | 210 |
| 30 manual comparison items/rubrics | 30 **new objective shape questions**; original free-response rubrics remain internal and ungraded | 30 |
| **Total** | **15 playable questions in every chapter; zero skipped working-edition items** | **450** |

Distractor labels come from reviewed chapter content. Reading alternatives are checked against the pinned JMdict reading map and source answer variants. Shape alternatives use the reviewed rubric and explicit incorrect contrasts. No new vocabulary or references were fabricated. Optional 訊, 靖 and 金閣寺 were not introduced as required quiz targets. The separate public sample uses three distinct reading questions to avoid ambiguous forest-meaning choices.

The private [MCQ audit](private/learning-presentation/mcq-presentation-v1.json) records stable IDs, source mappings, correct choices and explanations. Original extraction, reviewed content, manual rubrics and Thai editorial metadata remain preserved internally.

## Verification and screenshots

| Command / check | Actual result |
|---|---|
| Backend `python -m pytest -q --tb=short` | **133 passed, 19 skipped**, one existing Starlette/httpx deprecation warning. Skips concern optional isolated PostgreSQL / PostgreSQL-only migration and RLS tests. |
| Frontend `npm run test -- --reporter=dot` | **59 passed**, 16 files. |
| `npm run lint`; backend Ruff; `npm run typecheck` | Passed. |
| `npm run build:demo` | Passed, including TypeScript and the complete Vite build. |
| `npm run build` | Existing production guard correctly refused an unconfigured HTTPS `VITE_API_URL`. No deployment configuration or credentials were changed. |
| `npx playwright test --reporter=line` | **10 passed**: public guest learning/practice, empty states, error recovery, account gates, keyboard navigation and responsive/direct-refresh checks. |
| Protected preview browser verification | **90 complete chapter flows**: all 30 at 1440×1000, 820×1180 and 390×844. **1,353 answer interactions**, including wrong-only retries. All 94 comparison groups exercised at each size. |
| Accessibility / visual follow-up | **65 axe WCAG A/AA scans; zero automated violations** after fixes. Keyboard choice selection, feedback/next/result focus, reduced motion, button press behavior, final layout bounds and full-page PNG widths checked. Gradient/decorative contrast follow-ups are retained with the evidence; this is not a claim of screen-reader certification. |
| Zoom reflow | 720 CSS-pixel viewport at device scale 2, equivalent to 200% reflow from a 1440-pixel desktop; lesson, comparison and quiz checked. |
| Source / database safety | **1,021 protected files unchanged**. All **2,942 educational rows** match the synchronized receipt; the structured bundle requires zero updates. Public application checks still deny all 30 private lesson and question routes, even with the preview cookie. |

Visual review fixed account-sidebar contrast, undersized related-Kanji links, mobile comparison intrinsic-width overflow, button hover/press precedence and skip-link clipping in full-page captures.

- [Screenshot contact sheet](private/ui-ux-redesign/contact-sheet.png): 134 verified screenshots plus the contact sheet; component crops omit navigation only.
- [All chapter and screen screenshots](private/ui-ux-redesign/screenshots)
- [Complete browser results](private/ui-ux-redesign/browser-verification.json)
- [Final visual and focus checks](private/ui-ux-redesign/final-visual-review.json)
- [Source integrity](private/ui-ux-redesign/source-integrity.json)
- [Contrast follow-up](private/ui-ux-redesign/contrast-manual-review.json): gradient heading contrast **9.02:1**; ornamental glyph and arrow verified decorative/aria-hidden.
- [Verified local mirror / database receipt](private/editorial-preview/snapshots/verification.json)

Reproduce the protected browser checks with `node scripts/verify_ui_ux_redesign.mjs`, then `node scripts/review_ui_ux_evidence.mjs --refresh-screenshots`. The compatibility entry point `scripts/verify_editorial_preview.mjs` runs the new full-flow verifier. Evidence and capabilities stay under ignored `private/` paths.

## Remaining limits and restrictions

No local-preview blocker remains. Production build/release configuration is intentionally unconfigured, and account persistence remains disabled. Original unresolved Thai editorial concerns remain internal working-edition metadata. Responsive tests used real Edge browser contexts with emulated viewport sizes; they do not claim physical-device or every-screen-reader certification.

**Supabase writes in this redesign: 0.** No publication, `needs_review`, `catalog_visible`, access settings, account records, credentials or original extraction files were changed. No commit, push or deployment was performed.
