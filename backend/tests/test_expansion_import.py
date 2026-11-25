from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.content_revision import digest
from app.expansion_import import ImportPlan, ReferenceRelease, Target, apply_plan
from app.learning_paths import list_paths
from app.models import (
    ExampleSentence,
    JLPTAssignment,
    KanjiReading,
    KanjiRecord,
    LearningPath,
    LearningPathItem,
    LearningUnit,
    Vocabulary,
    VocabularyKanji,
)

CREDIT = {
    "source_url": "https://example.org/fixture",
    "license": "owner-authorized",
    "attribution": "Test fixture",
    "evidence": "isolated test only",
}
KANJI = {"kind": "kanji", "text": "校"}
WORD = {"kind": "vocabulary", "text": "学校", "reading": "がっこう"}
SENTENCE = {"kind": "sentence", "text": "学校に行きます。", "reading": "がっこうにいきます。"}
REFERENCES = [
    {
        "key": "kanji:校",
        "kind": "kanji",
        "text": "校",
        "level": 5,
        "file": "test",
        "order": 1,
        "readings": {"on": ["コウ"]},
    },
    {
        "key": "vocabulary:school",
        "kind": "vocabulary",
        "text": "学校",
        "reading": "がっこう",
        "level": 5,
        "file": "test",
        "order": 2,
        "dictionary_id": "1206750",
    },
]
MANIFEST = {"inventory_sha256": digest(REFERENCES)}
RELEASE = ReferenceRelease(
    **CREDIT, source_key="test", version="v1", manifest=MANIFEST, manifest_sha256=digest(MANIFEST)
)


def make_plan():
    items = [{"target": t} for t in (KANJI, WORD, SENTENCE)]
    return {
        "catalog_sha256": "a" * 64,
        "reference": RELEASE.model_dump(),
        "new_content": [
            {
                "target": KANJI,
                "meaning_th": "โรงเรียน",
                "readings": {"on": ["コウ"]},
                "credit": CREDIT,
            },
            {"target": WORD, "meaning_th": "โรงเรียน", "dictionary_id": "1206750", "credit": CREDIT},
            {"target": SENTENCE, "meaning_th": "ไปโรงเรียน", "credit": CREDIT},
        ],
        "assignments": [
            {"reference_key": r["key"], "target": t} for r, t in zip(REFERENCES, [KANJI, WORD])
        ],
        "paths": [
            {
                "kind": kind,
                "slug": slug,
                "level": level,
                "title_th": "โรงเรียน",
                "position": 0,
                "units": [{"key": "first", "title_th": "โรงเรียน", "position": 0, "items": items}],
            }
            for kind, slug, level in (("category", "school", None), ("jlpt", "n5", 5))
        ],
    }


