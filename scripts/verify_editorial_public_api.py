"""Verify the normal production application still hides the private working edition."""

import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import Settings
from app.content_revision import digest
from app.database import create_database_engine
from app.editorial_preview import COOKIE
from app.editorial_sync import snapshot
from app.main import create_app


def main():
    settings = Settings().model_copy(
        update={
            "content_source": "database",
            "expose_samples": False,
            "enable_user_writes": False,
            "development_user_ids": [],
        }
    )
    engine = create_database_engine(settings)
    try:
        with engine.connect() as c:
            c.execute(text("SET TRANSACTION READ ONLY"))
            before = digest(snapshot(c))
            c.rollback()
        token = parse_qs(
            urlparse(
                json.loads(
                    (ROOT / "private/editorial-preview/session.json").read_bytes()
                )["open_url"]
            ).query
        )["token"][0]
        # Even the actual local preview cookie grants no access in the ordinary app.
        with TestClient(
            create_app(settings, engine),
            base_url="http://127.0.0.1:8000",
            cookies={COOKIE: token},
        ) as public:
            assert (
                public.get("/api/v1/health").json()["account_writes_enabled"] is False
            )
            assert public.get("/api/v1/learning/catalog").json() == []
            assert public.get("/api/v1/lessons?limit=100").json() == []
            assert public.get("/api/v1/kanjis?limit=100").json() == []
            for n in range(1, 31):
                assert (
                    public.get(f"/api/v1/learning/lesson/chapter-{n:02}").status_code
                    == 404
                )
                assert (
                    public.get(f"/api/v1/learning/questions/chapter-{n:02}").status_code
                    == 404
                )
            for g in ["禾", "訊", "靖", "孫"]:
                assert public.get("/api/v1/kanjis/" + g).status_code == 404
            assert public.get("/__editorial/open").status_code == 404
            assert (
                public.put(
                    "/api/v1/me/progress/chapter-01",
                    json={"progress": 100, "expected_version": 0},
                ).status_code
                == 401
            )
        with engine.connect() as c:
            c.execute(text("SET TRANSACTION READ ONLY"))
            assert digest(snapshot(c)) == before
            c.rollback()
        result = {
            "normal_public_application": True,
            "hidden_lesson_routes": 30,
            "hidden_question_routes": 30,
            "private_catalog_hidden": True,
            "private_kanji_hidden": True,
            "preview_cookie_not_production_authorization": True,
            "preview_routes_not_mounted": True,
            "account_writes_enabled": False,
            "educational_data_unchanged_by_verification": True,
        }
        (ROOT / "private/editorial-preview/public-api-verification.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(result))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
