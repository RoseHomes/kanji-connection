# Documentation cleanup - 2026-11-18

Scope: all 19 original docs/ Markdown files and the root README. This was a
documentation-only change. Application code, database schema/data, protected
datasets and editorial corrections were not modified. No deployment, Git push or
live application test was performed.

## Organization and moves

| Previous path under docs/     | Canonical destination                                                       | Disposition                                                                   |
| ----------------------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| API.md                        | [architecture/API.md](../architecture/API.md)                               | Current, expanded to include implemented learning/account routes              |
| ARCHITECTURE.md               | [architecture/ARCHITECTURE.md](../architecture/ARCHITECTURE.md)             | Current design; removed contradictory future-work claims                      |
| ERD.md                        | [architecture/ERD.md](../architecture/ERD.md)                               | Schema diagram preserved                                                      |
| SCHEMA_REVIEW.md              | [architecture/SCHEMA_REVIEW.md](../architecture/SCHEMA_REVIEW.md)           | Constraints preserved; implementation status corrected                        |
| SECURITY.md                   | [architecture/SECURITY.md](../architecture/SECURITY.md)                     | Current token/ownership/content/deployment boundaries                         |
| ENVIRONMENT.md                | [guides/ENVIRONMENT.md](../guides/ENVIRONMENT.md)                           | Consolidated variable reference and template links                            |
| DATABASE.md                   | [guides/DATABASE.md](../guides/DATABASE.md)                                 | Current connection/operation guide; links to dated evidence                   |
| AUTH_AND_PROGRESS.md          | [guides/AUTH_AND_PROGRESS.md](../guides/AUTH_AND_PROGRESS.md)               | Protocol details retained; stale phase narration removed                      |
| CONTENT_PIPELINE.md           | [guides/CONTENT_PIPELINE.md](../guides/CONTENT_PIPELINE.md)                 | Private prerequisites and regeneration caveat added                           |
| DEPLOYMENT.md                 | [guides/DEPLOYMENT.md](../guides/DEPLOYMENT.md)                             | Detailed runbook retained; source-publication policy clarified                |
| CONTENT_AUDIT.md              | [reports/CONTENT_AUDIT.md](CONTENT_AUDIT.md)                                | Counts/dispositions/provenance retained; source title/case disclosure reduced |
| SEED_VALIDATION.md            | [reports/SEED_VALIDATION.md](SEED_VALIDATION.md)                            | Exact rehearsal counts/hashes and scope retained                              |
| SUPABASE_MIGRATION_REPORT.md  | [reports/SUPABASE_MIGRATION_REPORT.md](SUPABASE_MIGRATION_REPORT.md)        | Unique migration evidence preserved with dated-scope notice                   |
| LIVE_PRIVATE_IMPORT_REPORT.md | [reports/LIVE_PRIVATE_IMPORT_REPORT.md](LIVE_PRIVATE_IMPORT_REPORT.md)      | Import/learning/cleanup evidence and limitations retained                     |
| UI_READINESS.md               | [reports/UI_READINESS.md](UI_READINESS.md)                                  | Actual UI fixes, checks and untested browsers retained                        |
| DEPLOYMENT_READINESS.md       | [reports/DEPLOYMENT_READINESS.md](DEPLOYMENT_READINESS.md)                  | Build/configuration outcomes and hosted limits retained                       |
| AUTH_PLAN.md                  | [archive/AUTH_PLAN.md](../archive/AUTH_PLAN.md)                             | Superseded Auth design, clearly historical                                    |
| LIVE_PROGRESS_TEST_PLAN.md    | [archive/LIVE_PROGRESS_TEST_PLAN.md](../archive/LIVE_PROGRESS_TEST_PLAN.md) | Cancelled plan, never executed live; symbolic run identifiers                 |
| IMPLEMENTATION_STATUS.md      | [archive/IMPLEMENTATION_HISTORY.md](../archive/IMPLEMENTATION_HISTORY.md)   | Rolling phase history preserved; current summary extracted separately         |

Nineteen original documents moved; three were archived. No historical report was
deleted. Exact original bytes and a SHA-256 manifest were retained in ignored
local storage before public-facing revisions, including details removed for
disclosure reasons.

## Consolidations and additions

