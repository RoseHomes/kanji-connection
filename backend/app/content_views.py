"""Read-only presentation helpers. Never promote review state or expose quiz answers."""

from sqlalchemy import select

from .models import LessonSection


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
    sections = []
    for section in db.scalars(query.order_by(LessonSection.position)):
        blocks = []
        for original in section.blocks:
            # Structured blocks already cover the content. Duplicate raw page text can
            # contain answer keys and internal extraction notes; it is not a learner view.
            if original.get("kind") == "source_page_text":
                continue
            block = dict(original)
            if section.kind == "exercises":
                block.pop("answers", None)
                block.pop("answer_c_note", None)
                block["exercises"] = [
                    {k: v for k, v in item.items() if k != "answer"}
                    for item in block.get("exercises", [])
                ]
            blocks.append(block)
        sections.append(
            {
                "kind": section.kind,
                "blocks": blocks,
                "pdf_pages": section.provenance.get("pdf_pages", []),
            }
        )
    return sections
