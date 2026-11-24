"""Publish the accepted Kanji Connection MP3s and export a lesson playback index."""

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener

from generate_voicevox_audio import OUTPUT, ROOT, VOICE, NoRedirect, hiragana, read_json
from prepare_japanese_audio_release import ATTRIBUTION, save_json

BUCKET = "kanji-japanese-audio"
LIMIT = 1024 * 1024
PREFIX = "ja/metan-normal"
INDEX = ROOT / "frontend/public/japanese-audio/index.json"
TYPES = {
    "kanji_on": "kanji",
    "kanji_kun": "kanji",
    "component_name": "component",
    "vocabulary": "word",
    "phrase": "word",
    "proper_name": "word",
    "sentence": "sentence",
}


def checksum(data):
    return hashlib.sha256(data).hexdigest()


def lookup_key(kind, text, reading):
    normalized = hiragana(reading.strip()).replace(".", "")
    return checksum(f"{kind}\x1f{text.strip()}\x1f{normalized}".encode())[:32]


def prepare(manifest_path, mapping_path):
    manifest = read_json(manifest_path)
    mapping = read_json(mapping_path)
    if (
        mapping["manifest_sha256"] != checksum(manifest_path.read_bytes())
        or manifest["voice"] != VOICE
        or mapping["voice"] != VOICE
        or manifest["edition"] != mapping["edition"]
        or mapping["attribution"] != ATTRIBUTION
    ):
        raise ValueError("Mapping, production manifest or speaker identity mismatch")
    if {row["id"] for row in manifest["assets"]} != {
        row["audio_id"] for row in mapping["assets"]
    }:
        raise ValueError("Manifest and mapping have different audio IDs")
    files = {}
    for asset in mapping["assets"]:
        audio_id, web = asset["audio_id"], asset["web"]
        if (
            audio_id in files
            or not re.fullmatch(r"wav-[a-f0-9]{24}", audio_id)
            or not web
            or web["path"] != f"mp3/{audio_id}.mp3"
            or not re.fullmatch(r"[a-f0-9]{64}", web["sha256"])
        ):
            raise ValueError(f"Incomplete or invalid web asset: {audio_id}")
        source = manifest_path.parent / web["path"]
        data = source.read_bytes()
        if (
            len(data) != web["bytes"]
            or not 0 < len(data) <= LIMIT
            or checksum(data) != web["sha256"]
        ):
            raise ValueError(f"Local MP3 integrity mismatch: {audio_id}")
        files[audio_id] = (
            f"{PREFIX}/{audio_id}/{web['sha256']}.mp3",
            source,
            web["sha256"],
        )

    lessons = {}
    for row in mapping["content"]:
        kind = TYPES.get(row["type"])
        if not kind or row["reading_status"] != "ready_for_preview":
            continue
        audio_id = row["audio_id"]
        if audio_id not in files:
            raise ValueError(f"Unknown lesson audio ID: {audio_id}")
        key = lookup_key(kind, row["text"], row["verified_reading"])
        for ref in row["references"]:
            if ref["table"] == "quiz_questions":
                continue
            lesson = lessons.setdefault(ref["lesson_slug"], {})
            if lesson.setdefault(key, audio_id) != audio_id:
                raise ValueError(f"Conflicting playback keys in {ref['lesson_slug']}")

    media = {audio_id for lesson in lessons.values() for audio_id in lesson.values()}
    index = {
        "version": 1,
        "bucket": BUCKET,
        "attribution": ATTRIBUTION,
        "lessons": lessons,
        "files": {key: files[key][0] for key in sorted(media)},
    }
    return files, index


def project_origin(value):
    url = urlsplit(value)
    if (
        url.scheme != "https"
        or not re.fullmatch(r"[a-z0-9]+\.supabase\.co", url.netloc)
        or url.path not in {"", "/"}
        or url.query
        or url.fragment
    ):
        raise ValueError("Use an exact HTTPS Supabase project origin")
    return value.rstrip("/")


def local_setting(path, name):
    if path.is_file():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            key, separator, value = line.partition("=")
            if separator and key.strip() == name:
                return value.strip().strip("\"'")
    return None


def privileged_key(key, origin):
    if key.startswith("sb_secret_"):
        return key
    try:
        payload = key.split(".")[1]
        claims = json.loads(
            base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        )
        if (
            claims["role"] == "service_role"
            and claims["ref"] == urlsplit(origin).hostname.split(".")[0]
        ):
            return key
    except (ValueError, KeyError, IndexError):
        pass
    raise ValueError("Use the configured project's server-side Storage secret key")


