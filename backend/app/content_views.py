"""Read-only presentation helpers. Never promote review state or expose quiz answers."""

from sqlalchemy import select

from .models import LessonSection


def learner_card(card):
    result = {
        k: card[k]
        for k in ["character", "meaning_th", "reading_example", "example", "memory_note"]
        if k in card
    }
    study = card.get("study")
    if study:
        result["study"] = {
            k: study[k]
            for k in ["schema_version", "role", "required", "reading", "mnemonic_note_th"]
            if k in study
        }
        result["study"]["reading"] = {
            k: v
            for k, v in study["reading"].items()
            if k in {"kind", "label_th", "form", "reading", "note_th"}
        }
        result["study"]["example"] = {
            k: v
            for k, v in (study.get("example") or {}).items()
            if k in {"word", "reading", "meaning_th", "target_scope", "role", "optional"}
        } or None
        if study.get("role") != "supplementary":
            result["study"]["scope_note_th"] = study.get("scope_note_th", "")
    return result


def learner_block(original, cards=None):
    """Positive serialization contract: audit fields never cross the learner boundary."""
    result = {
        k: original[k]
        for k in ["subtitle_th", "category", "memory_tips", "instructions_th", "text"]
        if k in original
    }
    if "cards" in original:
        result["cards"] = [learner_card(c) for c in original["cards"]]
    endpoints = {
        e["glyph"]: e for p in original.get("typed_comparisons", []) for e in p["endpoints"]
    }

    def node(value):
        if not value:
            return None
        item = {k: value[k] for k in ["kanji", "reading", "meaning_th", "label_th"] if k in value}
        endpoint = endpoints.get(value["kanji"], {})
        if endpoint.get("kind") == "component":
            item["kind"] = "component"
        study = (cards or {}).get(value["kanji"], {}).get("study", {})
        if study.get("reading"):
            item["study_reading"] = learner_card({"study": study})["study"]["reading"]
        return item

    if "pairs" in original:
        result["pairs"] = [[node(s) for s in pair] for pair in original["pairs"]]
    if "diagram" in original:
        d = original["diagram"]
        result["diagram"] = {
            "core": node(d.get("core")),
            "related": [node(s) for s in d.get("related", [])],
            "comparison_pairs": [[node(s) for s in pair] for pair in d.get("comparison_pairs", [])],
        }
    if "vocabulary" in original:
        result["vocabulary"] = [
            {k: w[k] for k in ["word", "reading", "meaning_th", "usage_notes"] if k in w}
            for w in original["vocabulary"]
        ]
    if "sentences" in original:
        result["sentences"] = [
            {k: s[k] for k in ["text", "reading", "meaning_th", "source_url"] if k in s}
            for s in original["sentences"]
        ]
    if "exercises" in original:
        result["practice_count"] = len(original["exercises"]) + 1
        result["instructions_th"] = (
            "เลือกคำตอบทีละข้อ แล้วตรวจคำอธิบายก่อนทำข้อต่อไป ทบทวนข้อที่ยังสับสนได้เมื่อจบรอบ"
        )
    return result


def development_card(row):
    return {
        "character": row.character,
        "meaning_th": row.meaning_th,
        "onyomi": row.readings.get("on", []),
        "kunyomi": row.readings.get("kun", []),
        "romaji": row.romaji,
        "strokes": row.strokes,
        "component": "",
        "note_th": row.note_th,
        "source_url": row.source.get("url", ""),
        "review_status": row.review_status,
    }


def lesson_sections(db, lesson_id, private, samples):
    query = select(LessonSection).where(LessonSection.lesson_id == lesson_id)
    if not private:
        query = query.where(
            LessonSection.access_tier == "free",
            LessonSection.status.in_(["published", "sample"] if samples else ["published"]),
        )
    rows = list(db.scalars(query.order_by(LessonSection.position)))
    cards = {c["character"]: c for s in rows for b in s.blocks for c in b.get("cards", [])}
    sections = []
    for section in rows:
        blocks = []
        for original in section.blocks:
            # Structured blocks already cover the content. Duplicate raw page text can
            # contain answer keys and internal extraction notes; it is not a learner view.
            if original.get("kind") == "source_page_text":
                continue
            blocks.append(learner_block(original, cards))
        sections.append(
            {
                "kind": section.kind,
                "blocks": blocks,
            }
        )
    return sections
