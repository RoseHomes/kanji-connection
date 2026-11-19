# Kanji Connection — Hybrid Learning implementation

Implemented Guided Learning as the default for all 30 chapters, preserving the Modern Japanese Playful design and the complete **2026-11-19-final-v2** educational edition. Full Lesson is now a compact, complete reference view rather than the default long document.

## Working preview

Both local servers remain running. Open [the protected preview shortcut](private/editorial-preview/Open%20Kanji%20Editorial%20Preview.url) to authorize the browser at **http://127.0.0.1:5174**. The capability stays in the private shortcut; it is not included here. Sessions last eight hours.

Restart from the repository root in two terminals if needed:

```powershell
.\.venv\Scripts\python.exe scripts/serve_editorial_preview.py --local-snapshot
```

```powershell
cd frontend
npm run dev:editorial
```

The backend uses the existing verified, database-enforced read-only local mirror at 127.0.0.1:8001. This implementation did not update Supabase, rebuild the educational edition, or change its publication/access settings.

## Lesson experience delivered

- **Five phases / nine meaningful stages** in each working chapter: discover; four ordered Kanji groups; vocabulary/use; supported comparisons; optional checkpoint; review/practice. The two seven-card source sets become **4 + 3 + 4 + 3**, retaining source order. Sparse future/sample lessons adapt without empty comparison stages or fake cards.
- **Compact entry** with the real chapter counts, a visible Start/Continue action, phase rail and direct quiz access. Guided entry renders zero teaching cards until the learner starts.
- **Focused teaching** with essential readings/meaning/mnemonic visible, ancillary reading notes behind animated disclosures, optional material clearly separated, and supported comparison links directly from relevant learning groups.
- **Phone Kanji selection** shows one focused card within a 2–4-card segment, with selectable glyph tiles and a whole-group option. Individual cards are not mandatory wizard steps; Previous/Next remains unlocked.
- **Full Lesson** supplies compact reading/meaning summaries, expandable complete cards, all vocabulary, diagrams, comparisons, optional examples and all five verified sentences. Each section can return directly to its corresponding guided stage.
- **Persistent navigation** supplies Previous/Next, mode switching and a mobile/tablet outline. Within phone lessons it replaces the global bottom tabs, avoiding two stacked navigation bars. Global browsing navigation remains unchanged elsewhere.
- **Optional checkpoint** reuses two existing validated questions. It can be skipped or left after a wrong answer. It never changes the official 15-question quiz or its score, and its current answers survive switching lesson modes.

`?mode=guided|full&stage=…&card=…` records the current view and focused card. Browser back/forward, refresh and rotation preserve context. Session storage contains only mode, stage, visits and a numeric card index; it holds no educational records or scores and makes no account-write request. Blocked/corrupted storage falls back safely to URL navigation. Removed segments resolve predictably to a valid stage. Old `#lesson-section-N` bookmarks map to the corresponding Full Lesson section.

Comparison, Explorer-detail and quiz links carry a validated internal lesson return URL. Group changes retain that return path. Full Lesson tracks the section being read; switching back returns there without resetting to the chapter introduction. The original quiz retains its existing stateless results/retry behavior.

## Selection-control inventory

| Actual control | Implementation |
|---|---|
| Comparison group dropdown, 94 options | Shared select-only **Radix Select** picker; curated visual tiles and category chips retained. |
| Explorer chapter dropdown, 30 chapters + All | Same picker, coordinated with category filters and optional search; pending-catalog selection recovery fixed. |
| Lesson chapter switching | Shared picker with compact trigger and complete, wrapping chapter labels in the menu. |
| Guided / Full Lesson | Styled native buttons with pressed state and check marker; persistent alternate-mode action. |
| Phases and stage outline | Clickable current/visited/upcoming navigation; bounded mobile outline with outside dismissal, Escape and focus restoration. |
| Phone Kanji groups | Selected glyph tiles, visible check marker and whole-group toggle. |
| Catalog / comparison categories and mobile comparison pair focus | Existing accessible chip buttons retained and styled consistently. |
| Quizzes, account and review | Existing radio choices, login text inputs and review controls retained; no inappropriate replacement of conventional inputs. |

**Native-looking learner selects: 2 → 0.** No learner-facing native select was deliberately retained. Radix's hidden form-compatibility internals are not visible controls. Picker menus use a portal, collision handling, internal scrolling and managed keyboard/focus behavior. Enter/Space, arrows, Home/End, Escape, touch selection and focus restoration were exercised. [Radix Select documentation](https://www.radix-ui.com/primitives/docs/components/select) guided the shared primitive.

## Actual code areas

