import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.book_bundle import build_bundle
from app.book_import import apply_bundle
from app.book_verify import References, verify
from app.comparison_scoring import assess_comparison, comparison_rubric
from app.editorial import prepare_editorial
from app.json_content import load_dataset
from app.models import Base, Vocabulary
from app.thai_references import shared_string, verify_thai

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def prepared():
    source = ROOT / "private/kanji-connection-extracted"
    dictionaries = ROOT / "private/dictionaries"
    if not source.exists() or not (dictionaries / "JMdict_e.gz").exists():
        pytest.skip("Private source and pinned reference snapshots required")
    book = load_dataset(source)
    references = References(dictionaries)
    evidence = verify(book, references)
    editorial = prepare_editorial(book, references, ROOT / "content/editorial-corrections.json")
    return book, references, editorial, build_bundle(book, evidence, editorial)


def test_xlsx_phonetic_metadata_is_not_part_of_visible_text():
    root = ET.fromstring(
        '<si xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><t>日本</t><rPh><t>ニホン</t></rPh></si>'
    )
    assert shared_string(root) == "日本"


def test_every_original_audit_entry_is_retained_with_a_disposition(prepared):
    _, _, _, bundle = prepared
    records = {item["id"]: item for item in bundle.audit_records}
    assert len(records) == len(bundle.audit_records) == 62
    baseline_path = ROOT / "private/editorial/initial-audit.json"
    if baseline_path.exists():
        baseline = json.loads(baseline_path.read_text("utf-8"))
        assert len(baseline) == 61
        assert {item["id"] for item in baseline}.issubset(records)
    assert len([r for r in records.values() if r["status"] == "open"]) == 4
    assert len([r for r in records.values() if r["classification"] == "actual_content_error"]) == 1


def test_corrections_are_applied_without_rewriting_source(prepared):
    book, _, _, bundle = prepared
    original = next(w for c in book.chapters for w in c.vocabulary if w.word == "裁判")
    assert original.meaning_th == "ศาล / การพิจารณาคดี"
    row = next(
        op
        for op in bundle.operations
        if op["table"] == "vocabularies" and op["key"]["written_form"] == "裁判"
    )
    assert row["values"]["meaning_th"] == "การพิจารณาคดี"
    assert (
        row["values"]["provenance"]["editorial_correction"]["expected_meaning_th"]
        == original.meaning_th
    )
    section_words = [
        word
        for op in bundle.operations
        if op["table"] == "lesson_sections" and op["values"]["kind"] == "vocabulary"
        for word in op["values"]["blocks"][0]["vocabulary"]
    ]
    corrected = next(word for word in section_words if word["word"] == "裁判")
    assert corrected["meaning_th"] == "การพิจารณาคดี"
    assert corrected["source_meaning_th"] == original.meaning_th
    for source, digest in book.source_files.items():
        assert (
            hashlib.sha256(
                (ROOT / "private/kanji-connection-extracted" / source).read_bytes()
            ).hexdigest()
            == digest
        )
    for char, reading in [("口", "くち"), ("好", "すく"), ("靖", "やすい")]:
        record = next(
            op
            for op in bundle.operations
            if op["table"] == "kanjis" and op["key"]["character"] == char
        )
        assert reading in record["values"]["readings"]["kun"]
        assert record["values"]["review_status"] == "needs_review"


def test_all_supporting_characters_remain_non_teaching_and_reference_backed(prepared):
    _, _, editorial, bundle = prepared
    assert len(editorial["supporting"]) == len(bundle.supporting_glyphs) == 45
    for char in bundle.supporting_glyphs:
        row = next(
            op
            for op in bundle.operations
            if op["table"] == "kanjis" and op["key"]["character"] == char
        )
        supplement = row["values"]["source"]["reference_supplement"]
        assert row["values"]["strokes"] > 0 and supplement["meanings_en"]
        assert not supplement["source_card_present"] and not supplement["thai_translation_verified"]
        assert row["values"]["meaning_th"] == ""
    assert sum(op["table"] == "lesson_kanjis" for op in bundle.operations) == 420


