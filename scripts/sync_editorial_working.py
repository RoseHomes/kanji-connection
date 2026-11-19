"""Preflight, rehearse, commit or verify a guarded private educational revision."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from sqlalchemy import text

from app.book_bundle import Bundle
from app.config import Settings
from app.content_revision import WORKING_RELATIVE, digest, pointer_get
from app.database import create_database_engine
from app.editorial_sync import (
    execute_updates,
    prepare_updates,
    require_private,
    snapshot,
)
from app.json_content import SOURCE_RELATIVE, load_dataset

FOLDER = ROOT / "private/editorial-sync/2026-11-19-final-v2"
WORKING = ROOT / WORKING_RELATIVE


def load(path):
    return json.loads(path.read_bytes())


def save(name, data):
    FOLDER.mkdir(parents=True, exist_ok=True)
    (FOLDER / name).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def check_sources():
    manifest = load(WORKING / "manifest.json")
    if load_dataset(ROOT / SOURCE_RELATIVE).source_files != manifest["source_files"]:
        raise ValueError("Extraction differs from the working revision manifest")
    bundle = Bundle.model_validate_json((WORKING / "working-bundle.json").read_bytes())
    if digest(bundle.model_dump()) != manifest["bundle_sha256"]:
        raise ValueError("Working bundle differs from its manifest")
    return manifest, bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "rehearse", "apply", "verify"])
    args = parser.parse_args()
    manifest, bundle = check_sources()
    settings = Settings()
    if settings.enable_user_writes:
        raise ValueError("Keep production account writes disabled")
    engine = create_database_engine(settings)
    try:
        if args.mode == "prepare":
            if (FOLDER / "plan.json").exists():
                raise ValueError(
                    "A guarded plan already exists; do not replace its expected values"
                )
            with engine.connect() as c:
                c.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                )
                baseline = snapshot(c)
                c.rollback()
            # Bind both the final reviewed database snapshot and every specific
            # expected-original in the correction plan before preparing a write.
            reviewed = load(ROOT / "private/final-correction-plan/live-database.json")[
                "tables"
            ]
            if baseline != reviewed:
                raise ValueError(
                    "Live database differs from the final reviewed expected-original snapshot"
                )
            for change in load(
                ROOT / "private/final-correction-plan/proposed-changes.json"
            ):
                for target in change["database_targets"]:
                    row = next(
                        r
                        for r in baseline[target["table"]]
                        if r.get("id") == target["id"]
                    )
                    if pointer_get(row, target["pointer"]) != target["original"]:
                        raise ValueError(
                            "Final plan per-field expected-original mismatch"
                        )
            plan = prepare_updates(baseline, bundle, manifest["revision_id"])
            save("baseline.json", baseline)
            save("plan.json", plan)
            print(
                json.dumps(
                    {
                        "prepared": True,
                        "guarded_operations": len(plan["operations"]),
                        "database_writes": 0,
                    }
                )
            )
        elif args.mode in {"rehearse", "apply"}:
            baseline, plan = load(FOLDER / "baseline.json"), load(FOLDER / "plan.json")
            if plan["desired_bundle_sha256"] != digest(bundle.model_dump()):
                raise ValueError("Bundle changed after update preflight")
            if args.mode == "apply" and not (FOLDER / "rehearsal.json").exists():
                raise ValueError("A successful rollback rehearsal is required")
            if (FOLDER / "committed.json").exists():
                raise ValueError("Revision is already committed; use verify")
            with engine.connect() as c:
                tx = c.begin()
                try:
                    c.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
                    c.execute(text("SET LOCAL lock_timeout='10s'"))
                    c.execute(text("SET LOCAL statement_timeout='30s'"))
                    c.execute(text("SELECT pg_advisory_xact_lock(73911, 30)"))
                    result = execute_updates(
                        c, baseline, plan, rehearsal=args.mode == "rehearse"
                    )
                    if args.mode == "apply":
                        tx.commit()
                    else:
                        tx.rollback()
                except BaseException:
                    tx.rollback()
                    raise
            if args.mode == "rehearse":
                with engine.connect() as c:
                    c.execute(text("SET TRANSACTION READ ONLY"))
                    if snapshot(c) != baseline:
                        raise ValueError(
                            "Rehearsal did not leave the original data intact"
                        )
                    c.rollback()
                result["rolled_back_and_baseline_verified"] = True
            else:
                result["committed"] = True
            result.update(
                revision_id=manifest["revision_id"], source_files_unchanged=True
            )
            save(
                "rehearsal.json" if args.mode == "rehearse" else "committed.json",
                result,
            )
            print(json.dumps(result))
        else:
            committed = load(FOLDER / "committed.json")
            with engine.connect() as c:
                c.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                )
                actual = snapshot(c)
                require_private(actual)
                if digest(actual) != committed["after_sha256"]:
                    raise ValueError(
                        "Fresh connection verification differs from committed content"
                    )
                # Idempotence: the same desired bundle must now require no writes.
                if prepare_updates(actual, bundle, manifest["revision_id"])[
                    "operations"
                ]:
                    raise ValueError("Desired source and database projections differ")
                c.rollback()
            result = {
                "fresh_connection_verified": True,
                "all_30_chapters_synchronized": True,
                "desired_bundle_requires_zero_further_writes": True,
                "source_files_unchanged": True,
                "account_writes_enabled": False,
                "counts": {name: len(rows) for name, rows in actual.items()},
            }
            save("verified.json", result)
            print(json.dumps(result))
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - redact SQL/credentials at the CLI boundary
        # Never echo connection strings, SQL parameters, .env values or credentials.
        print(
            json.dumps(
                {
                    "stopped": True,
                    "error_type": type(exc).__name__,
                    "reason": str(exc)
                    if type(exc) is ValueError
                    else "Database details suppressed",
                }
            )
        )
        raise SystemExit(1) from None
