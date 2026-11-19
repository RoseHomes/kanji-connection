"""Build the final working edition offline; never writes extraction or opens SQL."""

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.book_verify import References
from app.content_revision import (
    REVISION_RELATIVE,
    WORKING_RELATIVE,
    WorkingRevision,
    build_working,
    digest,
)
from app.json_content import SOURCE_RELATIVE, load_dataset


def load(path):
    return json.loads(path.read_bytes())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def create_revision(book):
    plan = ROOT.parent / "Kanji_Connection_Final_Correction_Plan.md"
    # Read the entire specification, not a chapter subset or summary.
    specification = plan.read_text("utf-8")
    if len(re.findall(r"^## บท \d{2} —", specification, re.MULTILINE)) != 30:
        raise ValueError("Final specification must include all 30 chapters")
    folder = ROOT / "private/final-correction-plan"
    validation = load(folder / "validation.json")
    if hashlib.sha256(plan.read_bytes()).hexdigest() != validation["plan_sha256"]:
        raise ValueError("Final specification changed after its evidence validation")
    changes = []
    for item in load(folder / "proposed-changes.json"):
        replacement = item["proposed"]
        if item["source_pointer"] == "/exercise_c_prompt":
            replacement = replacement.replace("ระบุหรือวาด", "ระบุ")
        changes.append(
            {
                "chapter": item["chapter"],
                "pointer": item["source_pointer"],
                "expected": item["original"],
                "replacement": replacement,
                "reason": item["reason"],
                "references": list(
                    dict.fromkeys(re.findall(r"https?://[^)\s]+", item["references"]))
                ),
            }
        )
    changes.append(
        {
            "chapter": 21,
            "pointer": "/kanji_cards/7/reading_example",
            "expected": "やす",
            "replacement": "せい",
            "reason": "Finalized implementation: label the on-reading セイ explicitly on the optional 靖 card; retain 靖い only as a reference example.",
            "references": ["https://www.kanjipedia.jp/kanji/0003907200"],
        }
    )
    metadata = load(folder / "proposed-metadata.json")
    examples = [x for x in metadata if x.get("role")]
    scopes = [x for x in metadata if x.get("kind") == "card_reading_scope"]
    notes = [x for x in metadata if x.get("kind") == "vocabulary_usage_note"]
    sentences = {}
    for item in metadata:
        if item.get("kind") != "supplemental_sentences":
            continue
        sentences[str(item["chapter"])] = [
            {
                "text": row[1],
                "reading": row[2],
                "meaning_th": row[3],
                "source_url": row[4],
                "note_th": row[5],
            }
            for row in item["proposed"]
        ]
    rubrics = {
        str(r["chapter"]): r["proposed_rubric"]
        for r in load(folder / "proposed-rubrics.json")
    }
    for rubric in rubrics.values():
        rubric["new_model_is_editorial_proposal"] = False
        rubric["working_educational_version"] = True
        rubric["source_note"] = rubric.get("source_note", "")
    return WorkingRevision.model_validate(
        {
            "schema_version": 2,
            "revision_id": "2026-11-19-final-v2",
            "source_manifest_sha256": hashlib.sha256(
                json.dumps(book.source_files, sort_keys=True).encode()
            ).hexdigest(),
            "specification_sha256": hashlib.sha256(plan.read_bytes()).hexdigest(),
            "changes": changes,
            "examples": examples,
            "scopes": scopes,
            "vocabulary_notes": notes,
            "sentences": sentences,
            "rubrics": rubrics,
            "internal_review": [
                {
                    "kind": "thai_editorial",
                    "blocking": False,
                    "note": "Thai wording and untested mnemonic effectiveness remain internal review concerns; they do not block the private working edition.",
                }
            ],
            "finalized_decisions": {
                "禾": "component_primary_grain_meanings_retained",
                "訊": "supplementary_no_rare_spelling_memorization",
                "金閣寺": "optional_place_name_example",
                "靖": "supplementary_no_mandatory_靖い",
                "diagrams_2_4": "supported_comparison_network_no_invented_origins",
                "sentences_27_29": "verified_phrases_and_sentences",
            },
        }
    )


def main():
    book = load_dataset(ROOT / SOURCE_RELATIVE)
    before = dict(book.source_files)
    revision_path = ROOT / REVISION_RELATIVE
    if revision_path.exists():
        revision = WorkingRevision.model_validate_json(revision_path.read_bytes())
    else:
        revision = create_revision(book)
        save(revision_path, revision.model_dump())
    references = References(ROOT / "private/dictionaries")
    effective, evidence, editorial, bundle = build_working(
        book,
        references,
        ROOT / "content/editorial-corrections.json",
        revision,
    )
    output = ROOT / WORKING_RELATIVE
    save(output / "effective-book.json", effective.model_dump())
    save(output / "verification.json", evidence)
    save(output / "editorial.json", editorial)
    save(output / "working-bundle.json", bundle.model_dump())
    manifest = {
        "revision_id": revision.revision_id,
        "revision_sha256": digest(revision.model_dump()),
        "source_manifest_sha256": revision.source_manifest_sha256,
        "specification_sha256": revision.specification_sha256,
        "bundle_sha256": digest(bundle.model_dump()),
        "chapters": 30,
        "card_occurrences": 420,
        "mnemonics_replaced": 266,
        "examples_reviewed": 166,
        "comparison_rubrics": 30,
        "sentence_chapters": [27, 29],
        "publication_approved": False,
        "source_files": before,
    }
    save(output / "manifest.json", manifest)
    if load_dataset(ROOT / SOURCE_RELATIVE).source_files != before:
        raise ValueError("Extraction changed while building")
    print(json.dumps({k: v for k, v in manifest.items() if k != "source_files"}))


if __name__ == "__main__":
    main()
