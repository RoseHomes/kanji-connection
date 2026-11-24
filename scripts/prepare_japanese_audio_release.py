"""Apply reviewed reading decisions and package the local VOICEVOX library."""

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import time
import wave
from array import array
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from generate_voicevox_audio import (
    OUTPUT,
    VOICE,
    audio_id,
    pronunciation,
    read_json,
    validate_wav,
    write_wav,
)

ATTRIBUTION = "VOICEVOX:四国めたん"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def save_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def resolve(baseline, decisions_path, override_path, output):
    manifest = read_json(baseline)
    decisions = read_json(decisions_path)
    if sha256(baseline.read_bytes()) != decisions["baseline_sha256"]:
        raise ValueError("Reading review belongs to a different baseline manifest")
    items = {row["id"]: row for row in manifest["content"]}
    assets = {row["id"]: row for row in manifest["assets"]}
    reviewed = decisions["items"]
    held = {key for key, row in items.items() if row["status"] == "needs_manual_review"}
    if len(reviewed) != len(held) or {row["content_id"] for row in reviewed} != held:
        raise ValueError(
            "Reading decisions must cover each held content ID exactly once"
        )

    report = []
    for decision in reviewed:
        item = items[decision["content_id"]]
        original_reason = item["review_reason"]
        state = decision["disposition"]
        item["reading_review"] = {
            k: v for k, v in decision.items() if k != "content_id"
        }
        item["evidence"].extend(
            e for e in decision["evidence"] if e not in item["evidence"]
        )
        item["verified_reading"] = decision["reading"]
        if state == "playable":
            spoken = decision.get("spoken_reading", decision["reading"])
            asset_id = audio_id(spoken)
            asset = assets.setdefault(
                asset_id,
                {
                    "id": asset_id,
                    "input": spoken,
                    "expected_reading": spoken,
                    "path": f"wav/{asset_id}.wav",
                    "status": "ready_for_preview",
                    "content_ids": [],
                },
            )
            if (
                asset["status"] != "ready_for_preview"
                or asset["expected_reading"] != spoken
            ):
                raise ValueError(f"Cannot merge incompatible reading into {asset_id}")
            asset["content_ids"].append(item["id"])
            item.update(
                status="ready_for_preview",
                audio_id=asset_id,
                input=asset["input"],
                path=asset["path"],
            )
        elif state == "contextual":
            target = items[decision["context_content_id"]]
            chapters = set(decision["context_chapters"])
            if (
                target["status"] != "ready_for_preview"
                or not chapters
                or not chapters <= {ref["chapter"] for ref in target["references"]}
            ):
                raise ValueError(f"Invalid example target for {item['id']}")
            item.update(
                status="contextual_audio",
                audio_id=target["audio_id"],
                input=target["input"],
                path=target["path"],
            )
            assets[target["audio_id"]]["content_ids"].append(item["id"])
        elif state == "reference_only":
            item["status"] = "reference_only"
        elif state != "unresolved" or decision["reading"] is not None:
            raise ValueError(f"Unexpected reading disposition: {state}")
        if state != "unresolved":
            item["review_reason"] = None
        report.append(
            {
                "content_id": item["id"],
                "type": item["type"],
                "text": item["text"],
                "original_issue": original_reason,
                "references": item["references"],
                "audio_id": item["audio_id"],
                "status": item["status"],
                **decision,
            }
        )

    if override_path:
        seen = set()
        for override in read_json(override_path):
            asset = assets[override["audio_id"]]
            if (
                asset["input"] != override["input"]
                or asset["id"] in seen
                or not override["reason"]
            ):
                raise ValueError(f"Invalid engine query override for {asset['id']}")
            seen.add(asset["id"])
            asset["query_text"] = override["query_text"]
            asset["query_note"] = override["reason"]

    manifest["assets"] = sorted(assets.values(), key=lambda asset: asset["id"])
    statuses = Counter(item["status"] for item in items.values())
    manifest["counts"].update(
        ready_for_preview=statuses["ready_for_preview"],
        contextual_audio=statuses["contextual_audio"],
        reference_only=statuses["reference_only"],
        manual_review=statuses["needs_manual_review"],
        ready_audio_assets=len(assets),
        review_reasons=dict(
            Counter(
                item["review_reason"]
                for item in items.values()
                if item["review_reason"]
            )
        ),
    )
    manifest["reading_review"] = {
        "decisions_sha256": sha256(decisions_path.read_bytes()),
        "original_rows": len(report),
        "dispositions": dict(Counter(row["disposition"] for row in report)),
    }
    manifest["attribution"] = ATTRIBUTION
    save_json(output, manifest)
    save_json(output.with_suffix(".review.json"), report)
    with output.with_suffix(".review.csv").open(
        "x", encoding="utf-8-sig", newline=""
    ) as stream:
        columns = [
            "content_id",
            "type",
            "text",
            "chapters",
            "source_readings",
            "original_issue",
            "reading",
            "spoken_reading",
            "classification",
            "disposition",
            "status",
            "audio_id",
            "context_content_id",
            "context_chapters",
            "resolution",
            "evidence",
        ]
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in report:
            writer.writerow(
                {
                    **row,
                    "chapters": ", ".join(
                        map(str, sorted({ref["chapter"] for ref in row["references"]}))
                    ),
                    "source_readings": " / ".join(
                        sorted(
                            {ref["supplied_reading"] or "" for ref in row["references"]}
                        )
                    ),
                    "evidence": json.dumps(row["evidence"], ensure_ascii=False),
                }
            )
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))


