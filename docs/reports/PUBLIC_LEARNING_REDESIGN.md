# Public learning and UI redesign

Implemented locally on 2026-11-18. No commit, push, deployment, migration, seed,
credential change, content approval or production write was performed.

> Update 2026-11-19: the verified working edition was subsequently published in
> Supabase. The pre-publication database counts below are historical; a fresh
> read-only check confirms 30 published/free/catalog-visible lessons, 94
> comparison groups and 450 questions available without login. Answer keys stay
> server-side until a choice is submitted, and account writes remain disabled.

## Original implementation inspected

The existing React/TypeScript SPA uses React Router, TanStack Query, Lucide,
Tailwind and custom CSS. Routes already covered home, catalog, lesson details,
exploration, comparison, quizzes, review, dashboard and account. Supabase owns
PKCE, confirmation callbacks and persisted sessions; the API helper attaches
bearer credentials to account requests. Auth subject changes clear query caches.

FastAPI already provides anonymous publication-filtered reads and non-persisting
grading through `/learning/*`, alongside `/lessons` and `/kanjis`. `/me/*` requires
authenticated identity and ownership. PostgreSQL stores the existing 16-table
application model; no schema change was needed. Runtime writes depend on
ENABLE_USER_WRITES. Hosted settings disable the development content allowlist.

The inspection found four practical changes to make: learning copy implied an
account was needed, guest quiz/review results were saved locally, signed-in
read-only users could not check quiz answers, and catalog visibility alone could
expose unpublished lesson metadata. The existing structured section renderer,
source furigana, vocabulary, diagrams, grading, SRS and sync conflicts were retained.

## Live publication inspection

The existing Supabase connection was used only inside explicitly read-only
transactions, with bounded statement timeouts. Only aggregate counts were read;
no educational passages, accounts or credentials are included here.

| Record type                                | Count | Status observed |
| ------------------------------------------ | ----: | --------------- |
| Lessons                                    |    30 | needs_review    |
| Kanji records, including supporting glyphs |   358 | needs_review    |
| Vocabulary records                         |   197 | needs_review    |
| Kanji relationships                        |   240 | needs_review    |
| Lesson sections                            |   210 | needs_review    |
| Quiz questions                             |   450 | needs_review    |
| Published, free, catalog-visible lessons   |     0 | None eligible   |

Production therefore has a real publication empty state. Signing in is not an
editorial bypass. No record was promoted or made visible by this work. Existing
sample-mode code remains a distinctly labeled local demonstration, with its
existing provenance qualifications; it is not a substitute for the imported
curriculum and does not constitute new editorial approval. Hosted configuration
continues to forbid sample exposure.

## Visual system and page changes

The visual direction uses a warm paper canvas, dark ink, vermilion actions and
muted green study surfaces. Core tokens are `#faf9f5`, `#242c29`, `#a93624`,
`#315c50`, `#616c65` and `#dbdfd6`. Existing Noto Sans Thai/Japanese fonts retain
Tahoma, Yu Gothic, Meiryo and generic fallbacks. No dependency or image asset was
added. The character-grid ornament is decorative when no approved card exists.

Controls, borders, notices, cards, search fields, progress bars and navigation
share the same spacing and visual hierarchy. Reading line-height is 1.85;
source-provided ruby, contextual readings and PDF provenance remain intact.
Phone layouts use a single content column, tablet grids use two columns and
wide content uses up to three. Navigation collapses at 800px; content adjusts at
600px, 800px, 1080px and 1440px. Visible focus rings, a skip link, route focus,
keyboard-operable navigation, native form controls and reduced-motion styling
are included. No streak, JLPT level, time estimate or difficulty was fabricated.

