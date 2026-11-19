"""Private working-edition integration and security, using disposable SQLite only."""

import copy
import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert, select, update
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.book_bundle import Bundle
from app.config import Settings
from app.content_revision import WorkingRevision, apply_revision
from app.editorial_preview import create_preview_app
from app.editorial_sync import TABLES, execute_updates, prepare_updates, snapshot
from app.json_content import load_dataset
from app.learning import Learning
from app.main import create_app
from app.models import Base, QuizQuestion

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "private/editorial-sync/2026-11-19-final-v2"
WORKING = ROOT / "private/editorial-working"
TOKEN = "local-test-capability-" + "x" * 48


def load(path):
    return json.loads(path.read_bytes())


@pytest.fixture(scope="module")
def data():
    if not (FOLDER / "baseline.json").exists():
        pytest.skip(
            "Private review edition and guarded preflight are not distributed with the repo"
        )
    return (
        load(FOLDER / "baseline.json"),
        load(FOLDER / "plan.json"),
        Bundle.model_validate_json((WORKING / "working-bundle.json").read_bytes()),
    )


@pytest.fixture
def local_engine(data):
    baseline, _, _ = data
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with engine.begin() as c:
        for name, table in TABLES.items():
            if baseline[name]:
                c.execute(insert(table), baseline[name])
    yield engine
    engine.dispose()


def test_all_30_working_chapters_and_finalized_roles(data):
    book = load(WORKING / "effective-book.json")
    bundle = data[2]
    assert [c["chapter"] for c in book["chapters"]] == list(range(1, 31))
    assert all(
        "สังเกตรูปแล้วทวนความหมาย" != k["example"] and "อ่านพร้อมคำศัพท์และความหมาย" != k["memory_note"]
        for c in book["chapters"]
        for k in c["kanji_cards"]
    )
    cards = {}
    sentence_counts = {}
    for op in bundle.operations:
        if op["table"] != "lesson_sections":
            continue
        n = op["key"]["lesson_id"]["$ref"]["key"]["chapter"]
        block = op["values"]["blocks"][0]
        for card in block.get("cards", []):
            cards[n, card["character"]] = card
            assert card["study"]["reading"]["kind"] in {"word", "character", "component"}
        if block.get("sentences"):
            sentence_counts[n] = len(block["sentences"])
        if op["key"]["position"] == 6:
            assert block["comparison_rubric"]["auto_scorable"] is False
            assert block["comparison_rubric"]["max_score"] == 1
    assert len(cards) == 420
    assert cards[2, "禾"]["study"]["role"] == "component"
    assert "ธัญพืช" in cards[2, "禾"]["meaning_th"]
    assert cards[2, "禾"]["study"]["example"]["word"] == "秋"
    assert cards[8, "訊"]["study"]["required"] is False
    assert cards[21, "靖"]["study"]["required"] is False
    assert cards[21, "靖"]["study"]["reading"]["reading"] == "セイ"
    assert cards[10, "閣"]["study"]["example"]["optional"] is True
    assert cards[10, "閣"]["study"]["example"]["word"] == "金閣寺"
    assert cards[6, "好"]["study"]["reading"]["form"] == "好き"
    assert cards[10, "口"]["study"]["reading"]["reading"] == "くち"
    assert sentence_counts == {27: 2, 29: 3}
    for c in book["chapters"]:
        assert c["diagram"]["comparison_pairs"] == c["comparisons"]
        assert all(a["answer"] == q["answer"] for a, q in zip(c["answers"], c["exercises"]))
    assert book["chapters"][1]["diagram"]["core"] is None
    assert book["chapters"][3]["diagram"]["core"] is None
    assert book["chapters"][4]["answers"][10]["answer"] == "じゅっぷん / じっぷん"


def test_revision_is_edition_bound_and_preserves_extraction(data):
    original = load_dataset(ROOT / "private/kanji-connection-extracted")
    revision = WorkingRevision.model_validate_json(
        (ROOT / "private/editorial-revisions/2026-11-19-final-v2.json").read_bytes()
    )
    raw = original.model_dump()
    effective = apply_revision(original, revision)
    assert original.model_dump() == raw
    assert (
        effective.chapters[1].kanji_cards[6].meaning_th
        != original.chapters[1].kanji_cards[6].meaning_th
    )
    corrupted = revision.model_copy(deep=True)
    corrupted.changes[0].expected = "wrong original"
    with pytest.raises(ValueError, match="expected-original"):
        apply_revision(original, corrupted)
    assert original.model_dump() == raw


def test_update_rehearsal_rolls_back_and_applied_projection_is_idempotent(local_engine, data):
    baseline, plan, bundle = data
    with local_engine.connect() as c:
        tx = c.begin()
        result = execute_updates(c, baseline, plan, rehearsal=True)
        assert result["all_publication_states_preserved"]
        tx.rollback()
        assert snapshot(c) == baseline
        c.rollback()
        tampered = copy.deepcopy(plan)
        tampered["operations"] = [next(o for o in tampered["operations"] if o["table"] == "kanjis")]
        tampered["operations"][0]["values"]["access_tier"] = "free"
        with pytest.raises(ValueError, match="Unexpected field"):
            execute_updates(c, baseline, tampered)
        c.rollback()
        assert snapshot(c) == baseline
        c.rollback()
    with local_engine.begin() as c:
        execute_updates(c, baseline, plan)
    with local_engine.connect() as c:
        after = snapshot(c)
        assert not prepare_updates(after, bundle, plan["revision_id"])["operations"]
        for name in baseline:
            old = {r["id"]: r for r in baseline[name] if "id" in r}
            for row in after[name]:
                if row.get("id") not in old:
                    continue
                assert all(
                    row.get(k) == old[row["id"]].get(k)
                    for k in ["status", "review_status", "access_tier", "catalog_visible"]
                )