def read_generation_logs(paths):
    records = defaultdict(list)
    for path in paths:
        with path.open(encoding="utf-8") as stream:
            run = json.loads(next(stream))
            if run["event"] != "run" or any(
                run["engine"].get(key) != value for key, value in VOICE.items()
            ):
                raise ValueError(f"Unexpected voice or run header in {path}")
            for line in stream:
                row = json.loads(line)
                records[row["audio_id"]].append(
                    {**row, "run": path.name, "engine": run["engine"]}
                )
    return records


def ffmpeg(executable, *args):
    return subprocess.run(
        [executable, "-hide_banner", "-loglevel", "error", "-nostdin", *args],
        check=True,
        capture_output=True,
        timeout=60,
    ).stdout


def inspect_mp3(executable, path, wav_path, wav):
    pcm = ffmpeg(executable, "-xerror", "-i", str(path), "-f", "s16le", "-")
    frames = len(pcm) // (2 * wav["channels"])
    if frames != wav["frames"] or not any(pcm):
        raise ValueError(
            f"MP3 PCM frames {frames} do not match source WAV {wav['frames']}"
        )
    with wave.open(str(wav_path), "rb") as stream:
        original = array("h", stream.readframes(frames))[::8]
    decoded = array("h", pcm)[::8]
    cross_power = sum(a * b for a, b in zip(original, decoded, strict=True))
    scale = (sum(a * a for a in original) * sum(b * b for b in decoded)) ** 0.5
    similarity = cross_power / scale if scale else 0
    if similarity < 0.9:
        raise ValueError(
            f"MP3 waveform differs from the source WAV (correlation {similarity:.3f})"
        )
    data = path.read_bytes()
    return {
        "bytes": len(data),
        "sha256": sha256(data),
        "decoded_frames": frames,
        "waveform_correlation": round(similarity, 6),
    }


