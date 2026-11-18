# Deployment preparation results - 2026-11-18

Later backend-only review results appear in the final section. Earlier counts and
root-ignore/frontend behavior below are preserved as historical evidence, not
the current file-filter specification; use the current deployment runbook.

Status: prepared locally, **not deployed**. The chosen layout is two Vercel
projects: frontend/ (static Vite) and backend/ (FastAPI index.py). Exact
settings and owner steps are in [DEPLOYMENT.md](../guides/DEPLOYMENT.md). No
existing Supabase data, schema, grants, editorial layer, Auth settings or local
credential file was modified.

## Implemented

- Frontend Vercel configuration pins the Vite build, explicit development
  dependency installation and SPA deep links. API/assets are excluded from the
  HTML fallback. Node 22.x is pinned in package.json and its lock. Added only
  Node build typings; runtime frontend dependencies were not upgraded.
- Production frontend builds require exact HTTPS API/Auth origins and a public
  key. Extra VITE variables and known placeholder/unsafe API values fail closed.
  Local demo mode remains explicit and is not the Vercel build command.
- Backend has a FastAPI Vercel config, 30-second function limit,
  cache-control/private headers, a short schema-valid exclusion pattern and
  Python 3.13 selection. The hosted entrypoint enforces its boundary
  independently of automatic Vercel variables.
- Hosted startup rejects development UUID allowlists, sample mode/exposure,
  migration credentials, missing/placeholder values, non-HTTPS CORS and wrong
  pooler ports. Private development access is separately denied in Learning even
  after an unsafe settings copy. Local development behavior is preserved outside
  the hosted entrypoint.
- Pooling, prepared-statement disablement and verified JWT/owner predicates are
  preserved. Exact bearer-header CORS preflight is checked offline. Writes
  remain disabled by default.
- Project-level deployment allowlists exclude secrets, PDFs, private datasets,
  test artifacts, migrations and seed/editorial tooling. A root deployment
  excludes all source, requiring the correct individual project root. Template
  files are reviewable by Git but are not deployment inputs. New API responses
  retain existing public filters.
- CI build uses reserved offline fixture endpoints, with no project credentials.
  Existing guest UI assertions were aligned with the previously reviewed catalog
  navigation/API paths; no completed browser/Auth/integration suite was rerun in
  this preparation.

## Actual focused verification

| Check                                               | Result                                                       |
| --------------------------------------------------- | ------------------------------------------------------------ |
| New frontend deployment-configuration cases         | 11 passed                                                    |
| New backend hosted-configuration/CORS cases         | 15 passed                                                    |
| Frontend production TypeScript + Vite build         | Passed using nonsecret reserved fixture origins              |
| Production build with existing unset API origin     | Correctly rejected before bundling                           |
| Current Vercel schema checks for used config fields | Frontend and backend passed                                  |
| Offline Git/deployment boundary and rewrite audit   | Passed; no tracked-index claim                               |
| Reduced backend upload-tree import/health           | Passed in isolated process; database connect forbidden       |
| Python 3.13 Linux dependency resolution             | All 27 resolved packages have wheels; dry-run, zero installs |
| Changed-file ESLint/Ruff/format                     | Passed                                                       |
| Existing live DB/Auth/progress/import suites        | Not repeated; no Supabase connection made                    |

Only 29 frontend input files and 21 backend input files are included by the
audited allowlists. This is a source upload manifest, **not** a measured Vercel
function bundle: platform dependency installation and Linux packaging still need
an approved hosted build. The backend smoke copies only those allowed files and
imports the actual entrypoint, without local .env, tests, book JSON or
migration/import modules. It also verifies the hosted guard when VERCEL is
explicitly false, proving the entrypoint forces it on.

The frontend fixture bundle is a local check artifact, not a release build. It
is excluded from Git/uploads; Vercel must build again with actual per-project
environment variables. No real deployment origins have been invented or written
into local credential files.

Private evidence under private/deployment-review/: upload-manifest.json,
backend-smoke.json, config-validation.json, linux-dependencies.json,
missing-env-build.json and isolated backend-input directories. Do not upload
that directory or share raw resolver/log files.

## Remaining decisions and approval gates

