"""Review artifacts for the pinned N5 reference. No database writes."""

import csv
import io
import json
from collections import Counter

from jlpt_n5_reference import audit_matches, published
from publish_japanese_audio import lookup_key

from app.content_revision import digest
from app.expansion_import import ImportPlan, pair

# Explicit teaching selections from the checked catalog. These are proposals,
# never inferred from spelling, a keyword, or POS alone.
UNITS = (
    (
        "numbers-1",
        "ตัวเลขพื้นฐาน หนึ่งถึงห้า",
        ("一", "二", "三", "四", "五"),
        (),
        (),
        "numbers-and-counting",
    ),
    (
        "numbers-2",
        "ตัวเลขพื้นฐาน หกถึงสิบ",
        ("六", "七", "八", "九", "十"),
        (),
        ("numbers-1",),
        "numbers-and-counting",
    ),
    (
        "counting-people",
        "นับคนและบอกจำนวน",
        ("人",),
        (("人", "ひと"), ("一人", "ひとり"), ("二人", "ふたり")),
        ("numbers-1",),
        "japanese-counters",
    ),
    (
        "calendar",
        "วัน เดือน และช่วงเวลา",
        ("日", "月", "年", "時", "分"),
        (
            ("今日", "きょう"),
            ("明日", "あした"),
            ("三日", "みっか"),
            ("月曜日", "げつようび"),
            ("日曜日", "にちようび"),
            ("午前", "ごぜん"),
            ("午後", "ごご"),
            ("時間", "じかん"),
        ),
        ("numbers-2",),
        "dates-and-time",
    ),
    (
        "daily-objects",
        "สิ่งของใกล้ตัว",
        ("本",),
        (("本", "ほん"), ("机", "つくえ"), ("時計", "とけい"), ("新聞", "しんぶん")),
        (),
        "everyday-objects",
    ),
    (
        "home-and-school",
        "บ้าน โรงเรียน และผู้คน",
        ("学", "生"),
        (
            ("家", "いえ"),
            ("家族", "かぞく"),
            ("学校", "がっこう"),
            ("学生", "がくせい"),
            ("友達", "ともだち"),
            ("名前", "なまえ"),
        ),
        (),
        "everyday-vocabulary",
    ),
    (
        "everyday-actions",
        "การกระทำที่ใช้ในชีวิตประจำวัน",
        (),
        (
            ("歩く", "あるく"),
            ("走る", "はしる"),
            ("読む", "よむ"),
            ("話す", "はなす"),
            ("洗う", "あらう"),
            ("使う", "つかう"),
        ),
        ("home-and-school",),
        "everyday-vocabulary",
    ),
)
CATEGORIES = {
    "numbers-and-counting": "ตัวเลขและการนับ",
    "japanese-counters": "ลักษณนามญี่ปุ่น",
    "dates-and-time": "วันและเวลา",
    "everyday-objects": "สิ่งของในชีวิตประจำวัน",
    "everyday-vocabulary": "คำศัพท์ในชีวิตประจำวัน",
}
SENTENCE_PLACEMENT = {
    "学校に行きます。": ["home-and-school"],
    "友達と遊びます。": ["home-and-school"],
    "8時に家を出ます。": ["calendar", "home-and-school"],
}


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def read_baseline(path):
    document = json.loads(path.read_bytes())
    if (
        document.get("revision") not in {"0002", "0003"}
        or digest(document["tables"]) != document["sha256"]
    ):
        raise ValueError("Invalid canonical catalog snapshot checksum or revision")
    lessons = document["tables"]["lessons"]
    if [row["slug"] for row in sorted(lessons, key=lambda r: r["chapter"])] != [
        f"chapter-{n:02d}" for n in range(1, 31)
    ]:
        raise ValueError("Expected the canonical 30-chapter book snapshot")
    return document


