"""Prepare, rehearse or explicitly stage a learning import on loopback PostgreSQL."""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Literal

from alembic import command
from alembic.config import Config
from pydantic import Field
from sqlalchemy import create_engine, insert, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.content_revision import digest
from app.editorial_sync import TABLES as BOOK_TABLES
from app.editorial_sync import normalized
from app.expansion_import import SHA, ImportPlan, Model, apply_plan
from app.learning_paths import list_paths
from app.models import Base
from jlpt_n5_reference import fetch_sources, load_reference
from prepare_jlpt_n5 import prepare, read_baseline, write_json

EXPANSION = frozenset(
    (
        "example_sentences",
        "jlpt_reference_releases",
        "jlpt_assignments",
        "learning_paths",
        "learning_units",
        "learning_path_items",
    )
)
CATALOG = frozenset(BOOK_TABLES) | EXPANSION
BOOK_LAYOUT = {
    "lessons",
    "lesson_sections",
    "lesson_kanjis",
    "lesson_vocabularies",
    "quiz_questions",
}


class Approval(Model):
    plan_sha256: SHA
    reviewer: str = Field(min_length=1, max_length=200)
    decision_reference: str = Field(min_length=1, max_length=1000)
    approved: Literal[True]


def catalog_snapshot(connection, names=CATALOG):
    return normalized(
        {
            table.name: [
                dict(row)
                for row in connection.execute(
                    select(table).order_by(*table.primary_key)
                ).mappings()
            ]
            for table in Base.metadata.sorted_tables
            if table.name in names
        }
    )


def capture(output):
    from app.config import Settings
    from app.database import create_database_engine

    engine = create_database_engine(Settings())
    try:
        with engine.connect() as connection:
            connection.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            )
            connection.execute(text("SET LOCAL statement_timeout = '15s'"))
            revision = connection.scalar(
                text("SELECT version_num FROM public.alembic_version")
            )
            if revision not in {"0002", "0003"}:
                raise ValueError(
                    "Unknown catalog revision; migration is outside capture scope"
                )
            tables = catalog_snapshot(
                connection, CATALOG if revision == "0003" else frozenset(BOOK_TABLES)
            )
    finally:
        engine.dispose()
    path = output / "catalog-snapshot.json"
    if path.exists() and read_baseline(path)["sha256"] != digest(tables):
        raise ValueError(
            "Catalog changed. Use a separate private output directory for a new snapshot"
        )
    write_json(path, {"revision": revision, "sha256": digest(tables), "tables": tables})
    return {"revision": revision, "catalog_sha256": digest(tables), "read_only": True}


def local_engine():
    value = os.environ.get("EXPANSION_TEST_DATABASE_URL")
    if not value:
        raise ValueError(
            "Set EXPANSION_TEST_DATABASE_URL to a dedicated loopback PostgreSQL database"
        )
    url = make_url(value)
    if (
        url.drivername != "postgresql+psycopg"
        or url.host != "127.0.0.1"
        or url.database not in {"kanji_test", "kanji_expansion_dev"}
        or url.query
    ):
        raise ValueError(
            "Only literal 127.0.0.1, PostgreSQL and a dedicated test database name are allowed"
        )
    return create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 5})


