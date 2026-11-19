"""Run a persistent, local-only SQLite development server. Never connects to Supabase DB."""

import argparse
import os
import sys
from pathlib import Path
from uuid import UUID

import uvicorn
from sqlalchemy import create_engine, event, select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from sqlalchemy.orm import Session

from app.book_bundle import Bundle
from app.book_import import apply_bundle
from app.catalog import SAMPLES
from app.config import Settings
from app.learning import sample_questions
from app.main import create_app
from app.models import Base, LessonRecord, QuizQuestion
from app.seed import seed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev-user", type=UUID, action="append", default=[])
    parser.add_argument("--private-book", action="store_true")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.private_book and not args.dev_user:
        parser.error("--private-book requires at least one explicit --dev-user UUID")
    folder = ROOT / "private/development"
    folder.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        "sqlite:///" + str(folder / ("book.db" if args.private_book else "sample.db")),
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def constraints(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db, db.begin():
        if args.private_book:
            bundle = Bundle.model_validate_json(
                (ROOT / "private/json-content/import-bundle.json").read_bytes()
            )
            result = apply_bundle(db, bundle)
            print(
                "Local private import prepared; existing editorial differences preserved:",
                len(result["conflicts"]),
            )
        else:
            seed(db, include_samples=True)
            lesson = db.scalar(select(LessonRecord).where(LessonRecord.chapter == 2))
            for question, sample in zip(sample_questions(), SAMPLES):
                stable = question["key"].split(":", 1)[1]
                if not db.scalar(
                    select(QuizQuestion).where(
                        QuizQuestion.lesson_id == lesson.id,
                        QuizQuestion.stable_key == stable,
                    )
                ):
                    db.add(
                        QuizQuestion(
                            lesson_id=lesson.id,
                            stable_key=stable,
                            question_type="kanji_reading",
                            prompt={"text": question["prompt"]},
                            options=[],
                            answer_key={"kind": "sample", "text": sample.kunyomi[0]},
                            explanation_th="",
                            status="sample",
                            provenance={
                                "url": sample.source_url,
                                "kind": "independent_sample",
                            },
                        )
                    )
    settings = Settings(
        _env_file=None,
        content_source="database",
        expose_samples=not args.private_book,
        enable_user_writes=True,
        development_user_ids=args.dev_user,
        supabase_url=os.environ.get("SUPABASE_URL"),
    )
    print(
        "Local SQLite development only; no Supabase database connection or migration. Bind: 127.0.0.1"
    )
    uvicorn.run(create_app(settings, engine), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