def package_clip(asset, base, executable, records):
    result = {
        "audio_id": asset["id"],
        "input": asset["input"],
        "query_text": asset.get("query_text", asset["input"]),
        "wav": None,
        "web": None,
        "generation_status": "missing",
        "pronunciation_review": "pending",
    }
    try:
        expected_id = audio_id(asset["input"])
        if asset["id"] != expected_id or asset["path"] != f"wav/{expected_id}.wav":
            raise ValueError("Invalid WAV path or synthesis identity")
        wav_path = base / asset["path"]
        wav = validate_wav(wav_path.read_bytes())
        source = next(
            (
                row
                for row in reversed(records)
                if row["status"] == "generated"
                and row["sha256"] == wav["sha256"]
                and row["path"] == asset["path"]
                and row.get("query_text", row["input"]) == result["query_text"]
                and pronunciation(row["engine_moras"])
                == pronunciation(asset["expected_reading"])
            ),
            None,
        )
        if source is None:
            raise ValueError(
                "WAV lacks a matching generation record, engine moras, and SHA-256"
            )
        result["wav"] = {
            "path": asset["path"],
            **wav,
            "engine_moras": source["engine_moras"],
            "generated_in": source["run"],
            "engine_version": source["engine"]["engine_version"],
        }
        result["generation_status"] = (
            "reused_sample"
            if source.get("sample") and source["run"] == "sample-run.jsonl"
            else "generated"
        )
        relative_mp3 = f"mp3/{asset['id']}.mp3"
        web_path = base / relative_mp3
        if web_path.exists():
            info = inspect_mp3(executable, web_path, wav_path, wav)
            status = "skipped_existing"
        else:
            # Encode with a seekable WAV and a seekable MP3 so LAME can write its gapless header.
            from tempfile import TemporaryDirectory

            with TemporaryDirectory(dir=web_path.parent) as scratch:
                encoded = Path(scratch) / "clip.mp3"
                ffmpeg(
                    executable,
                    "-i",
                    str(wav_path),
                    "-map_metadata",
                    "-1",
                    "-c:a",
                    "libmp3lame",
                    "-b:a",
                    "64k",
                    str(encoded),
                )
                data = encoded.read_bytes()
                info = inspect_mp3(executable, encoded, wav_path, wav)
                try:
                    write_wav(web_path, data)
                    status = "encoded"
                except FileExistsError:
                    info = inspect_mp3(executable, web_path, wav_path, wav)
                    status = "skipped_existing"
        result["web"] = {
            "path": relative_mp3,
            **info,
            "status": status,
            "content_type": "audio/mpeg",
        }
    except (
        OSError,
        ValueError,
        EOFError,
        wave.Error,
        subprocess.SubprocessError,
    ) as exc:
        message = (
            exc.stderr.decode("utf-8", errors="replace").strip()
            if getattr(exc, "stderr", None)
            else str(exc)
        )
        result["error"] = f"{type(exc).__name__}: {message}"
        if isinstance(exc, FileNotFoundError) and not result["wav"] and records:
            result["last_generation_error"] = next(
                (
                    row.get("error")
                    for row in reversed(records)
                    if row["status"] == "failed"
                ),
                None,
            )
    return result


