"""Guarded updates to an existing private edition, never the insert-only importer."""

import copy
import json

from sqlalchemy import insert, select, update

from .content_revision import digest
from .models import Base

ALLOWED = {
    "kanjis": {"meaning_th", "readings", "note_th", "source"},
    "vocabularies": {"meaning_th", "usage_notes", "provenance"},
    "lesson_sections": {"blocks", "provenance"},
    "quiz_questions": {"prompt", "answer_key", "explanation_th", "provenance"},
    "lessons": {"title_th", "summary_th", "introduction_th", "anchors", "provenance"},
    "kanji_relations": {"explanation_th", "provenance"},
    "kanji_readings": {"position", "notes"},
    "components": {"label_th", "classification", "source"},
}
PROTECTED = {"status", "review_status", "access_tier", "catalog_visible"}
TABLES = {
    t.name: t
    for t in Base.metadata.sorted_tables
    # Keep the book edition digest and publication scope fixed as the catalog grows.
    if t.name in ALLOWED.keys() | {
        "kanji_components", "lesson_kanjis", "lesson_vocabularies",
        "visual_assets", "vocabulary_kanjis",
    }
}


def normalized(value):
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def snapshot(connection, *, lock=False):
    result = {}
    for name, table in TABLES.items():
        query = select(table).order_by(*table.primary_key)
        if lock:
            query = query.with_for_update()
        result[name] = [dict(row) for row in connection.execute(query).mappings()]
    return normalized(result)


def require_private(tables):
    if len(tables["lessons"]) != 30:
        raise ValueError("Expected the existing 30-chapter private edition")
    for rows in tables.values():
        for row in rows:
            if "access_tier" in row and row["access_tier"] != "private":
                raise ValueError("Editorial synchronization only operates on private content")
            for field in ["status", "review_status"]:
                if field in row and row[field] != "needs_review":
                    raise ValueError("Unexpected content review state; do not overwrite it")
            if row.get("catalog_visible"):
                raise ValueError("Editorial synchronization cannot publish lessons")


def prepare_updates(baseline, bundle, revision_id):
    require_private(baseline)
    if bundle.publication_approved:
        raise ValueError("Cannot synchronize a publication bundle")
    operations = []

    def resolve(value):
        if isinstance(value, dict) and "$ref" in value:
            spec = value["$ref"]
            key = {k: resolve(v) for k, v in spec["key"].items()}
            rows = [r for r in baseline[spec["table"]] if all(r[k] == v for k, v in key.items())]
            if len(rows) != 1:
                raise ValueError("Existing foreign-key identity is missing or ambiguous")
            return rows[0][spec["column"]]
        return value

    seen = set()
    for operation in bundle.operations:
        name = operation["table"]
        if name not in TABLES:
            raise ValueError("User data and unknown tables are outside editorial scope")
        key = {k: resolve(v) for k, v in operation["key"].items()}
        identity = (name, digest(key))
        if identity in seen:
            raise ValueError("Duplicate desired natural key")
        seen.add(identity)
        values = {k: resolve(v) for k, v in operation["values"].items()}
        matches = [r for r in baseline[name] if all(r.get(k) == v for k, v in key.items())]
        if not matches:
            # The only new row in this edition is the explicit on-reading of 靖.
            # A fixed allowlist prevents accidentally inserting missing content.
            if name != "kanji_readings" or key.get("kind") != "on" or key.get("reading") != "せい":
                raise ValueError("Unexpected new natural key; no general insert/import allowed")
            glyph = next(r for r in baseline["kanjis"] if r["id"] == key["kanji_id"])
            if glyph["character"] != "靖":
                raise ValueError("New reading belongs to an unexpected character")
            operations.append(
                {"table": name, "action": "insert_reading", "key": key, "values": values}
            )
            continue
        if len(matches) != 1:
            raise ValueError("Ambiguous existing natural key")
        original = matches[0]
        for field in PROTECTED & values.keys():
            if values[field] != original[field]:
                raise ValueError("A desired operation would change publication or review state")
        changed = {
            k: v for k, v in values.items() if k in ALLOWED.get(name, set()) and original[k] != v
        }
        if changed:
            table = TABLES[name]
            pk = {c.name: original[c.name] for c in table.primary_key}
            operations.append(
                {
                    "table": name,
                    "action": "update",
                    "key": pk,
                    "expected": copy.deepcopy(original),
                    "values": changed,
                }
            )
    return {
        "schema_version": 1,
        "revision_id": revision_id,
        "baseline_sha256": digest(baseline),
        "desired_bundle_sha256": digest(bundle.model_dump()),
        "operations": operations,
    }


def execute_updates(connection, baseline, plan, *, rehearsal=False):
    """Caller owns commit/rollback. Every expected row is locked before any write."""
    if digest(baseline) != plan["baseline_sha256"]:
        raise ValueError("The saved baseline does not match this update plan")
    current = snapshot(connection, lock=True)
    if current != baseline:
        raise ValueError("Live educational data changed since preflight; transaction aborted")
    require_private(current)
    expected_after = copy.deepcopy(baseline)
    updated = {}
    for op in plan["operations"]:
        name = op["table"]
        if name not in ALLOWED:
            raise ValueError("Table outside editorial update allowlist")
        table = TABLES[name]
        if op["action"] == "insert_reading":
            if (
                name != "kanji_readings"
                or op["key"].get("kind") != "on"
                or op["key"].get("reading") != "せい"
            ):
                raise ValueError("Unexpected insert")
            glyph = next(r for r in baseline["kanjis"] if r["id"] == op["key"]["kanji_id"])
            if glyph["character"] != "靖":
                raise ValueError("Unexpected reading target")
            values = {**op["key"], **op["values"]}
            if rehearsal:
                # PostgreSQL sequences do not roll back. Use a temporary negative
                # ID so rehearsal cannot consume an identity sequence value.
                values["id"] = -1
            new_id = connection.execute(
                insert(table).values(**values).returning(table.c.id)
            ).scalar_one()
            expected_after[name].append({"id": new_id, **op["key"], **op["values"]})
        else:
            if op["action"] != "update" or not set(op["values"]).issubset(ALLOWED[name]):
                raise ValueError("Unexpected field in editorial update")
            matches = [
                r for r in expected_after[name] if all(r[k] == v for k, v in op["key"].items())
            ]
            if len(matches) != 1 or matches[0] != op["expected"]:
                raise ValueError("Per-record expected-original guard failed")
            predicates = [table.c[k] == v for k, v in op["key"].items()]
            result = connection.execute(update(table).where(*predicates).values(**op["values"]))
            if result.rowcount != 1:
                raise ValueError("Guarded update did not affect exactly one row")
            matches[0].update(op["values"])
        updated[name] = updated.get(name, 0) + 1
    after = snapshot(connection)
    for name in expected_after:
        expected_after[name].sort(key=lambda r: tuple(r[c.name] for c in TABLES[name].primary_key))
    if normalized(expected_after) != after:
        raise ValueError("Post-update database does not match the complete expected projection")
    require_private(after)
    return {
        "updated_records_by_table": updated,
        "after_sha256": digest(after),
        "after_counts": {t: len(rows) for t, rows in after.items()},
        "all_publication_states_preserved": True,
        "user_tables_touched": False,
    }
