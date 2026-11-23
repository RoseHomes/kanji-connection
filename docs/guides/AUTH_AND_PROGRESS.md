# Accounts, practice and persistent progress

Implemented without changing the existing 16-table schema or Alembic
revision 0002. This guide describes configuration and current behavior. Dated
results are in the [implementation status](../reports/IMPLEMENTATION_STATUS.md)
and [live learning report](../reports/LIVE_PRIVATE_IMPORT_REPORT.md).
Private-source availability and deployment/publication approval are separate
from implemented application features.

## Configure authentication locally

Never commit or log credentials. Keep existing .env files; edit only the
following named entries locally. Never replace a configured file with the
example.

1. In frontend/.env.local configure the project's HTTPS URL and **public
   publishable key** (a legacy public anon key is also accepted):

   ```dotenv
   VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
   VITE_SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLIC_PUBLISHABLE_KEY
   VITE_API_URL=
   ```

2. Set backend/.env `SUPABASE_URL` to the same origin and leave
   `SUPABASE_JWT_AUDIENCE=authenticated`. Never provide a JWT signing secret.
   Projects using asymmetric ES256/RS256 signing keys are validated through the
   project's public `/auth/v1/.well-known/jwks.json` endpoint. Keys are cached
   for five minutes and verification checks signature, issuer, audience, expiry,
   issued-at, authenticated role and UUID subject. Legacy HS256 projects can
   instead set `SUPABASE_PUBLISHABLE_KEY` to the same public publishable/anon
   key: the backend validates the exact token with the project's Auth
   `/auth/v1/user` endpoint and requires the verified user ID to match its
   checked claims. No shared signing secret or privileged API key is needed;
   changing signing keys is not required.

3. Configure the Supabase Auth email provider and allowed redirect URL for your
   local browser origin, e.g. `http://127.0.0.1:5173/account` and/or
   `http://localhost:5173/account`. Keep the email-confirmation policy you want.
   Signup handles the confirmation-required response and returns the user to the
   account page; signin uses email/password, SDK session persistence/refresh and
   PKCE. Configure these values for your own development project; do not reuse
   private verification accounts or reset working provider settings. Restart the
   processes after changing values.

The browser/build guard rejects secret/service-role keys and never handles
database passwords. Supabase JS owns refresh-token storage and renewal. The API
treats browser sessions only as bearer tokens to verify; it does not trust a
client-provided owner ID or score. Signout clears the current browser session;
account changes clear cached private data and remount learning routes. Offline
JWT verification honors token expiry; immediate revocation of an already issued
access token is not implemented. Do not use long-lived access tokens as a
substitute for refresh sessions.

