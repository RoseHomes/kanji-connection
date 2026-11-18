"""Caller-owned insert-only importer. No credentials, engine creation or commits here."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .book_bundle import Bundle
from .models import Base

MODELS = {mapper.local_table.name: mapper.class_ for mapper in Base.registry.mappers}


def apply_bundle(session: Session, bundle: Bundle):
    """Insert missing rows; return conflicts instead of updating editorial fields."""
    if bundle.publication_approved:
        raise ValueError("This importer only prepares private needs_review material")
    # Preflight the entire plan before inserting anything. Link rows carry no
    # publication fields; content rows must retain their generated review state.
    identities = set()
    import json

    for op in bundle.operations:
        if op["table"] not in MODELS or op["table"] in {
            "user_progress",
            "review_items",
            "quiz_attempts",
        }:
            raise ValueError("Book import cannot touch user data or unknown tables")
        values = {**op["key"], **op["values"]}
        columns = MODELS[op["table"]].__table__.columns
        identity = (op["table"], json.dumps(op["key"], sort_keys=True))
        if identity in identities:
            raise ValueError("Duplicate import natural key")
        identities.add(identity)
        if not op["key"] or set(op["key"]) & set(op["values"]):
            raise ValueError("Invalid or overlapping import key")
        for field, value in values.items():
            if field not in columns:
                raise ValueError("Unknown import field")
            maximum = getattr(columns[field].type, "length", None)
            if isinstance(value, str) and maximum and len(value) > maximum:
                raise ValueError("Import string exceeds PostgreSQL column length")
        for field in ("status", "review_status"):
            if field in columns and values.get(field) != "needs_review":
                raise ValueError("Book content must remain needs_review")
        if "access_tier" in columns and values.get("access_tier") != "private":
            raise ValueError("Book content must remain private")
        if "catalog_visible" in columns and values.get("catalog_visible") is not False:
            raise ValueError("Book lessons cannot be catalog-visible")
    inserted = {}
    skipped = {}
    conflicts = []
    cache = {}
    operations = sorted(
        bundle.operations,
        key=lambda op: [t.name for t in Base.metadata.sorted_tables].index(op["table"]),
    )

    def resolve(value):
        if not isinstance(value, dict) or "$ref" not in value:
            return value
        spec = value["$ref"]
        key = {k: resolve(v) for k, v in spec["key"].items()}
        identity = (spec["table"], tuple(sorted(key.items())))
        row = cache.get(identity)
        if row is None:
            model = MODELS[spec["table"]]
            row = session.scalar(select(model).filter_by(**key))
        if row is None:
            raise ValueError(f"Unresolved foreign key in {spec['table']}")
        return getattr(row, spec["column"])

    for op in operations:
        model = MODELS[op["table"]]
        if op["table"] in {"user_progress", "review_items", "quiz_attempts"}:
            raise ValueError("Book import cannot touch user data")
        key = {k: resolve(v) for k, v in op["key"].items()}
        values = {k: resolve(v) for k, v in op["values"].items()}
        identity = (op["table"], tuple(sorted(key.items())))
        row = session.scalar(select(model).filter_by(**key))
        if row is None:
            row = model(**key, **values)
            session.add(row)
            session.flush()
            inserted[op["table"]] = inserted.get(op["table"], 0) + 1
        else:
            skipped[op["table"]] = skipped.get(op["table"], 0) + 1
            differences = [field for field, value in values.items() if getattr(row, field) != value]
            if differences:
                conflicts.append(
                    {
                        "table": op["table"],
                        "key": key,
                        "fields": differences,
                        "action": "preserved_existing_record",
                    }
                )
        cache[identity] = row
    return {"inserted": inserted, "skipped": skipped, "conflicts": conflicts}