- Added `frontend/src/lesson-stages.ts`, `lesson-experience.tsx`, `lesson-return.tsx`, `selection-controls.tsx` and `disclosure.tsx`.
- Refactored `pages/Lesson.tsx`, `lesson-sections.tsx`, `study-content.tsx` and `components.tsx` to share the original educational renderer across both modes.
- Integrated the selection and return-path behavior in `pages/Compare.tsx`, `Explorer.tsx`, `KanjiDetail.tsx` and `Quiz.tsx`; extended shared types and theme styles.
- Added stage-accounting, navigation/recovery and picker tests; updated public browser regression expectations for the guided entry.
- Added read-only baseline capture, complete hybrid browser verification and screenshot scripts; updated the editorial-preview guide and compatibility verification entry point.

Transitions use existing Motion: stages 180 ms, disclosures 200 ms, progress 180 ms and existing short button feedback. Reduced-motion mode removes spatial movement. Static teaching cards no longer imply a clickable flip interaction. No additional animation framework or backend endpoint/schema was introduced.

## Verification results

| Check | Observed result |
|---|---|
| Backend `python -m pytest -q --tb=short` | **133 passed, 19 skipped**, one existing Starlette/httpx deprecation warning. Optional isolated PostgreSQL / PostgreSQL-only checks were skipped. |
| Frontend `npm run test -- --reporter=dot` | **113 passed**, 19 test files. Includes all 30 chapter mappings and exact instructional-unit coverage. |
| `npm run typecheck`; `npm run lint` | Passed. |
| `npm run build:demo` | Passed. Lesson chunk approximately **32.7 kB raw / 9.3 kB gzip**; shared accessible selection chunk **89.9 kB / 30.5 kB gzip**. |
| `npm run build` | Correctly refused by the existing production guard: no configured exact HTTPS `VITE_API_URL`. Deployment configuration and credentials were not changed. This does not block the protected local preview. |
| Public `npx playwright test --reporter=line` | **10 passed**: guest learning, quiz, error recovery, account gates, mobile navigation and direct refresh. |
| Protected hybrid browser matrix | **120 chapter/viewport runs**: all 30 at 1440×1000, 820×1180, 390×844 and 320×800. **1,680 guided card occurrences and 1,680 complete Full Lesson card occurrences** checked across those runs. |
| Quiz / comparison regression | All **450 question payloads and 94 group payloads unchanged**. Four complete official quiz/review/retry/return flows, **64 official answer checks**, plus separate checkpoint mode-retention checks. All 94 groups selected on desktop, with responsive selection checks at the other sizes. |
| Accessibility / recovery | **67 axe WCAG A/AA scans, zero automated violations**. Keyboard, touch, focus restoration, mobile outline, mode position, old bookmarks, removed stages, refresh, history, rotation and blocked-storage recovery checked. |
| Educational source integrity | **1,026 protected files unchanged**, including the reviewed overlay, working bundle, effective book, reading exclusion map and MCQ audit. Every source card/non-card block is assigned once; all five sentences remain reachable in both modes. |
| Security | Unauthorized preview request rejected; HttpOnly/SameSite=Strict cookie preserved; account writes rejected; zero unexpected application writes or Auth requests observed. |

These are automated real-Edge browser/viewport checks, not claims of manual evaluation of every chapter, physical-device testing, or screen-reader certification. Representative screenshots were visually reviewed. The browser checks used the existing verified local snapshot, distinct from live Supabase verification at snapshot startup.

## Evidence and reproduction

- [Before/after contact sheet](private/hybrid-learning/before-after-contact-sheet.png)
- [Fresh viewport screenshots: desktop, tablet, mobile and 320px](private/hybrid-learning/showcase)
- [Full chapter, comparison, checkpoint and quiz screenshots](private/hybrid-learning/screenshots)
- [Complete browser results](private/hybrid-learning/browser-verification.json)
- [Final visual, persistent-control and recovery checks](private/hybrid-learning/final-visual-review.json)
- [Protected-source integrity](private/hybrid-learning/source-integrity.json)

To reproduce with the preview running:

```powershell
.\.venv\Scripts\python.exe scripts/capture_hybrid_baseline.py
node scripts/verify_hybrid_learning.mjs
node scripts/capture_hybrid_showcase.mjs
```

The baseline command preserves existing evidence. `verify_hybrid_learning.mjs --resume` retains completed checks after an interruption. The earlier redesign evidence remains intact under `private/ui-ux-redesign`.

**No local-preview blocker remains. No Supabase writes, educational-data changes, publication/access changes, credential changes, enabled account writes, commits, pushes or deployment were performed.**
