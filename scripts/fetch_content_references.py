"""Explicit reference download; never connects to an application database.

Existing snapshots are digest-checked and retained. Remove both files deliberately
to choose a newer upstream version, then rebuild all evidence.
"""

import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / "private/dictionaries"
    folder.mkdir(parents=True, exist_ok=True)
    for name in ("kanjidic2.xml.gz", "JMdict_e.gz"):
        path = folder / name
        metadata_path = folder / (name + ".source.json")
        url = "https://www.edrdg.org/pub/Nihongo/" + name
        if path.exists() or metadata_path.exists():
            metadata = json.loads(metadata_path.read_text("utf-8"))
            if hashlib.sha256(path.read_bytes()).hexdigest() != metadata["sha256"]:
                raise ValueError(f"Existing snapshot digest mismatch: {name}")
            print(f"Retained verified snapshot: {name}")
            continue
        with urllib.request.urlopen(url, timeout=120) as response:
            data = response.read()
        if not data.startswith(b"\x1f\x8b"):
            raise ValueError(f"Reference is not gzip: {name}")
        temporary = path.with_suffix(path.suffix + ".download")
        temporary.write_bytes(data)
        temporary.replace(path)
        metadata_path.write_text(
            json.dumps(
                {
                    "url": url,
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "bytes": len(data),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"Downloaded reference snapshot: {name}")


if __name__ == "__main__":
    main()
