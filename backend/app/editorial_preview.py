"""Capability-protected loopback preview. Never mounted by the production app."""

import hmac
import os
import time
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select

from .auth import Identity
from .content_views import development_card
from .database import read_session
from .learning import Learning
from .learning_routes import (
    check,
    curated_comparisons,
    learning_catalog,
    learning_compare,
    learning_kanjis,
    learning_lesson,
    learning_lessons,
    practice_check,
    practice_questions,
    questions,
)
from .learning_schema import AnswerInput, ChoiceInput
from .models import KanjiRecord, KanjiRelation, Vocabulary, VocabularyKanji

COOKIE = "kanji_editorial_v2"
PREVIEW_USER = UUID("00000000-0000-4000-8000-000000000030")


def create_preview_app(settings, engine, capability: str, *, origin="http://127.0.0.1:5174"):
    if settings.vercel or os.environ.get("VERCEL") == "1" or os.environ.get("VERCEL_ENV"):
        raise ValueError("Editorial preview must never run on a hosted deployment")
    if len(capability) < 40 or origin != "http://127.0.0.1:5174":
        raise ValueError(
            "Editorial preview requires a strong local capability and fixed loopback origin"
        )
    # This identity is local authorization, not a Supabase account or JWT. It is
    # accepted only inside this separate capability-gated process.
    local = settings.model_copy(
        update={
            "content_source": "database",
            "expose_samples": False,
            "enable_user_writes": False,
            "development_user_ids": [PREVIEW_USER],
        }
    )
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings, app.state.engine = local, engine
    identity = Identity(PREVIEW_USER)
    expires = time.time() + 8 * 3600

    @app.middleware("http")
    async def local_access(request, call_next):
        host = request.url.hostname
        peer = request.client.host if request.client else ""
        if host != "127.0.0.1" or peer not in {"127.0.0.1", "::1"}:
            return JSONResponse({"error": "Loopback access only"}, status_code=403)
        if request.headers.get("origin") not in {None, origin}:
            return JSONResponse({"error": "Unexpected origin"}, status_code=403)
        path = request.url.path
        if path != "/__editorial/ping":
            supplied = (
                request.query_params.get("token", "")
                if path == "/__editorial/open"
                else request.cookies.get(COOKIE, "")
            )
            if time.time() > expires or not hmac.compare_digest(supplied, capability):
                return JSONResponse(
                    {
                        "error": "Open the local editorial preview shortcut to authorize this browser"
                    },
                    status_code=401,
                )
        if request.method not in {"GET", "HEAD", "OPTIONS"} and not (
            request.method == "POST"
            and (
                path.startswith("/api/v1/learning/check/")
                or (path.startswith("/api/v1/learning/practice/") and path.endswith("/check"))
            )
        ):
            return JSONResponse(
                {"error": "Account and content writes are disabled"}, status_code=405
            )
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
        return response

    @app.get("/__editorial/ping")
    def ping():
        return {"status": "local_preview_running"}

    @app.get("/__editorial/open")
    def open_browser():
        response = RedirectResponse("/lessons", status_code=303)
        response.set_cookie(COOKIE, capability, httponly=True, samesite="strict", max_age=8 * 3600)
        return response

    DB = Annotated[object, Depends(read_session)]

    @app.get("/api/v1/learning/comparison-groups")
    def groups(request: Request, db: DB):
        return curated_comparisons(request, identity, db)

    @app.get("/api/v1/learning/practice/{slug}")
    def practice_list(slug: str, request: Request, db: DB):
        return practice_questions(slug, request, identity, db)

    @app.post("/api/v1/learning/practice/{slug}/{question_id}/check")
    def practice_answer(slug: str, question_id: str, body: ChoiceInput, request: Request, db: DB):
        return practice_check(slug, question_id, body, request, identity, db)

    @app.get("/api/v1/health")
    def health():
        return {
            "status": "ok",
            "content_mode": "database",
            "account_writes_enabled": False,
            "editorial_preview": True,
            "revision_id": "2026-11-19-final-v2",
        }

    @app.get("/api/v1/learning/catalog")
    @app.get("/api/v1/lessons")
    def catalog(
        request: Request,
        db: DB,
        q: str = Query("", max_length=100),
        part: int | None = Query(None, ge=1, le=6),
    ):
        return learning_catalog(request, identity, db, q, part)

    @app.get("/api/v1/learning/lessons")
    def lesson_list(request: Request, db: DB):
        return learning_lessons(request, identity, db)

    @app.get("/api/v1/learning/lesson/{slug}")
    @app.get("/api/v1/lessons/{slug}")
    def lesson(slug: str, request: Request, db: DB):
        return learning_lesson(slug, request, identity, db)

    @app.get("/api/v1/learning/questions/{slug}")
    def lesson_questions(slug: str, request: Request, db: DB):
        return questions(slug, request, identity, db)

    @app.post("/api/v1/learning/check/{key}")
    def check_answer(key: str, body: AnswerInput, request: Request, db: DB):
        return check(key, body, request, identity, db)

    @app.get("/api/v1/learning/kanjis")
    @app.get("/api/v1/kanjis")
    @app.get("/api/v1/search")
    def kanjis(
        request: Request,
        db: DB,
        q: str = Query("", max_length=100),
        offset: int = Query(0, ge=0),
        limit: int = Query(30, ge=1, le=100),
    ):
        return learning_kanjis(request, identity, db, q, offset, limit)

    @app.get("/api/v1/learning/compare")
    @app.get("/api/v1/compare")
    def compare(request: Request, db: DB, characters: str = Query("木,林,森", max_length=15)):
        return learning_compare(request, identity, db, characters)

    @app.get("/api/v1/kanjis/{character}")
    def character_card(character: str, db: DB):
        return development_card(Learning(db, local, identity).kanji(character))

    @app.get("/api/v1/kanjis/{character}/vocabulary")
    def character_words(character: str, db: DB, limit: int = Query(100, ge=1, le=100)):
        k = Learning(db, local, identity).kanji(character)
        return [
            {
                "written_form": w.written_form,
                "reading": w.reading,
                "meaning_th": w.meaning_th,
                "usage_notes": w.usage_notes,
            }
            for w in db.scalars(
                select(Vocabulary)
                .join(VocabularyKanji)
                .where(VocabularyKanji.kanji_id == k.id)
                .limit(limit)
            )
        ]

    @app.get("/api/v1/kanjis/{character}/relations")
    def character_relations(character: str, db: DB):
        k = Learning(db, local, identity).kanji(character)
        relations = []
        for relation in db.scalars(
            select(KanjiRelation).where(
                (KanjiRelation.source_id == k.id) | (KanjiRelation.target_id == k.id)
            )
        ):
            other = db.get(
                KanjiRecord,
                relation.target_id if relation.source_id == k.id else relation.source_id,
            )
            relations.append(
                {
                    "character": other.character,
                    "type": relation.relation_type,
                    "explanation_th": relation.explanation_th,
                }
            )
        return {
            "related": list(dict.fromkeys(r["character"] for r in relations)),
            "relations": relations,
        }

    return app
