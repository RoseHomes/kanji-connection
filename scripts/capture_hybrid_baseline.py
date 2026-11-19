"""Capture authorized learner responses for UI regression checks, without DB writes.

Run once with the protected local preview running. Existing evidence is preserved.
"""

import hashlib
import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / "private/hybrid-learning"
    folder.mkdir(exist_ok=True)
    target = folder / "baseline.json"
    if target.exists():
        print("Existing hybrid baseline preserved")
        return
    session = json.loads((ROOT / "private/editorial-preview/session.json").read_bytes())
    if session["origin"] != "http://127.0.0.1:5174":
        raise ValueError("Only the restricted loopback preview is supported")
    with httpx.Client(timeout=30) as client:
        response = client.get(session["open_url"], follow_redirects=False)
        if response.status_code != 303:
            raise ValueError(
                "Preview capability is unavailable; restart the local preview"
            )

        def get(path):
            response = client.get(session["origin"] + "/api/v1/learning/" + path)
            response.raise_for_status()
            return response.json()

        lessons = [get(f"lesson/chapter-{n:02}") for n in range(1, 31)]
        questions = [get(f"practice/chapter-{n:02}") for n in range(1, 31)]
        groups = get("comparison-groups")
    assert (
        len(lessons) == 30
        and len(groups) == 94
        and all(len(q) == 15 for q in questions)
    )
    files = [
        "private/editorial-working/effective-book.json",
        "private/editorial-working/working-bundle.json",
        "private/editorial-revisions/2026-11-19-final-v2.json",
        "private/learning-presentation/mcq-presentation-v1.json",
        "private/learning-presentation/reading-variants-v1.json",
    ]
    target.write_text(
        json.dumps(
            {
                "lessons": lessons,
                "groups": groups,
                "questions": questions,
                "protected_sha256": {
                    p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                    for p in files
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        "Captured 30 authorized chapters, 94 groups and 450 unchanged MCQ presentations"
    )


if __name__ == "__main__":
    main()
