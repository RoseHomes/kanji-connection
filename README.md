# Kanji Connection

**[Visit Website](https://kanji-connection-frontend.vercel.app)**

Kanji Connection is a Thai-language study site for Thai-speaking learners of Japanese. It teaches Kanji through visual patterns, vocabulary in context, and side-by-side comparisons. The lessons, comparisons, and quizzes are available without an account.

## Features

- **30 Kanji lessons.** Guided Learning breaks each chapter into small groups with readings, meanings, memory aids, vocabulary, comparisons, and optional quick checks.
- **Full Lesson mode.** Review all the material in a chapter in one view.
- **94 curated comparison groups.** Choose similar characters to study side by side.
- **450 multiple-choice questions.** Check answers as you go, read explanations, and revisit mistakes after each quiz.
- **Kanji explorer.** Look up individual characters and browse their readings, vocabulary, and related Kanji.

The personal dashboard and review area require sign-in. Account writes are disabled on the hosted site.

## Technology stack

| Area               | Technologies                                                                          |
| ------------------ | ------------------------------------------------------------------------------------- |
| Frontend           | React, TypeScript, Vite, React Router, TanStack Query, Tailwind CSS, Motion, Radix UI |
| Backend            | Python, FastAPI, Pydantic, SQLAlchemy, Alembic                                        |
| Data and identity  | PostgreSQL and Supabase Auth                                                          |
| Hosting            | Separate Vercel projects for the frontend and API                                     |
| Development checks | Vitest, Testing Library, Playwright, pytest, ESLint, Ruff                             |

## Project structure

| Path        | Contents                                                    |
| ----------- | ----------------------------------------------------------- |
| `frontend/` | React application, styles, and browser tests                |
| `backend/`  | FastAPI application, database migrations, and backend tests |
| `content/`  | Content schema and format documentation                     |
| `docs/`     | Setup guides and architecture documentation                 |
| `scripts/`  | Project maintenance and verification scripts                |

## Local development

Install **Node.js 22.x (22.12 or newer)**, npm, and **Python 3.13**. Clone the repository. The bundled sample runs without a Supabase project. Database mode serves published lessons from a configured database.

Start the API from the repository root on macOS or Linux:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cd backend
CONTENT_SOURCE=sample ENABLE_USER_WRITES=false ../.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

For Windows, see the PowerShell instructions in the [getting started guide](docs/guides/GETTING_STARTED.md).

Start the frontend in a second terminal from the repository root:

```sh
cd frontend
npm ci
npm run dev
```

Open the [local website](http://127.0.0.1:5173) or the [API documentation](http://127.0.0.1:8000/docs). Leave `VITE_API_URL` unset or empty so Vite proxies `/api` to the local FastAPI server.

## Environment variables

Use the [frontend example](frontend/.env.example) and [backend example](backend/.env.example) as references for your own environment. Keep database connection strings on the server.

| Variable                        | Purpose                                                             |
| ------------------------------- | ------------------------------------------------------------------- |
| `CONTENT_SOURCE`                | Selects `sample` or `database` mode for the API.                    |
| `DATABASE_URL`                  | Server-side PostgreSQL connection string required in database mode. |
| `CORS_ORIGINS`                  | JSON array of allowed frontend origins for cross-origin API calls.  |
| `SUPABASE_URL`                  | Supabase project origin used by the API to verify account tokens.   |
| `ENABLE_USER_WRITES`            | Keep `false` for read-only account access.                          |
| `VITE_API_URL`                  | API origin for the browser. Leave empty for the local proxy.        |
| `VITE_SUPABASE_URL`             | Supabase project origin for browser sign-in.                        |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Public publishable key or legacy anon key for browser sign-in.      |

From `frontend/`, use `npm run build:demo` for a local build that can run with the sample API. The production command, `npm run build`, requires the three `VITE_` variables listed above, with exact HTTPS API and Supabase origins. See the [environment guide](docs/guides/ENVIRONMENT.md) and [deployment guide](docs/guides/DEPLOYMENT.md) for additional configuration.

## Copyright and usage

**All rights reserved.** The project's source code is available for portfolio and evaluation purposes. Copying, modification, redistribution, or commercial reuse requires permission from the copyright holder, subject to applicable law and GitHub's terms. Third-party materials remain subject to their respective licenses. See the [third-party notices](docs/guides/THIRD_PARTY.md).