def total(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_source_parser_and_japanese_identity(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    from jlpt_n5_reference import read_csv

    assert (
        next(read_csv("\ufefflevel,word\r\nN5,学校\r\n".encode(), ("level", "word")))[1]["word"]
        == "学校"
    )
    for data in (b"level,word\nN4,x\n", b"level,word\nN5,x,y\n", b"level,level\nN5,N5\n"):
        with pytest.raises(ValueError):
            list(read_csv(data, ("level", "word")))
    for fields in (
        {"kind": "kanji", "text": "木木"},
        {"kind": "vocabulary", "text": "か\u3099", "reading": "が"},
        {"kind": "vocabulary", "text": "学校", "reading": "gakkou"},
        {"kind": "sentence", "text": "abc"},
    ):
        with pytest.raises(ValueError):
            Target(**fields)
    raw = make_plan()
    raw["new_content"].append(
        {"target": {**WORD, "reading": "ガッコウ"}, "meaning_th": "โรงเรียน", "credit": CREDIT}
    )
    with pytest.raises(ValueError, match="Duplicate canonical"):
        ImportPlan.model_validate(raw)
    raw = make_plan()
    raw["paths"][0]["units"][0]["items"].append({"target": WORD})
    with pytest.raises(ValueError, match="Duplicate path membership"):
        ImportPlan.model_validate(raw)


def test_rehearsal_reuses_targets_and_rolls_back(db_engine):
    plan = ImportPlan.model_validate(make_plan())
    with db_engine.connect() as connection:
        outer = connection.begin()
        if connection.dialect.name == "sqlite":
            connection.exec_driver_sql("BEGIN")
        with Session(connection) as db:
            db.add(
                LearningPath(
                    kind="category",
                    slug="school",
                    title_th="ชื่อเดิม",
                    status="published",
                    access_tier="free",
                )
            )
            db.flush()
            public_before = list_paths(db, None, 0, 100)
            first = apply_plan(db, plan, REFERENCES, trusted_release=RELEASE)
            assert first["inserted"] == {
                "example_sentences": 1,
                "jlpt_reference_releases": 1,
                "kanjis": 1,
                "vocabularies": 1,
                "kanji_readings": 1,
                "jlpt_assignments": 2,
                "learning_paths": 1,
                "learning_units": 2,
                "vocabulary_kanjis": 1,
                "learning_path_items": 6,
            }
            assert not apply_plan(db, plan, REFERENCES, trusted_release=RELEASE)["inserted"]
            assert total(db, LearningPathItem) == 6
            assert (
                total(db, KanjiRecord) == total(db, Vocabulary) == total(db, ExampleSentence) == 1
            )
            assert total(db, KanjiReading) == total(db, VocabularyKanji) == 1
            assert list_paths(db, None, 0, 100) == public_before
            assert {u.status for u in db.scalars(select(LearningUnit))} == {"needs_review"}
            assert {v.access_tier for v in db.scalars(select(Vocabulary))} == {"private"}
        outer.rollback()
    with Session(db_engine) as db:
        assert (
            total(db, JLPTAssignment) == total(db, LearningPathItem) == total(db, Vocabulary) == 0
        )


def test_conflict_is_atomic_and_release_changes_are_rejected(db_engine):
    plan = ImportPlan.model_validate(make_plan())
    with Session(db_engine) as db:
        apply_plan(db, plan, REFERENCES, trusted_release=RELEASE)
        raw = make_plan()
        raw["paths"][0]["units"][0]["title_th"] = "เปลี่ยนหัวข้อเดิม"
        raw["new_content"].append(
            {
                "target": {"kind": "kanji", "text": "木"},
                "meaning_th": "ต้นไม้",
                "readings": {"kun": ["き"]},
                "credit": CREDIT,
            }
        )
        with pytest.raises(ValueError, match="Insert-only plan conflicts"):
            apply_plan(db, ImportPlan.model_validate(raw), REFERENCES, trusted_release=RELEASE)
        assert total(db, KanjiRecord) == 1
        assert total(db, LearningPathItem) == 6
        raw = make_plan()
        raw["new_content"][0]["readings"] = {"on": ["ア"]}
        with pytest.raises(ValueError, match="attested"):
            apply_plan(db, ImportPlan.model_validate(raw), REFERENCES, trusted_release=RELEASE)
        raw = make_plan()
        raw["assignments"].pop()
        with pytest.raises(ValueError, match="assignment at the path level"):
            apply_plan(db, ImportPlan.model_validate(raw), REFERENCES, trusted_release=RELEASE)
        with pytest.raises(ValueError, match="independently verified inventory"):
            apply_plan(
                db, plan, [{**row, "level": 4} for row in REFERENCES], trusted_release=RELEASE
            )


def test_apply_approval_and_loopback_scope(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    from import_learning_content import approve_manifest, local_engine

    monkeypatch.setenv(
        "EXPANSION_TEST_DATABASE_URL",
        "postgresql+psycopg://postgres:test@example.invalid/kanji_test",
    )
    with pytest.raises(ValueError, match="127.0.0.1"):
        local_engine()
    approved = tmp_path / "approval.json"
    receipt = tmp_path / "dry-run.json"
    key = "a" * 64
    approved.write_text(
        f'{{"plan_sha256":"{key}","reviewer":"Editor","decision_reference":"review-1","approved":true}}'
    )
    receipt.write_text(f'{{"plan_sha256":"{key}","rolled_back":true,"idempotent":true}}')
    with pytest.raises(ValueError, match="Explicit approval"):
        approve_manifest(approved, receipt, key, "b" * 64)
    assert approve_manifest(approved, receipt, key, key).reviewer == "Editor"
