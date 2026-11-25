"""Public projections of curated learning paths and canonical content."""

import base64
import binascii
import hashlib
import json
import unicodedata
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy import String, and_, case, cast, func, or_, select, tuple_
from sqlalchemy.orm import Session

from .database import publication_read_session
from .models import (
    ExampleSentence,
    JLPTAssignment,
    JLPTReferenceRelease,
    KanjiReading,
    KanjiRecord,
    LearningPath,
    LearningPathItem,
    LearningUnit,
    Vocabulary,
)
from .repository import DatabaseRepository, contains
from .schemas import Kanji

router = APIRouter(prefix="/api/v1/learning/paths", tags=["learning paths"])
ReadSession = Annotated[Session | None, Depends(publication_read_session)]
PathKind = Literal["category", "jlpt"]
ItemType = Literal["kanji", "vocabulary", "sentence"]
ItemSort = Literal["learning", "reference"]
Slug = Annotated[str, Path(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=80)]


class Counts(BaseModel):
    kanji: int = 0
    vocabulary: int = 0
    sentence: int = 0


class Reference(BaseModel):
    source_key: str
    version: str
    source_url: str
    license: str
    attribution: str
    totals: Counts


class PathSummary(BaseModel):
    kind: PathKind
    slug: str
    title_th: str
    summary_th: str
    level: int | None
    counts: Counts
    reference: Reference | None


class UnitSummary(BaseModel):
    unit_key: str
    title_th: str
    intro_th: str
    available_count: int


class PathDetail(PathSummary):
    units: list[UnitSummary]


class Item(BaseModel):
    id: int  # Canonical ID; type distinguishes the three identity spaces.
    text: str
    meaning_th: str
    context_note_th: str
    level: int | None
    unit_key: str | None
    path_slug: str
    required: bool


class KanjiItem(Item):
    type: Literal["kanji"] = "kanji"
    kanji: Kanji


class VocabularyItem(Item):
    type: Literal["vocabulary"] = "vocabulary"
    reading: str
    usage_notes: str


class SentenceItem(Item):
    type: Literal["sentence"] = "sentence"
    reading: str
    usage_notes: str


LearningItem = Annotated[KanjiItem | VocabularyItem | SentenceItem, Field(discriminator="type")]


class ItemPage(BaseModel):
    items: list[LearningItem]
    next_cursor: str | None
    total: int


class UnitDetail(UnitSummary):
    path: PathSummary
    items: list[LearningItem]
    previous_unit_key: str | None
    next_unit_key: str | None
    practice_available: Literal[False] = False


def _public_paths():
    return (LearningPath.status == "published", LearningPath.access_tier == "free")


