# Kanji Connection

A Thai-language Kanji learning application built around visual comparison,
contextual readings, quizzes and spaced review. The public source supports a
sample experience; the book dataset and PDF are not
distributed with this repository.

## Project status

Authentication, persistent learning progress, quizzes, flashcards, explicit
guest-data synchronization and the dashboard are implemented. A 30-chapter
dataset was structurally validated and imported into private staging; **no
chapter has full editorial approval**. Deployment configuration is prepared, but
no hosted release or content publication is claimed. See the
[implementation status](docs/reports/IMPLEMENTATION_STATUS.md) for dated
evidence and limits.

## Tech stack

| Layer                | Technologies                                                        |
| -------------------- | ------------------------------------------------------------------- |
| Frontend             | React, TypeScript, Vite, React Router, TanStack Query, Tailwind CSS |
| Backend              | Python, FastAPI, Pydantic, SQLAlchemy, Alembic                      |
| Identity and storage | Supabase Authentication and PostgreSQL                              |
| Quality checks       | Vitest, Testing Library, Playwright, pytest, ESLint, Ruff           |
| Deployment target    | Separate Vercel frontend and FastAPI projects                       |

## Features

- Responsive lesson, vocabulary, comparison, explorer and review views with
  Thai/Japanese text.
- Source-provided group furigana, contextual reading notes and PDF provenance
  where available.
- Published public lessons, Kanji details and practice need no account. When no
  content is approved, public pages explain the publication empty state.
- Server-graded public quizzes keep results in component state for the current
  visit only. Comparison explanations remain pending manual review.
- Personal dashboards, review queues and progress require authentication;
  persistence also requires the existing server write permission.
- Legacy browser/cloud sync previews preserve explicit conflict choices, without
  automatically importing old records or storing new anonymous quiz history.
- Private content filters, verified bearer tokens and a hosted guard that
  disables development access.

See the [public learning and redesign report](docs/reports/PUBLIC_LEARNING_REDESIGN.md)
for the access matrix, visual system, actual verification and remaining approval limits.

Book-dependent features require separately authorized private inputs. Missing
readings, diagram cores and translations are not invented, and visual mnemonics
are not presented as verified historical etymology.

## Run the sample locally

Use Node 22.x (22.12 or newer) and Python 3.13. No Supabase credentials or book
files are needed for sample mode. On macOS/Linux, from the project root:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
cd backend
CONTENT_SOURCE=sample ENABLE_USER_WRITES=false ../.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open <http://127.0.0.1:5173>; API schemas are at <http://127.0.0.1:8000/docs>.
The [getting-started guide](docs/guides/GETTING_STARTED.md) includes Windows
PowerShell, configuration choices and troubleshooting. Never overwrite an
existing environment file.

## Architecture and checks

The SPA calls FastAPI under `/api/v1`. FastAPI validates Supabase tokens,
filters content by publication/access status, and scopes learning records to the
verified account. PostgreSQL transactions protect concurrent progress updates.
SQLite is used only for isolated tests and local development. Nothing migrates,
imports or publishes at startup.

See the [architecture](docs/architecture/ARCHITECTURE.md),
[API reference](docs/architecture/API.md) and
[database diagram](docs/architecture/ERD.md). The
[testing guide](docs/guides/TESTING.md) explains local checks, private-input
skips and disposable PostgreSQL requirements. Production builds require three
public configuration variables; an explicit local-only `npm run build:demo` is
available without hosted configuration.

## Documentation and publication

Start with the [documentation index](docs/README.md). Current guides are
separate from dated verification reports and archived plans. The
[deployment runbook](docs/guides/DEPLOYMENT.md) describes Vercel setup; it does
not authorize deployment or publication.

The PDF, extracted dataset, credentials, private verification artifacts and
browser profiles are excluded from public distribution. Review the
[repository publication checklist](docs/guides/PUBLICATION.md) before any push,
including generated JSON artifacts and content rights.
The [publication safety audit](docs/reports/PUBLICATION_READINESS.md) records
the resolved wording findings and final Git staging review. A successful safety
review does not authorize a commit, push, deployment or educational publication.

## Copyright and usage

**Copyright — All Rights Reserved.** The project's source code is publicly viewable for
developer portfolio and evaluation purposes only. This is not an open-source
project. Copying, redistribution, modification and commercial reuse require
prior permission from the copyright holder, except where applicable law or
GitHub's platform terms provide otherwise.

Private educational content, textbook materials, datasets, artwork and editorial
corrections are not licensed for reuse or distributed with this repository.
Public visibility grants no additional rights to those materials.

Third-party libraries, fonts, dictionaries and other external materials remain
subject to their respective copyright holders' licenses and attribution
requirements. This notice does not claim ownership of them or override their
terms. See the [third-party notices](docs/guides/THIRD_PARTY.md) and
[GitHub's licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)
for the distinction between public visibility and reuse permission.
