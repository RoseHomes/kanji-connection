# Testing and verification

Run the smallest checks relevant to a change. Dated reports record separate
scopes; their pass counts must not be added into a purported current full-suite
total. This documentation cleanup performs link/disclosure checks, not new
Auth/database testing.

## Frontend

From frontend/:

```sh
npm ci
npm run lint
npm run typecheck
npx vitest run src/deployment-config.test.ts
```

Use `npm test` for the full unit suite when appropriate. `npm run build`
requires the three valid public production variables; `npm run build:demo` is an
explicit local demo bundle. Run `npx playwright test` for the local sample
browser suite when relevant; it starts its own servers, uses Edge
locally/Chromium in CI and disables live Auth. Ensure ports 8000/5173 are free.
Production fixture builds in reports are not deployable release artifacts;
Vercel must build with actual approved environment values.

## Backend

From backend/, using the project's venv interpreter:

```powershell
..\.venv\Scripts\python.exe -m pytest -q tests/test_deployment_config.py
..\.venv\Scripts\python.exe -m ruff check . ../scripts
```

Use `python -m pytest -q` for broader changes. Default tests use synthetic
data/in-memory SQLite; Auth/JWKS are mocked with real generated signing keys.
Some book-specific tests skip without the separately held inputs. No private
book file should be added to make public CI pass. With no TEST_DATABASE_URL,
disposable PostgreSQL cases also skip.

## Disposable PostgreSQL only

The harness deliberately resets public and a test auth schema. It accepts only
literal 127.0.0.1, database kanji_test, the expected driver and no URL query
overrides. Never use Supabase, an existing database or a forwarded/tunnelled
remote port.

The literal password below is a disposable fixture, not a credential for any
project. With Docker running, from the root in PowerShell:

```powershell
docker run --detach --rm --name kanji-connection-local-tests `
  -e POSTGRES_USER=kanji_test -e POSTGRES_PASSWORD=local-test-only -e POSTGRES_DB=kanji_test `
  -p 127.0.0.1::5432 postgres:17
docker exec kanji-connection-local-tests pg_isready -U kanji_test -d kanji_test
$testDbPort = (docker port kanji-connection-local-tests 5432/tcp).Split(':')[-1]
$env:TEST_DATABASE_URL = "postgresql+psycopg://kanji_test:local-test-only@127.0.0.1:$testDbPort/kanji_test"
Set-Location backend
..\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:TEST_DATABASE_URL
docker stop kanji-connection-local-tests
```

Wait for pg_isready before testing. The local auth stub tests policy mechanics,
not live Supabase provider configuration. Do not treat a destructive test run as
a migration plan.

## Optional private operational checks

Private read-only UI review and edition-bound content rehearsals require
authorized local inputs and account configuration; they are not public-clone
prerequisites. The complete seed rehearsal uses SQLite and rolls back. Remote
imports, new accounts/emails or learning writes require a separately reviewed
operational scope; do not repeat completed live tests as a build step. See
[content pipeline](CONTENT_PIPELINE.md) and
[recorded verification](../reports/IMPLEMENTATION_STATUS.md#verification-by-phase).

Offline deployment helpers are `node scripts/audit_deployment.mjs` and
`python scripts/check_backend_package.py`; neither connects to Supabase or
deploys. The latter imports only allowed source inputs in a fresh isolated tree
and forbids DB connects.
