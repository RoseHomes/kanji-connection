from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jwt import PyJWKClient
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .database import create_database_engine, read_session
from .learning_routes import router as learning_router
from .repository import DatabaseRepository
from .sample_repository import SampleRepository
from .schemas import Kanji, Lesson, LessonDetail, VocabularyResponse

router = APIRouter(prefix="/api/v1")


def repository(request: Request, session: Annotated[Session | None, Depends(read_session)]):
    if request.app.state.settings.content_source == "sample":
        return SampleRepository()
    return DatabaseRepository(session, expose_samples=request.app.state.settings.expose_samples)


Repository = Annotated[DatabaseRepository | SampleRepository, Depends(repository)]


@router.get("/health")
def health(request: Request):
    source = request.app.state.settings.content_source
    return {
        "status": "ok",
        "version": "0.2.0",
        "content_mode": source,
        "account_writes_enabled": request.app.state.settings.enable_user_writes,
        "database": "not_connected"
        if source == "sample"
        else (
            "configured_not_checked" if request.app.state.engine is not None else "not_configured"
        ),
    }


@router.get("/lessons", response_model=list[Lesson])
def lessons(
    repo: Repository,
    q: str = Query("", max_length=100),
    part: int | None = Query(None, ge=1, le=6),
    status: str | None = Query(None, pattern="^(sample|needs_review|published)$"),
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
):
    return repo.lessons(q=q, part=part, status=status, offset=offset, limit=limit)


@router.get("/lessons/{slug}", response_model=LessonDetail)
def lesson(slug: str, repo: Repository):
    return repo.lesson(slug)


@router.get("/kanjis", response_model=list[Kanji])
def kanjis(
    repo: Repository,
    q: str = Query("", max_length=100),
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
):
    return repo.kanjis(q=q, offset=offset, limit=limit)


@router.get("/kanjis/{character}", response_model=Kanji)
def kanji(character: str, repo: Repository):
    return repo.kanji(character)


@router.get("/kanjis/{character}/relations")
def relations(character: str, repo: Repository):
    return repo.relations(character)


@router.get("/kanjis/{character}/vocabulary", response_model=list[VocabularyResponse])
def vocabulary(
    character: str,
    repo: Repository,
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
):
    return repo.vocabulary(character, offset=offset, limit=limit)


@router.get("/compare", response_model=list[Kanji])
def compare(repo: Repository, characters: str = Query("木,林,森", max_length=15)):
    chars = list(dict.fromkeys(characters.split(",")))
    if not 2 <= len(chars) <= 4 or any(len(c) != 1 for c in chars):
        raise HTTPException(422, "เลือกคันจิ 2–4 ตัว")
    return repo.compare(chars)


@router.get("/search", response_model=list[Kanji])
def search(repo: Repository, q: str = Query(..., min_length=1, max_length=100)):
    return repo.kanjis(q=q, offset=0, limit=30)


def create_app(settings: Settings | None = None, engine: Engine | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.require_hosted_safety()
    owned_engine = engine is None
    if (
        (settings.content_source == "database" or settings.enable_user_writes)
        and engine is None
        and settings.database_url
    ):
        engine = create_database_engine(settings)  # constructs pool; no connection yet

    @asynccontextmanager
    async def lifespan(application):
        yield
        if owned_engine and application.state.engine is not None:
            application.state.engine.dispose()

    application = FastAPI(title="Kanji Connection", version="0.2.0", lifespan=lifespan)
    application.state.settings = settings
    application.state.engine = engine
    application.state.jwks_client = (
        PyJWKClient(
            f"{settings.supabase_url}/auth/v1/.well-known/jwks.json", lifespan=300, timeout=5
        )
        if settings.supabase_url
        else None
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @application.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": str(exc.status_code), "message": exc.detail}},
            headers=exc.headers,
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {"code": "validation_error", "message": "Invalid request parameters"}
            },
        )

    @application.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        # Never expose connection details, SQL text, private rows or credentials.
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "database_unavailable",
                    "message": "Database temporarily unavailable",
                }
            },
        )

    application.include_router(router)
    application.include_router(learning_router)
    return application


app = create_app()
