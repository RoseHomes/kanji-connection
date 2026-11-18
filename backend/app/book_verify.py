"""Deterministic reference checks; never equates a dictionary hit with Thai approval."""

import gzip
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from .content_schema import Book
from .json_content import provenance


def kana(text):
    return (
        "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in text)
        .replace(".", "")
        .strip("-")
    )


def parse_example(text):
    """Recognize only an explicit Japanese form + kana reading in source text."""
    parts = text.rsplit(" ", 1)
    if (
        len(parts) == 2
        and re.fullmatch(r"[\u3041-\u3096\u30a1-\u30fa\u30fc]+", parts[1])
        and re.search(r"[\u4e00-\u9fff\u3041-\u3096\u30a1-\u30fa]", parts[0])
    ):
        return tuple(parts)
    return None


class References:
    def __init__(self, folder: Path):
        self.kanji = {}
        self.words = defaultdict(list)
        self.sources = []
        for name in ["kanjidic2.xml.gz", "JMdict_e.gz"]:
            path = folder / name
            metadata = json.loads((folder / (name + ".source.json")).read_text("utf-8"))
            if hashlib.sha256(path.read_bytes()).hexdigest() != metadata["sha256"]:
                raise ValueError("Reference digest mismatch")
            self.sources.append(
                {
                    **metadata,
                    "license": "CC-BY-SA-4.0",
                    "attribution": "James William Breen / Electronic Dictionary Research and Development Group",
                    "license_url": "https://www.edrdg.org/edrdg/licence.html",
                }
            )
        with gzip.open(folder / "kanjidic2.xml.gz") as stream:
            root = ET.parse(stream).getroot()
        for entry in root.findall("character"):
            self.kanji[entry.findtext("literal")] = {
                "readings": [
                    {"kind": "on" if r.get("r_type") == "ja_on" else "kun", "text": r.text}
                    for r in entry.findall("reading_meaning/rmgroup/reading")
                    if r.get("r_type") in {"ja_on", "ja_kun"}
                ],
                "meanings_en": [
                    m.text
                    for m in entry.findall("reading_meaning/rmgroup/meaning")
                    if m.get("m_lang") is None
                ],
                "stroke_count": int(entry.findtext("misc/stroke_count")),
            }
        with gzip.open(folder / "JMdict_e.gz") as stream:
            for event, entry in ET.iterparse(stream, events=("end",)):
                if entry.tag != "entry":
                    continue
                forms = [e.text for e in entry.findall("k_ele/keb")]
                for reading in entry.findall("r_ele"):
                    restrict = [e.text for e in reading.findall("re_restr")]
                    for form in forms or [reading.findtext("reb")]:
                        if restrict and form not in restrict:
                            continue
                        senses = [
                            sense
                            for sense in entry.findall("sense")
                            if (
                                not sense.findall("stagk")
                                or form in [s.text for s in sense.findall("stagk")]
                            )
                            and (
                                not sense.findall("stagr")
                                or reading.findtext("reb")
                                in [s.text for s in sense.findall("stagr")]
                            )
                        ]
                        self.words[(form, reading.findtext("reb"))].append(
                            {
                                "entry_id": entry.findtext("ent_seq"),
                                "meanings_en": [
                                    g.text for sense in senses for g in sense.findall("gloss")
                                ],
                                "registers": sorted(
                                    {m.text for sense in senses for m in sense.findall("misc")}
                                ),
                                "sense_notes": [
                                    n.text for sense in senses for n in sense.findall("s_inf")
                                ],
                            }
                        )
                entry.clear()