def propose_units(rows, inventory, tables, sentence_refs):
    by_pair = {pair(r["kind"], r["text"], r["reading"]): r for r in rows}
    used = set()
    unit_proposals, memberships, staged_units = [], [], []
    for position, (key, title, glyphs, words, prerequisites, category) in enumerate(
        UNITS
    ):
        desired = [pair("kanji", c) for c in glyphs] + [
            pair("vocabulary", w, r) for w, r in words
        ]
        offers = [by_pair[k] for k in desired if k in by_pair]
        slots = [
            r
            for r in offers
            if r["classification"] == "reuse_published"
            and "thai_meaning_not_confirmed" not in r["review_flags"]
        ]
        used.update(r["key"] for r in slots)
        staged = {
            "key": key,
            "title_th": title,
            "position": position,
            "items": [{"target": r["canonical"]} for r in slots],
        }
        if slots:
            staged_units.append((category, staged))
        unit_proposals.append(
            {
                "unit_key": key,
                "title_th": title,
                "order": position,
                "prerequisite_unit_keys_editorial_only": list(prerequisites),
                "staged_reference_keys": [r["key"] for r in slots],
                "reference_keys_to_review": [r["key"] for r in offers],
                "planned_identity_not_in_reference": [
                    k for k in desired if k not in by_pair
                ],
                "publication_ready": False,
            }
        )
        memberships.append(
            {
                "category_slug": category,
                "unit_key": key,
                "reference_keys": [r["key"] for r in offers],
                "selection": "manual seed from published book context",
                "approval_required": True,
            }
        )
    kanji_queue = sorted(
        (r for r in inventory if r["kind"] == "kanji" and r["key"] not in used),
        key=lambda r: (r["frequency"] is None, r["frequency"] or 0, r["order"]),
    )
    vocab_queue = [
        r for r in inventory if r["kind"] == "vocabulary" and r["key"] not in used
    ]
    queues = {
        "kanji_by_reference_frequency": [r["key"] for r in kanji_queue],
        "vocabulary_by_reference_order": [r["key"] for r in vocab_queue],
    }
    categories = [
        {
            "slug": slug,
            "title_th": title,
            "present_in_snapshot": any(
                p["slug"] == slug and p["kind"] == "category"
                for p in tables.get("learning_paths", [])
            ),
            "used_by_local_demo": slug in {"numbers-and-counting", "japanese-counters"},
        }
        for slug, title in CATEGORIES.items()
    ]
    return (
        {
            "units": unit_proposals,
            "unplaced_review_queue": queues,
            "book_sentence_candidates": [
                {
                    **example,
                    "proposed_unit_keys": SENTENCE_PLACEMENT.get(example["text"], []),
                    "license_and_context_approval_required": True,
                }
                for example in sentence_refs
            ],
        },
        {
            "categories": categories,
            "proposals": memberships,
            "unassigned_need_semantic_review": [
                k for queue in queues.values() for k in queue
            ],
        },
        staged_units,
    )


def audit_audio(inventory, mapping, release_audit, sentence_refs):
    def check(kind, text, reading):
        key = lookup_key(kind, text, reading)
        shared = mapping["shared"].get(key)
        scopes = {
            slug: entries[key]
            for slug, entries in mapping["lessons"].items()
            if entries.get(key)
        }
        if shared in mapping["files"]:
            state = "shared_exact"
        elif len(set(scopes.values())) > 1:
            state = "ambiguous_scope"
        elif scopes:
            state = "lesson_scope_review"
        elif kind == "kanji" and (reading.startswith("-") or reading.endswith("-")):
            state = "bound_reading_review"
        else:
            state = "missing_exact"
        return {
            "kind": kind,
            "text": text,
            "reading": reading,
            "lookup_key": key,
            "status": state,
            "audio_id": shared if state == "shared_exact" else None,
            "lesson_scopes": scopes,
        }

    rows = []
    for item in inventory:
        if item["kind"] == "kanji":
            versions = [
                check("kanji", item["text"], r)
                for r in dict.fromkeys(item["readings"]["on"] + item["readings"]["kun"])
            ]
        else:
            versions = [check("word", item["text"], item["reading"])]
        rows.append(
            {
                "reference_key": item["key"],
                "kind": item["kind"],
                "lookups": versions,
                "context_dependent_kanji_readings": [
                    v["reading"]
                    for v in versions
                    if v["kind"] == "kanji"
                    and ("." in v["reading"] or "-" in v["reading"])
                ],
                "alternate_pronunciations": sorted(
                    {
                        a["reading"]
                        for a in item.get("aliases", [])
                        if a["reading"] != item.get("reading")
                    }
                ),
            }
        )
    candidates = [check("sentence", e["text"], e["reading"]) for e in sentence_refs]
    status = Counter(v["status"] for row in rows for v in row["lookups"])
    missing = {
        v["lookup_key"]
        for row in rows
        for v in row["lookups"]
        if v["status"] == "missing_exact"
    }
    assets = len(mapping["files"])
    avg = (
        release_audit["web_bytes"] / assets
        if release_audit["web_files"] == assets
        else None
    )
    coverage = {
        kind: {
            "reference_items_with_shared_exact": sum(
                any(v["status"] == "shared_exact" for v in r["lookups"])
                for r in rows
                if r["kind"] == kind
            ),
            "reference_items_with_all_readings_shared": sum(
                bool(r["lookups"])
                and all(v["status"] == "shared_exact" for v in r["lookups"])
                for r in rows
                if r["kind"] == kind
            ),
            "lookup_statuses": dict(
                Counter(
                    v["status"] for r in rows if r["kind"] == kind for v in r["lookups"]
                )
            ),
        }
        for kind in ("kanji", "vocabulary")
    }
    return {
        "existing_mp3_assets": assets,
        "existing_mp3_bytes": release_audit["web_bytes"],
        "audio_index_sha256": digest(mapping),
        "audio_release_audit_sha256": digest(release_audit),
        "exact_lookup_statuses": dict(status),
        "coverage_by_kind": coverage,
        "vocabulary_with_alternate_dictionary_readings": sum(
            bool(r["alternate_pronunciations"]) for r in rows
        ),
        "kanji_with_bound_or_okurigana_readings": sum(
            bool(r["context_dependent_kanji_readings"]) for r in rows
        ),
        "unique_missing_exact_lookup_keys": len(missing),
        "storage_estimate_bytes_one_mp3_per_missing_key": round(len(missing) * avg)
        if avg is not None
        else None,
        "estimate_scope": "uses existing mean MP3 bytes; excludes new sentences, scope conflicts, bound readings and synthesis deduplication",
        "existing_book_sentence_candidates": candidates,
        "reference_items": rows,
    }


