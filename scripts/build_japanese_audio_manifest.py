"""Inventory the hash-verified published edition with no database or network writes."""

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from generate_voicevox_audio import OUTPUT, ROOT, VOICE, audio_id, hiragana, read_json

sys.path.insert(0, str(ROOT / "backend"))

from app.book_verify import References, parse_example
from app.content_revision import digest
from app.content_views import learner_block
from app.editorial_sync import snapshot
from app.learning_presentation import objective_questions
from sqlalchemy import create_engine

PRIVATE = ROOT / "private"
RECEIPT = PRIVATE / "publication-release/receipt.json"
KANA = re.compile(r"[ぁ-ゖー、。？！!?・\s]+")
JAPANESE_TOKEN = re.compile(r"[々ぁ-ゖァ-ヺー㐀-鿿]+")
KANJI = re.compile(r"[々㐀-鿿]")
PROSE_VARIANTS = {
    "入口": {"いりくち"},
    "十分": {"じっぷん", "じゅうぶん"},
    "日本": {"にっぽん"},
    "明日": {"あす", "みょうにち"},
}
SAMPLE = [
    ("kanji_on", "日", "にち"),
    ("kanji_on", "学", "がく"),
    ("kanji_on", "一", "いち"),
    ("kanji_on", "靖", "せい"),
    ("kanji_kun", "人", "ひと"),
    ("kanji_kun", "口", "くち"),
    ("kanji_kun", "湖", "みずうみ"),
    ("vocabulary", "入口", "いりぐち"),
    ("vocabulary", "好き", "すき"),
    ("vocabulary", "今日", "きょう"),
    ("vocabulary", "十分", "じゅっぷん"),
    ("vocabulary", "学校", "がっこう"),
    ("vocabulary", "自動ドア", "じどうどあ"),
    ("vocabulary", "明日", "あした"),
    ("phrase", "扉を開ける", "とびらをあける"),
    ("sentence", "お会計、お願いします。", "おかいけい、おねがいします。"),
    ("sentence", "水を飲みます。", "みずをのみます。"),
    ("sentence", "学校に行きます。", "がっこうにいきます。"),
    ("sentence", "友達と遊びます。", "ともだちとあそびます。"),
    ("sentence", "8時に家を出ます。", "はちじにいえをでます。"),
]


def load_publication(receipt_path, snapshot_path):
    receipt = read_json(receipt_path)
    if not receipt["committed"]:
        raise ValueError("Expected a committed publication receipt")
    if not snapshot_path:
        prefix = receipt["before_sha256"][:16]
        snapshot_path = (
            PRIVATE / f"editorial-preview/snapshots/working-{prefix}.sqlite3"
        )
    database = create_engine(
        f"sqlite:///{snapshot_path.resolve().as_uri()}?mode=ro&uri=true"
    )
    try:
        with database.connect() as connection:
            tables = snapshot(connection)
    finally:
        database.dispose()
    if digest(tables) != receipt["before_sha256"]:
        raise ValueError("Local mirror differs from the receipt's pre-publication hash")
    # Reproduce the publication script's exact status/access changes in memory.
    updates = {
        "status": "published",
        "review_status": "published",
        "access_tier": "free",
        "catalog_visible": True,
    }
    for rows in tables.values():
        for row in rows:
            for field in row.keys() & updates.keys():
                row[field] = updates[field]
    if digest(tables) != receipt["after_sha256"]:
        raise ValueError(
            "Reconstructed edition differs from the committed publication hash"
        )
    return tables, receipt


def reading_text(text):
    return hiragana(text.strip())