def package(manifest_path, log_paths, executable, output, workers):
    manifest = read_json(manifest_path)
    if manifest["voice"] != VOICE or manifest["schema_version"] != 1:
        raise ValueError("Unexpected voice or manifest schema")
    records = read_generation_logs(log_paths)
    base = manifest_path.resolve().parent
    (base / "mp3").mkdir(exist_ok=True)
    output.mkdir()
    assets = manifest["assets"]
    results = {}
    with (
        (output / "packaging.jsonl").open("x", encoding="utf-8") as log,
        ThreadPoolExecutor(max_workers=workers) as pool,
    ):
        for index, row in enumerate(
            pool.map(
                lambda asset: package_clip(
                    asset, base, executable, records[asset["id"]]
                ),
                assets,
            ),
            1,
        ):
            results[row["audio_id"]] = row
            log.write(json.dumps(row, ensure_ascii=False) + "\n")
            log.flush()
            if index % 25 == 0 or index == len(assets) or "error" in row:
                print(
                    f"[{index}/{len(assets)}] {row['audio_id']} {row.get('error', '')}",
                    flush=True,
                )
    content = []
    for row in manifest["content"]:
        clip = results.get(row["audio_id"])
        catalog = row.get("catalog", {})
        content.append(
            {
                "content_id": row["id"],
                "audio_id": row["audio_id"],
                "text": row["text"],
                "type": row["type"],
                "verified_reading": row["verified_reading"],
                "reading_status": row["status"],
                "references": row["references"],
                "reading_review": row.get("reading_review"),
                "generation_status": clip["generation_status"]
                if clip
                else "not_scheduled",
                "pronunciation_review": "pending"
                if clip and clip["wav"]
                else "not_available",
                "wav": clip["wav"] if clip else None,
                "web": clip["web"] if clip else None,
                "catalog": {
                    "edition": manifest["edition"]["id"],
                    "categories": catalog.get("categories", []),
                    "jlpt_levels": catalog.get("jlpt_levels", []),
                },
            }
        )
    save_json(
        output / "mapping.json",
        {
            "schema_version": 1,
            "edition": manifest["edition"],
            "voice": VOICE,
            "attribution": ATTRIBUTION,
            "manifest_sha256": sha256(manifest_path.read_bytes()),
            "content": content,
            "assets": list(results.values()),
        },
    )
    with (output / "pronunciation-review.csv").open(
        "x", encoding="utf-8-sig", newline=""
    ) as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "content_id",
                "audio_id",
                "text",
                "verified_reading",
                "chapters",
                "web_path",
                "web_sha256",
                "status",
                "reviewer",
                "reviewed_on",
                "notes",
            ]
        )
        for row in content:
            if not row["web"]:
                continue
            decision = row["reading_review"] or {}
            chapters = decision.get("context_chapters") or sorted(
                {ref["chapter"] for ref in row["references"]}
            )
            writer.writerow(
                [
                    row["content_id"],
                    row["audio_id"],
                    row["text"],
                    row["verified_reading"],
                    ", ".join(map(str, chapters)),
                    row["web"]["path"],
                    row["web"]["sha256"],
                    "pending",
                    "",
                    "",
                    "",
                ]
            )
    eligible = [
        row
        for row in content
        if row["audio_id"] or row["reading_status"] == "needs_manual_review"
    ]
    covered = sum(row["web"] is not None for row in eligible)
    verified = [row for row in eligible if row["audio_id"]]
    failed = [row for row in results.values() if "error" in row]
    unresolved = [
        row["content_id"]
        for row in content
        if row["reading_status"] == "needs_manual_review"
    ]
    unmatched = [
        row["content_id"]
        for row in content
        if not row["references"] or (row["audio_id"] and row["audio_id"] not in results)
    ]
    summary = {
        **manifest["counts"],
        "wav_files": sum(row["wav"] is not None for row in results.values()),
        "web_files": sum(row["web"] is not None for row in results.values()),
        "wav_file_statuses": dict(
            Counter(row["generation_status"] for row in results.values())
        ),
        "wav_bytes": sum(row["wav"]["bytes"] for row in results.values() if row["wav"]),
        "web_bytes": sum(row["web"]["bytes"] for row in results.values() if row["web"]),
        "coverage_content_with_web_audio": covered,
        "coverage_denominator_excluding_reference_only": len(eligible),
        "coverage_percent": round(100 * covered / len(eligible), 4),
        "verified_playback_items": len(verified),
        "verified_playback_coverage_percent": round(100 * covered / len(verified), 4),
        "all_inventory_coverage_percent": round(100 * covered / len(content), 4),
        "unresolved_content_ids": unresolved,
        "assets_with_errors": failed,
        "unmatched_content_ids": unmatched,
        "human_approved": 0,
        "ffmpeg": subprocess.check_output(
            [executable, "-version"], text=True
        ).splitlines()[0],
    }
    save_json(output / "audit.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return bool(failed or unmatched)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    review = modes.add_parser("resolve")
    review.add_argument("--baseline", type=Path, default=OUTPUT / "manifest.json")
    review.add_argument("--decisions", type=Path, required=True)
    review.add_argument("--overrides", type=Path)
    review.add_argument("--output", type=Path, required=True)
    encode = modes.add_parser("package")
    encode.add_argument("--manifest", type=Path, required=True)
    encode.add_argument("--log", type=Path, action="append", required=True)
    encode.add_argument("--ffmpeg", default="ffmpeg")
    encode.add_argument("--workers", type=int, default=4)
    encode.add_argument(
        "--output", type=Path, default=OUTPUT / f"release-{time.time_ns()}"
    )
    args = parser.parse_args()
    if args.mode == "resolve":
        resolve(args.baseline, args.decisions, args.overrides, args.output)
        return 0
    if args.workers < 1:
        parser.error("--workers must be positive")
    return int(package(args.manifest, args.log, args.ffmpeg, args.output, args.workers))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        sys.exit(f"Audio release: {exc}")
