# Supabase migration verification - 2026-11-13

> Dated migration evidence. Empty-table and unfinished-Auth statements describe
> this phase; the later [private import report](LIVE_PRIVATE_IMPORT_REPORT.md)
> records its subsequent state. Use current guides for operations, not this
> historical report.

Result: **committed successfully at Alembic revision 0002**. No seeds,
deployment or Git push. Credentials were loaded locally from backend/.env and
were not printed or included in artifacts.

## Authorization and preflight

The owner explicitly authorized migrations only if the existing database
contained default Supabase schemas and no conflicting application tables. The
inspection confirmed:

- Schemas: auth, extensions, graphql, graphql_public, public, realtime, storage
  and vault.
- Public schema: no existing tables, sequences, views or application type-name
  conflicts.
- Runtime and migration connections returned matching schema snapshots over
  encrypted TLS.
- Supabase auth.users, auth.uid() and authenticated role existed for the
  ownership constraints.
- Both upgrade functions and offline generated SQL were reviewed. No upgrade
  drops tables, seeds content, or alters Supabase-managed tables. Only
  application tables gain FKs that reference auth.users.

The read-only schema inspection saved table/sequence/view inventories, column
definitions, constraints, indexes, RLS flags and policies. This is a schema
inspection record, **not a full database/data backup**. It contains no user
rows. The owner allowed inspection instead of a backup, and the public
application schema was empty.

## Default privilege finding and fix

The project's default public-table ACLs included client privileges that could
otherwise be inherited by new tables, including TRUNCATE. RLS does not constrain
TRUNCATE. Before applying the pending migration 0002, it was hardened to revoke
all table privileges from PUBLIC, anon and authenticated on the 16 new
application tables and new Alembic tracking table. The tracking table also
gained RLS. Existing Supabase-managed objects/default privileges were not
modified. This does not activate direct client progress access; future auth work
must explicitly provision required privileges after the verified ownership flow
is ready.

## Applied changes

Alembic revisions 0001 and 0002 were applied in one caller-owned transaction,
with a 5-second lock timeout and 60-second per-statement timeout. The schema was
rechecked immediately before DDL. All verification below passed before commit;
failure would have rolled back the upgrade. After commit, read-only checks
through the runtime connection confirmed revision 0002 and the application
tables.

Created application tables:

| Content           | Learning/practice   | User state    |
| ----------------- | ------------------- | ------------- |
| kanjis            | lessons             | user_progress |
| kanji_readings    | lesson_kanjis       | quiz_attempts |
| components        | lesson_sections     | review_items  |
| kanji_components  | lesson_vocabularies |               |
| kanji_relations   | quiz_questions      |               |
| vocabularies      |                     |               |
| vocabulary_kanjis |                     |               |
| visual_assets     |                     |               |

The separate public.alembic_version tracking table contains revision 0002.

## Verification results

- Exactly 16 application tables plus the Alembic tracking table exist.
- All 16 application tables contain zero rows; no seeds or lesson publication
  occurred.
- RLS is enabled on all 17 newly created tables, including tracking metadata.
- Three owner_scope policies exist: user_progress, review_items, quiz_attempts.
- Three owner UUID foreign keys reference auth.users(id).
- Expected check constraints exist; Alembic metadata comparison reports no new
  upgrade operations.
- Neither anon nor authenticated has direct
  SELECT/INSERT/UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER privileges on the new
  tables.
- Existing non-public schema inventories, columns, constraints, indexes and
  policies match their preflight inspection snapshots. No Supabase-managed table
  was directly altered/dropped.
- Runtime database repository queries succeed and return empty public
  lesson/Kanji lists.
- Offline migration regression test: 1 passed; Ruff check passed for changed
  Python files.

## Local evidence and remaining work

Ignored private/database-review/ contains schema-before.json,
privileges-before.json, inspection-queries.json, reviewed
pending-migrations.sql, preflight.json, schema-after-precommit.json,
schema-after-committed.json and migration-result.json. These are private
operational artifacts; do not publish them with portfolio code.

This confirms schema creation, not account authentication, JWT verification,
populated lessons, premium-content publication or complete production
authorization testing. Auth routes/progress sync and the reviewed book import
remain unfinished. Seeds require separate owner authorization.
