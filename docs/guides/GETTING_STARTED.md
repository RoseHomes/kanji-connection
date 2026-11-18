# Getting started

Run the independently authored sample first. Book files, existing project
credentials and verification accounts are not prerequisites for a public clone.
All commands below assume the project root unless a directory change is shown.

## Requirements

- Node 22.x, at least 22.12, and npm.
- Python 3.13 with venv/pip.
- Git if using a checkout; Docker only for optional disposable PostgreSQL tests.

## Windows PowerShell

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
$env:CONTENT_SOURCE = 'sample'
$env:ENABLE_USER_WRITES = 'false'
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

These process-only settings select the sample even if a local backend/.env
exists. In a second terminal from the project root:

```powershell
Set-Location frontend
npm ci
npm run dev
```

## macOS/Linux

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
cd backend
CONTENT_SOURCE=sample ENABLE_USER_WRITES=false ../.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Start `npm ci` and `npm run dev` from frontend/ in another terminal. Open
<http://127.0.0.1:5173>; API schemas are at <http://127.0.0.1:8000/docs>. Use
the same browser origin consistently for local Auth/session storage if Auth is
enabled.

## Choose a development mode

| Mode                        | Required inputs                                        | Storage and boundaries                                      |
| --------------------------- | ------------------------------------------------------ | ----------------------------------------------------------- |
| Public sample               | None                                                   | Independent sample cards and browser guest storage          |
| Local account development   | Your own configured Supabase Auth                      | Ignored SQLite database; see account guide                  |
| Private content preview     | Separately authorized private book inputs and identity | Local-only allowlist; never hosted publication              |
| Hosted database application | Approved database/Auth/environment values              | Publication-filtered PostgreSQL APIs; writes off by default |

Only copy environment examples when no configured file already exists. Do not
replace working values. The examples choose database mode; that differs from the
credential-free sample commands above. Use the
[environment guide](ENVIRONMENT.md), [account guide](AUTH_AND_PROGRESS.md) and
[database guide](DATABASE.md) for optional setup.

## Common problems

- Missing Python dependencies: run pip through this project's venv, not an
  unrelated interpreter.
- Empty public database catalog: private/needs_review lessons are intentionally
  unavailable.
- Disabled save/sync controls: account writes are disabled or health
  configuration is unavailable.
- Failed production build: set the exact HTTPS API/Auth origins and public key;
  do not add an API path.
- No book-dependent tests/content: the public clone intentionally omits private
  inputs.

See [testing](TESTING.md) for focused checks and the explicit local demo build.
Deployment, publication and operations on an existing hosted database require
separate approval.
