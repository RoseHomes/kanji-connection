"""Build a loopback-only learning fixture from the verified local book edition."""

import json
from pathlib import Path

from app.content_revision import digest
from app.editorial_preview_snapshot import materialize_snapshot, readonly_engine
from app.editorial_sync import TABLES, snapshot
from app.models import (
    ExampleSentence,
    JLPTAssignment,
    JLPTReferenceRelease,
    KanjiRecord,
    LearningPath,
    LearningPathItem,
    LearningUnit,
    Vocabulary,
)
from sqlalchemy import create_engine, event, select, update
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
OPENJLPT_VERSION = "0d1d3410bec90bd4098a7c72de820543cb4f707c"
OPENJLPT_SOURCE = "https://github.com/evanclan/OpenJLPT"
EDITION = "2026-11-19-final-v2"


def _load_book():
    receipt = json.loads(
        (ROOT / "private/publication-release/receipt.json").read_bytes()
    )
    if receipt["revision"] != EDITION or receipt["committed"] is not True:
        raise ValueError(
            "The local development fixture requires the verified book release"
        )
    source = (
        ROOT
        / "private/editorial-preview/snapshots"
        / f"working-{receipt['before_sha256'][:16]}.sqlite3"
    )
    if not source.is_file():
        raise ValueError("The verified local book snapshot is missing")
    reader = readonly_engine(source)
    try:
        with reader.connect() as connection:
            data = snapshot(connection)
    finally:
        reader.dispose()
    if digest(data) != receipt["before_sha256"]:
        raise ValueError("The local book snapshot does not match the release receipt")
    return data, receipt


