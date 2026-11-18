"""Load the private structured source read-only; never opens PDF files or databases."""

import hashlib
import json
from pathlib import Path

from .content_schema import Book, Chapter, SourcePage

SOURCE_RELATIVE = Path("private/kanji-connection-extracted")


def load_dataset(folder: Path) -> Book:
    paths = sorted((folder / "chapters").glob("*.json"))
    if [p.name for p in paths] != [f"chapter_{i:02}.json" for i in range(1, 31)]:
        raise ValueError("Expected exactly chapter_01.json through chapter_30.json")
    chapters = [Chapter.model_validate_json(p.read_bytes()) for p in paths]
    aggregate = json.loads((folder / "kanji_connection_all.json").read_text("utf-8"))
    if aggregate["chapter_records"] != [c.model_dump() for c in chapters]:
        raise ValueError("Per-chapter JSON differs from aggregate source")
    if aggregate["page_count"] != 243 or aggregate["chapter_count"] != 30:
        raise ValueError("Aggregate page/chapter count mismatch")
    pages = [
        SourcePage.model_validate(p)
        for p in json.loads((folder / "all_pages_source_text.json").read_text("utf-8"))
    ]
    files = {
        str(p.relative_to(folder)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(folder.rglob("*"))
        if p.is_file()
    }
    book = Book(
        chapters=chapters,
        pages=pages,
        source_files=files,
        source_metadata={k: v for k, v in aggregate.items() if k != "chapter_records"},
    )
    report = json.loads((folder / "EXTRACTION_REPORT.json").read_text("utf-8"))
    actual = {
        "pages": len(pages),
        "chapters": len(chapters),
        "kanji_card_occurrences": sum(len(c.kanji_cards) for c in chapters),
        "unique_kanji": len({x.character for c in chapters for x in c.kanji_cards}),
        "vocabulary_rows": sum(len(c.vocabulary) for c in chapters),
        "exercise_rows": sum(len(c.exercises) for c in chapters),
        "exercise_answers_present": sum(bool(q.answer) for c in chapters for q in c.exercises),
        "comparison_pairs": sum(len(c.comparisons) for c in chapters),
        "memory_tips": sum(len(c.memory_tips) for c in chapters),
        "chapters_with_complete_answer_keys": [c.chapter for c in chapters],
    }
    if report != actual:
        raise ValueError("Extraction report does not reconcile to parsed records")
    return book


def provenance(book: Book, chapter: int, pointer: str, pages: list[int]):
    path = f"chapters/chapter_{chapter:02}.json"
    return {
        "source_file": path,
        "source_sha256": book.source_files[path],
        "json_pointer": pointer,
        "chapter": chapter,
        "pdf_pages": pages,
        "source_pdf": book.source_metadata["source_pdf"],
    }