def test_stale_data_and_publication_changes_abort(local_engine, data):
    baseline, plan, _ = data
    with local_engine.connect() as c:
        tx = c.begin()
        c.execute(
            update(TABLES["kanjis"])
            .where(TABLES["kanjis"].c.id == 1)
            .values(meaning_th="concurrent change")
        )
        with pytest.raises(ValueError, match="changed since preflight"):
            execute_updates(c, baseline, plan)
        tx.rollback()
        assert snapshot(c) == baseline


def test_all_working_source_answers_match_runtime_keys(local_engine, data):
    baseline, plan, _ = data
    with local_engine.begin() as c:
        execute_updates(c, baseline, plan)
    expected = {
        (chapter["chapter"], f"q-{answer['number']:02}"): answer["answer"].split(" / ")[0]
        for chapter in load(WORKING / "effective-book.json")["chapters"]
        for answer in chapter["answers"]
    }
    chapters = {row["id"]: row["chapter"] for row in baseline["lessons"]}
    graded = manual = 0
    with Session(local_engine) as db:
        service = Learning(db, Settings(_env_file=None))
        for q in db.scalars(select(QuizQuestion)):
            if q.stable_key == "comparison-c":
                result = service.grade(q, "รูปอักษรต่างกัน")
                assert result["correct"] is None and result["expected"] is None
                manual += 1
            else:
                result = service.grade(q, expected[chapters[q.lesson_id], q.stable_key])
                assert result["correct"] is True
                graded += 1
    assert (graded, manual) == (420, 30)


def test_preview_capability_origin_and_write_restrictions(local_engine, data):
    baseline, plan, _ = data
    with local_engine.begin() as c:
        execute_updates(c, baseline, plan)
    settings = Settings(_env_file=None, content_source="database", enable_user_writes=False)
    app = create_preview_app(settings, local_engine, TOKEN)
    with TestClient(app, base_url="http://127.0.0.1:5174", client=("127.0.0.1", 50000)) as client:
        assert client.get("/api/v1/learning/catalog").status_code == 401
        assert client.get("/__editorial/open?token=wrong").status_code == 401
        assert (
            client.get(
                "/__editorial/open?token=" + TOKEN, headers={"Origin": "https://example.com"}
            ).status_code
            == 403
        )
        response = client.get("/__editorial/open?token=" + TOKEN, follow_redirects=False)
        assert response.status_code == 303 and "HttpOnly" in response.headers["set-cookie"]
        assert "SameSite=strict" in response.headers["set-cookie"]
        assert len(client.get("/api/v1/learning/catalog").json()) == 30
        for n in range(1, 31):
            lesson = client.get(f"/api/v1/learning/lesson/chapter-{n:02}").json()
            assert lesson["private_development"] is True
            assert (
                sum(len(b.get("cards", [])) for s in lesson["sections"] for b in s["blocks"]) == 14
            )
        assert client.post("/api/v1/me/progress/chapter-01", json={}).status_code == 405
        assert client.put("/api/v1/me/progress/chapter-01", json={}).status_code == 405
        result = client.post(
            "/api/v1/learning/check/chapter-05:q-11",
            json={"answer": "じっぷん", "submission_id": str(uuid4())},
        ).json()
        assert result["correct"] is True and result["persisted"] is False
        result = client.post(
            "/api/v1/learning/check/chapter-01:comparison-c",
            json={"answer": "形", "submission_id": str(uuid4())},
        ).json()
        assert result["correct"] is None and result["expected"] is None
        assert client.get("/api/v1/health", headers={"Host": "evil.example"}).status_code == 403
    with local_engine.connect() as c:
        after = snapshot(c)
    with TestClient(create_app(settings, local_engine), base_url="http://127.0.0.1:5174") as public:
        assert public.get("/__editorial/open?token=" + TOKEN).status_code == 404
        assert public.get("/api/v1/learning/catalog").json() == []
        for n in range(1, 31):
            assert public.get(f"/api/v1/learning/lesson/chapter-{n:02}").status_code == 404
        assert public.get("/api/v1/kanjis/禾").status_code == 404
    with local_engine.connect() as c:
        assert snapshot(c) == after


def test_preview_refuses_hosted_and_remote_clients(local_engine):
    settings = Settings(_env_file=None)
    with pytest.raises(ValueError, match="hosted"):
        create_preview_app(settings.model_copy(update={"vercel": True}), local_engine, TOKEN)
    with pytest.raises(ValueError, match="strong"):
        create_preview_app(settings, local_engine, "weak")
    app = create_preview_app(settings, local_engine, TOKEN)
    with TestClient(app, base_url="http://127.0.0.1:5174", client=("192.0.2.1", 50000)) as remote:
        assert remote.get("/__editorial/ping").status_code == 403
