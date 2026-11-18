# GitHub publication safety audit - 2026-11-18

**Decision: ready for an approved first commit and public source push.**
The four content findings are resolved, the owner selected All Rights Reserved,
and a fresh Git index has been reviewed. No commit, push, deployment, history import,
history rewrite or Supabase operation was performed. This decision covers the
audited public source snapshot, not educational publication or hosted readiness.

## Git and file scope

The initial audit took place without a Git repository. On explicit owner authorization,
a fresh repository was initialized on `main` and 158 reviewed public files were staged.
The complete staged file list and added diff were inspected programmatically, with
raw evidence retained privately. The staged source scan reads index blobs rather
than relying only on working-tree contents.

There is no HEAD commit, commit/tag object, ref or configured remote. Nothing was
imported from the intentionally removed repository. This verifies the fresh local
repository only; it does not make claims about an unavailable former or remote history.

The initial post-exclusion inventory contained 156 text source/configuration/
documentation files, zero binary candidates, zero symlinks and no nonstandard
frontend dependency download sources. The two audit documents added afterward
are also included in the final disclosure/link review, bringing the final inventory
to 158 candidate files. All 182 local Markdown links resolve within that public set.

### Safe fixes applied

.gitignore now additionally excludes:

- `/content_audit.json`: source-derived chapter metadata/audit detail.
- `/seed_validation.json`: edition-bound and historical operational metadata.
- `/content/editorial-corrections.json`: protected, edition-bound source values.
- Case variants of PDF extensions, SQLite files and additional local credential stores.

The files themselves were not deleted, moved or edited. Existing private/,
reference/, environment, certificate/key, browser/test-artifact and dependency
exclusions were retained. Credential-free environment examples remain reviewable.
The public content/book.schema.json contains structure rather than chapter-title values.

Ignore rules protect ordinary additions, not force-adds or files already tracked
elsewhere. The actual initial index was reviewed in the final follow-up below. No claim
that ignored material is technically impossible to commit is made.

## Credential and disclosure checks

All prospective text files were checked for configured database secrets/project
configuration, known private test-account identifiers, common secret/token/private-key
patterns and personal absolute paths. No real configured secret or account identifier
was found. Token-like negative-test strings, reserved-domain example addresses and
repeated synthetic UUID fixtures were reviewed as fixtures, without printing their values.

README, documentation, deployment/environment templates, CI, application source and
configuration were included. Private raw logs, browser profiles, account state and
book/reference inputs are excluded rather than copied into the public audit report.
Pattern/exact-match scanning reduces disclosure risk; it is not an assertion that
an unavailable Git history or every possible secret format has been verified.

## Original content-clearance findings (resolved by replacement)

Exact matching against private inputs identified these public-source review locations.
Only locations/counts are disclosed, not the matched educational strings:

