"""Validated, edition-bound editorial overlays. Never changes the source Book."""

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .book_verify import kana
from .comparison_scoring import comparison_rubric


class ReadingAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    character: str
    source_reading: str
    effective_reading: str
    kind: Literal["on", "kun", "other"]
    scope: Literal["compound_voicing", "word_with_okurigana", "incomplete_stem"]
    context_forms: list[str]
    evidence_urls: list[str]
    note: str


class VocabularyCorrection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    word: str
    reading: str
    expected_meaning_th: str
    meaning_th: str
    evidence_urls: list[str]
    note: str


class EditorialLayer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int
    source_manifest_sha256: str
    reviewed_on: str
    reading_annotations: list[ReadingAnnotation]
    component_names: list[dict]
    expression_checks: list[dict]
    vocabulary_corrections: list[VocabularyCorrection]


def prepare_editorial(book, references, path: Path):
    data = path.read_bytes()
    layer = EditorialLayer.model_validate_json(data)
    digest = hashlib.sha256(json.dumps(book.source_files, sort_keys=True).encode()).hexdigest()
    if layer.schema_version != 1 or layer.source_manifest_sha256 != digest:
        raise ValueError("Editorial layer belongs to a different source edition")
    result = {
        "layer_sha256": hashlib.sha256(data).hexdigest(),
        "source_manifest_sha256": digest,
        "cards": {},
        "vocabulary": {},
        "component_names": layer.component_names,
        "expression_checks": layer.expression_checks,
        "supporting": {},
        "diagrams": {},
        "rubrics": {},
        "resolutions": {},
        "dictionary_sources": references.sources if references else [],
    }
    seen = set()
    for chapter in book.chapters:
        for i, card in enumerate(chapter.kanji_cards):
            for annotation in layer.reading_annotations:
                if (card.character, card.reading_example) != (
                    annotation.character,
                    annotation.source_reading,
                ):
                    continue
                if annotation.kind not in {"on", "kun", "other"} or not annotation.evidence_urls:
                    raise ValueError("Reading annotation needs classification and evidence")
                if annotation.scope == "incomplete_stem" and (
                    annotation.character,
                    annotation.effective_reading,
                    annotation.evidence_urls,
                ) != ("靖", "やすい", ["https://www.kanjipedia.jp/kanji/0003907200"]):
                    raise ValueError("Unsupported primary-reference reading supplement")
                if references and annotation.scope != "incomplete_stem":
                    readings = references.kanji[card.character]["readings"]
                    if not any(
                        kana(r["text"]) == kana(annotation.effective_reading) for r in readings
                    ):
                        raise ValueError("Annotated standalone reading failed dictionary check")
                key = f"ch{chapter.chapter:02}-card{i + 1:02}"
                result["cards"][key] = annotation.model_dump()
                seen.add(annotation.id)
                result["resolutions"][
                    f"card_reading_unconfirmed:{card.character}:{card.reading_example}"
                ] = {
                    "status": "resolved_context",
                    "evidence": annotation.model_dump(),
                    "note": "Source preserved; standalone index and source example scope are now distinct.",
                }
        for correction in layer.vocabulary_corrections:
            for word in chapter.vocabulary:
                if (word.word, word.reading) != (correction.word, correction.reading):
                    continue
                if word.meaning_th != correction.expected_meaning_th:
                    raise ValueError("Editorial correction expected source value differs")
                if correction.meaning_th not in correction.expected_meaning_th.split(" / "):
                    raise ValueError(
                        "This overlay only removes a contradicted source sense; it cannot invent a translation"
                    )
                result["vocabulary"][word.word + ":" + word.reading] = correction.model_dump()
                seen.add(correction.id)
        if chapter.diagram.core is None:
            # A pair network needs no made-up core. Nodes/edges and labels come
            # directly from the source comparisons, including component endpoints.
            pairs = [[side.model_dump() for side in pair] for pair in chapter.comparisons]
            nodes = {side.kanji: side.model_dump() for pair in chapter.comparisons for side in pair}
            result["diagrams"][str(chapter.chapter)] = {
                "view": "comparison_network",
                "core": None,
                "nodes": list(nodes.values()),
                "pairs": pairs,
                "source_json_pointer": "/diagram/comparison_pairs",
                "pdf_pages": [chapter.pdf_pages.comparison, chapter.pdf_pages.diagram],
                "historical_etymology_verified": False,
                "note": "Operational source-pair view, not a reconstruction of absent original artwork.",
            }
            result["resolutions"][f"diagram_core_not_provided:{chapter.chapter}"] = {
                "status": "resolved_mapping",
                "evidence": result["diagrams"][str(chapter.chapter)],
                "note": "Mapped every supplied pair without inventing a hub; original core stays null.",
            }
        result["rubrics"][str(chapter.chapter)] = comparison_rubric(chapter)
    if seen != {a.id for a in layer.reading_annotations} | {
        c.id for c in layer.vocabulary_corrections
    }:
        raise ValueError("Editorial layer contains unused source corrections")
    for component in layer.component_names:
        key = f"comparison_reading_unconfirmed:{component['glyph']}:{component['reading']}"
        result["resolutions"][key] = {
            "status": "resolved_reference",
            "evidence": component,
            "note": "Verified as a component name, not a standalone Kanji reading.",
        }
    for check in layer.expression_checks:
        result["resolutions"][f"vocabulary_pair_unconfirmed:{check['word']}:{check['reading']}"] = {
            "status": "resolved_reference",
            "evidence": check,
            "note": "Publisher evidence confirms expression/reading; exact JMdict membership is not required.",
        }
    taught = {k.character for chapter in book.chapters for k in chapter.kanji_cards}
    supporting = {
        glyph
        for chapter in book.chapters
        for word in chapter.vocabulary
        for glyph in word.word
        if "\u3400" <= glyph <= "\u9fff" and glyph not in taught
    }
    supporting |= {
        side.kanji
        for chapter in book.chapters
        for pair in chapter.comparisons
        for side in pair
        if side.kanji not in taught and side.kanji not in {"氵", "亻", "扌", "忄", "艹", "宀"}
    }
    for glyph in sorted(supporting):
        dictionary = references.kanji.get(glyph) if references else None
        if dictionary and dictionary["readings"] and dictionary["meanings_en"]:
            result["supporting"][glyph] = {
                **dictionary,
                "kind": "dictionary_supplement",
                "role": "supporting_not_teaching_card",
                "source_card_present": False,
                "thai_translation_verified": False,
                "thai_meaning_provided": False,
            }
            result["resolutions"]["supporting_glyph_fields:" + glyph] = {
                "status": "resolved_supporting_mapping",
                "evidence": {
                    "character": glyph,
                    "reference": "KANJIDIC2",
                    "snapshots": result["dictionary_sources"],
                },
                "note": "Reference readings, stroke count and English meanings supplied for a supporting record. Standalone teaching card and Thai gloss are still absent; those are not invented or approved.",
            }
    return result


def classify_audit(items, editorial):
    """Retain every original ID; distinguish technical disposition from approval."""
    records = []
    for original in items:
        item = {**original}
        kind = item["kind"]
        if kind in {"supporting_glyph_fields", "diagram_core_not_provided"}:
            category = "missing_source_data"
        elif kind == "component_comparison_not_kanji_relation":
            category = "database_mapping_limitation"
        else:
            category = "editorial_review_requirement"
        item["classification"] = category
        resolution = editorial.get("resolutions", {}).get(item["id"])
        if resolution:
            item.update(resolution)
        else:
            item["status"] = "open"
        records.append(item)
    return records
