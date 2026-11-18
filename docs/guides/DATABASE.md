# Database guide

The application uses SQLAlchemy/Alembic with Supabase PostgreSQL. The existing
private staging environment reached revision 0002 and imported 2,941 book rows
under separate authorization. These are dated verification results, not
permission to rerun those operations. See the
[migration report](../reports/SUPABASE_MIGRATION_REPORT.md),
[import report](../reports/LIVE_PRIVATE_IMPORT_REPORT.md),
[ERD](../architecture/ERD.md) and
[schema capabilities](../architecture/SCHEMA_REVIEW.md).

## Configure a development connection

Keep credentials in backend/.env or an approved secret manager, never in
documentation, logs, screenshots or public VITE variables. Copy the
[example](../../backend/.env.example) only if the destination does not exist.

1. Use the target project's Supabase Connect dialog and select its transaction
   pooler. Copy the actual hostname/user/database; do not infer a project
   endpoint.
2. Use the driver prefix `postgresql+psycopg://` and port 6543. URI-encode
   reserved password characters when constructing a URL manually. This is a
   database password, not an Auth publishable/anon or service-role key.
3. Select CONTENT_SOURCE=database and EXPOSE_SAMPLES=false. Set the Auth/CORS
   values separately as described in the [environment guide](ENVIRONMENT.md).
4. Only authorized migration tooling uses MIGRATION_DATABASE_URL, with a
   direct/session connection on the appropriate port rather than
   transaction-pooler port 6543. Do not configure that credential in a hosted
   application runtime.
5. Configure encrypted transport. require encrypts; verify-full also needs
   trusted certificate validation. Keep certificate keys private and review any
   CA packaging.

Backend settings load the project-relative environment file by absolute module
location; process values override it. Restart the process after changes. Prefer
a scoped runtime credential separate from migration access; a privileged
connection can bypass RLS.

## Runtime behavior

Engine construction is lazy. Startup and `/health` do not query, migrate or seed
the database. Public requests use READ ONLY transactions with bounded query
timeouts; unavailable configuration/storage returns a redacted 503 without
sample fallback. Pooling uses one connection, zero overflow, pre-ping/recycling
and disabled psycopg prepared statements. Migration tooling uses NullPool.

Publication/access filters apply independently to lessons, characters,
vocabulary, sections and relationships. Catalog-visible metadata is separately
controlled. Account queries derive ownership from verified tokens and use
per-owner transaction locks; version checks reject stale writes. Normal account
writes remain disabled by default. See [account behavior](AUTH_AND_PROGRESS.md).

## RLS and ownership

All 16 application tables and Alembic tracking metadata enable RLS. Client table
privileges are revoked; content tables have no anonymous read policies. When
Supabase's external auth schema is available, the three owner tables have owner
policies and auth.users foreign keys. Plain PostgreSQL without that schema
remains deny-all for those policies.

Backend publication/owner predicates remain necessary for privileged
connections. Do not equate a successful service probe with RLS enforcement,
grant browser DML access casually, or modify Supabase-managed tables.
Operational principal details remain private.

## Safe inspection and guarded operations

These commands do not connect or modify data; run from backend/:

```powershell
..\.venv\Scripts\python.exe -m app.config
..\.venv\Scripts\python.exe -m alembic upgrade head --sql
```

The older `app.seed --mode validate` and `--mode dry-run` commands concern
independent demonstration data, not the book. The
[book pipeline](CONTENT_PIPELINE.md) owns its separate validation/import
process. The generic importer preserves existing editorial changes as conflicts.
The guarded remote caller additionally requires exact hashes/schema/empty-table
assumptions and controls locking/commit. Do not rerun it against the populated
staging database.

Online migration/write opt-ins are safeguards, not approval. Migration 0001 is
retained; 0002 adds the domain and private defaults. Alembic makes repeated
upgrades a no-op, but a downgrade can delete data and is not a production
rollback strategy. Deployment performs no migration or import. Back up/review
existing state before separately authorized changes.

## Testing and evidence

Destructive integration tests reset only a validated disposable loopback
database and fake auth schema. Never target a hosted project or a tunnel. The
full container recipe and skip behavior are maintained in the
[testing guide](TESTING.md), not duplicated here. Private schema snapshots and
raw inspection logs are retained outside public documentation.

References:
[Supabase connections](https://supabase.com/docs/guides/database/connecting-to-postgres),
[prepared statements](https://supabase.com/kb/troubleshooting/disabling-prepared-statements-qL8lEL),
[JWT claims](https://supabase.com/docs/guides/auth/jwt-fields).