def _visible_items(path_ids, q="", item_type=None):
    path, unit, item = LearningPath, LearningUnit, LearningPathItem
    kanji, word, sentence = KanjiRecord, Vocabulary, ExampleSentence
    item_kind = case(
        (item.kanji_id.is_not(None), "kanji"),
        (item.vocabulary_id.is_not(None), "vocabulary"),
        else_="sentence",
    )
    assignment = (
        select(JLPTAssignment.id)
        .where(
            JLPTAssignment.release_id == path.jlpt_release_id,
            JLPTAssignment.level == path.jlpt_level,
            or_(
                JLPTAssignment.kanji_id == item.kanji_id,
                JLPTAssignment.vocabulary_id == item.vocabulary_id,
            ),
        )
        .correlate(path, item)
    )
    reference_key = assignment.with_only_columns(
        func.min(JLPTAssignment.reference_key)
    ).scalar_subquery()
    reference_order = assignment.with_only_columns(
        func.min(JLPTAssignment.match_provenance["reference_order"].as_integer()),
    ).scalar_subquery()
    query = (
        select(
            item.id.label("membership_id"),
            item.path_id,
            item.unit_id,
            item.sort_order,
            item.required,
            item.context_note_th,
            path.slug.label("path_slug"),
            unit.unit_key,
            func.coalesce(unit.sort_order, 0).label("unit_order"),
            case((item.unit_id.is_(None), 1), else_=0).label("supplementary"),
            item_kind.label("item_type"),
            func.coalesce(item.kanji_id, item.vocabulary_id, item.sentence_id).label("target_id"),
            case((item.sentence_id.is_(None), path.jlpt_level)).label("level"),
            func.coalesce(path.jlpt_level, 0).label("path_level"),
            reference_key.label("reference_key"),
            reference_order.label("reference_order"),
        )
        .select_from(item)
        .join(path, path.id == item.path_id)
        .outerjoin(unit, and_(unit.id == item.unit_id, unit.path_id == path.id))
        .outerjoin(kanji, kanji.id == item.kanji_id)
        .outerjoin(word, word.id == item.vocabulary_id)
        .outerjoin(sentence, sentence.id == item.sentence_id)
        .where(
            item.path_id.in_(path_ids),
            *_public_paths(),
            or_(item.unit_id.is_(None), unit.status == "published"),
            or_(
                and_(kanji.review_status == "published", kanji.access_tier == "free"),
                and_(word.status == "published", word.access_tier == "free"),
                and_(sentence.status == "published", sentence.access_tier == "free"),
            ),
            or_(path.kind == "category", item.sentence_id.is_not(None), assignment.exists()),
        )
    )
    if item_type:
        query = query.where(item_kind == item_type)
    if q:
        hiragana = str.maketrans({n: n - 96 for n in range(0x30A1, 0x30F7)})
        katakana = {v: k for k, v in hiragana.items()}
        readings = {q, q.translate(hiragana), q.translate(katakana)}
        legacy_readings = readings | {json.dumps(reading)[1:-1] for reading in readings}
        normalized_reading = (
            select(KanjiReading.id)
            .where(
                KanjiReading.kanji_id == kanji.id,
                or_(*(contains(KanjiReading.reading, reading) for reading in sorted(readings))),
            )
            .exists()
        )
        query = query.where(
            or_(
                *(
                    contains(column, q)
                    for column in (
                        kanji.character,
                        kanji.meaning_th,
                        kanji.romaji,
                        word.written_form,
                        word.meaning_th,
                        word.romaji,
                        sentence.text_ja,
                        sentence.meaning_th,
                    )
                ),
                *(
                    contains(column, reading)
                    for column in (word.reading, sentence.reading)
                    for reading in sorted(readings)
                ),
                *(
                    contains(cast(kanji.readings, String), reading)
                    for reading in sorted(legacy_readings)
                ),
                normalized_reading,
            )
        )
    return query


def _find_path(db, kind, slug):
    path = (
        db.scalar(
            select(LearningPath).where(
                LearningPath.kind == kind,
                LearningPath.slug == slug,
                *_public_paths(),
            )
        )
        if db is not None
        else None
    )
    if path is None:
        raise HTTPException(404, "ไม่พบเส้นทางที่เผยแพร่")
    return path


def scoped_kanji_ids(kind: PathKind, slug: str, include_prerequisites: bool = False):
    paths = (
        select(LearningPath.id).where(LearningPath.kind == kind, *_public_paths()).correlate(None)
    )
    if include_prerequisites:
        selected_level = (
            select(LearningPath.jlpt_level)
            .where(
                LearningPath.kind == "jlpt",
                LearningPath.slug == slug,
                *_public_paths(),
            )
            .correlate(None)
            .scalar_subquery()
        )
        paths = paths.where(LearningPath.jlpt_level >= selected_level)
    else:
        paths = paths.where(LearningPath.slug == slug)
    visible = _visible_items(paths, item_type="kanji").subquery()
    return select(visible.c.target_id)


def _summaries(db, paths):
    if not paths:
        return []
    rows = _visible_items([path.id for path in paths]).subquery()
    counts = {}
    for path_id, item_type, count in db.execute(
        select(rows.c.path_id, rows.c.item_type, func.count()).group_by(
            rows.c.path_id, rows.c.item_type
        )
    ):
        counts.setdefault(path_id, {})[item_type] = count
    release_ids = {p.jlpt_release_id for p in paths if p.jlpt_release_id is not None}
    releases = (
        {
            r.id: r
            for r in db.scalars(
                select(JLPTReferenceRelease).where(JLPTReferenceRelease.id.in_(release_ids))
            )
        }
        if release_ids
        else {}
    )
    result = []
    for path in paths:
        release = releases.get(path.jlpt_release_id)
        reference = None
        if release is not None:
            totals = release.manifest.get("counts", {}).get(f"N{path.jlpt_level}", {})
            reference = Reference(
                source_key=release.source_key,
                version=release.version,
                source_url=release.source_url,
                license=release.license,
                attribution=release.attribution,
                totals=Counts(**totals),
            )
        result.append(
            PathSummary(
                kind=path.kind,
                slug=path.slug,
                title_th=path.title_th,
                summary_th=path.summary_th,
                level=path.jlpt_level,
                counts=Counts(**counts.get(path.id, {})),
                reference=reference,
            )
        )
    return result


