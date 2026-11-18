# Vercel deployment runbook - prepared, not deployed

Prepared 2026-11-18. No Vercel project was created/linked/deployed, no
repository was pushed, and no Supabase connection, data/schema/editorial change
or Auth test was made. The imported book and previous live verifications are
preserved. Deployment is a separate owner approval; publishing educational
content is a different approval again.

## Architecture and project settings

Use two Vercel projects. The existing static SPA and API stay independently
configured; The browser calls the backend directly with its Supabase bearer
token.

| Setting                              | Frontend project                  | Backend project                               |
| ------------------------------------ | --------------------------------- | --------------------------------------------- |
| Root Directory                       | `frontend`                        | `backend`                                     |
| Framework preset                     | Vite                              | FastAPI                                       |
| Install                              | `npm ci --include=dev`            | FastAPI default using `requirements.txt`      |
| Build                                | `npm run build`                   | FastAPI default; no migration/seed build hook |
| Output                               | `dist`                            | Leave unset; `index.py` exports ASGI `app`    |
| Runtime                              | Node 22.x, pinned in package/lock | Python 3.13, pinned in `.python-version`      |
| Include files outside Root Directory | OFF                               | OFF                                           |

Use the settings and vercel.json inside each project root. The repository-root
.vercelignore and frontend/.vercelignore explicitly allow frontend build inputs
under both project-relative and repository-relative paths. All other repository
roots and protected inputs remain excluded. Root Directory must still be
`frontend` or `backend`; deploying the workspace root is unsupported. The frontend
project file takes precedence under Vercel's documented monorepo rules. These
allowlists are verified offline against both path bases, not against a remote
deployment. This does not establish which filtering path caused the earlier
missing-manifest failure. Vercel documents
[ignore-file precedence](https://vercel.com/docs/deployments/vercel-ignore#monorepos), the
[FastAPI entrypoint](https://vercel.com/docs/frameworks/backend/fastapi),
[Python runtime selection](https://vercel.com/docs/functions/runtimes/python)
and
[Node version pin](https://vercel.com/docs/functions/runtimes/node-js/node-js-versions).

`VITE_API_URL=https://BACKEND_ORIGIN` produces requests to
`https://BACKEND_ORIGIN/api/v1/...`. Do not add `/api`, `/api/v1`, a trailing
slash, query parameters or credentials to that value. The frontend SPA rewrite
handles `/account`, `/dashboard` and lesson deep links; it deliberately excludes
`/api` and `/assets` so missing APIs/chunks cannot turn into index.html. The
Vite development proxy is for local use and is not a production proxy.

## Environment variables

Review the credential-free templates:

- `frontend/.env.production.example`: exactly three public VITE variables.
- `backend/.env.production.example`: runtime-only secret/configuration values.

Enter real values in the correct Vercel project's Environment Variables UI,
selecting Production and/or an explicitly planned Preview environment. Keep
secret values out of public channels, Git and VITE variables. Vite embeds public
configuration at build time; changing it requires a new frontend build. Backend
changes require a new backend deployment. Keep the existing local .env files
unchanged.

Frontend:

| Variable                      | Value                                       |
| ----------------------------- | ------------------------------------------- |
| VITE_API_URL                  | Actual stable backend HTTPS origin          |
| VITE_SUPABASE_URL             | Existing Supabase Auth project HTTPS origin |
| VITE_SUPABASE_PUBLISHABLE_KEY | Existing PUBLIC publishable/anon key        |

Only these three VITE names are allowed in production. Missing/placeholder
origins, loopback HTTP origins, server secrets and extra VITE variables fail the
build. `npm run build:demo` is an explicit local demo build, not a Vercel
deployment command. Use `npm run dev` with the local API for the offline demo.

Backend:

| Variable                      | Required setting                                            |
| ----------------------------- | ----------------------------------------------------------- |
| CONTENT_SOURCE                | database                                                    |
| DATABASE_URL                  | Existing Supabase transaction-pooler psycopg URL, port 6543 |
| DATABASE_SSLMODE              | require (encrypted, as in existing setup)                   |
| DATABASE_CONNECT_TIMEOUT      | 10                                                          |
| DATABASE_STATEMENT_TIMEOUT_MS | 5000                                                        |
| DATABASE_POOL_TIMEOUT         | 5                                                           |
| EXPOSE_SAMPLES                | false                                                       |
| CORS_ORIGINS                  | JSON array of exact approved frontend HTTPS origins         |
| SUPABASE_URL                  | Same existing project origin as the frontend                |
| SUPABASE_JWT_AUDIENCE         | authenticated                                               |
| ENABLE_USER_WRITES            | false                                                       |
| DEVELOPMENT_USER_IDS          | []                                                          |

Use the actual Connect dialog URL already configured locally; do not infer a
hostname or change the database password. URL-encode password characters if
constructing a URL manually. Mark DATABASE_URL sensitive in Vercel. Do not set
MIGRATION_DATABASE_URL, TEST_DATABASE_URL, JWT signing secrets or Auth
service-role/secret keys in either project. Optional SUPABASE_PUBLISHABLE_KEY on
the backend is a PUBLIC key only, needed only by the existing legacy HS256
verification fallback; asymmetric JWKS validation does not need it.

Pool size remains one per function process, zero overflow, bounded wait and
prepared statements disabled. No durable disk, background worker, startup schema
operation or book JSON is required. DATABASE_SSLMODE=require encrypts but does
not authenticate the certificate identity; optional verify-full/system or a
reviewed CA configuration needs an approved hosted check before claiming
certificate verification. Custom CA files are not silently included by the
deployment allowlists.

The hosted entrypoint enforces production safety even if automatic platform
environment variables are disabled. It rejects development UUIDs, sample mode,
sample exposure, migration credentials, placeholders, missing settings and wrong
pooler ports. Private access also remains disabled inside Learning even if
settings are unsafely copied later. Both Production and Preview deny the local
development content bypass.

## Routing, CORS and Auth callback

Set backend CORS_ORIGINS to an exact array such as
`["https://ACTUAL_FRONTEND_PROJECT.vercel.app"]`. Add only preview origins
actually approved for use. No wildcard or localhost production entry is
supported. Supabase sessions are browser-local, refreshed by the existing SDK;
API requests carry Authorization: Bearer and need no cross-origin application
cookie. CORS therefore stays credentials=false. Backend responses use
private/no-store caching headers.

The existing signup callback is `${window.location.origin}/account`. The
existing SDK uses PKCE, detectSessionInUrl, session persistence and automatic
refresh. There is no backend Auth callback to configure. The SPA rewrite
preserves the frontend `/account` path, including query parameters used for
confirmation-code exchange.

Once the final frontend hostname exists and launch is approved:

1. In the EXISTING Supabase project, add `https://FRONTEND_HOST/account` to Auth
   Redirect URLs. Retain working local entries if local development is still
   needed.
2. At the approved production cutover, set Site URL to the canonical frontend
   HTTPS origin.
3. Keep the already configured email provider, confirmation settings and working
   templates. Inspect only for a hardcoded localhost override if a custom
   template was previously used; do not redo completed setup or replace the
   working ConfirmationURL flow unnecessarily.
4. Use that same canonical origin for signup and confirmation. PKCE verifier
   storage is origin/browser scoped; local and deployed browser sessions are not
   shared.

These are changes for the NEW hostname, not instructions to repeat previous Auth
tests. See
[Supabase redirect configuration](https://supabase.com/docs/guides/auth/redirect-urls)
and [PKCE behavior](https://supabase.com/docs/guides/auth/sessions/pkce-flow).

Deployment Protection is separate from Supabase Auth. A protected backend
preview can block cross-origin requests before FastAPI; allowing OPTIONS alone
does not authenticate its subsequent GET/POST. Choose an approved reachable
backend domain/protection policy for each frontend/backend pair. Never put a
Vercel protection-bypass secret in VITE variables or disable protection
silently. See
[Vercel OPTIONS allowlist](https://vercel.com/docs/deployment-protection/methods-to-bypass-deployment-protection/options-allowlist).

## Files that may leave the workspace

Both project .vercelignore files allow only build/runtime inputs. Private
JSON/PDFs, .env files (including templates), caches, credentials, browser
profiles, screenshots, local tools and tests are not deployment inputs. Backend
import/editorial/seed modules and migrations are excluded. The function
excludeFiles rule adds a second boundary; its pattern is within Vercel's schema
length limit. No private directory is mounted as a public/static asset
directory.

.gitignore excludes the same protected local material while allowing the
credential-free production templates to be reviewed. Deployment excludes those
templates too. The
[Vercel ignore rules](https://vercel.com/docs/deployments/vercel-ignore) are
project-root specific; keep the outside-root source option OFF. Future files
should pass the offline audit before any deployment.

This workspace has no Git metadata, so no tracked-index/history audit can be
claimed. Choose repository visibility through an approved publication decision.
For a public portfolio, include source and sanitized documentation only; use the
[publication checklist](PUBLICATION.md) before any push. Before the first push,
inspect git status and tracked paths; .gitignore does not untrack earlier files
or clean existing remote history. Keep private/, reference/, artifacts/, .env
and test outputs out of the index. GitHub connection/push remains a separate
approved action.

## Exact deployment sequence - only after approval

1. Choose the Vercel team/plan, project names, canonical frontend/backend
   domains and region appropriate to the existing Supabase location. Confirm
   current plan limits and any plan/commercial-use requirements in Vercel. No
   plan or region was guessed here.
2. Choose an approved source workflow: an approved Git integration, or CLI
   deployment from the exact individual project root. Do not upload the
   workspace root or local dist. The local readiness build uses reserved test
   endpoints and is not a release artifact.
3. Configure the BACKEND project with the table above and its production
   variables. Use the intended exact frontend origin in CORS; replace it if
   Vercel assigns a different final hostname. Leave migration/build hooks unset.
   Deploy backend only under the approved deployment scope; record its stable
   HTTPS origin.
4. Configure the FRONTEND project/root, three public variables and Node 22.x.
   Use the backend origin from step 3. Deploy only under the approved deployment
   scope. Record the actual canonical frontend origin.
5. Reconcile CORS with that exact actual frontend origin and redeploy the
   backend if it changed. Configure the new Supabase redirect/Site URL values as
   described above. Register separate exact preview pairs if previews are
   approved; do not point arbitrary preview branches at a write-enabled
   production API.
6. Perform only deployment-specific, initially read-only acceptance checks:
   function startup/health, frontend deep-link refresh, `/account` callback
   routing, approved and unapproved CORS origins, real API response type,
   no-store headers and zero public book content. Health alone does not prove
   database connectivity or deployed PKCE behavior. Any fresh account/email or
   learning-write test needs its own approved scope; do not repeat existing
   suites automatically.
7. Keep ENABLE_USER_WRITES=false and every book lesson private/needs_review.
   Enabling ongoing account writes, promoting a preview to production,
   publishing lessons or changing database roles requires explicit owner
   approval. Roll back a faulty release using the previous Vercel deployment;
   never reset/reseed the existing database.

No migration, seed, import or editorial approval command is part of deployment.
The existing revision 0002 and 2,941 private rows were already verified in the
preceding phase; this preparation did not re-query or modify them. Empty public
catalogs are intentional: even the dedicated account has no hosted development
allowlist access.

## Readiness and actual remaining blockers

Local preparation verifies builds/configuration/package boundaries, not an
actual Vercel Linux function or deployed domain. Actual project/domain
variables, hosted cold start, network/TLS access, protection policy, callback on
the new origin and end-to-end routing remain pending an approved
preview/deployment. No frontend or backend deployment URL has been provisioned
by this task.

Earlier service verification used a privileged database connection. Application
visibility and owner predicates remain enforced, but server queries are not
evidence of RLS enforcement. A dedicated runtime role/privilege decision is
still a production-hardening item; no role, grant or Supabase-managed object was
changed here. Never upload an Auth admin key to solve it.

Four educational editorial requirements remain separate. This deployment plan
grants no publication approval, and the default public application intentionally
has no book lessons. See
[deployment readiness](../reports/DEPLOYMENT_READINESS.md) for the focused check
results and private operational evidence.