- Root README is a concise overview/setup/architecture entry point with honest
  content, deployment and licensing limits. [docs/README.md](../README.md)
  indexes every canonical document.
- [Current status](IMPLEMENTATION_STATUS.md) replaces a mixed rolling log as the
  present-state reference; the original history remains archived with its test
  scopes/dates.
- Account endpoint details now live in one
  [API reference](../architecture/API.md). Historical test counts remain in
  reports/archive rather than repeated as current guide claims.
- Disposable PostgreSQL instructions moved from the database guide into
  [testing](../guides/TESTING.md). The password in that recipe is explicitly a
  local disposable fixture, not a project credential.
- Added [getting started](../guides/GETTING_STARTED.md) for portable sample
  setup and [publication maintenance](../guides/PUBLICATION.md) for
  disclosure/rights/generator review.
- Four tiny compatibility pages retain unchanged generator/output-link paths.
  They contain no duplicate report bodies; see
  [generator compatibility](../guides/PUBLICATION.md#documentation-generators).

## Disclosure and accuracy review

The reviewed Markdown contained no live password, access token, secret key,
personal email address, real account UUID or personal absolute filesystem path.
The cancelled proposal's operational run UUID and derived slug were replaced
with symbolic placeholders. Machine-specific setup commentary was removed.
Repository-relative optional private-input paths are documented as local
prerequisites, not hyperlinks or distributed files.

The public content audit withholds the full source chapter-title list and
dataset-specific correction values while retaining chapter/page counts,
dispositions, evidence methods, primary reference URLs and the four unresolved
editorial requirements. Full originals remain private. SHA-256 provenance values
were retained; these are not credentials.

Current API/security/architecture/schema/account guidance now reflects
implemented Auth, progress, quizzes, SRS, synchronization and hosted access
guards. Historical empty-table, unfinished-feature and earlier row-count
statements remain explicitly phase-scoped. No full editorial approval, public
course, teacher-grading endpoint or hosted release is invented.

## Validation

Local Markdown destinations, reference targets and heading fragments are checked
after relocation. Public source links resolve relative to each document.
External references are checked separately; loopback development examples are
not treated as live public services. Final checks after formatting produced:

| Check                                            | Result                                                                          |
| ------------------------------------------------ | ------------------------------------------------------------------------------- |
| Markdown files reviewed in the final structure   | 31, including the root README                                                   |
| Local destinations and heading references        | 171 checked; zero errors                                                        |
| Public external references                       | 25 successful HTTP responses                                                    |
| Loopback development examples                    | 2 documented, intentionally not contacted                                       |
| Credential/identifier/personal-path pattern scan | Zero remaining findings in reviewed Markdown                                    |
| Formatting                                       | All reviewed Markdown passed Prettier                                           |
| Snapshotted code/input files                     | 136 unchanged, including all 65 protected source files and the correction layer |
| Original documentation snapshots                 | All 20 byte/digest checks passed                                                |

Application/database/Auth suites were not rerun for documentation changes.

## Final structure

```text
README.md
docs/
  README.md
  architecture/   # 5 current design/reference documents
  guides/         # 8 setup/operation/maintenance guides
  reports/        # 8 status/verification/review documents
  archive/        # 3 historical documents plus archive index
  ERD.md                     # compatibility pointer
  CONTENT_AUDIT.md           # compatibility pointer
  SEED_VALIDATION.md         # compatibility pointer
  CONTENT_PIPELINE.md        # compatibility pointer
```

## Remaining publication work

Historical findings at the documentation-review date follow. The subsequent
[publication audit](PUBLICATION_READINESS.md) records the exclusion fixes,
wording replacements, All Rights Reserved decision and actual Git staging review.
These historical findings are not a statement of current licensing or Git status.

1. The root JSON audits contain source-derived metadata/historical flags; the
   protected correction layer and generated artifacts need a separate
   publication/rights review. They were not modified by this task and are not
   declared safe by the Markdown review.
2. Two unchanged generators still write three legacy documentation targets;
   compatibility pointers preserve paths. Generator routing/sanitization is a
   future code change.
3. No Git index/history exists here to audit, and no repository license has been
   chosen. Complete those release decisions before a public push; publishing
   docs does not authorize it.