def test_missing_core_diagrams_use_only_supplied_pairs_and_component_types(prepared):
    book, _, editorial, bundle = prepared
    for number in (2, 4):
        chapter = book.chapters[number - 1]
        view = editorial["diagrams"][str(number)]
        assert chapter.diagram.core is None and view["core"] is None
        assert view["pairs"] == [[s.model_dump() for s in pair] for pair in chapter.comparisons]
        assert view["pdf_pages"][-1] == chapter.pdf_pages.diagram
    component_pairs = []
    for op in bundle.operations:
        if op["table"] == "lesson_sections" and op["values"]["kind"] == "comparison":
            component_pairs.extend(
                p
                for p in op["values"]["blocks"][0]["typed_comparisons"]
                if any(e["kind"] == "component" for e in p["endpoints"])
            )
    assert len(component_pairs) == 4
    assert not bundle.gaps


def test_comparison_scoring_never_invents_automatic_credit(prepared):
    book, _, _, _ = prepared
    for chapter in book.chapters:
        rubric = comparison_rubric(chapter)
        assert assess_comparison("", rubric)["status"] == "unanswered"
        arbitrary = assess_comparison("Unverified answer", rubric)
        assert arbitrary["score"] is None and arbitrary["status"] == "needs_manual_review"
        for tip in rubric["source_tips"]:
            assert tip["text"] in chapter.memory_tips
            result = assess_comparison(tip["text"], rubric)
            assert result["source_quote_match"] and result["score"] is None


@pytest.mark.parametrize(
    "damage", ["edition", "expected_value", "invented_gloss", "unsupported_stem"]
)
def test_correction_layer_rejects_wrong_source_and_unsupported_changes(prepared, tmp_path, damage):
    book, references, _, _ = prepared
    policy = json.loads((ROOT / "content/editorial-corrections.json").read_text("utf-8"))
    if damage == "edition":
        policy["source_manifest_sha256"] = "0" * 64
    if damage == "expected_value":
        policy["vocabulary_corrections"][0]["expected_meaning_th"] = "wrong"
    if damage == "invented_gloss":
        policy["vocabulary_corrections"][0]["meaning_th"] = "fabricated"
    if damage == "unsupported_stem":
        policy["reading_annotations"][2]["effective_reading"] = "fabricated"
    path = tmp_path / "corrections.json"
    path.write_text(json.dumps(policy, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError):
        prepare_editorial(book, references, path)


def test_thai_evidence_has_exact_matches_and_never_auto_approves_all_translations(prepared):
    book, _, _, _ = prepared
    folder = ROOT / "private/editorial-references"
    if len(list(folder.glob("*.xlsx"))) != 4:
        pytest.skip("Official Thai snapshots unavailable")
    results = verify_thai(book, folder)
    assert len(results["sources"]) == 4
    assert len(results["vocabulary"]) == 240
    assert any(r["exact_translation_match"] for r in results["vocabulary"].values())
    assert any(r["status"] == "not_covered" for r in results["vocabulary"].values())
    assert not any(r["editorial_approved"] for r in results["vocabulary"].values())


def test_full_editorial_plan_preserves_existing_editor_changes(prepared):
    _, _, _, bundle = prepared
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def constraints(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        apply_bundle(session, bundle)
        session.commit()
        row = session.scalar(select(Vocabulary).where(Vocabulary.written_form == "裁判"))
        row.meaning_th = "EDITOR APPROVED VALUE"
        session.commit()
        second = apply_bundle(session, bundle)
        assert not second["inserted"]
        assert row.meaning_th == "EDITOR APPROVED VALUE"
        assert any("meaning_th" in c["fields"] for c in second["conflicts"])
    engine.dispose()
