# Repository publication and documentation maintenance

This checklist prepares a source-code portfolio; it does not authorize a push,
deployment, database operation or educational publication. Public source and
private teaching content have different disclosure and licensing boundaries.

## What belongs in the public repository

- Application source, migrations, synthetic tests, build manifests and
  credential-free templates.
- Current architecture/setup guides and sanitized, dated verification summaries.
- Clearly marked historical plans that explain design decisions without
  disclosing identities.

The textbook/PDF, extracted JSON, reference snapshots, private content previews,
raw logs, browser profiles, screenshots, credentials and account records do not
belong in public Git. Project-relative private-input paths in a guide describe
optional local files, not public downloads. Dated content hashes are provenance
metadata, not passwords or secret keys.

## Required before the first public push

1. Retain the owner's **All Rights Reserved** decision and the
   [root usage notice](../../README.md#copyright-and-usage). Do not add an
   open-source license or claim ownership of third-party materials. Keep
   protected educational inputs private and retain upstream obligations.
2. Inspect tracked files and history, not just ignore rules. An ignored file
   that was previously committed remains in history; rotate exposed secrets and
   clean history. The workspace had no Git metadata at the recorded review, so
   no history audit is claimed.
3. Keep private/, reference/, artifacts/, environment files, screenshots and
   test outputs excluded. Do not publish raw operational evidence to
   substantiate portfolio claims; sanitized dated reports describe its scope and
   limits.
4. Keep **content_audit.json**, **seed_validation.json** and
   **content/editorial-corrections.json** excluded. The publication audit added
   ignore rules and preserved their original bytes. Any later sanitized export
   needs its own review; do not force-add the protected originals.
5. Preserve the generic sample replacements recorded in the
   [publication audit](../reports/PUBLICATION_READINESS.md), and review the
   [third-party attribution guidance](THIRD_PARTY.md). The four original wording
   findings are resolved; new content changes need their own disclosure review.
6. Check all documentation paths/anchors, verify any unavailable external
   references and distinguish private-input requirements from a reproducible
   public sample.
7. Obtain explicit approval for the repository visibility/push. Publishing
   source does not publish lessons, enable hosted writes or authorize a
   deployment.

Known credentials, real account UUIDs/email addresses, personal absolute paths
and the cancelled test run's identifier are not required for a portfolio. Keep
the original local operational record separately if a public summary needs
redaction.

## Documentation ownership

| Category      | Purpose                                           | Maintenance rule                                             |
| ------------- | ------------------------------------------------- | ------------------------------------------------------------ |
| architecture/ | Current design, security and API/schema contracts | Update when implementation changes                           |
| guides/       | Current setup and operational procedures          | Keep prerequisites and safety boundaries explicit            |
| reports/      | Dated outcomes, counts, evidence and limitations  | Do not silently turn historical success into a current claim |
| archive/      | Superseded or cancelled plans and phase snapshots | Clearly mark as non-executable historical context            |

Use relative Markdown links. Commands and unlinked repository-relative file
paths are interpreted from the project root unless a guide says otherwise. Link
current state to the status summary; do not duplicate old endpoint tables or
conflicting feature claims. When moving a document, update the documentation
index and incoming references.

## Documentation generators

Application/generator code was outside this cleanup's permitted scope. Two
unchanged generators retain three legacy output paths:

| Generator              | Legacy output           | Canonical document                               |
| ---------------------- | ----------------------- | ------------------------------------------------ |
| scripts/write_erd.py   | docs/ERD.md             | [Schema diagram](../architecture/ERD.md)         |
| scripts/report_book.py | docs/CONTENT_AUDIT.md   | [Content audit](../reports/CONTENT_AUDIT.md)     |
| scripts/report_book.py | docs/SEED_VALIDATION.md | [Seed validation](../reports/SEED_VALIDATION.md) |

Those three paths are compatibility pointers. A fourth,
docs/CONTENT_PIPELINE.md, preserves the relative link emitted by the report
generator. This avoids modifying application code or leaving current references
broken, without duplicating the reports.

Regeneration overwrites pointers and may restore source titles, old phase
narration and root JSON metadata. Review generated output in a private working
copy, reconcile the canonical documents and repeat publication checks before
committing. Updating generator destinations and sanitization is a future code
change, not hidden in this docs reorganization.

## Verification claims

Private-source tests can skip in a public clone. Synthetic fixtures and
disposable database checks are not equivalent to live Supabase tests. Keep each
phase's test counts/scope dated, preserve negative results and pending editorial
requirements, and never invent an overall pass total or claim that a prepared
Vercel configuration has already been deployed.
