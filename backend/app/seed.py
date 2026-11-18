"""Insert-only independent sample seed. Never promotes or overwrites existing editorial records."""

import argparse

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .catalog import LESSONS, SAMPLES
from .database import create_database_engine, require_write_authorization
from .models import (
    Component,
    KanjiComponent,
    KanjiReading,
    KanjiRecord,
    KanjiRelation,
    LessonKanji,
    LessonRecord,
)


def seed(session: Session, *, include_samples: bool = False):
    if session.bind.dialect.name == "postgresql":
        session.execute(text("SELECT pg_advisory_xact_lock(17171701)"))
    status = "sample" if include_samples else "needs_review"
    component = session.scalar(select(Component).where(Component.glyph == "木"))
    if component is None:
        component = Component(
            glyph="木",
            label_th="ต้นไม้",
            classification="component",
            source={"kind": "independent_sample"},
            status=status,
        )
        session.add(component)
        session.flush()
    for sample in SAMPLES:
        record = session.scalar(
            select(KanjiRecord).where(KanjiRecord.character == sample.character)
        )
        if record is None:
            record = KanjiRecord(
                character=sample.character,
                meaning_th=sample.meaning_th,
                readings={"on": sample.onyomi, "kun": sample.kunyomi},
                romaji=sample.romaji,
                strokes=sample.strokes,
                note_th=sample.note_th,
                review_status=status,
                access_tier="free",
                source={
                    "url": sample.source_url,
                    "kind": "independent_sample",
                    "thai_review": "pending",
                },
            )
            session.add(record)
            session.flush()
            session.add(
                KanjiComponent(
                    kanji_id=record.id,
                    component_id=component.id,
                    position="whole_or_repeated",
                    explanation_th=sample.note_th,
                )
            )
            for kind, values in [("on", sample.onyomi), ("kun", sample.kunyomi)]:
                for position, value in enumerate(values):
                    session.add(
                        KanjiReading(
                            kanji_id=record.id, reading=value, kind=kind, position=position
                        )
                    )
    for item in LESSONS:
        record = session.scalar(select(LessonRecord).where(LessonRecord.chapter == item.id))
        if record is None:
            record = LessonRecord(
                chapter=item.id,
                slug=item.slug,
                title_th=item.title_th,
                status=status if item.id == 2 else "needs_review",
                summary_th=item.summary_th,
                anchors=item.anchors,
                catalog_visible=True,
                access_tier="free" if item.id == 2 else "private",
                introduction_th="เริ่มจาก 木 แล้วสังเกตส่วนประกอบที่ซ้ำใน 林 และ 森"
                if item.id == 2
                else "",
                provenance={
                    "kind": "curriculum_metadata",
                    "public_note": "ตัวอย่างเขียนใหม่ ไม่ใช่บทฉบับเต็มจากหนังสือ; คำแปลไทยรอตรวจบรรณาธิการ",
                },
            )
            session.add(record)
    session.flush()
    lesson_id = session.scalar(select(LessonRecord.id).where(LessonRecord.chapter == 2))
    ids = [
        session.scalar(select(KanjiRecord.id).where(KanjiRecord.character == s.character))
        for s in SAMPLES
    ]
    for position, kanji_id in enumerate(ids):
        if session.get(LessonKanji, (lesson_id, kanji_id)) is None:
            session.add(LessonKanji(lesson_id=lesson_id, kanji_id=kanji_id, position=position))
    for i, source in enumerate(ids):
        for target in ids[i + 1 :]:
            relation = session.scalar(
                select(KanjiRelation).where(
                    KanjiRelation.source_id == source,
                    KanjiRelation.target_id == target,
                    KanjiRelation.relation_type == "same_component",
                )
            )
            if relation is None:
                session.add(
                    KanjiRelation(
                        source_id=source,
                        target_id=target,
                        relation_type="same_component",
                        directed=False,
                        explanation_th="สังเกตส่วนประกอบ 木 ที่ปรากฏซ้ำ",
                        status=status,
                        provenance={"kind": "independent_sample"},
                    )
                )
    session.flush()


def validate_seed():
    """Validate structure/uniqueness only; this is not PDF or Japanese editorial approval."""
    if (
        len(LESSONS) != 30
        or len(SAMPLES) != 3
        or len({k.character for k in SAMPLES}) != len(SAMPLES)
    ):
        raise ValueError("Invalid sample dataset")
    if {lesson.id for lesson in LESSONS} != set(range(1, 31)) or len(
        {lesson.slug for lesson in LESSONS}
    ) != len(LESSONS):
        raise ValueError("Duplicate or missing chapter identifiers/slugs")
    for lesson in LESSONS:
        if len(lesson.anchors) != len(set(lesson.anchors)):
            raise ValueError("Duplicate anchors within a chapter")
    for item in SAMPLES:
        type(item).model_validate(item.model_dump())
        if any(len(readings) != len(set(readings)) for readings in (item.onyomi, item.kunyomi)):
            raise ValueError("Duplicate readings for a character/kind")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["validate", "dry-run", "import"], default="validate")
    parser.add_argument("--allow-remote-write", action="store_true")
    parser.add_argument(
        "--include-samples",
        action="store_true",
        help="Insert new sample records as sample; never promotes existing records",
    )
    args = parser.parse_args()
    validate_seed()
    if args.mode in {"validate", "dry-run"}:
        print(
            "Structural checks passed (not PDF/editorial approval). Offline plan: "
            "30 curriculum metadata entries and 3 independent samples; "
            "insert missing records only; no DB connection or writes attempted. "
            "Vocabulary, lesson sections and exercises are not included."
        )
        return
    require_write_authorization(args.allow_remote_write)
    engine = create_database_engine(migration=True)
    try:
        with Session(engine) as session, session.begin():
            session.execute(text("SET LOCAL statement_timeout = '30s'"))
            session.execute(text("SET LOCAL lock_timeout = '5s'"))
            seed(session, include_samples=args.include_samples)
    finally:
        engine.dispose()
    print("Sample seed transaction committed")


if __name__ == "__main__":
    main()
