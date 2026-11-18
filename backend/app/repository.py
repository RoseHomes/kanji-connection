"""Publication-filtered SQL queries; independent of the in-code sample catalog."""

import json

from fastapi import HTTPException
from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.orm import Session, aliased

from .models import (
    Component,
    KanjiComponent,
    KanjiReading,
    KanjiRecord,
    KanjiRelation,
    LessonKanji,
    LessonRecord,
    LessonSection,
    Vocabulary,
    VocabularyKanji,
)
from .schemas import Kanji, Lesson, LessonDetail, VocabularyResponse


def contains(column, value: str):
    # User '%'/'_' are literal search text, never wildcard operators.
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return column.ilike(f"%{escaped}%", escape="\\")


class DatabaseRepository:
    def __init__(self, session: Session, expose_samples: bool = False):
        self.session = session
        self.visible = ("published", "sample") if expose_samples else ("published",)

    def _kanji_response(self, row: KanjiRecord, components: list[str], readings: dict) -> Kanji:
        return Kanji(
            character=row.character,
            meaning_th=row.meaning_th,
            onyomi=readings.get("on", []),
            kunyomi=readings.get("kun", []),
            romaji=row.romaji,
            strokes=row.strokes,
            component="・".join(components),
            note_th=row.note_th,
            source_url=row.source.get("url", ""),
            review_status=row.review_status,
        )

    def _serialize_kanjis(self, rows: list[KanjiRecord]) -> list[Kanji]:
        if not rows:
            return []
        components: dict[int, list[str]] = {}
        for kanji_id, glyph in self.session.execute(
            select(KanjiComponent.kanji_id, Component.glyph)
            .join(Component)
            .where(
                KanjiComponent.kanji_id.in_([r.id for r in rows]),
                Component.status.in_(self.visible),
            )
            .order_by(KanjiComponent.kanji_id, KanjiComponent.position, Component.id)
        ):
            if glyph not in components.setdefault(kanji_id, []):
                components[kanji_id].append(glyph)
        readings: dict[int, dict] = {}
        for reading in self.session.scalars(
            select(KanjiReading)
            .where(KanjiReading.kanji_id.in_([r.id for r in rows]))
            .order_by(KanjiReading.position, KanjiReading.id)
        ):
            readings.setdefault(reading.kanji_id, {}).setdefault(reading.kind, []).append(
                reading.reading
            )
        return [
            self._kanji_response(
                row, components.get(row.id, []), readings.get(row.id, row.readings)
            )
            for row in rows
        ]

    def lessons(self, q="", part=None, status=None, offset=0, limit=30):
        count = (
            select(func.count())
            .select_from(LessonKanji)
            .join(KanjiRecord)
            .where(
                LessonKanji.lesson_id == LessonRecord.id,
                KanjiRecord.review_status.in_(self.visible),
                KanjiRecord.access_tier == "free",
            )
            .scalar_subquery()
        )
        query = select(LessonRecord, count).where(LessonRecord.catalog_visible.is_(True))
        if part:
            query = query.where(LessonRecord.chapter.between((part - 1) * 5 + 1, part * 5))
        if status:
            query = query.where(LessonRecord.status == status)
        if q:
            query = query.where(
                or_(
                    contains(LessonRecord.title_th, q),
                    contains(cast(LessonRecord.anchors, String), q),
                    contains(cast(LessonRecord.anchors, String), json.dumps(q)[1:-1]),
                )
            )
        return [
            self._lesson_response(row, n)
            for row, n in self.session.execute(
                query.order_by(LessonRecord.chapter).offset(offset).limit(limit)
            )
        ]

    def _lesson_response(self, row, count):
        return Lesson(
            id=row.id,
            chapter=row.chapter,
            is_available=row.status in self.visible and row.access_tier == "free",
            slug=row.slug,
            part=(row.chapter - 1) // 5 + 1,
            title_th=row.title_th,
            summary_th=row.summary_th,
            anchors=row.anchors,
            status=row.status if row.status in self.visible else "needs_review",
            available_count=count
            if row.status in self.visible and row.access_tier == "free"
            else 0,
        )

    def lesson(self, slug: str):
        row = self.session.scalar(
            select(LessonRecord).where(
                LessonRecord.slug == slug,
                LessonRecord.catalog_visible.is_(True),
                LessonRecord.status.in_(self.visible),
                LessonRecord.access_tier == "free",
            )
        )
        if row is None:
            raise HTTPException(404, "ไม่พบบทเรียนที่เผยแพร่")
        kanjis = list(
            self.session.scalars(
                select(KanjiRecord)
                .join(LessonKanji)
                .where(
                    LessonKanji.lesson_id == row.id,
                    KanjiRecord.review_status.in_(self.visible),
                    KanjiRecord.access_tier == "free",
                )
                .order_by(LessonKanji.position, KanjiRecord.id)
            )
        )
        sections = list(
            self.session.scalars(
                select(LessonSection)
                .where(
                    LessonSection.lesson_id == row.id,
                    LessonSection.status.in_(self.visible),
                    LessonSection.access_tier == "free",
                )
                .order_by(LessonSection.position)
            )
        )
        # Internal PDF paths, page audit notes and private provenance are never serialized.
        return LessonDetail(
            **self._lesson_response(row, len(kanjis)).model_dump(),
            kanjis=self._serialize_kanjis(kanjis),
            introduction_th=row.introduction_th,
            provenance=row.provenance.get("public_note", ""),
            sections=[{"kind": s.kind, "blocks": s.blocks} for s in sections],
        )

    def kanjis(self, q="", offset=0, limit=30):
        query = select(KanjiRecord).where(
            KanjiRecord.review_status.in_(self.visible), KanjiRecord.access_tier == "free"
        )
        if q:
            component_match = (
                select(KanjiComponent.kanji_id)
                .join(Component)
                .where(
                    Component.status.in_(self.visible),
                    or_(contains(Component.glyph, q), contains(Component.label_th, q)),
                )
            )
            reading_match = select(KanjiReading.kanji_id).where(contains(KanjiReading.reading, q))
            query = query.where(
                or_(
                    contains(KanjiRecord.character, q),
                    contains(KanjiRecord.meaning_th, q),
                    contains(cast(KanjiRecord.readings, String), q),
                    contains(KanjiRecord.romaji, q),
                    KanjiRecord.id.in_(component_match),
                    KanjiRecord.id.in_(reading_match),
                )
            )
        return self._serialize_kanjis(
            list(self.session.scalars(query.order_by(KanjiRecord.id).offset(offset).limit(limit)))
        )

    def kanji(self, character: str):
        row = self.session.scalar(
            select(KanjiRecord).where(
                KanjiRecord.character == character,
                KanjiRecord.review_status.in_(self.visible),
                KanjiRecord.access_tier == "free",
            )
        )
        if row is None:
            raise HTTPException(404, "ไม่พบคันจิที่เผยแพร่")
        return self._serialize_kanjis([row])[0]

    def compare(self, characters: list[str]):
        rows = list(
            self.session.scalars(
                select(KanjiRecord).where(
                    KanjiRecord.character.in_(characters),
                    KanjiRecord.review_status.in_(self.visible),
                    KanjiRecord.access_tier == "free",
                )
            )
        )
        if len(rows) != len(characters):
            raise HTTPException(404, "ไม่พบคันจิที่เผยแพร่")
        lookup = {r.character: r for r in rows}
        return self._serialize_kanjis([lookup[c] for c in characters])

    def relations(self, character: str):
        source = self.session.scalar(
            select(KanjiRecord).where(
                KanjiRecord.character == character,
                KanjiRecord.review_status.in_(self.visible),
                KanjiRecord.access_tier == "free",
            )
        )
        if source is None:
            raise HTTPException(404, "ไม่พบคันจิที่เผยแพร่")
        target = aliased(KanjiRecord)
        neighbor = (KanjiRelation.source_id == source.id) & (target.id == KanjiRelation.target_id)
        reverse = and_(
            KanjiRelation.directed.is_(False),
            KanjiRelation.target_id == source.id,
            target.id == KanjiRelation.source_id,
        )
        rows = list(
            self.session.execute(
                select(KanjiRelation, target.character)
                .join(target, or_(neighbor, reverse))
                .where(
                    KanjiRelation.status.in_(self.visible),
                    target.review_status.in_(self.visible),
                    target.access_tier == "free",
                )
                .order_by(KanjiRelation.id)
                .limit(50)
            )
        )
        return {
            "character": character,
            "depth": 1,
            "related": list(dict.fromkeys(c for _, c in rows)),
            "relations": [
                {
                    "character": c,
                    "type": r.relation_type,
                    "explanation_th": r.explanation_th,
                    "directed": r.directed,
                }
                for r, c in rows
            ],
        }

    def vocabulary(self, character: str, offset=0, limit=30):
        self.kanji(character)
        query = (
            select(Vocabulary)
            .join(VocabularyKanji)
            .join(KanjiRecord)
            .where(
                KanjiRecord.character == character,
                Vocabulary.status.in_(self.visible),
                Vocabulary.access_tier == "free",
            )
            .distinct()
            .order_by(Vocabulary.id)
            .offset(offset)
            .limit(limit)
        )
        return [
            VocabularyResponse.model_validate(row, from_attributes=True)
            for row in self.session.scalars(query)
        ]
