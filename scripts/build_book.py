"""JSON -> strict Pydantic -> private insert plan. No .env or database access."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.book_bundle import build_bundle
from app.book_verify import References, verify
from app.content_schema import Book
from app.editorial import prepare_editorial
from app.json_content import SOURCE_RELATIVE, load_dataset
from app.thai_references import verify_thai


def main():
    book = load_dataset(ROOT / SOURCE_RELATIVE)
    folder = ROOT / "private/dictionaries"
    references = (
        References(folder)
        if all(
            (folder / name).exists() and (folder / (name + ".source.json")).exists()
            for name in ["kanjidic2.xml.gz", "JMdict_e.gz"]
        )
        else None
    )
    evidence = verify(book, references)
    editorial = prepare_editorial(
        book, references, ROOT / "content/editorial-corrections.json"
    )
    thai = verify_thai(book, ROOT / "private/editorial-references")
    evidence["thai_reference_checks"] = thai
    bundle = build_bundle(book, evidence, editorial)
    output = ROOT / "private/json-content"
    output.mkdir(parents=True, exist_ok=True)
    (output / "book.json").write_text(book.model_dump_json(indent=2), encoding="utf-8")
    (output / "verification.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "import-bundle.json").write_text(
        bundle.model_dump_json(indent=2), encoding="utf-8"
    )
    (output / "editorial.json").write_text(
        json.dumps(editorial, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "audit-dispositions.json").write_text(
        json.dumps(bundle.audit_records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    baseline_path = ROOT / "private/editorial/initial-audit.json"
    if baseline_path.exists():
        baseline_ids = {
            item["id"] for item in json.loads(baseline_path.read_text("utf-8"))
        }
        if not baseline_ids.issubset({item["id"] for item in bundle.audit_records}):
            raise ValueError(
                "An original audit entry was lost during editorial processing"
            )
    (ROOT / "content/book.schema.json").write_text(
        json.dumps(Book.model_json_schema(), indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "chapters": len(book.chapters),
                "kanji": len(
                    {x.character for c in book.chapters for x in c.kanji_cards}
                ),
                "vocabulary": len(
                    {(x.word, x.reading) for c in book.chapters for x in c.vocabulary}
                ),
                "numbered_exercises": sum(len(c.exercises) for c in book.chapters),
                "numbered_answers": sum(len(c.answers) for c in book.chapters),
                "source_issues": len(bundle.unresolved_issues),
                "schema_gaps": len(bundle.gaps),
                "operations": len(bundle.operations),
                "database_connections": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
