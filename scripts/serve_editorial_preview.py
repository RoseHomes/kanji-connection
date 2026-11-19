"""Start the separate, capability-protected, read-only loopback preview backend."""

import argparse
import json
import secrets
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import Settings
from app.database import create_database_engine
from app.editorial_preview import create_preview_app
from app.editorial_preview_snapshot import create_verified_preview_engine


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-snapshot",action="store_true",help="Verify Supabase against the working edition and serve a read-only local mirror")
    args = parser.parse_args()
    settings = Settings()
    engine = create_verified_preview_engine(settings) if args.local_snapshot else create_database_engine(settings)
    capability = secrets.token_urlsafe(48)
    app = create_preview_app(settings, engine, capability)
    folder = ROOT / "private/editorial-preview"
    folder.mkdir(parents=True, exist_ok=True)
    url = "http://127.0.0.1:5174/__editorial/open?token=" + capability
    (folder / "session.json").write_text(
        json.dumps(
            {"open_url": url, "origin": "http://127.0.0.1:5174", "expires_in_hours": 8}
        ),
        encoding="utf-8",
    )
    # Keep the capability out of logs and the implementation report. The local
    # shortcut grants this browser an HttpOnly, SameSite=Strict preview cookie.
    (folder / "Open Kanji Editorial Preview.url").write_text(
        "[InternetShortcut]\nURL=" + url + "\n", encoding="utf-8"
    )
    print(
        "Local editorial backend: 127.0.0.1:8001. Open the private preview shortcut.",
        flush=True,
    )
    try:
        uvicorn.run(
            app, host="127.0.0.1", port=8001, access_log=False, log_level="warning"
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