| Page or component | Result                                                                                                                                                            |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| App shell         | Persistent desktop navigation; keyboard/Escape mobile menu; public and personal destinations remain distinct                                                      |
| Home              | New editorial layout; public API-backed card previews and featured lessons; publication empty state; learning method and practice entry points                    |
| Catalog           | Published-only results, numeric supported part filters, chapter cards and empty/search states without an implied login unlock                                     |
| Lesson            | Reading toolbar, section navigation, prominent Kanji, source vocabulary/diagrams, practice links, eligible previous/next links and protected save action          |
| Explorer          | Search, real paginated results, card detail links and public empty state                                                                                          |
| Kanji detail      | New `/explore/:character` route using existing public detail, vocabulary and relationship APIs                                                                    |
| Comparison        | Selection comes from accessible API cards; shared-component display uses returned metadata; late suggestions do not overwrite typed input                         |
| Quiz              | Question progress, selectable options/free responses, feedback and round summary; manual explanations have no fabricated automatic score or teacher queue promise |
| Review            | Personal account gate; real authenticated review queue and existing SRS; answer reveal remains possible when writes are disabled                                  |
| Dashboard         | Personal account gate; server-supplied progress/results/due counts; real recent quiz history and existing explicit legacy sync conflicts                          |
| Account           | Matching responsive account layout and public-learning links; signup, confirmation, signin and local-session signout logic preserved                              |

## Access matrix

| Experience                                                 | Anonymous                                             | Authenticated                                              | Persistence                             |
| ---------------------------------------------------------- | ----------------------------------------------------- | ---------------------------------------------------------- | --------------------------------------- |
| Home/catalog/lesson reading                                | Eligible published content                            | Same public rules; no automatic private access             | None                                    |
| Kanji details/readings/vocabulary/relationships/comparison | Eligible published records                            | Same public rules                                          | None                                    |
| Public exercises and answer checks                         | Yes, for eligible questions/lessons                   | Yes, including read-only accounts                          | Non-persisting checks; round state only |
| Dashboard, saved history and personal review queue         | Friendly signin explanation; no personal API requests | Owner-scoped reads                                         | Existing records only                   |
| Save progress, review ratings or quiz attempts             | Requires an account                                   | Also requires explicit backend write enablement            | Disabled when ENABLE_USER_WRITES=false  |
| Legacy browser-data synchronization                        | Not available                                         | Explicit preview/conflict decisions; apply requires writes | No automatic import or overwrite        |
| Account signup/signin/confirmation                         | Available when Auth is configured                     | Account management/signout                                 | Existing Supabase session handling      |

Public practice writes neither a localStorage history nor learning rows. It sends
the current answer to the existing read-only grading endpoint, then holds the
result in React state. Navigating away or refreshing resets the round. Public
requests can bypass session lookup and omit bearer headers, so unavailable Auth
does not block anonymous reading. User-specific requests retain bearer handling.
The existing local-only developer preview is still explicitly allowlisted and
disabled on Vercel; it is not a role automatically granted by signing in.

## Backend and API changes

No new backend route was needed. The catalog query now requires eligible status,
free access and catalog visibility together. Sample-mode listings show only the
existing available demo, rather than 29 unteachable navigation placeholders.
Learning lesson/question lookup respects catalog-hidden content outside the
explicit local development boundary. Both lesson-reading API paths now use the
existing section sanitizer, excluding raw page blocks and embedded exercise
answers; additive PDF page metadata is retained. Answers are checked through the
existing grading API, after the same lesson/question visibility gates.

Response shapes and endpoint paths remain compatible. CORS, token verification,
ownership, production private/no-store headers and write enforcement are unchanged.
Migrations, models, source JSON, editorial corrections and deployment settings
were not altered. No production credential or new environment variable is needed.

## Verification