Sources:
[Supabase JWT verification](https://supabase.com/docs/guides/auth/jwts),
[signup](https://supabase.com/docs/reference/javascript/auth-signup),
[session handling](https://supabase.com/docs/reference/javascript/auth-getsession).

## Roll out Turnstile and password protection

1. In **Cloudflare → Turnstile**, add a **Managed** widget for
   `kanji-connection-frontend.vercel.app`. Add other frontend hostnames only
   if they will serve the account page. Leave pre-clearance off.
2. Set `VITE_TURNSTILE_SITE_KEY` in the Vercel frontend project to the widget's
   public site key. Build and deploy the frontend and verify the challenge
   renders on login, signup, and the password-reset request form.
3. In **Supabase → Authentication → URL Configuration**, set the Site URL to
   `https://kanji-connection-frontend.vercel.app` and allow
   `https://kanji-connection-frontend.vercel.app/account` as a redirect. Keep
   **Confirm email** on for the Email provider. Open PKCE reset links in the
   same browser used to request them.
4. In the Supabase Email provider password settings, set **Minimum password
   length** to **12** and enable **Prevent use of leaked passwords** on Pro or
   above. Enable **Require current password when changing password** to enforce
   the signed-in form's current-password check at the server. Recovery sessions
   use the email link instead.
5. After the frontend is live, open **Supabase → Authentication → Attack
   Protection** (also labeled **Bot and Abuse Protection**), enable CAPTCHA,
   select **Cloudflare Turnstile**, and save the matching widget **secret key**
   there. Keep the secret out of Vercel's browser variables. Test sign-in,
   signup, and a complete password reset using a test account.

Supabase enforces its configured length and leaked-password checks on password
creation and updates. The app also rejects email matches and obvious patterns
in signup, signed-in change, and recovery. Supabase's documented hosted settings
and Auth Hooks do not expose a new plaintext password for a custom check, so
direct Auth API requests can bypass the app-specific rules. The interface hides
account-specific errors, but provider response details and email rate limits
are outside the app's control.

[Cloudflare widget setup](https://developers.cloudflare.com/turnstile/get-started/) ·
[Supabase CAPTCHA](https://supabase.com/docs/guides/auth/auth-captcha) ·
[Supabase password security](https://supabase.com/docs/guides/auth/password-security) ·
[Supabase Auth Hooks](https://supabase.com/docs/guides/auth/auth-hooks)

## Persistent local development without Supabase database writes

A local runner creates/updates **only** ignored SQLite files under
private/development/. It binds to loopback, uses the same application APIs/ORM
schema, and preserves existing rows. It does not use DATABASE_URL or
MIGRATION_DATABASE_URL for its database connection. Set the public Auth origin
in this terminal so it can validate your real sign-in token:

```powershell
$env:SUPABASE_URL='https://YOUR_PROJECT.supabase.co'
# Only for legacy HS256 projects:
# $env:SUPABASE_PUBLISHABLE_KEY='YOUR_PUBLIC_PUBLISHABLE_KEY'
.\.venv\Scripts\python.exe scripts/dev_server.py
```

In a second terminal, run the existing frontend dev command. The default local
database contains the independent 木/林/森 sample, three structured reading
questions, and persistent account progress. This is not a seed against Supabase.

To practice all existing private chapter content locally, use a separate book
database:

```powershell
.\.venv\Scripts\python.exe scripts/dev_server.py --private-book --dev-user YOUR_AUTH_USER_UUID
```

Get the account UUID from your own Auth user record. Repeat --dev-user for
additional explicitly authorized testers. The runner imports the existing
prepared bundle only into private/development/book.db. It preserves editorial
changes and does not publish or reclassify any book record. Other authenticated
users and guests cannot view those private lessons/questions/cards. Public
routes keep their existing publication filters. The learning lesson route uses a
separate development response model and disclosure banner for private previews;
public Kanji response models remain publication-only. Supporting-only Kanji are
preserved in the database but excluded from teaching flashcards. No
authentication bypass or fake-login switch is included in the development
server.

## Enable production account persistence

`ENABLE_USER_WRITES=false` is the safe default in backend/.env.example.
Protected GETs and the guest-sync preview are read-only. Set
`ENABLE_USER_WRITES=true` in the Vercel backend's Production environment and
redeploy. Hosted writes require the platform's `VERCEL_ENV=production`.
`DEVELOPMENT_USER_IDS=[]` defaults to no private access. Hosted
Preview and Production always require it empty; private allowlisting is local
development only. The local runner enables writes only on its explicit SQLite
engine. No new migration is necessary.

PostgreSQL account transactions set the verified subject locally for existing
RLS, apply owner filters to every query, use per-owner transaction advisory
locks, and commit only successful mutations. The function-scoped transaction
finishes before a success response is sent; a commit failure returns an error
and rolls back. A privileged backend DB connection still relies on those
application owner filters. On the existing Supabase project the runtime role
bypasses RLS. RLS, revoked browser-role table grants, and owner foreign keys
protect the direct database boundary. The browser uses the authenticated API.

## Learning behavior and conflict handling

- Lesson reading completion is self-reported and stored separately from quiz
  performance. Progress updates carry expected_version; stale updates return 409
  without overwriting.
- Quiz GET responses omit answer keys, source provenance and grading metadata.
  Server submissions grade against the available stored key, accept only
  source-listed aliases, and normalize equivalent kana for reading questions. No
  client score is accepted.
- Quiz submission UUIDs are idempotent per owner. Reusing a UUID for a different
  question or answer returns 409; retries of the same answer return the stored
  outcome.
- Official multiple-choice answers are graded and saved when signed in with
  account writes enabled. Guest answers and lesson quick checks are stateless.
- Comparison answers are pending manual review. The existing non-null correct
  column holds false internally, with grade_status stored in the existing JSON
  column; pending entries are exposed as correct=null and excluded from
  automatic score totals. There is no teacher grading endpoint until teacher
  authorization and approved rubrics are defined.
- Flashcard scheduling is self-assessed: first success one day, successes double
  up to 90 days, a lapse resets to one day and repeats the card in the current
  UI round. The server computes dates/counts; expected_version rejects
  stale/retried schedule mutations.
- Current guest learning creates no account progress or quiz history. Existing
  legacy browser records can be imported explicitly. Signing in does not sync
  or delete them automatically.
  Preview lists both guest/cloud values. Existing records require explicit radio
  choices; new records are proposed as imports but still require final
  confirmation. Unavailable content stays local.
- Sync apply revalidates the snapshot under the owner's transaction lock; a
  stale cloud snapshot returns 409. It replaces only explicitly selected guest
  records, never adds counts together. Guest quiz answers are regraded
  server-side, not imported as trusted scores. Local copies remain after success
  or failure. Cancellation makes no changes.
- Dashboard shows read progress, graded correct/total, pending manual responses,
  recent attempts and due reviews. Unapproved/private content is visible only to
  allowlisted development identities, and account history is owner scoped.

The guest sample quiz is usable without an account or database. Account
persistence requires an authenticated session plus the local development DB (or
a separately authorized PostgreSQL configuration). Database failures never
silently fall back to guest/sample account writes.

## API and verification

The complete endpoint inventory lives in the
[API reference](../architecture/API.md). The [testing guide](TESTING.md)
distinguishes synthetic checks, optional private-input checks and dated live
verification. The [frontend readiness report](../reports/UI_READINESS.md)
records source presentation/read-only controls. Test counts belong to individual
reports, not a combined claim that every suite was rerun against the hosted
service.

Signup, confirmation, sign-in/session handling and the controlled live learning
test were previously verified. No teacher grading endpoint or full editorial
approval is implemented. Ongoing hosted account writes and a public deployment
remain separate release decisions.
