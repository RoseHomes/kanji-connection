# Kanji Connection documentation

Start with the [project overview](../README.md) and
[getting started](guides/GETTING_STARTED.md). The public clone runs an
independently authored sample without book files or credentials. Private source
data, accounts and raw verification artifacts are not distributed here.

The application features and private staging import have been verified in
separate phases. No book chapter has full editorial approval, no hosted release
is claimed, and deployment, ongoing writes and content publication remain
separate decisions. See the [current status](reports/IMPLEMENTATION_STATUS.md)
for exact scope and limits.

## Architecture

| Document                                            | What it answers                                                          |
| --------------------------------------------------- | ------------------------------------------------------------------------ |
| [System architecture](architecture/ARCHITECTURE.md) | How UI, Auth, API, persistence and the content pipeline fit together     |
| [API reference](architecture/API.md)                | Public, local-development and authenticated endpoints and error behavior |
| [Database diagram](architecture/ERD.md)             | Tables, keys and relationships in the 16-table learning schema           |
| [Schema review](architecture/SCHEMA_REVIEW.md)      | Constraints, supported capabilities and remaining domain limits          |
| [Security boundaries](architecture/SECURITY.md)     | Tokens, ownership, private content, RLS caveats and disclosure rules     |

## Guides

| Document                                                  | Use it when                                                                               |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| [Getting started](guides/GETTING_STARTED.md)              | Running the public sample on Windows, macOS or Linux                                      |
| [Environment configuration](guides/ENVIRONMENT.md)        | Choosing local/hosted variables and handling public versus secret configuration           |
| [Database guide](guides/DATABASE.md)                      | Configuring pooling, reads, ownership and guarded database operations                     |
| [Accounts and learning](guides/AUTH_AND_PROGRESS.md)      | Understanding sessions, local account development, scheduling and sync conflicts          |
| [Content pipeline](guides/CONTENT_PIPELINE.md)            | Maintaining authorized structured inputs, overlays, provenance and insert-only plans      |
| [Testing](guides/TESTING.md)                              | Selecting focused checks and using disposable PostgreSQL safely                           |
| [Deployment runbook](guides/DEPLOYMENT.md)                | Preparing the two Vercel projects after deployment approval                               |
| [Publication and docs maintenance](guides/PUBLICATION.md) | Reviewing a public portfolio, content rights, tracked history and generator compatibility |
| [Third-party attribution](guides/THIRD_PARTY.md)          | Dependency licenses, dictionary/reference rights and distribution boundaries              |

## Verification reports

Reports are dated evidence, not repeatable work orders. Do not combine their
test counts or infer editorial/production approval from structural validation or
a local build.

| Document                                                                  | Evidence retained                                                                      |
| ------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| [Current implementation status](reports/IMPLEMENTATION_STATUS.md)         | Reconciled feature status and phase-by-phase verification                              |
| [Migration verification](reports/SUPABASE_MIGRATION_REPORT.md)            | Revision 0002, constraints, RLS/privilege checks and pre-import empty-table state      |
| [Content audit](reports/CONTENT_AUDIT.md)                                 | Structural counts, audit dispositions, references and four open editorial requirements |
| [Seed validation](reports/SEED_VALIDATION.md)                             | Edition hashes, local rehearsal counts, rollback and idempotency                       |
| [Private import and live learning](reports/LIVE_PRIVATE_IMPORT_REPORT.md) | 2,941 committed private rows, scoped learning results and four-row cleanup             |
| [Frontend readiness](reports/UI_READINESS.md)                             | Actual UI fixes, responsive inspection, focused cases and device/browser limits        |
| [Deployment readiness](reports/DEPLOYMENT_READINESS.md)                   | Configuration/build/package checks and unresolved hosted decisions                     |
| [Documentation cleanup](reports/DOCUMENTATION_REVIEW.md)                  | Moves, consolidations, disclosure review and link-validation outcome                   |
| [Publication safety audit](reports/PUBLICATION_READINESS.md)              | All Rights Reserved notice, staged-file safety review and clean-source build evidence  |

The [public learning redesign report](reports/PUBLIC_LEARNING_REDESIGN.md) records
the current access matrix, UI system, regression tests and publication restrictions.

## Archive

The [archive index](archive/README.md) identifies superseded Auth planning, the
cancelled temporary-fixture test and the previous implementation phase log. They
preserve unique history without serving as current instructions.

## Compatibility references

Four short legacy pages remain for unchanged generators: [ERD](ERD.md),
[content audit](CONTENT_AUDIT.md), [seed validation](SEED_VALIDATION.md) and
[content pipeline](CONTENT_PIPELINE.md). Follow their links to the canonical
categories. See
[generator maintenance](guides/PUBLICATION.md#documentation-generators) before
regenerating them.

All command snippets assume the repository root unless stated otherwise.
Private-input paths are descriptions, not public file links. Publishing this
documentation does not include the dataset or grant content reuse rights;
complete the publication checklist first.
