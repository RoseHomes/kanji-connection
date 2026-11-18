# API reference

All paths below are relative to `/api/v1`. Run the backend and use `/docs` or
`/openapi.json` for executable request/response schemas. This reference is
grouped by access boundary; availability depends on the configured content
source and publication status.

## Public catalog and content

| Method | Path                             | Behavior                                                       |
| ------ | -------------------------------- | -------------------------------------------------------------- |
| GET    | `/health`                        | Liveness, content mode and write capability; no database probe |
| GET    | `/lessons`                       | Publication-filtered catalog; q, part, status, offset, limit   |
| GET    | `/lessons/{slug}`                | Available lesson; inaccessible content returns 404             |
| GET    | `/kanjis`                        | Available characters; q, offset, limit                         |
| GET    | `/kanjis/{character}`            | One available character                                        |
| GET    | `/kanjis/{character}/relations`  | Typed, direction-aware one-hop relations; at most 50           |
| GET    | `/kanjis/{character}/vocabulary` | Published free vocabulary; offset and limit                    |
| GET    | `/compare`                       | 2-4 distinct available characters in `characters`              |
| GET    | `/search`                        | Required q; Japanese, Thai, kana, romaji or component search   |

## Learning presentation and practice

These routes allow optional bearer authentication. Private content is visible
only to explicitly allowlisted local development identities; hosted deployments
disable that access.

| Method | Path                             | Behavior                                                         |
| ------ | -------------------------------- | ---------------------------------------------------------------- |
| GET    | `/learning/lessons`              | Practice lesson selector                                         |
| GET    | `/learning/catalog`              | Full presentation metadata; q and part                           |
| GET    | `/learning/kanjis`               | Teaching-card search/pagination; supporting-only glyphs excluded |
| GET    | `/learning/compare`              | Ordered comparison for 2-4 available characters                  |
| GET    | `/learning/lesson/{slug}`        | Cards and structured sections with source pages                  |
| GET    | `/learning/questions/{slug}`     | Questions without answer keys                                    |
| POST   | `/learning/check/{question_key}` | Nonpersistent answer assessment                                  |

Lesson presentation omits raw extraction blocks and exercise answer keys.
Internal source paths are not public provenance fields. Manual comparison
responses remain ungraded. Nonpersistent checking still requires access to the
question; it is not a privacy bypass.

## Account-owned learning

These routes require a verified Supabase bearer token. `owner_id`, correctness
and schedule dates are never accepted as authoritative browser fields. Mutations
require enabled account writes in the configured environment; read-only staging
keeps controls disabled.

| Method | Path                          | Behavior                                                         |
| ------ | ----------------------------- | ---------------------------------------------------------------- |
| GET    | `/me`                         | Verified subject                                                 |
| GET    | `/me/dashboard`               | Owner lesson progress, quiz summary/history and review schedules |
| GET    | `/me/review-cards`            | Available cards with this owner's schedules                      |
| POST   | `/me/attempts/{question_key}` | Idempotent submission UUID and source-grounded grading           |
| PUT    | `/me/progress/{slug}`         | Self-reported reading completion with expected_version           |
| PUT    | `/me/reviews/{character}`     | Self-assessed review with expected_version; server scheduling    |
| POST   | `/me/sync/preview`            | Read-only guest/cloud conflict preview                           |
| POST   | `/me/sync/apply`              | Atomic application of explicit conflict choices                  |

Question keys combine a lesson slug and stable question key. Identical
submission retries return the stored result; reusing a submission UUID for
different input returns 409. See
[account behavior](../guides/AUTH_AND_PROGRESS.md) for scheduling and sync
rules.

## Responses and limits

List endpoints return deterministically ordered arrays, not total-count
envelopes. Comparison, query lengths and pagination are bounded. Handled API
errors use `{"error":{"code":"...","message":"..."}}`; validation failures are
redacted. 401 requires authentication, 404 hides unavailable content, 409
reports a version/identity conflict, and 503 indicates unavailable
configuration/database or disabled account writes. Database mode never silently
substitutes sample data. There is no teacher-grading, content-publication or
administrative user endpoint.