def bootstrap(connection, baseline):
    if inspect(connection).get_table_names(schema="public"):
        raise ValueError("Bootstrap and rehearsal require an empty, isolated database")
    config = Config(str(ROOT / "backend/alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "backend/migrations"))
    config.attributes["connection"] = connection
    command.upgrade(config, "0003")
    tables = baseline["tables"]
    for table in Base.metadata.sorted_tables:
        if table.name not in tables or not tables[table.name]:
            continue
        connection.execute(insert(table), tables[table.name])
        if "id" in table.c:
            connection.execute(
                text(
                    "SELECT setval(pg_get_serial_sequence(:table_name, 'id'), :max_id)"
                ),
                {
                    "table_name": f"public.{table.name}",
                    "max_id": max(row["id"] for row in tables[table.name]),
                },
            )


def verify_preserved(before, after, *, baseline_only=False):
    for name in before:
        table = Base.metadata.tables[name]
        keys = [column.name for column in table.primary_key]
        current = {tuple(row[k] for k in keys): row for row in after[name]}
        if any(current.get(tuple(row[k] for k in keys)) != row for row in before[name]):
            raise ValueError(f"Existing rows changed in {name}")
        if name in BOOK_LAYOUT and len(before[name]) != len(after[name]):
            raise ValueError(f"Original book layout changed in {name}")
    if not baseline_only and len(before["lessons"]) != 30:
        raise ValueError("The original 30 lessons must be preserved")


def approve_manifest(approval_path, rehearsal_path, plan_sha, explicit_sha):
    approval = Approval.model_validate_json(approval_path.read_bytes())
    rehearsal = json.loads(rehearsal_path.read_bytes())
    if explicit_sha != plan_sha or approval.plan_sha256 != plan_sha:
        raise ValueError(
            "Explicit approval and decision must match the current manifest SHA-256"
        )
    if (
        rehearsal.get("plan_sha256") != plan_sha
        or rehearsal.get("rolled_back") is not True
        or rehearsal.get("idempotent") is not True
    ):
        raise ValueError("Rehearse the exact manifest successfully before staging")
    return approval


def stage(baseline, plan, inventory, release, *, approval=None, seed_empty=False):
    if (
        plan.catalog_sha256 != baseline["sha256"]
        or not set(baseline["tables"]) <= CATALOG
    ):
        raise ValueError(
            "The plan is tied to a different or unsupported canonical snapshot"
        )
    if not set(BOOK_TABLES) <= set(baseline["tables"]):
        raise ValueError("The catalog snapshot is missing book tables")
    engine = local_engine()
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
                connection.execute(text("SET LOCAL statement_timeout = '60s'"))
                connection.execute(text("SET LOCAL lock_timeout = '5s'"))
                # A catalog-wide local lock also protects shared category placements
                # when two different source versions are staged concurrently.
                connection.execute(text("SELECT pg_advisory_xact_lock(73911, 3005)"))
                if approval is None or seed_empty:
                    bootstrap(connection, baseline)
                elif (
                    connection.scalar(
                        text("SELECT version_num FROM public.alembic_version")
                    )
                    != "0003"
                ):
                    raise ValueError("Local target must already be at revision 0003")
                before = catalog_snapshot(connection)
                verify_preserved(baseline["tables"], before, baseline_only=True)
                with Session(connection) as session:
                    public_before = [
                        p.model_dump() for p in list_paths(session, None, 0, 100)
                    ]
                    first = apply_plan(
                        session, plan, inventory, trusted_release=release
                    )
                    second = apply_plan(
                        session, plan, inventory, trusted_release=release
                    )
                    if second["inserted"] or second["conflicts"]:
                        raise ValueError("Import was not idempotent")
                    if [
                        p.model_dump() for p in list_paths(session, None, 0, 100)
                    ] != public_before:
                        raise ValueError(
                            "Staging unexpectedly changed public catalog projections"
                        )
                    verify_preserved(before, catalog_snapshot(connection))
                if approval is None:
                    transaction.rollback()
                    if inspect(connection).get_table_names(schema="public"):
                        raise RuntimeError(
                            "Rehearsal left persistent application tables"
                        )
                else:
                    transaction.commit()
            except BaseException:
                if transaction.is_active:
                    transaction.rollback()
                raise
    finally:
        engine.dispose()
    return {
        "plan_sha256": digest(plan.model_dump(mode="json")),
        "catalog_sha256": baseline["sha256"],
        "revision_rehearsed": "0003",
        "first": first,
        "repeat": second,
        "idempotent": True,
        "original_lesson_count": 30,
        "original_rows_preserved": True,
        "public_path_projection_unchanged": True,
        "rolled_back": approval is None,
        "approval": approval.model_dump(mode="json") if approval is not None else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "private/jlpt-n5-import")
    parser.add_argument(
        "--jmdict", type=Path, default=ROOT / "private/dictionaries/JMdict_e.gz"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("fetch")
    commands.add_parser(
        "capture-current",
        help="Read-only catalog snapshot using the configured runtime",
    )
    commands.add_parser("prepare")
    dry = commands.add_parser(
        "dry-run",
        help="Migrate empty loopback PostgreSQL, rehearse twice and roll back all DDL/data",
    )
    dry.add_argument("--manifest", type=Path)
    seal = commands.add_parser(
        "seal",
        help="Record explicit approval for a rehearsed manifest, without database changes",
    )
    apply = commands.add_parser(
        "apply", help="Stage a reviewed manifest on loopback PostgreSQL"
    )
    for guarded in (seal, apply):
        guarded.add_argument("--manifest", type=Path, required=True)
        guarded.add_argument("--approval", type=Path, required=True)
        guarded.add_argument("--approve-sha256", required=True)
    apply.add_argument("--bootstrap-empty", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "private").resolve()):
        parser.error(
            "Output must remain inside the project’s ignored private directory"
        )
    output.mkdir(parents=True, exist_ok=True)
    if args.command == "fetch":
        fetch_sources(output / "source")
        return
    if args.command == "capture-current":
        print(json.dumps(capture(output)))
        return
    baseline = read_baseline(output / "catalog-snapshot.json")
    if args.command == "prepare":
        inventory, release, examples = load_reference(output / "source", args.jmdict)
        index = json.loads(
            (ROOT / "frontend/public/assets/japanese-audio-index.json").read_bytes()
        )
        audio_release = json.loads(
            (ROOT / "private/audio-voicevox/release/audit.json").read_bytes()
        )
        print(
            json.dumps(
                prepare(
                    output, baseline, inventory, release, examples, index, audio_release
                )
            )
        )
        return
    plan = ImportPlan.model_validate_json(
        (args.manifest or output / "import-manifest.json").read_bytes()
    )
    sha = digest(plan.model_dump(mode="json"))
    rehearsal_file = output / f"dry-run-{sha}.json"
    approval = None
    if args.command in {"seal", "apply"}:
        approval = approve_manifest(
            args.approval, rehearsal_file, sha, args.approve_sha256
        )
    inventory, release = [], None
    if plan.reference is not None:
        inventory, release, _ = load_reference(output / "source", args.jmdict)
    if args.command == "seal":
        if plan.catalog_sha256 != baseline["sha256"] or (
            plan.reference and plan.reference != release
        ):
            raise ValueError("The reviewed plan refers to different source inputs")
        write_json(
            output / f"approved-{sha}.manifest.json", plan.model_dump(mode="json")
        )
        write_json(
            output / f"approved-{sha}.decision.json", approval.model_dump(mode="json")
        )
        print(json.dumps({"approved_plan_sha256": sha, "database_writes": 0}))
        return
    receipt = stage(
        baseline,
        plan,
        inventory,
        release,
        approval=approval,
        seed_empty=getattr(args, "bootstrap_empty", False),
    )
    write_json(output / f"apply-{sha}.json" if approval else rehearsal_file, receipt)
    if not approval:
        write_json(output / "dry-run-results.json", receipt)
    print(json.dumps(receipt))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as exc:
        raise SystemExit(f"Stopped: {exc}") from None