def _units(db, path_id):
    visible = _visible_items([path_id]).subquery()
    counts = (
        select(visible.c.unit_id, func.count().label("total"))
        .group_by(visible.c.unit_id)
        .subquery()
    )
    return db.execute(
        select(LearningUnit, counts.c.total)
        .join(counts, counts.c.unit_id == LearningUnit.id)
        .where(LearningUnit.path_id == path_id)
        .order_by(LearningUnit.sort_order, LearningUnit.id)
    ).all()


def _unit_summary(unit, count):
    return UnitSummary(
        unit_key=unit.unit_key,
        title_th=unit.title_th,
        intro_th=unit.intro_th,
        available_count=count,
    )


def _items(db, rows):
    ids = {
        kind: {r.target_id for r in rows if r.item_type == kind}
        for kind in ("kanji", "vocabulary", "sentence")
    }
    kanji_rows = (
        list(db.scalars(select(KanjiRecord).where(KanjiRecord.id.in_(ids["kanji"]))))
        if ids["kanji"]
        else []
    )
    kanjis = dict(
        zip((r.id for r in kanji_rows), DatabaseRepository(db)._serialize_kanjis(kanji_rows))
    )
    words = (
        {
            r.id: r
            for r in db.scalars(select(Vocabulary).where(Vocabulary.id.in_(ids["vocabulary"])))
        }
        if ids["vocabulary"]
        else {}
    )
    sentences = (
        {
            r.id: r
            for r in db.scalars(
                select(ExampleSentence).where(ExampleSentence.id.in_(ids["sentence"]))
            )
        }
        if ids["sentence"]
        else {}
    )
    result = []
    for row in rows:
        common = {
            "id": row.target_id,
            "context_note_th": row.context_note_th,
            "level": row.level,
            "unit_key": row.unit_key,
            "path_slug": row.path_slug,
            "required": row.required,
        }
        if row.item_type == "kanji":
            k = kanjis[row.target_id]
            result.append(KanjiItem(**common, text=k.character, meaning_th=k.meaning_th, kanji=k))
        elif row.item_type == "vocabulary":
            word = words[row.target_id]
            result.append(
                VocabularyItem(
                    **common,
                    text=word.written_form,
                    meaning_th=word.meaning_th,
                    reading=word.reading,
                    usage_notes=word.usage_notes,
                )
            )
        else:
            sentence = sentences[row.target_id]
            result.append(
                SentenceItem(
                    **common,
                    text=sentence.text_ja,
                    meaning_th=sentence.meaning_th,
                    reading=sentence.reading,
                    usage_notes=sentence.usage_notes_th,
                )
            )
    return result


def _cursor_key(cursor, scope, key_types):
    try:
        token = json.loads(base64.b64decode(cursor, altchars=b"-_", validate=True))
        values = token[1:]
        if (
            not isinstance(token, list)
            or token[0] != scope
            or len(values) != len(key_types)
            or any(type(value) is not kind for value, kind in zip(values, key_types))
        ):
            raise ValueError
    except (ValueError, TypeError, IndexError, KeyError, binascii.Error):
        raise HTTPException(422, "ตัวแบ่งหน้าไม่ตรงกับตัวกรองปัจจุบัน") from None
    return values


