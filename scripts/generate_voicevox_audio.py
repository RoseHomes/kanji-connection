"""Generate local VOICEVOX WAVs from a Kanji Connection audio manifest."""

import argparse
import hashlib
import io
import ipaddress
import json
import re
import struct
import sys
import time
import unicodedata
import wave
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "private/audio-voicevox"
ENGINE = "http://127.0.0.1:50021"
VOICE = {
    "name": "四国めたん",
    "style": "ノーマル",
    "speaker_style_id": 2,
    "speaker_uuid": "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff",
}


def read_json(path):
    return json.loads(path.read_bytes())


def audio_id(text):
    return (
        "wav-"
        + hashlib.sha256(
            f"voicevox:{VOICE['speaker_uuid']}:2:{text}".encode()
        ).hexdigest()[:24]
    )


def hiragana(value):
    return "".join(
        chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c
        for c in unicodedata.normalize("NFC", value)
    )


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Engine:
    def __init__(self, origin, timeout=90, attempts=3):
        url = urlsplit(origin)
        local = url.hostname == "localhost" or (
            url.hostname and ipaddress.ip_address(url.hostname).is_loopback
        )
        if (
            url.scheme != "http"
            or not local
            or not url.port
            or url.username
            or url.password
            or url.path not in {"", "/"}
            or url.query
            or url.fragment
        ):
            raise ValueError("Use a loopback HTTP engine origin with an explicit port")
        self.origin = origin.rstrip("/")
        self.timeout = timeout
        self.attempts = attempts
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def request(self, path, *, params=None, body=None, post=False):
        url = self.origin + path + ("?" + urlencode(params) if params else "")
        request = Request(url, method="POST" if post else "GET")
        if body is not None:
            request.data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            request.add_header("Content-Type", "application/json")
        for attempt in range(1, self.attempts + 1):
            try:
                with self.opener.open(request, timeout=self.timeout) as response:
                    return response.read()
            except HTTPError as exc:
                with exc:
                    error = ValueError(
                        f"{path} HTTP {exc.code}: {exc.read(500).decode('utf-8', 'replace')}"
                    )
                if exc.code not in {408, 429, 500, 502, 503, 504}:
                    raise error from exc
            except (OSError, URLError) as exc:
                error = ValueError(f"{path}: {exc}")
            if attempt < self.attempts:
                print(
                    f"  retry {attempt + 1}/{self.attempts} after {error}", flush=True
                )
                time.sleep(2 ** (attempt - 1))
        raise error

    def probe(self):
        version = json.loads(self.request("/version"))
        speakers = json.loads(self.request("/speakers"))
        matches = [
            style["id"]
            for speaker in speakers
            if speaker["name"] == VOICE["name"]
            and speaker["speaker_uuid"] == VOICE["speaker_uuid"]
            for style in speaker["styles"]
            if style["name"] == VOICE["style"]
        ]
        if matches != [VOICE["speaker_style_id"]]:
            raise ValueError(f"Unexpected 四国めたん / ノーマル style IDs: {matches}")
        return {"origin": self.origin, "engine_version": version, **VOICE}

    def synthesis(self, asset):
        params = {"speaker": VOICE["speaker_style_id"]}
        query = json.loads(
            self.request(
                "/audio_query",
                params={**params, "text": asset.get("query_text", asset["input"])},
                post=True,
            )
        )
        actual = "".join(
            mora["text"]
            for phrase in query["accent_phrases"]
            for mora in phrase["moras"]
        )
        if pronunciation(actual) != pronunciation(asset["expected_reading"]):
            raise ValueError(
                f"Engine reading {actual!r} differs from {asset['expected_reading']!r}; check manually"
            )
        return self.request("/synthesis", params=params, body=query, post=True), actual


def pronunciation(text):
    """Compare kana segments, allowing VOICEVOX's particle を and long-vowel spellings."""
    text = re.sub(r"[\s、。？！!?・]", "", hiragana(text)).replace("を", "お")
    vowels = {
        "あ": "あかがさざただなはばぱまゃやらゎわぁ",
        "い": "いきぎしじちぢにひびぴみりぃ",
        "う": "うくぐすずつづぬふぶぷむゅゆるゔぅ",
        "え": "えけげせぜてでねへべぺめれぇ",
        "お": "おこごそぞとどのほぼぽもょよろぉ",
    }
    mora_vowel = {c: vowel for vowel, kana in vowels.items() for c in kana}
    result = []
    for c in text:
        previous = mora_vowel.get(result[-1]) if result else None
        if previous and (c == "ー" or (previous, c) in {("お", "う"), ("え", "い")}):
            c = previous
        result.append(c)
    return "".join(result)