def _add_fixture(db, data):
    # Full reference totals come from the pinned audit. Only these six N5
    # assignments are included. CSV row numbers exclude the header.
    manifest = {
        "scope": "development-only",
        "counts": {
            "N5": {"kanji": 84, "vocabulary": 674},
            "N4": {"kanji": 169, "vocabulary": 630},
            "N3": {"kanji": 387, "vocabulary": 1659},
            "N2": {"kanji": 398, "vocabulary": 1778},
            "N1": {"kanji": 1345, "vocabulary": 3070},
        },
        "file_sha256": {
            "kanji-n5.csv": "d1d20aed0512e368314efe7d5d8e217984f9681b9ab6dd137c081d627c3d7d57",
            "vocab-n5.csv": "ea82df093658fa35f24fd53073ce9a0a07765f50314bce04debf45b278ebfcd3",
        },
    }
    release = JLPTReferenceRelease(
        source_key="openjlpt",
        version=OPENJLPT_VERSION,
        source_url=f"{OPENJLPT_SOURCE}/tree/{OPENJLPT_VERSION}",
        license="CC BY-SA 4.0",
        attribution="OpenJLPT · Jonathan Waller (Tanos) · JMdict / KANJIDIC2 (EDRDG)",
        manifest=manifest,
        manifest_sha256=digest(manifest),
    )
    db.add(release)
    db.flush()
    glyphs = {
        k.character: k.id
        for k in db.scalars(
            select(KanjiRecord).where(
                KanjiRecord.character.in_(tuple("一二三")),
                KanjiRecord.review_status == "published",
                KanjiRecord.access_tier == "free",
            )
        )
    }
    words = {
        (w.written_form, w.reading): w.id
        for w in db.scalars(
            select(Vocabulary).where(
                Vocabulary.written_form.in_(("一人", "二人", "三日", "百円", "十分")),
                Vocabulary.status == "published",
                Vocabulary.access_tier == "free",
            )
        )
    }
    kanjis = [{"kanji_id": glyphs[glyph]} for glyph in "一二三"]
    people = [
        {"vocabulary_id": words[pair]}
        for pair in (("一人", "ひとり"), ("二人", "ふたり"))
    ]
    day = {"vocabulary_id": words[("三日", "みっか")]}
    for glyph, row_number, target in zip("一二三", (2, 8, 13), kanjis, strict=True):
        db.add(
            JLPTAssignment(
                release_id=release.id,
                reference_key=f"kanji:{glyph}",
                level=5,
                **target,
                match_provenance={
                    "file": "kanji-n5.csv",
                    "reference_order": row_number,
                    "method": "glyph",
                },
            )
        )
    for key, row_number, jmdict, target in zip(
        ("3fb1b70809", "94c2076821", "1713d0bbe8"),
        (528, 544, 599),
        ("1576150", "1582670", "1301330"),
        (*people, day),
        strict=True,
    ):
        db.add(
            JLPTAssignment(
                release_id=release.id,
                reference_key=f"vocabulary:{key}",
                level=5,
                **target,
                match_provenance={
                    "file": "vocab-n5.csv",
                    "reference_order": row_number,
                    "jmdict_id": jmdict,
                    "method": "written_form_and_reading",
                },
            )
        )
    chapter = next(l for l in data["lessons"] if l["slug"] == "chapter-29")
    section = next(
        s
        for s in data["lesson_sections"]
        if s["lesson_id"] == chapter["id"] and s["kind"] == "vocabulary"
    )
    original = next(
        s
        for block in section["blocks"]
        for s in block.get("sentences", [])
        if s["text"] == "8時に家を出ます。"
    )
    sentence = ExampleSentence(
        text_ja=original["text"],
        reading=original["reading"],
        meaning_th=original["meaning_th"],
        usage_notes_th=original["note_th"],
        status="published",
        access_tier="free",
        provenance={
            "edition": EDITION,
            "chapter_slug": chapter["slug"],
            "section_position": section["position"],
            "source_url": original["source_url"],
        },
    )
    db.add(sentence)
    db.flush()

    def path(kind, slug, title, order, **extra):
        result = LearningPath(
            kind=kind,
            slug=slug,
            title_th=title,
            status="published",
            access_tier="free",
            sort_order=order,
            **extra,
        )
        db.add(result)
        db.flush()
        return result

    def unit(parent, key, title, items):
        lesson = LearningUnit(
            path_id=parent.id, unit_key=key, title_th=title, status="published"
        )
        db.add(lesson)
        db.flush()
        for order, target in enumerate(items):
            db.add(
                LearningPathItem(
                    path_id=parent.id,
                    unit_id=lesson.id,
                    sort_order=order,
                    required="sentence_id" not in target,
                    **target,
                )
            )

    numbers = path("category", "numbers-and-counting", "ตัวเลขและการนับ", 0)
    unit(
        numbers,
        "basic-numbers",
        "ตัวเลขในคำศัพท์และเวลา",
        [
            *kanjis,
            {"vocabulary_id": words[("百円", "ひゃくえん")]},
            {"vocabulary_id": words[("十分", "じゅっぷん")]},
            {"sentence_id": sentence.id},
        ],
    )
    counters = path("category", "japanese-counters", "ลักษณนามญี่ปุ่น", 1)
    unit(
        counters,
        "people-and-time",
        "นับคนและเวลา",
        [*people, day, {"sentence_id": sentence.id}],
    )
    for level in range(5, 0, -1):
        jlpt = path(
            "jlpt",
            f"n{level}",
            f"JLPT N{level}",
            5 - level,
            jlpt_level=level,
            jlpt_release_id=release.id,
        )
        if level == 5:
            unit(
                jlpt,
                "numbers-in-use",
                "N5 · ตัวเลขและคำที่ใช้ในการนับ",
                [*kanjis, *people, day],
            )


def development_engine(folder):
    data, receipt = _load_book()
    mirror = materialize_snapshot(data, folder)
    mirror.dispose()
    path = folder / f"working-{receipt['before_sha256'][:16]}.sqlite3"
    writer = create_engine("sqlite:///" + path.as_posix())

    @event.listens_for(writer, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    try:
        with Session(writer) as db, db.begin():
            for table in TABLES.values():
                changes = {
                    field: "published"
                    for field in ("status", "review_status")
                    if field in table.c
                }
                if "access_tier" in table.c:
                    changes["access_tier"] = "free"
                if "catalog_visible" in table.c:
                    changes["catalog_visible"] = True
                if changes:
                    db.execute(update(table).values(**changes))
            if digest(snapshot(db.connection())) != receipt["after_sha256"]:
                raise ValueError(
                    "The local mirror does not reproduce the public book edition"
                )
            _add_fixture(db, data)
            db.flush()
            if digest(snapshot(db.connection())) != receipt["after_sha256"]:
                raise ValueError("Expansion fixture changed the existing book edition")
    finally:
        writer.dispose()
    return readonly_engine(path)
