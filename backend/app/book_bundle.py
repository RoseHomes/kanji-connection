"""JSON-to-existing-schema mapping. All source content stays private/needs_review."""

import hashlib
import json
from collections import defaultdict

from pydantic import BaseModel, Field

from .content_schema import Book
from .editorial import classify_audit
from .json_content import provenance


class Bundle(BaseModel):
    schema_version: int = 2
    source_sha256: str
    operations: list[dict]
    unresolved_issues: list[dict]
    gaps: list[dict] = Field(default_factory=list)
    publication_approved: bool = False
    supporting_glyphs: list[str] = Field(default_factory=list)
    editorial_layer_sha256: str | None = None
    audit_records: list[dict] = Field(default_factory=list)


def ref(table, key):
    return {"$ref": {"table": table, "key": key, "column": "id"}}


def build_bundle(book: Book, evidence: dict, editorial: dict | None = None) -> Bundle:
    editorial = editorial or {}
    operations = []
    gaps = []

    def add(table, key, **values):
        operations.append({"table": table, "key": key, "values": values})

    def vocabulary_view(word):
        record = word.model_dump()
        correction = editorial.get("vocabulary", {}).get(word.word + ":" + word.reading)
        if correction:
            record["source_meaning_th"] = word.meaning_th
            record["meaning_th"] = correction["meaning_th"]
            record["editorial_correction"] = correction
        return record

    cards = defaultdict(list)
    words = defaultdict(list)
    auxiliary = defaultdict(list)
    components = {}
    for c in book.chapters:
        for i, pair in enumerate(c.comparisons):
            for item in pair:
                if item.kanji in {"氵", "亻", "扌", "忄", "艹", "宀"}:
                    components.setdefault(item.kanji, []).append(
                        {
                            "record": item.model_dump(),
                            "source": provenance(
                                book, c.chapter, f"/comparisons/{i}", [c.pdf_pages.comparison]
                            ),
                        }
                    )
    for glyph, occurrences in sorted(components.items()):
        add(
            "components",
            {"glyph": glyph},
            label_th=occurrences[0]["record"]["meaning_th"],
            classification="component",
            source={
                "occurrences": occurrences,
                "name_verification": [
                    n for n in editorial.get("component_names", []) if n["glyph"] == glyph
                ],
            },
            status="needs_review",
        )
    for c in book.chapters:
        for i, k in enumerate(c.kanji_cards):
            cards[k.character].append(
                {
                    "record": k.model_dump(),
                    "source": provenance(book, c.chapter, f"/kanji_cards/{i}", [k.pdf_page]),
                    "evidence": evidence["cards"][f"ch{c.chapter:02}-card{i + 1:02}"],
                    "editorial": editorial.get("cards", {}).get(f"ch{c.chapter:02}-card{i + 1:02}"),
                }
            )
        for i, w in enumerate(c.vocabulary):
            words[(w.word, w.reading)].append(
                {
                    "record": w.model_dump(),
                    "source": provenance(book, c.chapter, f"/vocabulary/{i}", [w.pdf_page]),
                }
            )
    for (form, reading), occurrences in words.items():
        for char in form:
            if "\u3400" <= char <= "\u9fff" and char not in cards:
                auxiliary[char].extend(o["source"] for o in occurrences)
    for c in book.chapters:
        for i, pair in enumerate(c.comparisons):
            for item in pair:
                if item.kanji not in cards and item.kanji not in components:
                    auxiliary[item.kanji].append(
                        provenance(book, c.chapter, f"/comparisons/{i}", [c.pdf_pages.comparison])
                    )
    for char, occurrences in sorted(cards.items()):
        groups = {"on": [], "kun": [], "other": []}
        for o in occurrences:
            annotation = o["editorial"]
            reading = (
                annotation["effective_reading"] if annotation else o["record"]["reading_example"]
            )
            matches = o["evidence"]["reading_matches"]
            kind = annotation["kind"] if annotation else matches[0]["kind"] if matches else "other"
            if reading not in groups[kind]:
                groups[kind].append(reading)
        first = occurrences[0]
        add(
            "kanjis",
            {"character": char},
            meaning_th=first["record"]["meaning_th"],
            readings=groups,
            review_status="needs_review",
            access_tier="private",
            romaji="",
            strokes=(first["evidence"]["dictionary"] or {}).get("stroke_count"),
            jlpt_estimate=None,
            note_th="",
            source={
                "occurrences": occurrences,
                "selection": "first source candidate; all variants retained, not editorially resolved",
            },
        )
        for kind, readings in groups.items():
            for i, reading in enumerate(readings):
                add(
                    "kanji_readings",
                    {
                        "kanji_id": ref("kanjis", {"character": char}),
                        "kind": kind,
                        "reading": reading,
                    },
                    position=i,
                    notes="Source example reading; reference classification is not editorial approval",
                )
    for char, sources in sorted(auxiliary.items()):
        supplement = editorial.get("supporting", {}).get(char)
        groups = {"on": [], "kun": [], "other": []}
        if supplement:
            for reading in supplement["readings"]:
                if reading["text"] not in groups[reading["kind"]]:
                    groups[reading["kind"]].append(reading["text"])
        add(
            "kanjis",
            {"character": char},
            meaning_th="",
            readings=groups,
            review_status="needs_review",
            access_tier="private",
            romaji="",
            strokes=supplement["stroke_count"] if supplement else None,
            jlpt_estimate=None,
            note_th="",
            source={
                "kind": "supporting_printed_glyph",
                "standalone_fields_provided": False,
                "sources": sources,
                "reference_supplement": supplement,
                "dictionary_sources": editorial.get("dictionary_sources", []),
            },
        )
        for kind, readings in groups.items():
            for position, reading in enumerate(readings):
                add(
                    "kanji_readings",
                    {
                        "kanji_id": ref("kanjis", {"character": char}),
                        "kind": kind,
                        "reading": reading,
                    },
                    position=position,
                    notes="Pinned KANJIDIC2 supporting reference; no standalone source card or Thai translation supplied",
                )
        gaps.append(
            {
                "id": "supporting_glyph_fields:" + char,
                "kind": "supporting_glyph_fields",
                "character": char,
                "sources": sources,
                "note": "Printed in words/comparisons; no standalone card or meaning invented",
            }
        )
    for (form, reading), occurrences in sorted(words.items()):
        key = {"written_form": form, "reading": reading}
        correction = editorial.get("vocabulary", {}).get(form + ":" + reading)
        add(
            "vocabularies",
            key,
            meaning_th=correction["meaning_th"]
            if correction
            else occurrences[0]["record"]["meaning_th"],
            romaji="",
            usage_notes="",
            status="needs_review",
            access_tier="private",
            provenance={
                "occurrences": occurrences,
                "selection": "first source gloss; variants retained",
                "editorial_correction": correction,
            },
        )
        for i, char in enumerate(form):
            if char in cards or char in auxiliary:
                add(
                    "vocabulary_kanjis",
                    {"vocabulary_id": ref("vocabularies", key), "position": i},
                    kanji_id=ref("kanjis", {"character": char}),
                )
    relations = defaultdict(list)
    for c in book.chapters:
        lk = {"chapter": c.chapter}
        p = c.pdf_pages

        def card_view(index, chapter=c):
            record = chapter.kanji_cards[index].model_dump()
            annotation = editorial.get("cards", {}).get(
                f"ch{chapter.chapter:02}-card{index + 1:02}"
            )
            if annotation:
                record["editorial_reading_scope"] = annotation
            return record

        typed_pairs = []
        for pair in c.comparisons:
            endpoints = [
                {
                    "kind": "component" if side.kanji in components else "kanji",
                    "glyph": side.kanji,
                    "reading": side.reading,
                    "meaning_th": side.meaning_th,
                }
                for side in pair
            ]
            if any(
                endpoint["kind"] == "kanji"
                and endpoint["glyph"] not in cards
                and endpoint["glyph"] not in auxiliary
                for endpoint in endpoints
            ):
                raise ValueError("Broken typed comparison endpoint")
            typed_pairs.append({"relation_type": "visual_similarity", "endpoints": endpoints})
        add(
            "lessons",
            lk,
            slug=f"chapter-{c.chapter:02}",
            title_th=c.title_th,
            summary_th=c.subtitle_th,
            introduction_th="",
            anchors=[k.character for k in c.kanji_preview],
            catalog_visible=False,
            status="needs_review",
            access_tier="private",
            provenance={
                "source": provenance(book, c.chapter, "/", list(range(p.start, p.end + 1))),
                "part": c.part,
                "category": c.category,
                "source_editorial_status": c.editorial_status,
            },
        )
        for i, k in enumerate(c.kanji_cards):
            add(
                "lesson_kanjis",
                {
                    "lesson_id": ref("lessons", lk),
                    "kanji_id": ref("kanjis", {"character": k.character}),
                },
                position=i,
            )
        for i, w in enumerate(c.vocabulary):
            add(
                "lesson_vocabularies",
                {
                    "lesson_id": ref("lessons", lk),
                    "vocabulary_id": ref(
                        "vocabularies", {"written_form": w.word, "reading": w.reading}
                    ),
                },
                position=i,
            )
        payloads = [
            (
                "introduction",
                p.opener,
                {
                    "subtitle_th": c.subtitle_th,
                    "category": c.category,
                    "kanji_preview": [x.model_dump() for x in c.kanji_preview],
                },
            ),
            ("cards", p.kanji_cards[0], {"cards": [card_view(i) for i in range(7)]}),
            ("cards", p.kanji_cards[1], {"cards": [card_view(i) for i in range(7, 14)]}),
            (
                "comparison",
                p.comparison,
                {
                    "pairs": [[x.model_dump() for x in pair] for pair in c.comparisons],
                    "memory_tips": c.memory_tips,
                    "typed_comparisons": typed_pairs,
                },
            ),
            (
                "mnemonic",
                p.diagram,
                {
                    "diagram": c.diagram.model_dump(),
                    "historical_etymology_verified": False,
                    "editorial_view": editorial.get("diagrams", {}).get(str(c.chapter)),
                },
            ),
            (
                "vocabulary",
                p.vocabulary,
                {"vocabulary": [vocabulary_view(word) for word in c.vocabulary]},
            ),
            (
                "exercises",
                p.exercises,
                {
                    "exercises": [x.model_dump() for x in c.exercises],
                    "answers": [x.model_dump() for x in c.answers],
                    "exercise_c_prompt": c.exercise_c_prompt,
                    "answer_c_note": c.answer_c_note,
                },
            ),
        ]
        for i, (kind, page, payload) in enumerate(payloads):
            add(
                "lesson_sections",
                {"lesson_id": ref("lessons", lk), "position": i},
                kind=kind,
                blocks=[
                    payload,
                    {"kind": "source_page_text", "text": book.pages[page - 1].plain_text},
                ],
                status="needs_review",
                access_tier="private",
                provenance=provenance(book, c.chapter, "/", [page]),
            )
        for i, q in enumerate(c.exercises):
            answer = c.answers[i]
            add(
                "quiz_questions",
                {"lesson_id": ref("lessons", lk), "stable_key": f"q-{q.number:02}"},
                question_type=q.type,
                prompt={"text": q.prompt, "number": q.number},
                options=[],
                answer_key={
                    "kind": "explicit_source",
                    "text": answer.answer,
                    "source": provenance(book, c.chapter, f"/answers/{i}", [answer.pdf_page]),
                    "editorial_verified": False,
                },
                explanation_th="",
                status="needs_review",
                provenance=provenance(book, c.chapter, f"/exercises/{i}", [q.pdf_page]),
            )
        add(
            "quiz_questions",
            {"lesson_id": ref("lessons", lk), "stable_key": "comparison-c"},
            question_type="comparison",
            prompt={"text": c.exercise_c_prompt},
            options=[],
            answer_key={
                "kind": "reference_only",
                "text": c.answer_c_note,
                "auto_scorable": False,
                "source": provenance(book, c.chapter, "/answer_c_note", [p.answer_key]),
                "rubric": editorial.get("rubrics", {}).get(str(c.chapter)),
            },
            explanation_th="",
            status="needs_review",
            provenance=provenance(book, c.chapter, "/exercise_c_prompt", [p.exercises]),
        )
        for i, pair in enumerate(c.comparisons):
            a, b = sorted(x.kanji for x in pair)
            if a in components or b in components:
                if editorial:
                    editorial["resolutions"][f"component_comparison:{c.chapter}:{i}"] = {
                        "status": "resolved_mapping",
                        "evidence": typed_pairs[i],
                        "note": "Typed component/Kanji endpoints stored in comparison sections and validated against imported entities; no Kanji-only FK misuse.",
                    }
                gaps.append(
                    {
                        "id": f"component_comparison:{c.chapter}:{i}",
                        "kind": "component_comparison_not_kanji_relation",
                        "source": provenance(book, c.chapter, f"/comparisons/{i}", [p.comparison]),
                        "note": "Preserved in comparison section; component is not a standalone teaching Kanji and no contains relation was inferred",
                    }
                )
                continue
            relations[(a, b, "visual_similarity")].append(
                {
                    "pair": [x.model_dump() for x in pair],
                    "source": provenance(book, c.chapter, f"/comparisons/{i}", [p.comparison]),
                    "memory_tips": c.memory_tips,
                }
            )
        for i, related in enumerate(c.diagram.related):
            a, b = sorted([c.diagram.core.kanji, related.kanji])
            if a == b:
                continue
            relations[(a, b, "mnemonic")].append(
                {
                    "core": c.diagram.core.model_dump(),
                    "related": related.model_dump(),
                    "source": provenance(book, c.chapter, f"/diagram/related/{i}", [p.diagram]),
                    "historical_etymology_verified": False,
                }
            )
    for (a, b, kind), occurrences in sorted(relations.items()):
        add(
            "kanji_relations",
            {
                "source_id": ref("kanjis", {"character": a}),
                "target_id": ref("kanjis", {"character": b}),
                "relation_type": kind,
            },
            directed=False,
            explanation_th="",
            status="needs_review",
            provenance={
                "occurrences": occurrences,
                "classification": "source pedagogical connection; not historical etymology",
            },
        )
    digest = hashlib.sha256(json.dumps(book.source_files, sort_keys=True).encode()).hexdigest()
    records = classify_audit([*book.issues, *gaps], editorial)
    for correction in editorial.get("vocabulary", {}).values():
        records.append(
            {
                "id": "vocabulary_sense_error:" + correction["id"],
                "kind": "vocabulary_sense_error",
                "classification": "actual_content_error",
                "status": "resolved_correction",
                "evidence": correction,
                "note": correction["note"],
            }
        )
    open_ids = {item["id"] for item in records if item["status"] == "open"}
    return Bundle(
        source_sha256=digest,
        operations=operations,
        unresolved_issues=[
            item
            for item in records
            if item["id"] in open_ids and item["id"] not in {g["id"] for g in gaps}
        ],
        gaps=[
            item
            for item in records
            if item["id"] in open_ids and item["id"] in {g["id"] for g in gaps}
        ],
        supporting_glyphs=sorted(auxiliary),
        editorial_layer_sha256=editorial.get("layer_sha256"),
        audit_records=records,
    )
