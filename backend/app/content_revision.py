"""Edition-bound working revisions. Original extraction and approval stay untouched."""

import copy
import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .book_bundle import build_bundle, ref
from .book_verify import kana, parse_example, verify
from .content_schema import Book, Chapter
from .editorial import prepare_editorial

REVISION_RELATIVE = Path("private/editorial-revisions/2026-11-19-final-v2.json")
WORKING_RELATIVE = Path("private/editorial-working")


class Change(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chapter: int = Field(ge=1, le=30)
    pointer: str
    expected: str
    replacement: str
    reason: str
    references: list[str]


class WorkingRevision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[2]
    revision_id: str
    source_manifest_sha256: str
    specification_sha256: str
    changes: list[Change]
    examples: list[dict]
    scopes: list[dict]
    vocabulary_notes: list[dict]
    sentences: dict[str, list[dict]]
    rubrics: dict[str, dict]
    internal_review: list[dict]
    finalized_decisions: dict[str, str]


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def pointer_get(value, pointer):
    for part in pointer.strip("/").split("/"):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def pointer_set(value, pointer, replacement):
    parts = pointer.strip("/").split("/")
    parent = value
    for part in parts[:-1]:
        parent = parent[int(part)] if isinstance(parent, list) else parent[part]
    parent[int(parts[-1]) if isinstance(parent, list) else parts[-1]] = replacement


def apply_revision(book: Book, revision: WorkingRevision) -> Book:
    manifest = hashlib.sha256(json.dumps(book.source_files, sort_keys=True).encode()).hexdigest()
    if manifest != revision.source_manifest_sha256:
        raise ValueError("Working revision belongs to another extraction edition")
    chapters = [c.model_dump() for c in book.chapters]
    seen = set()
    for change in revision.changes:
        key = (change.chapter, change.pointer)
        if key in seen:
            raise ValueError("Duplicate editorial source pointer")
        seen.add(key)
        if not change.references or not change.reason:
            raise ValueError("Editorial changes need evidence and rationale")
        if change.pointer.split("/")[1] not in {
            "kanji_cards",
            "kanji_preview",
            "vocabulary",
            "memory_tips",
            "answers",
            "comparisons",
            "diagram",
            "answer_c_note",
            "exercise_c_prompt",
        }:
            raise ValueError("Working revision cannot alter source identity or status")
        chapter = chapters[change.chapter - 1]
        if pointer_get(chapter, change.pointer) != change.expected:
            raise ValueError(f"Editorial expected-original mismatch: chapter {change.chapter}")
        pointer_set(chapter, change.pointer, change.replacement)
        if change.pointer.startswith("/answers/"):
            number = int(change.pointer.split("/")[2])
            chapter["exercises"][number]["answer"] = change.replacement
    return book.model_copy(update={"chapters": [Chapter.model_validate(c) for c in chapters]})


def reading_display(card, references):
    """A full kun form is printed with okurigana, never as ruby on a lone glyph."""
    g, reading = card.character, card.reading_example
    if g == "禾":
        return {
            "kind": "component",
            "label_th": "ชื่อส่วนประกอบ",
            "form": g,
            "reading": "のぎへん",
            "note_th": "เกี่ยวกับธัญพืช; 禾 ยังมีนัยหนวดปลายรวง. のぎ เป็นคำอ่านของอักษร ส่วน のぎへん เป็นชื่อส่วนประกอบ",
        }
    if g == "好" and reading == "すき":
        return {
            "kind": "word",
            "label_th": "คำอ่านทั้งคำ",
            "form": "好き",
            "reading": "すき",
            "note_th": "好き เป็นคำที่มี き กำกับท้าย ไม่ใช่เสียงของ 好 เดี่ยวทุกกรณี",
        }
    if g == "口" and reading == "ぐち":
        return {
            "kind": "character",
            "label_th": "คำอ่านเมื่อใช้เป็นคำเดี่ยว",
            "form": g,
            "reading": "くち",
            "note_th": "ใน 入口・出口 ส่วน 口 อ่าน ぐち; อ่านคำประสมทั้งคำตามตัวอย่าง",
        }
    dictionary = references.kanji.get(g, {}) if references else {}
    match = next(
        (r for r in dictionary.get("readings", []) if kana(r["text"]) == kana(reading)), None
    )
    if match and match["kind"] == "on":
        return {
            "kind": "character",
            "label_th": "คำอ่านคันจิ · 音読み",
            "form": g,
            "reading": match["text"],
            "note_th": "เป็นเสียงตัวอย่างหนึ่งแบบ; คำศัพท์อาจใช้เสียงอื่น",
        }
    if match and "." in match["text"]:
        suffix = match["text"].split(".", 1)[1]
        return {
            "kind": "word",
            "label_th": "คำอ่านคำตัวอย่าง · 訓読み",
            "form": g + suffix,
            "reading": reading,
            "note_th": "อ่านรวมอักษรคานะที่ตามท้ายคันจิ",
        }
    return {
        "kind": "character",
        "label_th": "คำอ่านตัวอย่าง",
        "form": g,
        "reading": reading,
        "note_th": "อ่านคำศัพท์ทั้งคำตามตัวอย่าง ไม่บังคับทุกคำให้ใช้เสียงนี้",
    }


def build_working(book, references, baseline_path: Path, revision: WorkingRevision):
    effective = apply_revision(book, revision)
    editorial = prepare_editorial(book, references, baseline_path)
    # 靖 is optional. Its indexed on-reading is explicit, while the attested rare
    # kun reading remains a marked reference and is not assigned as a core word.
    editorial["cards"]["ch21-card08"].update(
        effective_reading="せい",
        kind="on",
        scope="supplementary_character",
        context_forms=["靖い"],
        note="音読み セイ; 靖い（やすい）は参考用。必須語彙にはしない。",
    )
    editorial["layer_sha256"] = digest(revision.model_dump())
    editorial["working_revision"] = revision.revision_id
    editorial["rubrics"] = copy.deepcopy(revision.rubrics)
    for c in effective.chapters:
        if c.diagram.core is None:
            editorial["diagrams"][str(c.chapter)]["pairs"] = [
                [side.model_dump() for side in pair] for pair in c.comparisons
            ]
    evidence = verify(effective, references)
    bundle = build_bundle(effective, evidence, editorial)
    examples = {(x["chapter"], x["source_pointer"].rsplit("/", 1)[0]): x for x in revision.examples}
    scopes = {(x["chapter"], x["source_pointer"]): x for x in revision.scopes}
    word_meanings = {
        (w.word, w.reading): w.meaning_th for c in effective.chapters for w in c.vocabulary
    }
    notes = {
        x["word"] + ":" + x["reading"]: x["proposed_usage_notes"] for x in revision.vocabulary_notes
    }
    studies = {}
    for c in effective.chapters:
        for i, card in enumerate(c.kanji_cards):
            p = f"/kanji_cards/{i}"
            candidate = examples.get((c.chapter, p))
            pair = parse_example(card.example)
            example = None
            if candidate:
                role = candidate["role"]
                example = {
                    "word": candidate["word"],
                    "reading": candidate["reading"],
                    "meaning_th": candidate["meaning_th"],
                    "target_scope": candidate["target_scope"],
                    "role": role,
                    "optional": role not in {"core", "core_phrase", "component_demo"},
                    "references": candidate["references"],
                }
            elif pair:
                example = {
                    "word": pair[0],
                    "reading": pair[1],
                    "meaning_th": word_meanings.get(pair),
                    "role": "core",
                    "optional": False,
                    "target_scope": "คำอ่านของคำตัวอย่างทั้งคำ",
                    "references": [],
                }
            role = (
                "component"
                if card.character == "禾"
                else "supplementary"
                if card.character in {"訊", "靖"}
                else "core"
            )
            studies[(c.chapter, i)] = {
                "schema_version": 2,
                "role": role,
                "required": role != "supplementary",
                "reading": reading_display(card, references),
                "example": example,
                "scope_note_th": scopes.get((c.chapter, p), {}).get("proposed_scope_label", ""),
                "mnemonic_note_th": "ภาพช่วยจำจากรูปและความสัมพันธ์ ไม่ใช่คำอธิบายประวัติอักษร",
                "revision_id": revision.revision_id,
            }
    for op in bundle.operations:
        table, values = op["table"], op["values"]
        if table == "kanjis":
            for occurrence in values["source"].get("occurrences", []):
                n = occurrence["source"]["chapter"]
                p = occurrence["source"]["json_pointer"]
                occurrence["original_record"] = pointer_get(book.chapters[n - 1].model_dump(), p)
                occurrence["study"] = studies[(n, int(p.split("/")[-1]))]
            values["source"]["working_revision"] = revision.revision_id
            if op["key"]["character"] == "靖":
                values["readings"] = {"on": ["せい"], "kun": ["やすい"], "other": []}
                values["note_th"] = (
                    "ตัวอักษรเสริม · 音読み セイ; 靖い（やすい）เป็นรูปสะกดอ้างอิง ไม่ใช่ศัพท์บังคับ"
                )
        elif table == "vocabularies":
            values["usage_notes"] = notes.get(
                op["key"]["written_form"] + ":" + op["key"]["reading"], ""
            )
            values["provenance"]["working_revision"] = revision.revision_id
            for occurrence in values["provenance"]["occurrences"]:
                n = occurrence["source"]["chapter"]
                occurrence["original_record"] = pointer_get(
                    book.chapters[n - 1].model_dump(), occurrence["source"]["json_pointer"]
                )
        elif table == "lesson_sections":
            n = op["key"]["lesson_id"]["$ref"]["key"]["chapter"]
            position, block = op["key"]["position"], values["blocks"][0]
            values["provenance"]["working_revision"] = revision.revision_id
            if position in {1, 2}:
                for j, card in enumerate(block["cards"]):
                    i = (position - 1) * 7 + j
                    card["study"] = studies[(n, i)]
            elif position == 5:
                for w in block["vocabulary"]:
                    w["usage_notes"] = notes.get(w["word"] + ":" + w["reading"], "")
                block["sentences"] = revision.sentences.get(str(n), [])
            elif position == 6:
                block["comparison_rubric"] = revision.rubrics[str(n)]
                if n == 30:
                    block["instructions_th"] = (
                        "ข้อ 1–7: ความหมายตามบริบท (7 คะแนน) · ข้อ 8–14: อ่านคำศัพท์ทั้งคำ (7 คะแนน) · ข้อ C: แยกรูปอักษร (ผู้สอนตรวจ 1 คะแนน). รวม 15 คะแนน แยกผลการอ่านกับการสังเกตรูป."
                    )
        elif table == "quiz_questions":
            n = op["key"]["lesson_id"]["$ref"]["key"]["chapter"]
            values["provenance"]["working_revision"] = revision.revision_id
            if op["key"]["stable_key"] == "comparison-c":
                values["answer_key"]["rubric"] = revision.rubrics[str(n)]
                values["explanation_th"] = revision.rubrics[str(n)]["model_response_th"]
            else:
                i = int(op["key"]["stable_key"].split("-")[1]) - 1
                values["answer_key"]["original_text"] = book.chapters[n - 1].answers[i].answer
                if values["answer_key"]["text"] != values["answer_key"]["original_text"]:
                    values["explanation_th"] = "เฉลยฉบับแก้ไขตามบริบท: " + values["answer_key"]["text"]
        elif table == "lessons":
            values["provenance"]["working_revision"] = revision.revision_id
        elif table == "kanji_relations":
            values["provenance"]["working_revision"] = revision.revision_id
            for occurrence in values["provenance"]["occurrences"]:
                n = occurrence["source"]["chapter"]
                occurrence["original_record"] = pointer_get(
                    book.chapters[n - 1].model_dump(), occurrence["source"]["json_pointer"]
                )
    # Keep the existing attested kun reference alongside the newly explicit on
    # reading. No unrelated index rows are removed or reclassified.
    bundle.operations.append(
        {
            "table": "kanji_readings",
            "key": {
                "kanji_id": ref("kanjis", {"character": "靖"}),
                "kind": "kun",
                "reading": "やすい",
            },
            "values": {"position": 0, "notes": "คำอ่านอ้างอิงของ 靖い · รูปเขียนเสริม ไม่ใช่ศัพท์บังคับ"},
        }
    )
    # Some original annotations already provided this row; reject duplicates.
    identities = [(o["table"], digest(o["key"])) for o in bundle.operations]
    if len(identities) != len(set(identities)):
        raise ValueError("Duplicate working bundle natural key")
    return effective, evidence, editorial, bundle