@router.get("", response_model=list[PathSummary])
def list_paths(
    db: ReadSession,
    kind: PathKind | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    if db is None:
        return []
    query = select(LearningPath).where(*_public_paths())
    if kind is not None:
        query = query.where(LearningPath.kind == kind)
    paths = list(
        db.scalars(
            query.order_by(
                LearningPath.kind,
                LearningPath.sort_order,
                LearningPath.id,
            )
            .offset(offset)
            .limit(limit)
        )
    )
    return _summaries(db, paths)


@router.get("/{kind}/{slug}", response_model=PathDetail)
def path_detail(kind: PathKind, slug: Slug, db: ReadSession):
    path = _find_path(db, kind, slug)
    return PathDetail(
        **_summaries(db, [path])[0].model_dump(),
        units=[_unit_summary(u, n) for u, n in _units(db, path.id)],
    )


@router.get("/{kind}/{slug}/items", response_model=ItemPage)
def path_items(
    kind: PathKind,
    slug: Slug,
    db: ReadSession,
    item_type: Annotated[ItemType | None, Query(alias="type")] = None,
    q: str = Query("", max_length=100),
    sort: ItemSort = "learning",
    include_prerequisites: bool = False,
    cursor: str | None = Query(None, max_length=1000),
    limit: int = Query(30, ge=1, le=100),
):
    path = _find_path(db, kind, slug)
    if kind == "category" and (include_prerequisites or sort == "reference"):
        raise HTTPException(422, "ใช้ตัวกรองระดับอ้างอิงได้เฉพาะเส้นทาง JLPT")
    paths = [path]
    if include_prerequisites:
        paths += list(
            db.scalars(
                select(LearningPath)
                .where(
                    LearningPath.kind == "jlpt",
                    LearningPath.jlpt_level > path.jlpt_level,
                    *_public_paths(),
                )
                .order_by(LearningPath.jlpt_level)
            )
        )
    q = unicodedata.normalize("NFC", q.strip())
    visible = _visible_items([p.id for p in paths], q, item_type).subquery()
    if include_prerequisites:
        ranked = select(
            visible,
            func.row_number()
            .over(
                partition_by=(visible.c.item_type, visible.c.target_id),
                order_by=(visible.c.path_level, visible.c.membership_id),
            )
            .label("occurrence"),
        ).subquery()
        visible = select(ranked).where(ranked.c.occurrence == 1).subquery()
    c = visible.c
    order = [-c.path_level]
    key_types = [int]
    if sort == "reference":
        order.extend(
            [
                case((c.reference_key.is_(None), 1), else_=0),
                case((c.reference_order.is_(None), 1), else_=0),
                func.coalesce(c.reference_order, 0),
                func.coalesce(c.reference_key, ""),
            ]
        )
        key_types.extend([int, int, int, str])
    order.extend([c.supplementary, c.unit_order, c.sort_order, c.membership_id])
    key_types.extend([int, int, int, int])
    scope = hashlib.sha256(
        json.dumps(
            [
                [(p.id, p.jlpt_release_id) for p in paths],
                q,
                item_type,
                sort,
                include_prerequisites,
            ]
        ).encode()
    ).hexdigest()
    query = select(visible, *(key.label(f"key_{i}") for i, key in enumerate(order)))
    if cursor:
        query = query.where(tuple_(*order) > tuple_(*_cursor_key(cursor, scope, key_types)))
    rows = db.execute(query.order_by(*order).limit(limit + 1)).all()
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        values = [getattr(rows[-1], f"key_{i}") for i in range(len(order))]
        next_cursor = base64.urlsafe_b64encode(json.dumps([scope, *values]).encode()).decode()
    return ItemPage(
        items=_items(db, rows),
        next_cursor=next_cursor,
        total=db.scalar(select(func.count()).select_from(visible)),
    )


@router.get("/{kind}/{slug}/units/{unit_key}", response_model=UnitDetail)
def unit_detail(kind: PathKind, slug: Slug, unit_key: Slug, db: ReadSession):
    path = _find_path(db, kind, slug)
    units = _units(db, path.id)
    index = next((i for i, (unit, _) in enumerate(units) if unit.unit_key == unit_key), None)
    if index is None:
        raise HTTPException(404, "ไม่พบหน่วยเรียนที่เผยแพร่")
    unit, count = units[index]
    rows = db.execute(
        _visible_items([path.id])
        .where(LearningPathItem.unit_id == unit.id)
        .order_by(LearningPathItem.sort_order, LearningPathItem.id)
    ).all()
    return UnitDetail(
        **_unit_summary(unit, count).model_dump(),
        path=_summaries(db, [path])[0],
        items=_items(db, rows),
        previous_unit_key=units[index - 1][0].unit_key if index else None,
        next_unit_key=units[index + 1][0].unit_key if index + 1 < len(units) else None,
    )
