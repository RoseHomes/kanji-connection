"""Smoke import only the audited backend upload files in an isolated offline process."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "private/deployment-review"


def main():
    manifest = json.loads((FOLDER / "upload-manifest.json").read_bytes())
    # Fresh input trees cannot conceal missing dependencies with stale files.
    folder = Path(tempfile.mkdtemp(prefix="backend-input-", dir=FOLDER))
    for name in manifest["projects"]["backend"]["input_files"]:
        destination = folder / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "backend" / name, destination)
    environment = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(
            (
                "DATABASE_",
                "MIGRATION_",
                "SUPABASE_",
                "DEVELOPMENT_",
                "VERCEL",
                "CONTENT_",
                "CORS_",
                "ENABLE_",
                "EXPOSE_",
                "TEST_DATABASE",
            )
        )
    }
    environment.update(
        {
            "VERCEL": "0",
            "CONTENT_SOURCE": "database",
            "EXPOSE_SAMPLES": "false",
            "DATABASE_URL": "postgresql+psycopg://fixture:fixture@pooler.example.test:6543/postgres",
            "SUPABASE_URL": "https://auth.example.test",
            "CORS_ORIGINS": '["https://frontend.example.test"]',
            "DEVELOPMENT_USER_IDS": "[]",
            "ENABLE_USER_WRITES": "false",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    code = """
import json, psycopg
def deny(*args, **kwargs):
    raise RuntimeError("Database connections forbidden in offline package smoke")
psycopg.connect = deny
from index import app
assert app.state.settings.vercel is True
from fastapi.testclient import TestClient
with TestClient(app) as client:
    response=client.get("/api/v1/health")
    assert response.status_code == 200 and response.json()["content_mode"] == "database"
    assert response.json()["account_writes_enabled"] is False
print(json.dumps({"packaged_entrypoint_imported":True,"health_passed":True,"database_connections":0,"hosted_development_access":False}))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=folder,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            "Packaged backend smoke failed; output suppressed to prevent credential leakage"
        )
    report = json.loads(result.stdout)
    (FOLDER / "backend-smoke.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report))


if __name__ == "__main__":
    main()
