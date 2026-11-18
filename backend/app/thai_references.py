"""Read pinned Japan Foundation XLSX references using the standard library only."""

import hashlib
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def shared_string(item):
    # Phonetic runs (rPh) are ruby metadata, not part of the cell's visible text.
    return "".join(
        child.text or "" if child.tag.endswith("}t") else "".join(child.itertext())
        for child in item
        if child.tag.endswith("}t") or child.tag.endswith("}r")
    )


def worksheet_rows(path):
    with zipfile.ZipFile(path) as archive:
        strings = [shared_string(x) for x in ET.fromstring(archive.read("xl/sharedStrings.xml"))]
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        for row in sheet.findall("m:sheetData/m:row", NS):
            values = {}
            for cell in row.findall("m:c", NS):
                value = cell.findtext("m:v", default="", namespaces=NS)
                if cell.get("t") == "s":
                    value = strings[int(value)]
                elif cell.get("t") == "inlineStr":
                    value = "".join(t.text or "" for t in cell.findall("m:is/m:t", NS))
                values[re.sub(r"\d", "", cell.get("r"))] = value
            yield int(row.get("r")), values


def normalized_thai(text):
    # Only canonical equivalence and whitespace; never substring/synonym approval.
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", text))


def verify_thai(book, folder):
    entries = defaultdict(list)
    sources = []
    for path in sorted(folder.glob("*.xlsx")):
        metadata = json.loads(path.with_suffix(".source.json").read_text("utf-8"))
        if hashlib.sha256(path.read_bytes()).hexdigest() != metadata["sha256"]:
            raise ValueError("Thai reference snapshot digest mismatch")
        sources.append(
            {
                **metadata,
                "attribution": "The Japan Foundation",
                "rights": "All rights reserved; private verification only",
            }
        )
        columns = None
        for number, row in worksheet_rows(path):
            if "IndexNo." in row.values():
                kana_col = next((k for k, v in row.items() if "かな" in v), None)
                kanji_col = next((k for k, v in row.items() if "漢字" in v), None)
                thai_col = next((k for k, v in row.items() if "タイ語" in v), None)
                if not all((kana_col, kanji_col, thai_col)):
                    raise ValueError("Unsupported Thai reference header")
                columns = (kana_col, kanji_col, thai_col)
                continue
            if not columns:
                continue
            reading, written, thai = (row.get(k, "").strip() for k in columns)
            # Outer parentheses mean this textbook writes the form in kana.
            written = written.strip("（）()")
            if not written or not reading or not thai:
                continue
            entries[(written, reading)].append(
                {
                    "meaning_th": thai,
                    "file": path.name,
                    "sheet": 1,
                    "row": number,
                    "source": metadata,
                }
            )
    results = {}
    for chapter in book.chapters:
        for i, word in enumerate(chapter.vocabulary):
            hits = entries.get((word.word, word.reading), [])
            exact = any(
                normalized_thai(word.meaning_th) == normalized_thai(h["meaning_th"]) for h in hits
            )
            results[f"ch{chapter.chapter:02}-word{i + 1:02}"] = {
                "word": word.word,
                "reading": word.reading,
                "source_meaning_th": word.meaning_th,
                "references": hits,
                "exact_translation_match": exact,
                "status": "reference_exact_match"
                if exact
                else "sense_review_required"
                if hits
                else "not_covered",
                "editorial_approved": False,
            }
    cards = {}
    for chapter in book.chapters:
        for i, card in enumerate(chapter.kanji_cards):
            hits = entries.get((card.character, card.reading_example), [])
            cards[f"ch{chapter.chapter:02}-card{i + 1:02}"] = {
                "references": hits,
                "exact_translation_match": any(
                    normalized_thai(card.meaning_th) == normalized_thai(h["meaning_th"])
                    for h in hits
                ),
                "editorial_approved": False,
            }
    return {"sources": sources, "vocabulary": results, "cards": cards}
