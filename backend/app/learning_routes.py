"""Account APIs commit only owner-owned learning rows with explicit write enablement."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .auth import CurrentUser, OptionalUser
from .content_views import development_card, lesson_sections
from .database import read_session
from .learning import Learning, grade_sample, public_lesson, sample_questions
from .learning_schema import (
    AnswerInput,
    ChoiceInput,
    DevelopmentLesson,
    GuestSnapshot,
    ProgressInput,
    ReviewInput,
    SyncInput,
)
from .models import KanjiRecord, LessonKanji, LessonRecord, ReviewItem
from .repository import DatabaseRepository
from .sample_repository import SampleRepository
from .schemas import LessonDetail

router = APIRouter(prefix="/api/v1")
ReadSession = Annotated[Session | None, Depends(read_session)]


@router.get("/learning/comparison-groups")
def curated_comparisons(request: Request, user: OptionalUser, db: ReadSession):
    from .learning_presentation import comparison_groups

    return comparison_groups(db, request.app.state.settings, user)


@router.get("/learning/practice/{slug}")
def practice_questions(slug: str, request: Request, user: OptionalUser, db: ReadSession):
    from .learning_presentation import practice, public_question

    return [public_question(q) for q in practice(db, request.app.state.settings, user, slug)]


@router.post("/learning/practice/{slug}/{question_id}/check")
def practice_check(
    slug: str,
    question_id: str,
    body: ChoiceInput,
    request: Request,
    user: OptionalUser,
    db: ReadSession,
):
    from .learning_presentation import check_choice

    return check_choice(db, request.app.state.settings, user, slug, question_id, body.option_id)


def account_session(request: Request, user: CurrentUser):
    settings = request.app.state.settings
    writing = request.method in {
        "POST",
        "PUT",
        "DELETE",
        "PATCH",
    } and not request.url.path.endswith("/sync/preview")
    if writing and not settings.enable_user_writes:
        raise HTTPException(
            503, "Account writes are disabled; configure an authorized development database"
        )
    if request.app.state.engine is None:
        raise HTTPException(503, "Account database is not configured")
    with Session(request.app.state.engine, expire_on_commit=False) as session:
        try:
            if session.bind.dialect.name == "postgresql":
                session.execute(
                    text("SELECT set_config('statement_timeout', :timeout, true)"),
                    {"timeout": str(settings.database_statement_timeout_ms)},
                )
                session.execute(
                    text("SELECT set_config('request.jwt.claim.sub', :owner, true)"),
                    {"owner": str(user.id)},
                )
                session.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:owner, 0))"),
                    {"owner": str(user.id)},
                )
            yield session
            if writing:
                session.commit()
        finally:
            session.rollback()


AccountSession = Annotated[Session, Depends(account_session, scope="function")]


@router.get("/me")
def me(user: CurrentUser):
    return {"id": str(user.id)}


@router.get("/learning/lessons")
def learning_lessons(request: Request, user: OptionalUser, db: ReadSession):
    if db is None:
        return [{"slug": "chapter-02", "title": "ตัวอย่าง: 木・林・森", "private_development": False}]
    service = Learning(db, request.app.state.settings, user)
    return [
        {
            "slug": l.slug,
            "title": l.title_th,
            "private_development": not public_lesson(l, service.settings.expose_samples),
        }
        for l in db.scalars(select(LessonRecord).order_by(LessonRecord.chapter))
        if (public_lesson(l, service.settings.expose_samples) and l.catalog_visible)
        or service.private
    ]


@router.get("/learning/catalog")
def learning_catalog(
    request: Request,
    user: OptionalUser,
    db: ReadSession,
    q: str = Query("", max_length=100),
    part: int | None = Query(None, ge=1, le=6),
):
    if db is None:
        return SampleRepository().lessons(q=q, part=part)
    service = Learning(db, request.app.state.settings, user)
    if not service.private:
        return DatabaseRepository(db, service.settings.expose_samples).lessons(q=q, part=part)
    result = []
    sizes = dict(
        db.execute(
            select(LessonKanji.lesson_id, func.count()).group_by(LessonKanji.lesson_id)
        ).all()
    )
    for row in db.scalars(select(LessonRecord).order_by(LessonRecord.chapter)):
        if part and (row.chapter - 1) // 5 + 1 != part:
            continue
        if q.casefold() not in " ".join([row.title_th, row.summary_th, *row.anchors]).casefold():
            continue
        result.append(
            {
                "chapter": row.chapter,
                "slug": row.slug,
                "part": (row.chapter - 1) // 5 + 1,
                "title_th": row.title_th,
                "summary_th": row.summary_th,
                "anchors": row.anchors,
                "status": row.status,
                "is_available": True,
                "private_development": True,
                "available_count": sizes.get(row.id, 0),
            }
        )
    return result


@router.get("/learning/kanjis")
def learning_kanjis(
    request: Request,
    user: OptionalUser,
    db: ReadSession,
    q: str = Query("", max_length=100),
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
):
    if db is None:
        return SampleRepository().kanjis(q=q, offset=offset, limit=limit)
    service = Learning(db, request.app.state.settings, user)
    if not service.private:
        return DatabaseRepository(db, service.settings.expose_samples).kanjis(
            q=q, offset=offset, limit=limit
        )
    rows = [
        k
        for k in db.scalars(select(KanjiRecord).order_by(KanjiRecord.id))
        if k.source.get("kind") != "supporting_printed_glyph"
        and q.casefold()
        in " ".join(
            [
                k.character,
                k.meaning_th,
                k.romaji,
                *k.readings.get("on", []),
                *k.readings.get("kun", []),
            ]
        ).casefold()
    ]
    return [development_card(k) for k in rows[offset : offset + limit]]


@router.get("/learning/compare")
def learning_compare(
    request: Request,
    user: OptionalUser,
    db: ReadSession,
    characters: str = Query("木,林,森", max_length=15),
):
    chars = list(dict.fromkeys(characters.split(",")))
    if not 2 <= len(chars) <= 4 or any(len(c) != 1 for c in chars):
        raise HTTPException(422, "เลือกคันจิ 2–4 ตัว")
    if db is None:
        return SampleRepository().compare(chars)
    service = Learning(db, request.app.state.settings, user)
    if not service.private:
        return DatabaseRepository(db, service.settings.expose_samples).compare(chars)
    return [development_card(service.kanji(c)) for c in chars]


@router.get("/learning/questions/{slug}")
def questions(slug: str, request: Request, user: OptionalUser, db: ReadSession):
    if db is None:
        if slug != "chapter-02":
            raise HTTPException(404, "Lesson unavailable")
        return sample_questions()
    return Learning(db, request.app.state.settings, user).questions(slug)


@router.get("/learning/lesson/{slug}")
def learning_lesson(slug: str, request: Request, user: OptionalUser, db: ReadSession):
    if db is None:
        return SampleRepository().lesson(slug)
    service = Learning(db, request.app.state.settings, user)
    row = service.lesson(slug)
    cards = []
    for k in db.scalars(
        select(KanjiRecord)
        .join(LessonKanji)
        .where(LessonKanji.lesson_id == row.id)
        .order_by(LessonKanji.position)
    ):
        if not service.can_see_kanji(k):
            continue
        cards.append(k)
    private = not public_lesson(row, request.app.state.settings.expose_samples) or any(
        k.access_tier != "free" or k.review_status not in ("published", "sample") for k in cards
    )
    if private:
        serialized = [development_card(k) for k in cards]
    else:
        serialized = DatabaseRepository(
            db, request.app.state.settings.expose_samples
        )._serialize_kanjis(cards)
    model = DevelopmentLesson if private else LessonDetail
    result = model(
        id=row.id,
        chapter=row.chapter,
        slug=row.slug,
        part=(row.chapter - 1) // 5 + 1,
        title_th=row.title_th,
        summary_th=row.summary_th,
        anchors=row.anchors,
        status=row.status,
        is_available=True,
        available_count=len(serialized),
        kanjis=serialized,
        introduction_th=row.introduction_th or row.summary_th,
        provenance="เนื้อหาทดสอบส่วนตัว · ยังไม่ผ่านการอนุมัติเผยแพร่"
        if private
        else "บทเรียนที่เปิดให้เรียน · ตัวอย่างระบุสถานะไว้แยกต่างหาก",
        sections=lesson_sections(db, row.id, service.private, service.settings.expose_samples),
    )
    return {**result.model_dump(), "private_development": private}


@router.post("/learning/check/{question_key}")
def check(
    question_key: str, body: AnswerInput, request: Request, user: OptionalUser, db: ReadSession
):
    if db is None:
        return grade_sample(question_key, body.answer)
    service = Learning(db, request.app.state.settings, user)
    return {**service.grade(service.question(question_key), body.answer), "persisted": False}


@router.get("/me/dashboard")
def dashboard(request: Request, user: CurrentUser, db: AccountSession):
    return Learning(db, request.app.state.settings, user).dashboard()


@router.post("/me/attempts/{question_key}")
def attempt(
    question_key: str, body: AnswerInput, request: Request, user: CurrentUser, db: AccountSession
):
    return {
        **Learning(db, request.app.state.settings, user).attempt(
            question_key, body.submission_id, body.answer
        ),
        "persisted": True,
    }


@router.put("/me/progress/{slug}")
def progress(
    slug: str, body: ProgressInput, request: Request, user: CurrentUser, db: AccountSession
):
    return Learning(db, request.app.state.settings, user).progress(
        slug, body.progress, body.expected_version
    )


@router.get("/me/review-cards")
def review_cards(request: Request, user: CurrentUser, db: AccountSession):
    service = Learning(db, request.app.state.settings, user)
    result = []
    schedules = {
        row.kanji_id: row
        for row in db.scalars(
            select(ReviewItem).where(
                ReviewItem.owner_id == user.id, ReviewItem.kanji_id.is_not(None)
            )
        )
    }
    for k in db.scalars(select(KanjiRecord).order_by(KanjiRecord.id)):
        if k.source.get("kind") == "supporting_printed_glyph":
            continue
        if not service.can_see_kanji(k):
            continue
        r = schedules.get(k.id)
        result.append(
            {
                "character": k.character,
                "meaning_th": k.meaning_th,
                "onyomi": k.readings.get("on", []),
                "kunyomi": k.readings.get("kun", []),
                "private_development": k.access_tier != "free"
                or k.review_status not in ("published", "sample"),
                "schedule": service.serialize_review(r) if r else None,
            }
        )
        if len(result) >= 500:
            break
    return result


@router.put("/me/reviews/{character}")
def review(
    character: str, body: ReviewInput, request: Request, user: CurrentUser, db: AccountSession
):
    return Learning(db, request.app.state.settings, user).review(
        character, body.knew, body.expected_version
    )


@router.post("/me/sync/preview")
def preview(body: GuestSnapshot, request: Request, user: CurrentUser, db: AccountSession):
    return Learning(db, request.app.state.settings, user).preview_sync(body)


@router.post("/me/sync/apply")
def sync(body: SyncInput, request: Request, user: CurrentUser, db: AccountSession):
    return Learning(db, request.app.state.settings, user).apply_sync(body)