| Item                         | Required owner action / limitation                                                                                                                                                                                                            |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Actual projects and domains  | Choose the team/plan, roots, stable frontend/backend domains and approved region; none was created or linked.                                                                                                                                 |
| Hosted values                | Enter the existing project URL/public key and existing DB secret into the correct Vercel project, plus the new actual API/CORS origins. Keep secrets in the approved local/hosted secret store.                                               |
| New Auth origin              | Add the deployed /account redirect; update Site URL at approved cutover. Keep the completed provider/confirmation setup.                                                                                                                      |
| Preview protection           | Choose a reachable API/protection policy for the approved frontend/backend pair; OPTIONS access alone does not bypass protection on real requests.                                                                                            |
| Git workflow                 | This workspace has no Git metadata; ignore rules were evaluated offline. Private repository setup, index/history inspection and any push/connection remain separate actions.                                                                  |
| Actual Vercel function/build | Cold starts, hosted Linux packaging, network/TLS, domain routing and deployed callback behavior cannot be claimed without deployment authorization.                                                                                           |
| Runtime database privileges  | Earlier service verification used a privileged connection; RLS enforcement is not inferred. A dedicated runtime role is a production-hardening decision; no role/grant changes were made. Server predicates/read-only routes remain enforced. |
| Ongoing writes               | ENABLE_USER_WRITES stays false. An approved one-off integration test did not authorize enabling continuous production writes.                                                                                                                 |
| Content                      | All 30 lessons remain private/needs_review; zero publication approval is inferred. Four educational editorial requirements remain separate.                                                                                                   |

Deployment approval permits only its agreed preview/production scope. Publishing
lessons, enabling ongoing learning writes or changing Supabase privileges is a
separate decision. This preparation requests no credentials and executes none of
those actions.

## Repeat only a relevant changed check

```powershell
node scripts/audit_deployment.mjs
.\.venv\Scripts\python.exe scripts/check_backend_package.py
.\.venv\Scripts\python.exe -m pytest -q backend/tests/test_deployment_config.py
# frontend/:
npx vitest run src/deployment-config.test.ts
```

Run the real production npm build only after supplying its valid production
variables. Do not migrate, seed or import as part of building or deploying. The
earlier imported book remains in the existing database; deployment packaging
needs none of its source files.

## Backend-only follow-up - 2026-11-18

The current official FastAPI and Python Runtime documentation confirms that
`index.py`, `tool.vercel.entrypoint = "index:app"`, Python 3.13 selected by
`.python-version`, and runtime dependencies from requirements.txt are supported.
No entrypoint, application behavior, runtime dependency pin or backend/vercel.json
change was necessary. Exact project settings and environment names are recorded
in the [deployment runbook](../guides/DEPLOYMENT.md#environment-variables).

The backend allowlist previously handled only project-relative paths; the shared
root fallback permitted frontend inputs alone. Both now explicitly preserve the
backend runtime files under either tested base while excluding book/editorial
tooling, real environment files, certificates, local databases, tests, migrations
and private inputs. The frontend-specific ignore file is unchanged. This is a
local packaging correction, not a claim about the earlier Vercel filter internals.

The package smoke helper also clears inherited Python module paths and asserts
that imports come from the filtered copy. Network/database connection functions
are blocked during the smoke check. It still tests hosted safety with VERCEL
disabled, ensuring `index.py` applies the boundary independently.

| Check                                                                                 | Result                                                                                                                    |
| ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `node scripts/audit_deployment.mjs`                                                   | 4 backend path-base combinations and 4 existing frontend combinations passed; 21 backend/29 frontend input files retained |
| `python scripts/check_backend_package.py`                                             | Isolated reduced-package import, hosted guards and health response passed; zero database connections                      |
| `pytest tests/test_deployment_config.py tests/test_configuration.py -q` from backend/ | 27 passed; one existing TestClient dependency deprecation warning                                                         |
| Linux CPython 3.13 runtime dependency dry-run                                         | 27 packages resolved to wheels; no pytest/Ruff/Alembic, zero installs                                                     |
| Current official Vercel schema checks                                                 | Used framework, duration, exclusions and header fields passed; no whole-schema meta-validation claim                      |
| Changed Python helper Ruff lint/format and JS syntax                                  | Passed                                                                                                                    |

The SQLAlchemy engine remains lazy, with a one-connection pool, zero overflow,
bounded timeouts and psycopg prepared statements disabled for the transaction
pooler. No startup migration, seed or import exists. Supabase JWT verification
uses the configured issuer and audience; legacy verification conditionally needs
a public publishable/anon key. CORS is restricted to exact frontend HTTPS origins.
Private lessons remain unpublished and hosted development access remains disabled.

Remaining hosted checks: actual Vercel Linux execution/cold starts, pooler
reachability/TLS, runtime-role privileges and new-origin integration. A successful
offline health check proves none of those. No Supabase connection, role/grant/data
change, Auth test, schema migration, commit, push or deployment was performed.
