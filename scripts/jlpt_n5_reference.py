"""Pinned OpenJLPT inventory and editorial evidence for the N5 rehearsal."""

import csv
import gzip
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from urllib.request import urlopen
from xml.etree import ElementTree

from app.content_revision import digest
from app.expansion_import import (
    ReferenceRelease,
    Target,
    index_catalog,
    kana,
    nfc,
    pair,
)

VERSION = "0d1d3410bec90bd4098a7c72de820543cb4f707c"
REPO = "https://github.com/evanclan/OpenJLPT"
RAW = f"https://raw.githubusercontent.com/evanclan/OpenJLPT/{VERSION}"
FILES = {
    "kanji-n5.csv": (
        "data/csv/kanji-n5.csv",
        "d1d20aed0512e368314efe7d5d8e217984f9681b9ab6dd137c081d627c3d7d57",
    ),
    "vocab-n5.csv": (
        "data/csv/vocab-n5.csv",
        "ea82df093658fa35f24fd53073ce9a0a07765f50314bce04debf45b278ebfcd3",
    ),
    "vocab-n5.json": (
        "data/json/vocab/n5.json",
        "cbb221c9a3a92108fcd02fb088d9afacc70bc8c96570d5730425de0a49dad5f3",
    ),
    "NOTICE.md": (
        "NOTICE.md",
        "a2e6f45517bb1a1c047628991832244916888a4ced3aa26adeafb89705588557",
    ),
    "LICENSE": (
        "LICENSE",
        "28a9529c7d0bb4dc51f4bf5c116a3d16ef247a052f7591466768ddf563fd1cf5",
    ),
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def fetch_sources(folder):
    folder.mkdir(parents=True, exist_ok=True)
    for name, (location, checksum) in FILES.items():
        path = folder / name
        if path.exists():
            verify_file(path, checksum)
            continue
        with urlopen(f"{RAW}/{location}", timeout=20) as response:
            data = response.read()
        if sha256(data) != checksum:
            raise ValueError(f"Pinned checksum differs for {name}")
        path.write_bytes(data)


def verify_file(path, checksum):
    data = path.read_bytes()
    if sha256(data) != checksum:
        raise ValueError(f"Source checksum differs for {path.name}")
    return data


def list_field(value):
    return list(dict.fromkeys(nfc(item) for item in value.split(";") if item.strip()))


def read_csv(data, required):
    reader = csv.DictReader(
        io.StringIO(data.decode("utf-8-sig"), newline=""), strict=True
    )
    if (
        not reader.fieldnames
        or len(set(reader.fieldnames)) != len(reader.fieldnames)
        or not set(required) <= set(reader.fieldnames)
    ):
        raise ValueError("Unexpected or duplicate CSV header")
    for number, row in enumerate(reader, 1):
        if None in row or any(v is None for v in row.values()) or row["level"] != "N5":
            raise ValueError(f"Invalid N5 reference row {number}")
        yield number, row


def dictionary_evidence(path, wanted):
    metadata = json.loads(path.with_name(path.name + ".source.json").read_bytes())
    raw = verify_file(path, metadata["sha256"])
    result = {}
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as xml:
        for event, node in ElementTree.iterparse(xml, events=("start", "end")):
            if event == "start" and node.tag == "JMdict":
                root = node
            if event != "end" or node.tag != "entry":
                continue
            key = node.findtext("ent_seq")
            if key in wanted:
                forms = [nfc(x.text) for x in node.findall("k_ele/keb")]
                pairs = set()
                for reading in node.findall("r_ele"):
                    value = kana(reading.findtext("reb"))
                    restricted = [nfc(r.text) for r in reading.findall("re_restr")]
                    if reading.find("re_nokanji") is not None or not forms:
                        pairs.add((value, value))
                    else:
                        pairs.update((form, value) for form in restricted or forms)
                result[key] = {
                    "pairs": sorted(pairs),
                    "senses": [
                        {
                            "written_restrictions": [
                                nfc(x.text) for x in s.findall("stagk")
                            ],
                            "reading_restrictions": [
                                kana(x.text) for x in s.findall("stagr")
                            ],
                            "pos": [x.text for x in s.findall("pos")],
                            "gloss_en": [
                                x.text
                                for x in s.findall("gloss")
                                if x.get(
                                    "{http://www.w3.org/XML/1998/namespace}lang", "eng"
                                )
                                == "eng"
                            ],
                        }
                        for s in node.findall("sense")
                    ],
                }
            root.remove(node)
    return result, {
        "url": metadata["url"],
        "sha256": metadata["sha256"],
        "license": "CC BY-SA 4.0",
    }


def load_reference(folder, jmdict):
    raw = {name: verify_file(folder / name, sha) for name, (_, sha) in FILES.items()}
    json_rows = json.loads(raw["vocab-n5.json"])
    examples = {item["id"]: item for item in json_rows}
    vocab = list(
        read_csv(
            raw["vocab-n5.csv"],
            (
                "id",
                "word",
                "reading",
                "level",
                "jmdict_id",
                "other_forms",
                "example_ja",
                "pos",
            ),
        )
    )
    dictionary, dictionary_source = dictionary_evidence(
        jmdict, {r["jmdict_id"] for _, r in vocab if r["jmdict_id"]}
    )
    inventory = []
    for order, row in read_csv(
        raw["kanji-n5.csv"],
        ("character", "level", "onyomi", "kunyomi", "freq", "strokes"),
    ):
        text = nfc(row["character"])
        Target(kind="kanji", text=text)
        inventory.append(
            {
                "key": f"kanji:{text}",
                "kind": "kanji",
                "text": text,
                "level": 5,
                "order": order,
                "file": "kanji-n5.csv",
                "strokes": int(row["strokes"]),
                "frequency": int(row["freq"]) if row["freq"] else None,
                "readings": {
                    "on": list_field(row["onyomi"]),
                    "kun": list_field(row["kunyomi"]),
                },
                "reference_gloss_en": list_field(row["meanings"]),
            }
        )
    for order, row in vocab:
        text, reading = nfc(row["word"]), kana(row["reading"])
        Target(kind="vocabulary", text=text, reading=reading)
        if not re.fullmatch(r"[a-f0-9]{10}", row["id"]):
            raise ValueError("Invalid or missing upstream vocabulary ID")
        parallel = examples.get(row["id"])
        if not parallel or (
            nfc(parallel["word"]),
            kana(parallel["reading"]),
            parallel["level"],
        ) != (text, reading, "N5"):
            raise ValueError("CSV and JSON vocabulary identities differ")
        dictionary_id = row["jmdict_id"] or None
        lexeme = dictionary.get(dictionary_id, {"pairs": [], "senses": []})
        confirmed = (text, reading) in lexeme["pairs"]
        # Reading restrictions govern possible pairs. A written alternative from the
        # CSV alone is retained for review but does not authorize an alias import.
        aliases = (
            [
                {"text": w, "reading": r}
                for w, r in lexeme["pairs"]
                if (w, r) != (text, reading)
            ]
            if confirmed
            else []
        )
        senses = [
            s
            for s in lexeme["senses"]
            if (not s["written_restrictions"] or text in s["written_restrictions"])
            and (not s["reading_restrictions"] or reading in s["reading_restrictions"])
        ]
        sentence_refs = [
            {"tatoeba_id": e.get("tatoeba_id"), "has_furigana": bool(e.get("furigana"))}
            for e in parallel.get("examples", [])
        ]
        if row["example_ja"] and not any(
            e["ja"] == row["example_ja"] for e in parallel.get("examples", [])
        ):
            raise ValueError("CSV and JSON sentence evidence differ")
        inventory.append(
            {
                "key": f"vocabulary:{row['id']}",
                "kind": "vocabulary",
                "text": text,
                "reading": reading,
                "level": 5,
                "order": order,
                "file": "vocab-n5.csv",
                "dictionary_id": dictionary_id,
                "dictionary_pair_verified": confirmed,
                "source_other_forms": list_field(row["other_forms"]),
                "pos": list_field(row["pos"]),
                "aliases": aliases,
                "dictionary_senses": senses,
                "reference_gloss_en": list_field(row["meanings"]),
                "example_candidates": sentence_refs,
            }
        )
    counts = Counter(row["kind"] for row in inventory)
    if (
        counts != {"kanji": 84, "vocabulary": 674}
        or len(examples) != len(vocab)
        or len(json_rows) != len(vocab)
    ):
        raise ValueError(f"Pinned N5 inventory count differs: {counts}")
    if len({r["key"] for r in inventory}) != len(inventory) or len(
        {pair(r["kind"], r["text"], r.get("reading", "")) for r in inventory}
    ) != len(inventory):
        raise ValueError("Duplicate normalized reference identity")
    manifest = {
        "counts": {"N5": dict(counts)},
        "inventory_sha256": digest(inventory),
        "sources": {
            name: {"url": f"{RAW}/{location}", "sha256": sha}
            for name, (location, sha) in FILES.items()
        },
        "dictionary": dictionary_source,
    }
    release = ReferenceRelease(
        source_key="openjlpt",
        version=VERSION,
        source_url=f"{REPO}/tree/{VERSION}",
        license="CC BY-SA 4.0",
        attribution="OpenJLPT · Jonathan Waller (Tanos) · JMdict/KANJIDIC2 (EDRDG) · Tatoeba (candidate references only)",
        evidence=f"{RAW}/NOTICE.md",
        manifest=manifest,
        manifest_sha256=digest(manifest),
    )
    return inventory, release, examples


def target_from_catalog(kind, row):
    text = row.get("character") or row.get("written_form") or row["text_ja"]
    return {"kind": kind, "text": text, "reading": row.get("reading", "")}


def published(kind, row):
    return (
        row.get("review_status" if kind == "kanji" else "status") == "published"
        and row.get("access_tier") == "free"
    )


def audit_matches(inventory, tables, examples):
    lookup = index_catalog(tables)
    reference_siblings = defaultdict(list)
    for item in inventory:
        if item.get("dictionary_id"):
            reference_siblings[item["dictionary_id"]].append(item["key"])
    by_form, by_reading, by_dict = (
        defaultdict(list),
        defaultdict(list),
        defaultdict(list),
    )
    for item in tables["vocabularies"]:
        by_form[nfc(item["written_form"])].append(item)
        by_reading[kana(item["reading"])].append(item)
        if owner := item["provenance"].get("jmdict_id"):
            by_dict[str(owner)].append(item)
    places = {
        r["id"]: r["slug"]
        for r in tables["lessons"]
        if published("vocabulary", r) and r["catalog_visible"]
    }
    lesson_matches = defaultdict(set)
    for name, kind, key in (
        ("lesson_kanjis", "kanji", "kanji_id"),
        ("lesson_vocabularies", "vocabulary", "vocabulary_id"),
    ):
        for place in tables[name]:
            if place["lesson_id"] in places:
                lesson_matches[(kind, place[key])].add(places[place["lesson_id"]])
    reviewed_sentences = []
    for section in tables["lesson_sections"]:
        if section["lesson_id"] in places and published("vocabulary", section):
            for block_index, block in enumerate(section["blocks"]):
                for index, example in enumerate(block.get("sentences", [])):
                    reviewed_sentences.append(
                        {
                            "chapter": places[section["lesson_id"]],
                            "position": section["position"],
                            "pointer": f"/blocks/{block_index}/sentences/{index}",
                            **example,
                        }
                    )
    result = []
    for ref in inventory:
        kind, text, reading = ref["kind"], ref["text"], ref.get("reading", "")
        identity = pair(kind, text, reading)
        exact = lookup.get(identity, [])
        alias, alternate, homophones = {}, {}, []
        blockers = []
        siblings = [
            key
            for key in reference_siblings.get(ref.get("dictionary_id"), [])
            if key != ref["key"]
        ]
        if siblings:
            blockers.append("reference_jmdict_shared_identity")
        if kind == "vocabulary":
            candidates = [(a["text"], a["reading"]) for a in ref["aliases"]]
            candidates.extend((form, reading) for form in ref["source_other_forms"])
            for form, pronunciation in candidates:
                if pair(kind, form, pronunciation) != identity:
                    alias.update(
                        (r["id"], r)
                        for r in lookup.get(pair(kind, form, pronunciation), [])
                    )
            if ref["dictionary_id"]:
                alias.update(
                    (r["id"], r)
                    for r in by_dict[ref["dictionary_id"]]
                    if r not in exact
                )
            alternate = {r["id"]: r for r in by_form[text] if r not in exact}
            homophones = [
                r["written_form"]
                for r in by_reading[reading]
                if r["written_form"] != text
            ]
            if not ref["dictionary_pair_verified"]:
                blockers.append("dictionary_pair_unverified")
            if len(ref["dictionary_senses"]) > 1:
                blockers.append("sense_selection")
            if ref["example_candidates"]:
                blockers.append("source_sentence_attribution_and_translation")
        row = exact[0] if len(exact) == 1 else None
        if len(exact) > 1:
            outcome = "conflict"
            blockers.append("normalized_canonical_collision")
        elif row:
            outcome = "reuse_published" if published(kind, row) else "reuse_restricted"
            if outcome == "reuse_restricted":
                blockers.append("canonical_visibility")
        elif alias or alternate:
            outcome = "unresolved_variant"
            blockers.append("variant_or_reading_review")
        else:
            outcome = "new_candidate"
        if not row or not re.search(r"[ก-๛]", row["meaning_th"] or ""):
            blockers.append("thai_meaning_not_confirmed")
        if not row:
            blockers.append("new_or_variant_license_review")
        # Only exact complete sentences are recognized here. Earlier prose
        # fragments and substring matches are not a Thai gloss or a linked example.
        source_examples = {
            nfc(e["ja"])
            for e in examples.get(ref["key"].split(":", 1)[1], {}).get("examples", [])
        }
        attested = [
            {"chapter": e["chapter"], "pointer": e["pointer"], "text": e["text"]}
            for e in reviewed_sentences
            if nfc(e["text"]) in source_examples
        ]
        catalog_sentences = [
            s["id"]
            for s in tables.get("example_sentences", [])
            if nfc(s["text_ja"]) in source_examples and published("vocabulary", s)
        ]
        if not attested and not catalog_sentences:
            blockers.append("reviewed_example_missing")
        result.append(
            {
                "key": ref["key"],
                "kind": kind,
                "text": text,
                "reading": reading,
                "classification": outcome,
                "canonical": target_from_catalog(kind, row) if row else None,
                "canonical_id": row["id"] if row else None,
                "canonical_sha256": digest(row) if row else None,
                "other_reference_keys_with_same_dictionary_id": siblings,
                "existing_meaning_th": row["meaning_th"] if row else None,
                "source_lesson_slugs": sorted(lesson_matches[(kind, row["id"])])
                if row
                else [],
                "exact_candidates": [target_from_catalog(kind, r) for r in exact],
                "variant_candidates": [
                    target_from_catalog(kind, r) for r in alias.values()
                ],
                "alternate_reading_candidates": [
                    target_from_catalog(kind, r) for r in alternate.values()
                ],
                "homophones_not_used_for_matching": sorted(set(homophones)),
                "approved_book_sentence_exact_matches": attested,
                "catalog_sentence_exact_matches": catalog_sentences,
                "review_flags": blockers,
                "publication_ready": False,
            }
        )
    return result, reviewed_sentences