class Storage:
    def __init__(self, origin, key=None):
        self.base = project_origin(origin) + "/storage/v1"
        self.opener = build_opener(NoRedirect())
        self.auth = {"apikey": key} if key else {}
        if key and not key.startswith("sb_secret_"):
            self.auth["Authorization"] = f"Bearer {key}"

    def request(self, path, *, data=None, headers=None, missing=False):
        for attempt in range(3):
            try:
                req = Request(self.base + path, data=data, headers=headers or {})
                with self.opener.open(req, timeout=20) as response:
                    return response.read(LIMIT + 65536), response.headers
            except HTTPError as exc:
                with exc:
                    code = exc.code
                    # Supabase may return HTTP 400 with a structured 404 for missing public objects.
                    try:
                        detail = json.loads(exc.read(2048))
                    except (ValueError, UnicodeError):
                        detail = {}
                embedded = (
                    str(detail.get("statusCode", ""))
                    if isinstance(detail, dict)
                    else ""
                )
                if missing and (code == 404 or (code == 400 and embedded == "404")):
                    return None, None
                if code not in {408, 429, 500, 502, 503, 504} or attempt == 2:
                    raise ValueError(f"Storage HTTP {code} for {path}") from None
            except (OSError, URLError) as exc:
                if attempt == 2:
                    raise ValueError(
                        f"Storage request failed for {path}: {type(exc).__name__}"
                    ) from None
            time.sleep(2**attempt)

    def ensure_bucket(self):
        path = f"/bucket/{BUCKET}"
        data, _ = self.request(path, headers=self.auth)
        bucket = json.loads(data)
        if (
            bucket.get("public") is not True
            or bucket.get("allowed_mime_types") != ["audio/mpeg"]
            or bucket.get("file_size_limit") != LIMIT
        ):
            raise ValueError(
                "Existing bucket differs from the expected public MP3 configuration"
            )

    def verify(self, audio_id, file, upload):
        path, source, expected = file
        public = f"/object/public/{BUCKET}/{path}"
        data, headers = self.request(public, missing=True)
        status = "verified_existing"
        if data is None and upload:
            upload_data = source.read_bytes()
            if checksum(upload_data) != expected:
                raise ValueError(f"Local MP3 changed after preflight: {audio_id}")
            try:
                self.request(
                    f"/object/{BUCKET}/{path}",
                    data=upload_data,
                    headers={
                        **self.auth,
                        "Content-Type": "audio/mpeg",
                        "Cache-Control": "max-age=31536000, immutable",
                        "x-upsert": "false",
                    },
                )
                status = "uploaded"
            except ValueError:
                # A prior request may have succeeded before timing out. Only accept matching bytes.
                data, headers = self.request(public, missing=True)
                if data is None:
                    raise
            for attempt in range(3):
                if data is not None:
                    break
                data, headers = self.request(public, missing=True)
                if data is None and attempt < 2:
                    time.sleep(2**attempt)
        if data is None:
            return {
                "audio_id": audio_id,
                "status": "missing",
                "url": self.base + public,
            }
        if checksum(data) != expected or headers.get_content_type() != "audio/mpeg":
            raise ValueError(f"Public bytes or media type do not match for {audio_id}")
        return {
            "audio_id": audio_id,
            "status": status,
            "url": self.base + public,
            "bytes": len(data),
            "sha256": expected,
        }


def write_index(path, index):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if read_json(path) == index:
            return
        raise ValueError(
            f"Index already exists with different contents. Choose a new path: {path}"
        )
    save_json(path, index)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "upload", "verify"])
    parser.add_argument(
        "--manifest", type=Path, default=OUTPUT / "production-manifest.json"
    )
    parser.add_argument("--mapping", type=Path, default=OUTPUT / "release/mapping.json")
    parser.add_argument(
        "--origin",
        default=os.environ.get("SUPABASE_URL")
        or local_setting(ROOT / "backend/.env", "SUPABASE_URL"),
    )
    parser.add_argument("--index", type=Path)
    parser.add_argument(
        "--report", type=Path, default=OUTPUT / f"storage-{time.time_ns()}.jsonl"
    )
    args = parser.parse_args()
    files, index = prepare(args.manifest, args.mapping)
    if args.mode == "prepare":
        write_index(args.index or OUTPUT / "playback-index-preview.json", index)
        print(
            f"Local preflight passed for {len(files)} MP3s and {len(index['lessons'])} lessons."
        )
        return 0
    key = None
    if args.mode == "upload":
        key = os.environ.get("SUPABASE_STORAGE_SECRET_KEY") or local_setting(
            OUTPUT / ".env.storage", "SUPABASE_STORAGE_SECRET_KEY"
        )
    if not args.origin or (args.mode == "upload" and not key):
        raise ValueError(
            "Set SUPABASE_URL and, for upload, SUPABASE_STORAGE_SECRET_KEY in the local shell"
        )
    storage = Storage(args.origin, privileged_key(key, args.origin) if key else None)
    if key:
        storage.ensure_bucket()
    failures = 0
    with (
        args.report.open("x", encoding="utf-8") as log,
        ThreadPoolExecutor(max_workers=6) as pool,
    ):

        def transfer(entry):
            audio_id, file = entry
            try:
                return storage.verify(audio_id, file, bool(key))
            except ValueError as exc:
                return {"audio_id": audio_id, "status": "failed", "error": str(exc)}

        for number, result in enumerate(pool.map(transfer, files.items()), 1):
            log.write(json.dumps(result) + "\n")
            log.flush()
            failures += result["status"] in {"missing", "failed"}
            if number % 25 == 0 or number == len(files):
                print(
                    f"{number}/{len(files)} checked, {failures} unavailable or failed",
                    flush=True,
                )
    if not failures:
        write_index(args.index or INDEX, index)
    print(
        f"Verified {len(files) - failures}/{len(files)} public MP3 objects. Report {args.report}"
    )
    return int(bool(failures))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as exc:
        sys.exit(f"Japanese audio Storage: {exc}")