class Inventory:
    def __init__(self, references, revision):
        self.references = references
        self.items = {}
        self.variants = defaultdict(set)
        for form, reading in references.words:
            self.variants[form].add(reading)
        self.notes = {
            (row["chapter"], row["word"], row["reading"]): row
            for row in revision["vocabulary_notes"]
        }
        self.prose = []

    def record(
        self, kind, text, supplied, ref, evidence=(), *, issue=None, use_written=False
    ):
        text = text.strip()
        expected = reading_text(supplied).replace(".", "") if supplied else None
        if not expected:
            issue = issue or "missing_reading"
        elif not KANA.fullmatch(expected):
            issue = issue or "reading_not_single_kana_form"
        elif not evidence:
            issue = issue or "source_reading_unconfirmed"
        # Keep identity independent of review status while preserving bound readings as distinct.
        key = (kind, text, expected)
        item = self.items.setdefault(
            key,
            {
                "id": "ja-" + digest(key)[:24],
                "type": kind,
                "text": text,
                "verified_reading": expected if not issue else None,
                "status": "needs_manual_review" if issue else "ready_for_preview",
                "review_reason": issue,
                "audio_id": None,
                "input": None,
                "path": None,
                "evidence": [],
                "references": [],
            },
        )
        if item["status"] != ("needs_manual_review" if issue else "ready_for_preview"):
            raise ValueError(f"Inconsistent evidence for {kind} {text!r} {supplied!r}")
        if not issue:
            item["input"] = text if use_written else expected
            item["audio_id"] = audio_id(item["input"])
            item["path"] = f"wav/{item['audio_id']}.wav"
        source = {**ref, "supplied_reading": supplied}
        if source not in item["references"]:
            item["references"].append(source)
        for entry in evidence:
            if entry not in item["evidence"]:
                item["evidence"].append(entry)
        return item

    def kanji(self, kind, glyph, supplied, ref):
        value = reading_text(supplied)
        entries = self.references.kanji.get(glyph, {}).get("readings", [])
        matches = [
            entry
            for entry in entries
            if entry["kind"] == kind
            and reading_text(entry["text"]).replace(".", "") == value.replace(".", "")
        ]
        evidence = [
            {"source": "KANJIDIC2", "notation": entry["text"]} for entry in matches
        ]
        if (kind, glyph, value) == ("kun", "禾", "のぎ"):
            evidence = [
                {
                    "source": "edition reference",
                    "url": "https://www.kanjipedia.jp/kanji/0000635400",
                }
            ]
        if (kind, glyph, value) == ("kun", "靖", "やすい"):
            evidence = [
                {
                    "source": "edition reference for full kun form 靖い",
                    "url": "https://www.kanjipedia.jp/kotoba/0003907800",
                }
            ]
        issue = None
        if "-" in value:
            issue = "bound_reading_needs_context"
        elif not evidence:
            issue = "kanji_reading_not_confirmed_for_kind"
        self.record(f"kanji_{kind}", glyph, supplied, ref, evidence, issue=issue)

    def word(self, text, supplied, ref, annotations=(), kind="vocabulary"):
        matching = [
            entry
            for raw in sorted(self.variants[text])
            if reading_text(raw) == reading_text(supplied)
            for entry in self.references.words[(text, raw)]
            if entry["meanings_en"]
        ]
        evidence = [
            {"source": "JMdict", "entry_id": entry_id}
            for entry_id in sorted({entry["entry_id"] for entry in matching})
        ]
        evidence += [{"source": "edition reference", **entry} for entry in annotations]
        note = self.notes.get((ref["chapter"], text, supplied))
        # These two source-backed non-dictionary cases have explicit contextual readings.
        if note and (text, supplied) in {("何円", "なんえん"), ("十分", "じゅっぷん")}:
            evidence.append(
                {
                    "source": "edition vocabulary decision",
                    "citation": note["references"],
                }
            )
        item = self.record(
            kind, text, supplied, ref, evidence, use_written=kind == "phrase"
        )
        alternatives = sorted(
            {reading_text(raw) for raw in self.variants[text]}
            - {reading_text(supplied)}
        )
        if alternatives:
            item["dictionary_alternatives"] = alternatives

    def display_reading(self, study, ref):
        glyph, reading, kind = study["form"], study["reading"], study["kind"]
        if kind == "word":
            self.word(glyph, reading, ref)
        elif kind == "component":
            self.record(
                "component_name",
                glyph,
                reading,
                ref,
                [{"source": "explicit published component name"}],
            )
        else:
            entries = self.references.kanji.get(glyph, {}).get("readings", [])
            kinds = {
                entry["kind"]
                for entry in entries
                if "-" not in entry["text"]
                and reading_text(entry["text"]).replace(".", "")
                == reading_text(reading)
            }
            if len(kinds) == 1:
                self.kanji(next(iter(kinds)), glyph, reading, ref)
            else:
                self.record(
                    "context_reading",
                    glyph,
                    reading,
                    ref,
                    issue="reading_kind_or_context_unclear",
                )

    def prose_candidates(self):
        known = {
            (item["text"], ref["chapter"])
            for item in self.items.values()
            if item["status"] == "ready_for_preview"
            for ref in item["references"]
        }
        for text, source in self.prose:
            for token in dict.fromkeys(JAPANESE_TOKEN.findall(text)):
                # Thai notes contain visual glyphs and reading fragments alongside actual words.
                # Only consider lexical written forms attested in the pinned dictionary here.
                if (
                    len(token) > 1
                    and KANJI.search(token)
                    and self.variants.get(token)
                    and (token, source["chapter"]) not in known
                ):
                    item = self.record(
                        "note_word",
                        token,
                        None,
                        source,
                        issue="inline_word_missing_reading",
                    )
                    item["dictionary_alternatives"] = sorted(self.variants[token])

    def manifest(self, receipt, chapters, quiz_count):
        asset_map = {}
        for item in self.items.values():
            if not item["audio_id"]:
                continue
            asset = asset_map.setdefault(
                item["audio_id"],
                {
                    "id": item["audio_id"],
                    "input": item["input"],
                    "expected_reading": item["verified_reading"],
                    "path": item["path"],
                    "status": "ready_for_preview",
                    "content_ids": [],
                },
            )
            if asset["expected_reading"] != item["verified_reading"]:
                asset["status"] = "needs_manual_review"
            asset["content_ids"].append(item["id"])
        for item in self.items.values():
            if (
                item["audio_id"]
                and asset_map[item["audio_id"]]["status"] == "needs_manual_review"
            ):
                item.update(
                    status="needs_manual_review",
                    review_reason="conflicting_readings_for_synthesis_input",
                )
        by_content = {
            (item["type"], item["text"], item["verified_reading"]): item
            for item in self.items.values()
            if item["status"] == "ready_for_preview"
        }
        sample = []
        for key in SAMPLE:
            item = by_content.get(key)
            if item is None:
                raise ValueError(f"Sample content is absent or blocked: {key}")
            sample.append(
                {
                    k: item[k]
                    for k in ("type", "text", "verified_reading", "audio_id", "path")
                }
            )
        items = sorted(
            self.items.values(),
            key=lambda item: (item["type"], item["text"], item["id"]),
        )
        ready = sum(item["status"] == "ready_for_preview" for item in items)
        return {
            "schema_version": 1,
            "voice": VOICE,
            "edition": {
                "id": receipt["revision"],
                "publication_sha256": receipt["after_sha256"],
                "source": "receipt-verified local reproduction of published database snapshot",
            },
            "dictionary_sources": self.references.sources,
            "counts": {
                "chapters": chapters,
                "public_quiz_questions_inspected": quiz_count,
                "content_items": len(items),
                "source_references": sum(len(item["references"]) for item in items),
                "by_type": dict(
                    sorted(Counter(item["type"] for item in items).items())
                ),
                "ready_for_preview": ready,
                "manual_review": len(items) - ready,
                "ready_audio_assets": sum(
                    asset["status"] == "ready_for_preview"
                    for asset in asset_map.values()
                ),
                "review_reasons": dict(
                    sorted(
                        Counter(
                            item["review_reason"]
                            for item in items
                            if item["review_reason"]
                        ).items()
                    )
                ),
            },
            "sample": sample,
            "content": items,
            "assets": sorted(asset_map.values(), key=lambda asset: asset["id"]),
        }


