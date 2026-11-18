"""Loopback private UI preview: every SQL transaction is read-only; no write routes."""

import json
import sys
from pathlib import Path
from uuid import UUID

import uvicorn
from fastapi.responses import JSONResponse
from sqlalchemy import event

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import Settings
from app.database import create_database_engine
from app.main import create_app


def main():
    account = json.loads((ROOT / "private/live-auth-test/state.json").read_bytes())
    settings = Settings().model_copy(
        update={
            "content_source": "database",
            "expose_samples": False,
            "enable_user_writes": False,
            "development_user_ids": [UUID(account["user_id"])],
        }
    )
    engine = create_database_engine(settings)

    @event.listens_for(engine, "begin")
    def read_only(connection):
        connection.exec_driver_sql("SET TRANSACTION READ ONLY")

    app = create_app(settings, engine)

    @app.middleware("http")
    async def deny_writes(request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            return JSONResponse(
                status_code=405, content={"error": "Read-only UI preview"}
            )
        return await call_next(request)

    try:
        uvicorn.run(
            app, host="127.0.0.1", port=8000, access_log=False, log_level="warning"
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
