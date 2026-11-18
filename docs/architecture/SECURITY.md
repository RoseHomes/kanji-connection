# Security and publication boundaries

## Authentication and authorization

Supabase JS handles browser sign-in, session storage/refresh and local signout.
FastAPI verifies bearer tokens with the project's JWKS for ES256/RS256, or
verifies legacy HS256 tokens through Auth using a public key. Claims include
signature, issuer, audience, time, authenticated role and UUID subject.
Browser-supplied owner IDs and scores are not trusted.

Every learning query is owner scoped. PostgreSQL mutations use transaction-local
verified context, per-owner advisory locks and optimistic versions. Quiz retry
UUIDs are unique per owner. Guest/cloud sync previews both states, rejects stale
snapshots and requires explicit conflict choices; it does not merge counts or
delete local data automatically.

All application tables enable RLS; Supabase owner policies/FKs complement the
API filters. A privileged database connection can bypass RLS. Owner checks and
publication filters must therefore remain enforced in application code. The live
service probe is evidence of those predicates, not proof that RLS blocked a
privileged connection. A least-privilege runtime credential remains a
production-hardening decision.

## Content and deployment

Book content stays private/needs_review, with no full editorial chapter
approval. Catalog visibility is separate from detail access. Local previews
require an explicit verified development identity; hosted Preview/Production
reject development allowlists, sample mode/exposure and migration credentials.
The same account has no hosted preview bypass.

No PDF/private dataset is needed in the hosted runtime or frontend bundle.
Deployment allowlists exclude private sources, credentials, tests, screenshots,
browser profiles and operational import/migration tools. Only public Supabase
configuration belongs in VITE variables; production builds reject other VITE
names and invalid API origins. See
[environment configuration](../guides/ENVIRONMENT.md) and
[deployment](../guides/DEPLOYMENT.md).

## Operational controls and limits

- Public database reads use READ ONLY transactions and bounded
  query/pool/connect timeouts.
- Database mode fails closed; database/config errors do not reveal SQL or
  credentials.
- CORS uses exact approved origins. Responses use private/no-store headers on
  Vercel.
- Startup never migrates, imports or publishes. CLI write opt-ins are guards,
  not authorization.
- Account writes default off; one-off verification did not authorize ongoing
  production writes.
- Immediate revocation of an already issued access token is not implemented.
  Expiry and refresh behavior remain important; browser storage is not a custom
  password store.
- Production rate-limit policy, a least-privilege runtime role and actual hosted
  behavior remain release decisions. No completed penetration or
  assistive-technology audit is claimed.

Use a disposable loopback database for destructive integration tests. Never use
a hosted database URL, tunnel or existing application database as the test reset
target. See [testing](../guides/TESTING.md).

## Repository disclosure

Never commit credentials, actual account identifiers, local machine paths,
private evidence, source book excerpts or protected images. Source edition
hashes are audit metadata, not credentials. Project-relative private-input paths
describe optional local files; they do not make those inputs public. Follow the
[publication checklist](../guides/PUBLICATION.md), including non-Markdown
generated artifacts and content rights.

If a secret enters Git history, revoke/rotate it and clean the history before
publication; ignore rules do not remove tracked content. Report sensitive
details through an approved private maintainer channel rather than a public
issue. The application is **All Rights Reserved**; see the
[root usage notice](../../README.md#copyright-and-usage). Third-party licenses
remain applicable, and protected textbook/reference inputs are not licensed for reuse.
