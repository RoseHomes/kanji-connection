"""Restricted live learning harness; content remains read-only throughout testing."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from uuid import UUID, uuid4

import uvicorn
from fastapi.responses import JSONResponse
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from import_private_book import (
    FOLDER,
    counts,
    foreign_key_check,
    private_check,
    require,
    schema_check,
    verify_sources,
)

from app.auth import Identity
from app.config import Settings
from app.database import create_database_engine
from app.learning import Learning
from app.main import create_app
from app.models import (
    Base,
    KanjiRecord,
    LessonRecord,
    QuizAttempt,
    QuizQuestion,
    ReviewItem,
    UserProgress,
)

OWNED = {"user_progress", "review_items", "quiz_attempts"}
PLAN = FOLDER / "learning-plan.json"


def save(path, value):
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )


def content_digest(connection):
    digest = hashlib.sha256()
    for table in Base.metadata.sorted_tables:
        if table.name in OWNED:
            continue
        rows = [
            dict(r)
            for r in connection.execute(
                select(table).order_by(*table.primary_key.columns)
            ).mappings()
        ]
        digest.update(
            json.dumps(
                [table.name, rows], sort_keys=True, ensure_ascii=False, default=str
            ).encode()
        )
    return digest.hexdigest()


def prepare(settings):
    require(
        not PLAN.exists(), "Learning plan already exists; inspect rather than overwrite"
    )
    result = json.loads((FOLDER / "result.json").read_bytes())
    require(
        result.get("committed") and result.get("postcommit_verified"),
        "Import not verified",
    )
    verify_sources()
    owner = UUID(
        json.loads((ROOT / "private/live-auth-test/state.json").read_bytes())["user_id"]
    )
    engine = create_database_engine(settings)
    try:
        with engine.connect() as c, c.begin():
            c.execute(text("SET TRANSACTION READ ONLY"))
            schema_check(c)
            private_check(c)
            require(counts(c) == result["after_counts"], "Imported inventory changed")
            with Session(bind=c) as db:
                lesson = db.scalar(
                    select(LessonRecord).where(LessonRecord.chapter == 1)
                )
                questions = list(
                    db.scalars(
                        select(QuizQuestion)
                        .where(QuizQuestion.lesson_id == lesson.id)
                        .order_by(QuizQuestion.stable_key)
                    )
                )
                require(
                    questions[0].answer_key["kind"] == "reference_only",
                    "Unexpected question order",
                )
                require(
                    questions[1].answer_key["kind"] == "explicit_source",
                    "Unexpected scoring key",
                )
                kanji = next(
                    k
                    for k in db.scalars(select(KanjiRecord).order_by(KanjiRecord.id))
                    if k.source.get("kind") != "supporting_printed_glyph"
                )
                plan = {
                    "run_id": str(uuid4()),
                    "owner_id": str(owner),
                    "lesson_id": lesson.id,
                    "slug": lesson.slug,
                    "kanji_id": kanji.id,
                    "character": kanji.character,
                    "content_digest": content_digest(c),
                    "baseline_counts": counts(c),
                    "questions": [
                        {
                            "id": q.id,
                            "key": f"{lesson.slug}:{q.stable_key}",
                            "answer": q.answer_key["text"],
                            "submission_id": str(uuid4()),
                            "manual": i == 0,
                        }
                        for i, q in enumerate(questions[:2])
                    ],
                }
                require(
                    all(
                        len(q["answer"]) <= 2000 and q["answer"].strip()
                        for q in plan["questions"]
                    ),
                    "Unusable source answer",
                )
                save(PLAN, plan)
        print(
            json.dumps(
                {
                    "learning_plan_prepared": True,
                    "book_rows_modified": 0,
                    "planned_progress_rows": 1,
                    "planned_review_rows": 1,
                    "planned_attempt_rows": 2,
                }
            )
        )
    finally:
        engine.dispose()


def restricted_app(settings, plan):
    settings = settings.model_copy(
        update={
            "content_source": "database",
            "expose_samples": False,
            "enable_user_writes": True,
            "development_user_ids": [UUID(plan["owner_id"])],
        }
    )
    app = create_app(settings)
    allowed = {
        ("PUT", "/api/v1/me/progress/" + plan["slug"]),
        ("PUT", "/api/v1/me/reviews/" + plan["character"]),
        *(("POST", "/api/v1/me/attempts/" + q["key"]) for q in plan["questions"]),
    }

    @app.middleware("http")
    async def restrict(request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if (request.method, request.url.path) not in allowed:
                return JSONResponse(
                    status_code=403, content={"error": "Outside approved learning test"}
                )
            body = await request.json()
            if request.method == "POST":
                q = next(
                    q for q in plan["questions"] if request.url.path.endswith(q["key"])
                )
                if (
                    body.get("submission_id") != q["submission_id"]
                    or body.get("answer") != q["answer"]
                ):
                    return JSONResponse(
                        status_code=403, content={"error": "Outside fixed submission"}
                    )
            elif "/progress/" in request.url.path:
                if (body.get("progress"), body.get("expected_version")) not in {
                    (50, 0),
                    (100, 1),
                }:
                    return JSONResponse(
                        status_code=403,
                        content={"error": "Outside fixed progress sequence"},
                    )
            elif body.get("knew") is not True or body.get("expected_version") not in {
                0,
                1,
            }:
                return JSONResponse(
                    status_code=403, content={"error": "Outside fixed review sequence"}
                )
        return await call_next(request)

    return app


def serve(settings, plan):
    uvicorn.run(
        restricted_app(settings, plan),
        host="127.0.0.1",
        port=8000,
        access_log=False,
        log_level="warning",
    )


def verify_or_cleanup(settings, plan, cleanup):
    owner = UUID(plan["owner_id"])
    engine = create_database_engine(settings)
    report = {"cleanup": cleanup, "book_content_unchanged": False}
    try:
        with engine.connect() as c, c.begin():
            if not cleanup:
                c.execute(text("SET TRANSACTION READ ONLY"))
            else:
                c.execute(text("SET LOCAL lock_timeout='5s'"))
                c.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:owner,0))"),
                    {"owner": str(owner)},
                )
                c.execute(
                    text(
                        "LOCK TABLE public.user_progress,public.review_items,public.quiz_attempts IN SHARE ROW EXCLUSIVE MODE"
                    )
                )
            schema_check(c)
            require(
                content_digest(c) == plan["content_digest"],
                "Book content changed; stop",
            )
            report["book_content_unchanged"] = True
            with Session(bind=c, join_transaction_mode="rollback_only") as db:
                progress = list(
                    db.scalars(
                        select(UserProgress).where(UserProgress.owner_id == owner)
                    )
                )
                reviews = list(
                    db.scalars(select(ReviewItem).where(ReviewItem.owner_id == owner))
                )
                attempts = list(
                    db.scalars(select(QuizAttempt).where(QuizAttempt.owner_id == owner))
                )
                require(
                    len(progress) <= 1 and len(reviews) <= 1 and len(attempts) <= 2,
                    "Unexpected owner records",
                )
                for p in progress:
                    require(
                        p.lesson_id == plan["lesson_id"]
                        and (p.progress, p.version) in {(50, 1), (100, 2)},
                        "Changed progress",
                    )
                for r in reviews:
                    require(
                        r.kanji_id == plan["kanji_id"]
                        and r.vocabulary_id is None
                        and r.version in {1, 2}
                        and r.reviews == r.version
                        and r.interval_days == r.version
                        and r.lapses == 0,
                        "Changed review",
                    )
                for a in attempts:
                    q = next(
                        (
                            q
                            for q in plan["questions"]
                            if UUID(q["submission_id"]) == a.submission_id
                        ),
                        None,
                    )
                    require(
                        q is not None
                        and a.question_id == q["id"]
                        and a.selected_answer["answer"] == q["answer"],
                        "Changed attempt",
                    )
                settings = settings.model_copy(update={"development_user_ids": [owner]})
                if not cleanup:
                    require(
                        (len(progress), len(reviews), len(attempts)) == (1, 1, 2),
                        "Missing test writes",
                    )
                    require(
                        progress[0].progress == 100 and progress[0].version == 2,
                        "Progress persistence failed",
                    )
                    require(
                        reviews[0].reviews == 2 and reviews[0].interval_days == 2,
                        "Schedule persistence failed",
                    )
                    own = Learning(db, settings, Identity(owner)).dashboard()
                    require(
                        own["quiz"]["graded"] == 1
                        and own["quiz"]["correct"] == 1
                        and own["quiz"]["pending"] == 1,
                        "Quiz aggregation failed",
                    )
                    other = uuid4()
                    # Equal visibility avoids confusing hidden content with owner isolation.
                    alternate = Learning(
                        db,
                        settings.model_copy(update={"development_user_ids": [other]}),
                        Identity(other),
                    ).dashboard()
                    require(
                        not alternate["lessons"]
                        and not alternate["cards"]
                        and alternate["quiz"]["graded"] == 0
                        and alternate["quiz"]["pending"] == 0,
                        "Owner isolation failed",
                    )
                    report.update(
                        {
                            "fresh_database_session_persistence": True,
                            "owner_isolation": True,
                            "progress": 100,
                            "review_interval_days": 2,
                            "quiz_graded": 1,
                            "quiz_correct": 1,
                            "quiz_pending": 1,
                        }
                    )
                    save(
                        FOLDER / "learning-records.json",
                        {
                            "progress": [
                                {
                                    col.name: getattr(p, col.name)
                                    for col in p.__table__.columns
                                }
                                for p in progress
                            ],
                            "reviews": [
                                {
                                    col.name: getattr(r, col.name)
                                    for col in r.__table__.columns
                                }
                                for r in reviews
                            ],
                            "attempts": [
                                {
                                    col.name: getattr(a, col.name)
                                    for col in a.__table__.columns
                                }
                                for a in attempts
                            ],
                        },
                    )
                else:
                    removed = {}
                    for model, records in [
                        (QuizAttempt, attempts),
                        (ReviewItem, reviews),
                        (UserProgress, progress),
                    ]:
                        removed[model.__tablename__] = 0
                        for row in records:
                            predicates = [
                                col == getattr(row, col.name)
                                for col in model.__table__.primary_key.columns
                            ]
                            deleted = db.execute(
                                delete(model).where(
                                    *predicates, model.owner_id == owner
                                )
                            )
                            require(deleted.rowcount == 1, "Cleanup identity mismatch")
                            removed[model.__tablename__] += 1
                    report["deleted"] = removed
        if cleanup:
            with engine.connect() as c, c.begin():
                c.execute(text("SET TRANSACTION READ ONLY"))
                require(
                    counts(c) == plan["baseline_counts"],
                    "Postcleanup inventory mismatch",
                )
                require(
                    content_digest(c) == plan["content_digest"],
                    "Postcleanup content changed",
                )
                private_check(c)
                foreign_key_check(c)
                report["postcleanup_verified"] = True
        save(
            FOLDER
            / (
                "learning-cleanup.json" if cleanup else "learning-database-results.json"
            ),
            report,
        )
        print(json.dumps(report))
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "serve", "verify", "cleanup"])
    args = parser.parse_args()
    settings = Settings()
    if args.mode == "prepare":
        prepare(settings)
    else:
        plan = json.loads(PLAN.read_bytes())
        if args.mode == "serve":
            serve(settings, plan)
        else:
            verify_or_cleanup(settings, plan, args.mode == "cleanup")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - redact credentials/source/SQL at CLI boundary
        print(
            json.dumps(
                {
                    "stopped": True,
                    "error_type": type(exc).__name__,
                    "reason": str(exc)
                    if type(exc) is RuntimeError
                    else "Details suppressed; inspect locally",
                }
            )
        )
        raise SystemExit(1) from None