def prepare(output, baseline, inventory, release, examples, audio_index, audio_release):
    tables = baseline["tables"]
    rows, sentence_refs = audit_matches(inventory, tables, examples)
    sequence, categories, selected_units = propose_units(
        rows, inventory, tables, sentence_refs
    )
    reuse = [r for r in rows if r["classification"] == "reuse_published"]
    paths = (
        [
            {
                "kind": "jlpt",
                "slug": "n5",
                "level": 5,
                "title_th": "JLPT N5",
                "position": 0,
                "units": [u for _, u in selected_units],
            }
        ]
        if selected_units
        else []
    )
    for pos, (key, title) in enumerate(CATEGORIES.items()):
        units = [unit for category, unit in selected_units if category == key]
        if units:
            paths.append(
                {
                    "kind": "category",
                    "slug": key,
                    "title_th": title,
                    "position": pos,
                    "units": units,
                }
            )
    plan = ImportPlan(
        catalog_sha256=baseline["sha256"],
        reference=release,
        reuse=[
            {"target": r["canonical"], "row_sha256": r["canonical_sha256"]}
            for r in reuse
        ],
        assignments=[
            {"target": r["canonical"], "reference_key": r["key"]} for r in reuse
        ],
        paths=paths,
    )
    candidates = [r for r in rows if r["classification"] != "reuse_published"]
    unresolved = [r for r in rows if r["review_flags"]]
    outcome = {
        kind: dict(Counter(r["classification"] for r in rows if r["kind"] == kind))
        for kind in ("kanji", "vocabulary")
    }
    summary = {
        "reference_version": release.version,
        "catalog_revision": baseline["revision"],
        "catalog_sha256": baseline["sha256"],
        "source_totals": release.manifest["counts"],
        "matching": outcome,
        "publication_ready": 0,
        "flags": dict(Counter(flag for r in rows for flag in r["review_flags"])),
        "published_kanji_in_chapters": sum(
            r["kind"] == "kanji"
            and r["classification"] == "reuse_published"
            and bool(r["source_lesson_slugs"])
            for r in rows
        ),
        "catalog_published": {
            "kanji": sum(published("kanji", r) for r in tables["kanjis"]),
            "vocabulary": sum(
                published("vocabulary", r) for r in tables["vocabularies"]
            ),
        },
        "book_sentences": len(sentence_refs),
        "reference_sentences_with_ids": len(
            {
                e["tatoeba_id"]
                for row in inventory
                for e in row.get("example_candidates", [])
                if e["tatoeba_id"]
            }
        ),
        "staged_unit_proposals": len(selected_units),
        "staged_new_records": 0,
        "published_book_chapters": sum(
            published("vocabulary", r) and r["catalog_visible"]
            for r in tables["lessons"]
        ),
    }
    for name, value in {
        "reference-inventory.json": inventory,
        "canonical-mappings.json": rows,
        "new-and-unresolved.json": candidates,
        "validation-and-conflicts.json": {
            "summary": summary,
            "review_rows": unresolved,
        },
        "category-proposals.json": categories,
        "unit-proposals.json": sequence,
        "audio-coverage.json": audit_audio(
            inventory, audio_index, audio_release, sentence_refs
        ),
        "import-manifest.json": plan.model_dump(mode="json"),
        "approval-template.json": {
            "plan_sha256": digest(plan.model_dump(mode="json")),
            "reviewer": "",
            "decision_reference": "",
            "approved": False,
        },
    }.items():
        write_json(output / name, value)
    sheet = io.StringIO(newline="")
    writer = csv.writer(sheet)
    writer.writerow(
        [
            "reference_key",
            "kind",
            "text",
            "reading",
            "classification",
            "canonical_id",
            "thai_existing",
            "review_flags",
            "review_decision",
            "reviewer",
            "evidence",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row["key"],
                row["kind"],
                row["text"],
                row["reading"],
                row["classification"],
                row["canonical_id"],
                row["existing_meaning_th"],
                ";".join(row["review_flags"]),
                "",
                "",
                "",
            ]
        )
    csv_bytes = sheet.getvalue().encode("utf-8-sig")
    checklist = output / "editorial-review.csv"
    if checklist.is_file() and checklist.read_bytes() != csv_bytes:
        with checklist.open(encoding="utf-8-sig", newline="") as stream:
            previous = csv.DictReader(stream)
            editorial_columns = {"review_decision", "reviewer", "evidence"}
            if not editorial_columns <= set(previous.fieldnames or []) or any(
                any(row.get(column) for column in editorial_columns) for row in previous
            ):
                checklist = output / "editorial-review.regenerated.csv"
    checklist.write_bytes(csv_bytes)
    return summary
