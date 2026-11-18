"""Explicit official XLSX downloads. Existing verified snapshots are never replaced."""

import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ("starter_c", "starter_competences_vocabulary_index_TH.xlsx"),
    ("elementary1_c", "elementary1_competences_vocabulary_index_TH.xlsx"),
    ("elementary2_c", "elementary2_competences_vocabulary_index_TH.xlsx"),
    ("pre_intermediate", "preintermediate_vocabulary_index_TH.xlsx"),
]


def main():
    folder = ROOT / "private/editorial-references"
    folder.mkdir(parents=True, exist_ok=True)
    for group, name in FILES:
        path = folder / name
        metadata_path = path.with_suffix(".source.json")
        url = f"https://marugoto.jpf.go.jp/assets/docs/teacher/resource/{group}/{name}"
        if path.exists() or metadata_path.exists():
            metadata = json.loads(metadata_path.read_text("utf-8"))
            if hashlib.sha256(path.read_bytes()).hexdigest() != metadata["sha256"]:
                raise ValueError("Existing Thai reference snapshot digest mismatch")
        else:
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read()
            if not data.startswith(b"PK"):
                raise ValueError("Expected an XLSX archive")
            path.write_bytes(data)
            metadata_path.write_text(
                json.dumps(
                    {"url": url, "sha256": hashlib.sha256(data).hexdigest()}, indent=2
                ),
                encoding="utf-8",
            )
        print(f"Pinned official reference: {name}")


if __name__ == "__main__":
    main()