def validate_wav(data):
    with wave.open(io.BytesIO(data), "rb") as wav:
        channels, width, rate, frames = (
            wav.getnchannels(),
            wav.getsampwidth(),
            wav.getframerate(),
            wav.getnframes(),
        )
        pcm = wav.readframes(frames)
    if (
        width != 2
        or frames <= 0
        or len(pcm) != frames * channels * width
        or not any(pcm)
    ):
        raise ValueError("Expected a complete, non-silent 16-bit PCM WAV")
    peak = max(abs(value) for (value,) in struct.iter_unpack("<h", pcm))
    return {
        "sample_rate_hz": rate,
        "channels": channels,
        "frames": frames,
        "duration_seconds": round(frames / rate, 3),
        "peak_pcm": peak,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def write_wav(path, data):
    """Publish a validated WAV atomically without replacing any existing file."""
    from tempfile import NamedTemporaryFile

    with NamedTemporaryFile(dir=path.parent, suffix=".partial", delete=False) as stream:
        temp = Path(stream.name)
        try:
            stream.write(data)
            stream.close()
            # A hard link provides atomic, no-overwrite publication on Windows NTFS.
            path.hardlink_to(temp)
        finally:
            stream.close()
            temp.unlink()


def generate(engine, manifest_path, selection, report):
    manifest = read_json(manifest_path)
    if manifest["schema_version"] != 1 or manifest["voice"] != VOICE:
        raise ValueError("Unsupported manifest schema or voice")
    assets = {asset["id"]: asset for asset in manifest["assets"]}
    if selection == "sample":
        selected = [row["audio_id"] for row in manifest["sample"]]
    else:
        selected = [
            asset_id
            for asset_id, asset in assets.items()
            if asset["status"] == "ready_for_preview"
        ]
    if len(set(selected)) != len(selected) or not selected:
        raise ValueError("Expected a nonempty selection of unique audio IDs")
    base = manifest_path.resolve().parent
    jobs = []
    for asset_id in selected:
        asset = assets[asset_id]
        expected_path = f"wav/{audio_id(asset['input'])}.wav"
        path = base / expected_path
        if (
            asset["status"] != "ready_for_preview"
            or asset_id != audio_id(asset["input"])
            or asset["path"] != expected_path
            or not path.resolve().is_relative_to(base)
        ):
            raise ValueError(f"Invalid or blocked asset: {asset_id}")
        jobs.append((asset, path))

    probe = engine.probe()
    print(json.dumps(probe, ensure_ascii=False), flush=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    sample_by_id = {row["audio_id"]: row for row in manifest["sample"]}
    failures = 0
    with report.open("x", encoding="utf-8") as log:
        log.write(
            json.dumps(
                {"event": "run", "selection": selection, "engine": probe},
                ensure_ascii=False,
            )
            + "\n"
        )
        for i, (asset, path) in enumerate(jobs, 1):
            result = {
                "audio_id": asset["id"],
                "path": asset["path"],
                "input": asset["input"],
                "query_text": asset.get("query_text", asset["input"]),
                "expected_reading": asset["expected_reading"],
                "pronunciation_review": "pending",
            }
            if asset["id"] in sample_by_id:
                result["sample"] = sample_by_id[asset["id"]]
            try:
                if path.exists():
                    result.update(
                        validate_wav(path.read_bytes()), status="skipped_existing"
                    )
                else:
                    data, actual = engine.synthesis(asset)
                    result.update(
                        validate_wav(data), engine_moras=actual, status="generated"
                    )
                    path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        write_wav(path, data)
                    except FileExistsError:
                        result.pop("engine_moras")
                        result.update(
                            validate_wav(path.read_bytes()), status="skipped_existing"
                        )
            except (OSError, ValueError, KeyError, wave.Error, EOFError) as exc:
                failures += 1
                result.update(status="failed", error=f"{type(exc).__name__}: {exc}")
            log.write(json.dumps(result, ensure_ascii=False) + "\n")
            log.flush()
            print(
                f"[{i}/{len(jobs)}] {result['status']} {asset['id']} {result.get('error', '')}",
                flush=True,
            )
    print(
        f"Finished {len(jobs)} selected assets with {failures} failures. Report {report}"
    )
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["probe", "sample", "all-ready"])
    parser.add_argument("--engine", default=ENGINE)
    parser.add_argument("--manifest", type=Path, default=OUTPUT / "manifest.json")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        engine = Engine(args.engine, args.timeout)
        if args.mode == "probe":
            print(json.dumps(engine.probe(), ensure_ascii=False))
            return 0
        stamp = time.time_ns()
        report = args.report or args.manifest.parent / f"run-{args.mode}-{stamp}.jsonl"
        return generate(engine, args.manifest, args.mode, report)
    except (OSError, ValueError, KeyError) as exc:
        print(f"VOICEVOX pipeline: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
