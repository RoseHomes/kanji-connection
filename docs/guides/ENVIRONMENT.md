# Environment configuration

Environment examples contain placeholders only. Do not overwrite an existing
configured file. Backend settings read backend/.env independently of the working
directory; process variables take precedence. Frontend Vite variables are public
build-time values.

Templates: [frontend development](../../frontend/.env.example),
[backend development](../../backend/.env.example),
[frontend production](../../frontend/.env.production.example),
[backend production](../../backend/.env.production.example).

| Variable                      | Location                       | Purpose/default                                                 |
| ----------------------------- | ------------------------------ | --------------------------------------------------------------- |
| CONTENT_SOURCE                | Backend                        | sample without configuration; database for stored content       |
| DATABASE_URL                  | Backend secret                 | SQLAlchemy psycopg transaction-pooler URL                       |
| MIGRATION_DATABASE_URL        | Authorized tooling only        | Separate direct/session connection; forbidden in hosted runtime |
| DATABASE_SSLMODE              | Backend                        | require or verify-full; default require                         |
| DATABASE_SSLROOTCERT          | Backend                        | Approved CA configuration when verifying TLS                    |
| DATABASE_CONNECT_TIMEOUT      | Backend                        | 1-30 seconds; default 10                                        |
| DATABASE_POOL_TIMEOUT         | Backend                        | 1-30 seconds; default 5                                         |
| DATABASE_STATEMENT_TIMEOUT_MS | Backend                        | 100-60000 milliseconds; default 5000                            |
| EXPOSE_SAMPLES                | Backend                        | false; explicit sample/free database opt-in only locally        |
| CORS_ORIGINS                  | Backend                        | JSON array of exact origins; no wildcard/path/trailing slash    |
| SUPABASE_URL                  | Backend                        | Exact HTTPS issuer/JWKS project origin                          |
| SUPABASE_JWT_AUDIENCE         | Backend                        | authenticated                                                   |
| SUPABASE_PUBLISHABLE_KEY      | Backend, optional public value | Legacy HS256 Auth-server verification only                      |
| ENABLE_USER_WRITES            | Backend                        | false by default; separate approval for hosted writes           |
| DEVELOPMENT_USER_IDS          | Local backend only             | Explicit authenticated UUID list; hosted deployments require [] |
| VERCEL                        | Platform/hosted boundary       | Hosted safety guard; index.py enforces it independently         |
| VITE_API_URL                  | Frontend public                | Exact HTTPS backend origin in production; blank local dev proxy |
| VITE_SUPABASE_URL             | Frontend public                | Existing Auth project HTTPS origin                              |
| VITE_SUPABASE_PUBLISHABLE_KEY | Frontend public                | Publishable/anon key, never secret/service-role                 |
| VITE_TURNSTILE_SITE_KEY       | Frontend, optional public value | Turnstile site key for login, signup, and reset requests         |
| TEST_DATABASE_URL             | Disposable test process only   | Guarded loopback database; never a hosted URL                   |

Production permits only the named VITE variables. Database credentials,
signing secrets, service-role keys and development identities never belong in
the browser bundle. Changing public values requires rebuilding the frontend.
Hosted setup also rejects placeholders, sample exposure, development bypasses
and migration credentials.

The API pool is one connection per process with zero overflow and prepared
statements disabled. require encrypts transport but does not authenticate the
certificate identity; verify-full needs an appropriate trusted CA setup. The
database guide owns connection instructions; the deployment guide owns hosted
settings and new-origin callback steps.

No credentials are needed for sample mode, synthetic unit checks or offline
planning. Valid-looking settings are not proof of connectivity. Public builds
require no private book source. Noto Sans Thai/Japanese currently load through
Google Fonts with system fallbacks; self-hosted licensed subsets remain an
optional hardening task.

See [getting started](GETTING_STARTED.md), [database](DATABASE.md),
[accounts](AUTH_AND_PROGRESS.md) and [deployment](DEPLOYMENT.md).