| Candidate file                                                                       | Finding                                                                                  | Required decision                                                                  |
| ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| [backend/app/catalog.py](../../backend/app/catalog.py#L42)                           | 19 exact chapter-title matches; its comment attributes metadata to a build specification | Confirm independent provenance/right to publish, or authorize replacement metadata |
| [backend/tests/test_book_pipeline.py](../../backend/tests/test_book_pipeline.py#L58) | One non-title source string of at least 20 characters                                    | Confirm permitted fixture provenance or authorize a synthetic replacement          |
| [frontend/e2e/guest.spec.ts](../../frontend/e2e/guest.spec.ts#L12)                   | One exact title match                                                                    | Resolve consistently with curriculum metadata                                      |
| [frontend/src/pages/Home.tsx](../../frontend/src/pages/Home.tsx#L164)                | One non-title source string of at least 20 characters                                    | Confirm independent/permitted wording or authorize replacement                     |

Overlap is not proof of copying, protected expression or a licensing violation.
The audit cannot establish authorship from a source comment or absent Git history.
The initial audit left these runtime/test files unchanged pending authorization.
The owner subsequently authorized scoped replacements, recorded below. This table
preserves the original finding locations and does not describe current blockers.

### Authorized replacement follow-up - 2026-11-18

- `backend/app/catalog.py`: removed the entire book-like title/anchor inventory.
  Thirty generic numbered demo slots preserve IDs, slugs, parts, filtering and the
  three-card sample in slot 2. The sample title and navigation summary are newly
  written UI copy, not adapted textbook explanations.
- `backend/tests/test_book_pipeline.py`: replaced the source-derived negative
  parser fixture with an English UI string without a word/reading pair.
- `frontend/e2e/guest.spec.ts`: updated both sample-title assertions; the flashcard
  answer assertion and desktop/mobile interaction coverage remain intact.
- `frontend/src/pages/Home.tsx`: replaced the flagged feature heading with generic
  application-demo wording; the interaction and surrounding layout remain intact.

The repeated disclosure scan found **zero source-title matches, zero source-string
overlap findings and zero new non-fixture sensitive findings** across the prospective
public set. This is the same exact-match scope as the initial audit, not a blanket
legal clearance for all possible wording. Existing synthetic negative-test fixtures
remain classified as fixtures.

Database mode still selects `DatabaseRepository` and serializes stored lesson titles;
the learning catalog likewise uses stored titles with the existing privacy gates.
No production title fallback was introduced. Private book inputs, editorial corrections,
environment files and all other protected files outside the four authorized source
edits retain their recorded hashes. No live database access was needed.

Focused follow-up verification:

| Check                                                              | Result                                                           |
| ------------------------------------------------------------------ | ---------------------------------------------------------------- |
| Sample API, database API and book pipeline tests                   | 33 passed, 1 skipped, 7 PostgreSQL cases deliberately deselected |
| Home component test                                                | 1 passed                                                         |
| Guest browser flows, including mobile search and persistent review | 3 passed                                                         |
| Ruff lint and formatting of changed Python files                   | Passed                                                           |
| ESLint of changed frontend files and TypeScript checking           | Passed                                                           |

The skipped case is the existing PostgreSQL-only RLS/transaction check under SQLite;
no live PostgreSQL suite or full application suite was repeated. Backend tests retained
the existing dependency deprecation warning.

## Dependency and attribution review

The owner selected **All Rights Reserved** for the application. The
[root copyright and usage notice](../../README.md#copyright-and-usage) limits
public viewing to portfolio/evaluation purposes and requires prior permission for
copying, redistribution, modification and commercial reuse, subject to applicable
law and GitHub's platform terms. No owner name or open-source license was invented.
Private educational materials are not licensed for reuse. Third-party ownership,
licenses and attribution obligations remain unaffected.

292 frontend lock entries declare licenses. All 38 inspected local Python distributions
have license metadata/classifiers/files. No undeclared/UNLICENSED package was identified.
No dependency binary or private dictionary snapshot is in the candidate Git set.

The [third-party guide](../guides/THIRD_PARTY.md) records the license groups and primary
terms: EDRDG data attribution/share-alike, restricted reference materials, OFL fonts,
and LGPL/BSD/MIT/ISC/Apache/MPL distribution considerations. Dependency manifests alone
are not a grant to redistribute a textbook, reference spreadsheet or derived dataset.
Future built/binary releases need their applicable upstream notices; those are separate
from this source-only push and no deployment was performed.

## Clean-public-source verification

No existing repository was available for a literal git clone. A fresh Git-equivalent
export was created from the audited candidate list, with no private/, reference/,
actual .env, root derived audits, correction layer, node_modules or project venv copied.

| Check in the clean export                            | Result                                                  |
| ---------------------------------------------------- | ------------------------------------------------------- |
| New isolated Python venv and dependency installation | Passed                                                  |
| Backend public-source tests                          | 79 passed, 51 skipped, one existing deprecation warning |
| Backend sample import/startup                        | Passed without private inputs or credentials            |
| Fresh npm ci from the lock                           | Passed                                                  |
| Production TypeScript/Vite build                     | Passed with reserved, nonsecret fixture origins         |

Private-input/disposable-PostgreSQL tests skip rather than requiring protected content.
No live Auth, Supabase persistence/import test or hosted database operation was repeated.
The fixture frontend output is not a real deployment artifact. The export shows that
excluding the three derived/edition-specific JSON files does not break the sample build.

All 144 protected application, configuration, dataset, correction and environment-file
hashes matched the original audit snapshot before the authorized follow-up. The follow-up
permits only the four named source replacements. Of the 144 baseline files, 141 still
match and three contain authorized changes. The browser test was outside that baseline;
comparison with the preserved clean export confirms only its two title assertions changed.
Raw manifests, findings, build logs and source fingerprints stay private.

## Final licensing and staged-publication review - 2026-11-18

Updated public files: `README.md`, `.gitignore`, `docs/README.md`,
`docs/architecture/SECURITY.md`, `docs/guides/PUBLICATION.md`,
`docs/guides/THIRD_PARTY.md`, `docs/reports/DOCUMENTATION_REVIEW.md` and this report.
No open-source license file was added and no copyright owner was named.

| Check                                    | Result                                                                                                                                               |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Fresh local repository                   | Initialized on `main`; no commits, imported history or remotes                                                                                       |
| Staged inventory and complete added diff | 158 files, all additions; working tree matches index                                                                                                 |
| Excluded inputs                          | No protected dataset, PDF, real environment file, credential store, local database, browser artifact or dependency/build directory staged or tracked |
| Index-blob source disclosure scan        | Zero source-title/source-string findings; all four original findings remain resolved                                                                 |
| Index-blob sensitive-value scan          | Zero non-fixture sensitive findings; synthetic negative-test fixtures remain documented                                                              |
| Documentation                            | All Rights Reserved notice consistent in current guidance; historical reports explicitly identified as historical                                    |
| Private source and editorial files       | Unchanged; no live Supabase access or data modification                                                                                              |

The staged-file review verifies ignore rules and every staged path, not a claim that
ignore rules can prevent a future force-add. Additional certificate extensions are
excluded without removing any local files. Raw staged manifests/diffs and build logs
remain under ignored private audit storage.

The exact staged application snapshot is exported into an isolated directory without
private inputs. Backend compilation/sample startup and a fresh frontend dependency
installation plus TypeScript/Vite production build all passed there. All 188 local
Markdown links resolve within the public file set, and 124 non-Markdown files in the
final index match the built snapshot. Existing isolated
public Python dependencies are reused only after requirements equality is verified.
Reserved nonsecret fixture origins are used for the build; this output is not a
deployment artifact. Application integration suites and live services are not retested.
Documentation-only updates afterward do not change the built application snapshot.

Real lesson metadata continues to come from PostgreSQL in database mode through the
existing repository and learning APIs. Hosted privacy checks and lesson editorial
statuses are unchanged. No private curriculum is embedded in the generic sample catalog.

**Remaining publication blockers: none identified in the reviewed source snapshot.**
Stop here until a first commit and push are explicitly authorized. A commit is still
required before Git can push this unborn branch. Do not import old history, add private
files or change the selected rights notice as part of that next step. Any later file
changes require a fresh staged review; educational publication and deployment remain
separate decisions.