def verify(book: Book, references: References | None):
    """Structural loading is mandatory; reference/semantic uncertainty stays explicit."""
    issues = {}

    def issue(kind, key, source, **details):
        identity = f"{kind}:{key}"
        item = issues.setdefault(
            identity, dict(id=identity, kind=kind, status="needs_review", sources=[], **details)
        )
        if source not in item["sources"]:
            item["sources"].append(source)

    evidence = {
        "cards": {},
        "vocabulary": {},
        "answers": {},
        "comparisons": {},
        "examples": {},
        "dictionary_sources": references.sources if references else [],
        "editorial_approved": False,
    }
    for c in book.chapters:

        def src(pointer, page, chapter=c.chapter):
            return provenance(book, chapter, pointer, [page])

        if c.diagram.core is None:
            issue(
                "diagram_core_not_provided",
                str(c.chapter),
                src("/diagram", c.pdf_pages.diagram),
                note="Source JSON provides comparison pairs only; no core/related graph invented",
            )
        for i, card in enumerate(c.kanji_cards):
            key = f"ch{c.chapter:02}-card{i + 1:02}"
            dictionary = references.kanji.get(card.character) if references else None
            matches = (
                [r for r in dictionary["readings"] if kana(r["text"]) == kana(card.reading_example)]
                if dictionary
                else []
            )
            if (card.character, card.reading_example) == ("禾", "のぎ"):
                matches = matches or [
                    {
                        "kind": "kun",
                        "text": "のぎ",
                        "source": "https://www.kanjipedia.jp/kanji/0000635400",
                        "note": "Supplementary primary entry checked in the earlier source audit; omitted from KANJIDIC selected readings",
                    }
                ]
            evidence["cards"][key] = {
                "reading_verified": bool(matches),
                "reading_matches": matches,
                "dictionary": dictionary,
                "thai_translation_verified": False,
            }
            if not matches:
                issue(
                    "card_reading_unconfirmed",
                    card.character + ":" + card.reading_example,
                    src(f"/kanji_cards/{i}", card.pdf_page),
                    character=card.character,
                    reading=card.reading_example,
                )
            # Only parse an actual Japanese example with an explicit space-separated reading.
            parts = parse_example(card.example)
            if parts:
                hits = references.words.get(tuple(parts), []) if references else []
                evidence["examples"][key] = {
                    "written_form": parts[0],
                    "reading": parts[1],
                    "pair_verified": bool(hits),
                    "references": hits,
                }
                if not hits:
                    issue(
                        "example_pair_unconfirmed",
                        card.example,
                        src(f"/kanji_cards/{i}/example", card.pdf_page),
                        example=card.example,
                    )
        for i, w in enumerate(c.vocabulary):
            key = f"ch{c.chapter:02}-word{i + 1:02}"
            hits = references.words.get((w.word, w.reading), []) if references else []
            evidence["vocabulary"][key] = {
                "pair_verified": bool(hits),
                "references": hits,
                "thai_translation_verified": False,
            }
            if not hits:
                issue(
                    "vocabulary_pair_unconfirmed",
                    w.word + ":" + w.reading,
                    src(f"/vocabulary/{i}", w.pdf_page),
                    word=w.word,
                    reading=w.reading,
                )
        for i, q in enumerate(c.exercises):
            key = f"ch{c.chapter:02}-q{q.number:02}"
            if q.type == "vocabulary_reading":
                hits = references.words.get((q.prompt, q.answer), []) if references else []
                evidence["answers"][key] = {"pair_verified": bool(hits), "references": hits}
                if not hits:
                    issue(
                        "answer_reading_unconfirmed",
                        q.prompt + ":" + q.answer,
                        src(f"/exercises/{i}", q.pdf_page),
                    )
            else:
                matches = [card.meaning_th for card in c.kanji_cards if card.character == q.prompt]
                evidence["answers"][key] = {
                    "matches_source_card": q.answer in matches,
                    "thai_translation_verified": False,
                }
                if q.answer not in matches:
                    issue(
                        "answer_meaning_differs_from_card",
                        key,
                        src(f"/exercises/{i}", q.pdf_page),
                        answer=q.answer,
                        source_meanings=matches,
                    )
        for i, pair in enumerate(c.comparisons):
            for side in pair:
                dictionary = references.kanji.get(side.kanji) if references else None
                matches = (
                    [r for r in dictionary["readings"] if kana(r["text"]) == kana(side.reading)]
                    if dictionary
                    else []
                )
                evidence["comparisons"][f"ch{c.chapter:02}-pair{i + 1}-{side.kanji}"] = {
                    "reading_verified": bool(matches),
                    "reading": side.reading,
                }
                if not matches:
                    issue(
                        "comparison_reading_unconfirmed",
                        side.kanji + ":" + side.reading,
                        src(f"/comparisons/{i}", c.pdf_pages.comparison),
                        character=side.kanji,
                        reading=side.reading,
                    )
        for i, q in enumerate(c.exercises):
            if q.type == "vocabulary_reading" and not any(
                w.word == q.prompt and w.reading == q.answer for w in c.vocabulary
            ):
                issue(
                    "exercise_word_outside_lesson_vocabulary",
                    f"{c.chapter}:{q.number}",
                    src(f"/exercises/{i}", q.pdf_page),
                )
            if q.type == "kanji_meaning" and not any(
                k.character == q.prompt for k in c.kanji_cards
            ):
                issue(
                    "exercise_kanji_outside_lesson",
                    f"{c.chapter}:{q.number}",
                    src(f"/exercises/{i}", q.pdf_page),
                )
    global_source = {"source_files": book.source_files, "pdf_pages": list(range(1, 244))}
    for kind, note in [
        (
            "thai_semantic_review_required",
            "All Thai meanings/translations require editorial approval; dictionary membership does not establish semantic equivalence",
        ),
        (
            "mnemonic_claim_review_required",
            "90 memory tips and 30 diagram records retain source wording; composition/phonetic claims are not verified historical etymologies",
        ),
        (
            "comparison_rubric_required",
            "30 C answer notes refer back to comparisons and are not explicit scorable keys",
        ),
        (
            "diagram_visual_review_required",
            "JSON retains relationship data, not PDF artwork; no raster/SVG visual assets imported or approved",
        ),
    ]:
        issue(kind, "book", global_source, note=note)
    if references is None:
        issue(
            "reference_verification_unavailable",
            "book",
            global_source,
            note="Dictionary snapshots unavailable; structural checks only",
        )
    book.issues = sorted(issues.values(), key=lambda i: i["id"])
    return evidence
