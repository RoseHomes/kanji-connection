"""Real private JSON coverage and insert-only ORM integration, entirely offline."""

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

from app.book_bundle import build_bundle
from app.book_import import apply_bundle
from app.book_verify import parse_example, verify
from app.content_schema import Chapter, SourcePage
from app.json_content import load_dataset
from app.models import Base, KanjiRecord

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "private/kanji-connection-extracted"


@pytest.fixture(scope="module")
def book():
    if not SOURCE.exists():
        pytest.skip("Private structured source unavailable")
    return load_dataset(SOURCE)


@pytest.fixture(scope="module")
def bundle(book):
    return build_bundle(book, verify(book, None))


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def constraints(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as value:
        yield value
    engine.dispose()


def test_strict_page_model_rejects_bad_page_or_unknown_fields():
    with pytest.raises(ValidationError):
        SourcePage(pdf_page=0, section="cover", plain_text="x")
    with pytest.raises(ValidationError):
        SourcePage(pdf_page=1, section="cover", plain_text="x", unexpected=True)


def test_explicit_japanese_examples_are_recognized_without_inventing_words():
    assert parse_example("入口 いりぐち") == ("入口", "いりぐち")
    assert parse_example("Demo UI text without a word-reading pair") is None


def test_all_chapters_and_source_report_reconcile(book):
    assert len(book.chapters) == 30 and len(book.pages) == 243
    assert len({x.character for c in book.chapters for x in c.kanji_cards}) == 313
    assert len({(x.word, x.reading) for c in book.chapters for x in c.vocabulary}) == 197
    assert sum(len(c.kanji_cards) for c in book.chapters) == 420
    assert sum(len(c.vocabulary) for c in book.chapters) == 240
    assert sum(len(c.exercises) for c in book.chapters) == 420
    assert sum(len(c.answers) for c in book.chapters) == 420
    assert sum(len(c.comparisons) for c in book.chapters) == 90
    assert sum(len(c.memory_tips) for c in book.chapters) == 90


def test_json_source_is_not_normalized_or_rewritten(book):
    for path, digest in book.source_files.items():
        assert hashlib.sha256((SOURCE / path).read_bytes()).hexdigest() == digest
    for chapter in book.chapters:
        original = json.loads(
            (SOURCE / f"chapters/chapter_{chapter.chapter:02}.json").read_text("utf-8")
        )
        assert chapter.model_dump() == original


def test_pages_and_answer_alignment(book):
    assert [p.pdf_page for p in book.pages] == list(range(1, 244))
    for c in book.chapters:
        assert c.pdf_pages.start == 11 + (c.chapter - 1) * 7
        for q, a in zip(c.exercises, c.answers):
            assert (q.number, q.prompt, q.answer) == (a.number, a.prompt, a.answer)
            assert a.pdf_page == 221 + (c.chapter - 1) // 2
        assert c.diagram.comparison_pairs == c.comparisons


@pytest.mark.parametrize(
    "damage",
    [
        "missing_answer",
        "wrong_answer",
        "bad_page",
        "broken_node",
        "duplicate_card",
        "unknown_field",
    ],
)
def test_rejects_missing_conflicting_or_broken_content(book, damage):
    chapter = book.chapters[0].model_dump()
    if damage == "missing_answer":
        chapter["answers"].pop()
    if damage == "wrong_answer":
        chapter["answers"][0]["answer"] = "CONFLICT"
    if damage == "bad_page":
        chapter["kanji_cards"][0]["pdf_page"] = 243
    if damage == "broken_node":
        chapter["diagram"]["core"]["kanji"] = "無"
    if damage == "duplicate_card":
        chapter["kanji_cards"][1] = chapter["kanji_cards"][0]
    if damage == "unknown_field":
        chapter["guessed_content"] = "invalid"
    with pytest.raises(ValidationError):
        Chapter.model_validate(chapter)


def test_missing_diagram_fields_remain_missing_and_flagged(book):
    evidence = verify(book, None)
    assert len(evidence["examples"]) == 254
    assert book.chapters[1].diagram.core is None and book.chapters[3].diagram.core is None
    assert {i["id"] for i in book.issues if i["kind"] == "diagram_core_not_provided"} == {
        "diagram_core_not_provided:2",
        "diagram_core_not_provided:4",
    }
    assert not evidence["editorial_approved"]


def test_all_foreign_keys_idempotency_and_editorial_changes_preserved(bundle, session):
    first = apply_bundle(session, bundle)
    assert sum(first["inserted"].values()) == len(bundle.operations)
    assert not first["conflicts"]
    session.commit()
    record = session.scalar(select(KanjiRecord).where(KanjiRecord.character == "木"))
    record.meaning_th = "EDITORIAL CHANGE"
    record.review_status = "verified"
    session.commit()
    second = apply_bundle(session, bundle)
    assert not second["inserted"]
    assert record.meaning_th == "EDITORIAL CHANGE" and record.review_status == "verified"
    assert any("meaning_th" in c["fields"] for c in second["conflicts"])
    assert session.scalar(select(func.count()).select_from(KanjiRecord)) == 313 + len(
        bundle.supporting_glyphs
    )


def test_rollback_leaves_no_partial_import(bundle, session):
    apply_bundle(session, bundle)
    session.rollback()
    assert all(
        session.scalar(select(func.count()).select_from(t)) == 0
        for t in Base.metadata.sorted_tables
    )


@pytest.mark.parametrize("damage", ["public", "user_data", "duplicate_key", "oversize"])
def test_preflight_rejects_unsafe_plans_before_any_insert(bundle, session, damage):
    broken = bundle.model_copy(deep=True)
    if damage == "public":
        next(op for op in broken.operations if op["table"] == "lessons")["values"][
            "catalog_visible"
        ] = True
    if damage == "user_data":
        broken.operations.append({"table": "user_progress", "key": {}, "values": {}})
    if damage == "duplicate_key":
        broken.operations.append(broken.operations[0])
    if damage == "oversize":
        next(op for op in broken.operations if op["table"] == "lessons")["values"]["title_th"] = (
            "x" * 301
        )
    with pytest.raises(ValueError):
        apply_bundle(session, broken)
    assert all(
        session.scalar(select(func.count()).select_from(t)) == 0
        for t in Base.metadata.sorted_tables
    )


def test_relations_keep_mnemonics_separate_and_no_fake_assets(bundle):
    relations = [op for op in bundle.operations if op["table"] == "kanji_relations"]
    assert {op["key"]["relation_type"] for op in relations} == {"mnemonic", "visual_similarity"}
    assert all(op["key"]["source_id"] != op["key"]["target_id"] for op in relations)
    assert not any(op["table"] in {"visual_assets", "kanji_components"} for op in bundle.operations)
    assert sum(op["table"] == "quiz_questions" for op in bundle.operations) == 450
    assert all(not op["values"].get("catalog_visible", False) for op in bundle.operations)
    assert all(op["values"].get("options", []) == [] for op in bundle.operations)