def group_by(rows, key):
    groups = defaultdict(list)
    for row in rows:
        groups[row[key]].append(row)
    return groups


def build(tables, inventory, receipt):
    lessons = [
        row
        for row in tables["lessons"]
        if row["catalog_visible"]
        and row["status"] == "published"
        and row["access_tier"] == "free"
    ]
    sections = group_by(tables["lesson_sections"], "lesson_id")
    quiz = group_by(tables["quiz_questions"], "lesson_id")
    lesson_kanji = group_by(tables["lesson_kanjis"], "lesson_id")
    lesson_vocab = group_by(tables["lesson_vocabularies"], "lesson_id")
    kanji = {
        row["id"]: row
        for row in tables["kanjis"]
        if row["review_status"] == "published" and row["access_tier"] == "free"
    }
    kanji_ids = {row["character"]: row["id"] for row in kanji.values()}
    readings = group_by(tables["kanji_readings"], "kanji_id")
    vocabulary_kanji = group_by(tables["vocabulary_kanjis"], "vocabulary_id")
    words = {
        row["id"]: row
        for row in tables["vocabularies"]
        if row["status"] == "published" and row["access_tier"] == "free"
    }
    question_count = 0
    inventoried_kanji = set()
    for lesson in lessons:
        lesson_id = lesson["id"]
        base = {
            "chapter": lesson["chapter"],
            "lesson_slug": lesson["slug"],
            "lesson_id": lesson_id,
        }
        blocks = [
            (section, i, block)
            for section in sorted(sections[lesson_id], key=lambda row: row["position"])
            if section["status"] == "published" and section["access_tier"] == "free"
            for i, block in enumerate(section["blocks"])
            if block.get("kind") != "source_page_text"
        ]
        cards = [card for _, _, block in blocks for card in block.get("cards", [])]
        study_cards = {card["character"]: card for card in cards}
        glyph_refs = defaultdict(list)
        for link in lesson_kanji[lesson_id]:
            if link["kanji_id"] in kanji:
                glyph_refs[link["kanji_id"]].append(
                    {**base, "table": "lesson_kanjis", "position": link["position"]}
                )
        word_rows = {
            (
                words[link["vocabulary_id"]]["written_form"],
                words[link["vocabulary_id"]]["reading"],
            ): words[link["vocabulary_id"]]
            for link in lesson_vocab[lesson_id]
            if link["vocabulary_id"] in words
        }
        vocabulary = [
            word for _, _, block in blocks for word in block.get("vocabulary", [])
        ]
        if set(word_rows) != {(word["word"], word["reading"]) for word in vocabulary}:
            raise ValueError(
                f"Section and relational vocabulary differ in {lesson['slug']}"
            )

        def note(value, ref):
            if value and JAPANESE_TOKEN.search(value):
                inventory.prose.append((value, ref))

        for section, block_index, raw in blocks:
            projected = learner_block(raw, study_cards)
            section_ref = {
                **base,
                "table": "lesson_sections",
                "section_id": section["id"],
                "section_kind": section["kind"],
                "section_position": section["position"],
            }

            def ref(path, section_ref=section_ref, block_index=block_index, **fields):
                return {
                    **section_ref,
                    "pointer": f"/blocks/{block_index}/{path}",
                    **fields,
                }

            for i, card in enumerate(projected.get("cards", [])):
                card_ref = ref(
                    f"cards/{i}",
                    page=raw["cards"][i].get("pdf_page"),
                    glyph=card["character"],
                )
                study = card.get("study")
                note(card.get("memory_note"), {**card_ref, "field": "memory_note"})
                if not study:
                    example = parse_example(card.get("example", ""))
                    if example:
                        inventory.word(*example, {**card_ref, "field": "example"})
                    elif card.get("example"):
                        inventory.record(
                            "card_example", card["example"], None, card_ref
                        )
                    continue
                inventory.display_reading(
                    study["reading"], {**card_ref, "field": "study.reading"}
                )
                note(
                    study.get("scope_note_th"),
                    {**card_ref, "field": "study.scope_note_th"},
                )
                if study["example"]:
                    example = study["example"]
                    role = example["role"]
                    kind = (
                        "phrase"
                        if role.endswith("_phrase")
                        else "proper_name"
                        if role == "proper_name"
                        else "vocabulary"
                    )
                    inventory.word(
                        example["word"],
                        example["reading"],
                        {**card_ref, "field": "study.example", "role": role},
                        raw["cards"][i]["study"]["example"]["references"],
                        kind=kind,
                    )

            def node(value, node_ref, show_reading=True, glyph_refs=glyph_refs):
                glyph = value["kanji"]
                if glyph in kanji_ids:
                    glyph_refs[kanji_ids[glyph]].append(node_ref)
                if not show_reading:
                    return
                if value.get("study_reading"):
                    inventory.display_reading(value["study_reading"], node_ref)
                elif value.get("reading"):
                    if value.get("kind") == "component":
                        inventory.record(
                            "component_name",
                            glyph,
                            value["reading"],
                            node_ref,
                            [{"source": "explicit published component name"}],
                        )
                    else:
                        inventory.display_reading(
                            {
                                "form": glyph,
                                "reading": value["reading"],
                                "kind": "character",
                            },
                            node_ref,
                        )

            for i, pair in enumerate(projected.get("pairs", [])):
                for j, value in enumerate(pair):
                    node(value, ref(f"pairs/{i}/{j}"))
            if diagram := projected.get("diagram"):
                if diagram["core"]:
                    node(diagram["core"], ref("diagram/core"))
                for i, value in enumerate(diagram["related"]):
                    node(value, ref(f"diagram/related/{i}"))
                for i, pair in enumerate(diagram["comparison_pairs"]):
                    for j, value in enumerate(pair):
                        node(
                            value,
                            ref(f"diagram/comparison_pairs/{i}/{j}"),
                            show_reading=False,
                        )

            for i, word in enumerate(projected.get("vocabulary", [])):
                text, supplied = word["word"], word["reading"]
                word_ref = ref(
                    f"vocabulary/{i}",
                    vocabulary_id=word_rows[text, supplied]["id"],
                    page=raw["vocabulary"][i].get("pdf_page"),
                )
                inventory.word(text, supplied, word_ref)
                for link in vocabulary_kanji[word_ref["vocabulary_id"]]:
                    if link["kanji_id"] in kanji:
                        use = {
                            **word_ref,
                            "field": "indexed_vocabulary_glyph",
                            "glyph_position": link["position"],
                        }
                        glyph_refs[link["kanji_id"]].append(use)
                usage = word.get("usage_notes", "")
                note(usage, {**word_ref, "field": "usage_notes"})
                for variant in sorted(PROSE_VARIANTS.get(text, ())):
                    if variant in usage:
                        inventory.record(
                            "vocabulary_variant",
                            text,
                            variant,
                            {**word_ref, "field": "usage_notes"},
                            [
                                {
                                    "source": "explicit contextual reading in the published vocabulary note"
                                }
                            ],
                        )
            for i, sentence in enumerate(projected.get("sentences", [])):
                evidence = (
                    [
                        {
                            "source": "published sentence and kana transcription",
                            "url": sentence["source_url"],
                        }
                    ]
                    if sentence.get("source_url")
                    else []
                )
                inventory.record(
                    "sentence",
                    sentence["text"],
                    sentence.get("reading"),
                    ref(f"sentences/{i}"),
                    evidence,
                    use_written=True,
                )
            for i, tip in enumerate(projected.get("memory_tips", [])):
                note(tip, ref(f"memory_tips/{i}"))
            note(projected.get("text"), ref("text"))

        inventoried_kanji.update(glyph_refs)
        for kanji_id, refs in glyph_refs.items():
            row = kanji[kanji_id]
            glyph = row["character"]
            for use in refs:
                for reading in readings[kanji_id]:
                    inventory.kanji(
                        reading["kind"],
                        glyph,
                        reading["reading"],
                        {
                            **use,
                            "kanji_id": kanji_id,
                            "kanji_reading_id": reading["id"],
                        },
                    )
                if not readings[kanji_id]:
                    for kind in ("on", "kun"):
                        for supplied in row["readings"].get(kind, []):
                            inventory.kanji(
                                kind,
                                glyph,
                                supplied,
                                {**use, "kanji_id": kanji_id, "field": "readings"},
                            )
            note(
                row.get("note_th"),
                {**base, "table": "kanjis", "kanji_id": kanji_id, "field": "note_th"},
            )

        published_questions = [q for q in quiz[lesson_id] if q["status"] == "published"]
        originals = [
            {
                "key": q["stable_key"],
                "type": q["question_type"],
                "prompt": q["prompt"]["text"],
                "answer": q["answer_key"].get("text", ""),
            }
            for q in sorted(published_questions, key=lambda q: q["stable_key"])
        ]
        rubric = next(
            (
                block["comparison_rubric"]
                for _, _, block in blocks
                if "comparison_rubric" in block
            ),
            None,
        )
        questions = objective_questions(
            cards, vocabulary, originals, rubric, slug=lesson["slug"]
        )
        question_count += len(questions)
        readings_by_key = {
            q["key"]: q for q in originals if q["type"] == "vocabulary_reading"
        }
        for question in questions:
            key = question["source_question_key"]
            quiz_ref = {
                **base,
                "table": "quiz_questions",
                "key": key,
                "presentation_id": question["id"],
            }
            if key not in readings_by_key:
                # Kanji recognition/shape items are visual. Thai feedback can still mention words.
                note(question["explanation"], {**quiz_ref, "field": "feedback"})
                continue
            form = readings_by_key[key]["prompt"]
            target = next(word for word in vocabulary if word["word"] == form)
            inventory.word(
                form, target["reading"], {**quiz_ref, "field": "Japanese prompt"}
            )
            for option in question["options"]:
                inventory.record(
                    "quiz_kana_choice",
                    option["text"],
                    option["text"],
                    {**quiz_ref, "field": "option", "option_id": option["id"]},
                    [{"source": "literal kana in public quiz option"}],
                )
    if (
        len(lessons) != receipt["chapters_verified"]
        or question_count != receipt["questions_verified"]
    ):
        raise ValueError(
            "Public lesson or quiz coverage differs from the publication receipt"
        )
    if set(kanji) != inventoried_kanji:
        raise ValueError(
            f"Published kanji without a lesson reference: {sorted(set(kanji) - inventoried_kanji)}"
        )
    inventory.prose_candidates()
    return inventory.manifest(receipt, len(lessons), question_count)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, default=RECEIPT)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    tables, receipt = load_publication(args.receipt, args.snapshot)
    revision = read_json(
        PRIVATE / "editorial-revisions" / f"{receipt['revision']}.json"
    )
    manifest = build(
        tables, Inventory(References(PRIVATE / "dictionaries"), revision), receipt
    )
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    with (args.output / "manual-review.csv").open(
        "x", encoding="utf-8-sig", newline=""
    ) as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "content_id",
                "type",
                "text",
                "source_readings",
                "reason",
                "chapters",
                "dictionary_candidates",
            ]
        )
        for row in manifest["content"]:
            if row["status"] == "needs_manual_review":
                writer.writerow(
                    [
                        row["id"],
                        row["type"],
                        row["text"],
                        " / ".join(
                            sorted(
                                {r["supplied_reading"] or "" for r in row["references"]}
                            )
                        ),
                        row["review_reason"],
                        ", ".join(
                            map(str, sorted({r["chapter"] for r in row["references"]}))
                        ),
                        " / ".join(row.get("dictionary_alternatives", [])),
                    ]
                )
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        sys.exit(f"Audio inventory: {exc}")