| Check                                                      | Actual result                                                                                                                                              |
| ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Frontend unit/component tests                              | 53 passed, including public gates, anonymous request headers, API-backed home, detail vocabulary/ruby, readonly practice and no local quiz persistence     |
| Backend focused publication/auth/learning/deployment tests | 58 passed, 1 PostgreSQL-only check skipped, 14 PostgreSQL cases deliberately deselected; one existing TestClient dependency warning                        |
| Browser checks                                             | 10 distinct scenarios passed: original public flows plus empty production content, mobile keyboard navigation and 360/768/1440px direct navigation/refresh |
| Visual inspection                                          | Desktop/mobile homepage, lesson, quiz and account screenshots reviewed; Thai/Japanese text visible; a narrow heading layout adjusted                       |
| TypeScript and ESLint                                      | Passed                                                                                                                                                     |
| Changed Python Ruff lint/format                            | Passed                                                                                                                                                     |
| Filtered production build                                  | Fresh npm installation and TypeScript/Vite build passed using nonsecret reserved origins, without source datasets or credentials                           |
| Deployment boundaries                                      | Four frontend and four backend path-base checks passed; 30 frontend runtime files, 21 backend files; isolated backend import/health passed                 |
| Source disclosure scan                                     | No private-source string overlaps or non-fixture sensitive findings                                                                                        |

Backend regressions use disposable in-memory SQLite and synthetic fixtures, not
Supabase writes. They prove anonymous published reads, denial for unpublished,
premium and catalog-hidden records even after signin, omission of unrevealed
answers, 401s on anonymous personal APIs, 503s on disabled writes and zero created
progress/review/attempt rows for public checks. Existing ownership, JWT and hosted
development-boundary cases were included. Auth UI/session cases use mocks; the
previous live Auth verification was not repeated and no account was created.

Screenshots are ignored local artifacts, not newly licensed educational images.
Browser checks used desktop Edge with viewport emulation, not physical devices,
Safari/Firefox or a complete assistive-technology audit. Source section components
were tested with isolated fixtures; the unapproved 30-chapter book was not made
public for visual testing. Actual hosted behavior still needs an authorized deployment.

## Changed files

- Backend: `app/repository.py`, `app/learning.py`, `app/sample_repository.py`.
- Backend tests: `tests/test_api.py`, `tests/test_database_api.py`, new `tests/test_public_learning.py`.
- Frontend shell/system: `src/main.tsx`, `src/components.tsx`, `src/api.ts`, `src/styles.css`.
- Frontend pages: `src/pages/Home.tsx`, `Catalog.tsx`, `Lesson.tsx`, `Explorer.tsx`,
  `Compare.tsx`, `Quiz.tsx`, `Review.tsx`, `Dashboard.tsx`, `Account.tsx`, new `KanjiDetail.tsx`.
- Frontend tests: `src/pages/Home.test.tsx`, `Lesson.test.tsx`, `Quiz.test.tsx`,
  `src/ui-readiness.test.tsx`, new `src/api.test.ts`, `src/public-access.test.tsx`,
  `src/pages/KanjiDetail.test.tsx`.
- Browser tests: `e2e/guest.spec.ts`, `e2e/learning.spec.ts`, new
  `e2e/public-experience.spec.ts`, and `playwright.config.ts` to force local-only API/Auth settings.
- Documentation: root README, docs index and this report.

## Publication and deployment limits

All 30 imported lessons still require their outstanding editorial decisions and
explicit publication approval, including related cards, sections and questions.
The existing four editorial requirements were not resolved or bypassed here.
Public empty pages are therefore expected on the current production dataset.
Source page provenance and visual mnemonics are not claims of historical etymology.

Personal writes remain disabled by the existing production setting; signin alone
cannot enable saving. Legacy synchronization is retained for old records, while
new anonymous rounds intentionally have no saved history. Manual grading still
has no implemented teacher workflow, so the interface does not promise one.

Separate Vercel frontend/backend projects, Root Directories, SPA rewrites,
requirements/lockfiles, Python version, strict browser environment validation and
backend configuration remain unchanged. New detail routes use the existing SPA
fallback. The existing API origin and exact backend CORS origins are still required.
No Supabase publication, hosted write enablement or deployment is authorized by
this report. Review the final source changes before any separately approved commit.
