"""End-to-end MCQ conversion, authorization and learner-boundary privacy.

The private fixture is optional for distributed CI; locally all 30 chapters run.
All database operations in these tests use disposable SQLite, never Supabase.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, insert
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.content_views import learner_block
from app.editorial_preview import PREVIEW_USER, create_preview_app
from app.editorial_sync import TABLES, execute_updates, snapshot
from app.learning_presentation import kana, practice, reading_variants
from app.main import create_app
from app.models import Base

ROOT = Path(__file__).resolve().parents[2]
TOKEN = "redesign-test-" + "x" * 64


@pytest.fixture(scope="module")
def edition():
    folder = ROOT / "private/editorial-sync/2026-11-19-final-v2"
    if not (folder / "baseline.json").exists():
        pytest.skip("Private working edition not distributed with repository")
    load = lambda p: json.loads(p.read_bytes())
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    baseline = load(folder / "baseline.json")
    with engine.begin() as connection:
        for name, table in TABLES.items():
            if baseline[name]:
                connection.execute(insert(table), baseline[name])
        execute_updates(connection, baseline, load(folder / "plan.json"))
    yield engine, load(ROOT / "private/learning-presentation/mcq-presentation-v1.json")
    engine.dispose()


@pytest.fixture
def preview(edition):
    engine, _ = edition
    settings = Settings(_env_file=None, content_source="database", enable_user_writes=False)
    app = create_preview_app(settings, engine, TOKEN)
    with TestClient(app, base_url="http://127.0.0.1:5174", client=("127.0.0.1", 50000)) as client:
        assert (
            client.get("/__editorial/open?token=" + TOKEN, follow_redirects=False).status_code
            == 303
        )
        yield client, settings, app


def walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def test_all_450_runtime_questions_match_versioned_audit_and_have_one_answer(edition, preview):
    engine, audit = edition
    client, _, app = preview
    counts = {"meaning": 0, "glyph": 0, "reading": 0, "shape": 0}
    with engine.connect() as connection:
        before = snapshot(connection)
    writes = []

    def observe(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().split()[0].upper() in {
            "INSERT",
            "UPDATE",
            "DELETE",
            "ALTER",
            "CREATE",
            "DROP",
        }:
            writes.append(statement.split()[0])

    event.listen(engine, "before_cursor_execute", observe)
    try:
        with Session(engine) as db:
            for chapter in audit["chapters"]:
                slug = f"chapter-{chapter['chapter']:02}"
                # Same identity used by the restricted preview; ordinary app gets no such grant.
                from app.auth import Identity

                user = Identity(PREVIEW_USER)
                actual = practice(db, app.state.settings, user, slug)
                expected = chapter["objective_questions"]
                by_id = {q["id"]: q for q in expected}
                assert {q["id"] for q in actual} == set(by_id)
                for q in actual:
                    assert q == by_id[q["id"]], {
                        k: (v, by_id[q["id"]].get(k))
                        for k, v in q.items()
                        if v != by_id[q["id"]].get(k)
                    }
                public = client.get("/api/v1/learning/practice/" + slug)
                assert public.status_code == 200 and len(public.json()) == 15
                assert (
                    "correct_option_id" not in public.text
                    and "source_question_key" not in public.text
                )
                for q in actual:
                    counts[q["kind"]] += 1
                    assert 3 <= len(q["options"]) <= 4
                    assert len({o["id"] for o in q["options"]}) == len(q["options"])
                    assert len({o["text"] for o in q["options"]}) == len(q["options"])
                    assert sum(o["id"] == q["correct_option_id"] for o in q["options"]) == 1
                    correct = client.post(
                        f"/api/v1/learning/practice/{slug}/{q['id']}/check",
                        json={"option_id": q["correct_option_id"]},
                    )
                    assert correct.status_code == 200 and correct.json()["correct"] is True
                    assert correct.json()["persisted"] is False and correct.json()["explanation"]
                    wrong = next(o for o in q["options"] if o["id"] != q["correct_option_id"])
                    result = client.post(
                        f"/api/v1/learning/practice/{slug}/{q['id']}/check",
                        json={"option_id": wrong["id"]},
                    )
                    assert result.status_code == 200 and result.json()["correct"] is False
                    if q["kind"] == "reading":
                        word = q["prompt"].split("「")[1].split("」")[0]
                        assert word in reading_variants(), (
                            "Pinned dictionary reading exclusions required"
                        )
                        accepted = {kana(r) for r in reading_variants()[word]}
                        assert all(
                            kana(o["text"]) not in accepted
                            for o in q["options"]
                            if o["id"] != q["correct_option_id"]
                        )
        assert counts["meaning"] + counts["glyph"] == 210
        assert counts["reading"] == 210 and counts["shape"] == 30
        assert not writes
    finally:
        event.remove(engine, "before_cursor_execute", observe)
    with engine.connect() as connection:
        assert snapshot(connection) == before


def test_all_30_lesson_payloads_hide_internal_audit_and_keep_full_content(preview):
    client, _, _ = preview
    forbidden = {
        "pdf_page",
        "pdf_pages",
        "source",
        "source_files",
        "raw_text",
        "answers",
        "answer_key",
        "comparison_rubric",
        "revision_id",
        "provenance",
        "expected_original",
        "editorial_reading_scope",
        "typed_comparisons",
    }
    cards = phrases = 0
    assert all("id" not in lesson for lesson in client.get("/api/v1/learning/catalog").json())
    for n in range(1, 31):
        lesson = client.get(f"/api/v1/learning/lesson/chapter-{n:02}").json()
        assert not (set(walk_keys(lesson)) & forbidden)
        assert "id" not in lesson
        for section in lesson["sections"]:
            for block in section["blocks"]:
                cards += len(block.get("cards", []))
                phrases += len(block.get("sentences", []))
    assert cards == 420 and phrases == 5


def test_94_curated_groups_are_authorized_and_relevant(preview):
    client, _, _ = preview
    groups = client.get("/api/v1/learning/comparison-groups").json()
    assert len(groups) == 94 and {g["chapter"] for g in groups} == set(range(1, 31))
    assert all(len(g["characters"]) in {2, 3} and g["difference_th"] for g in groups)
    triad = next(
        g for g in groups if [c["character"] for c in g["characters"]] == ["大", "犬", "太"]
    )
    assert "人" not in triad["difference_th"] and "天" not in triad["difference_th"]
    assert "pdf_page" not in set(walk_keys(groups))
    component = next(c for g in groups for c in g["characters"] if c["character"] == "扌")
    assert component["reading"]["kind"] == "component"


def test_mcq_rejects_fabricated_options_free_text_and_unknown_question(preview):
    client, _, _ = preview
    question = client.get("/api/v1/learning/practice/chapter-01").json()[0]
    path = f"/api/v1/learning/practice/chapter-01/{question['id']}/check"
    assert client.post(path, json={"option_id": "forged"}).status_code == 422
    assert client.post(path, json={"answer": "人"}).status_code == 422
    assert (
        client.post(
            path, json={"option_id": question["options"][0]["id"], "score": 100}
        ).status_code
        == 422
    )
    assert (
        client.post(path.replace(question["id"], "unknown"), json={"option_id": "x"}).status_code
        == 404
    )


def test_practice_feedback_is_opt_in_and_matches_server_grading(preview):
    client, _, _ = preview
    path = "/api/v1/learning/practice/chapter-01"
    plain = client.get(path).json()[0]
    response = client.get(path, params={"include_feedback": "true"})
    assert "feedback" not in plain
    assert "no-store" in response.headers["Cache-Control"]
    question = response.json()[0]
    feedback = question.pop("feedback")
    assert question == plain
    explanations = feedback.pop("selection_explanations")
    for option in question["options"]:
        grade = client.post(
            f"{path}/{question['id']}/check", json={"option_id": option["id"]}
        ).json()
        correct = option["id"] == feedback["correct_option_id"]
        assert grade == {
            **feedback,
            "correct": correct,
            "persisted": False,
            "selection_explanation": explanations["correct" if correct else "incorrect"],
        }


def test_new_public_routes_do_not_bypass_private_access(edition):
    engine, _ = edition
    with TestClient(
        create_app(Settings(_env_file=None, content_source="database"), engine)
    ) as client:
        assert client.get("/api/v1/learning/comparison-groups").json() == []
        assert (
            client.get("/api/v1/learning/practice/chapter-01?include_feedback=true").status_code
            == 404
        )
        for n in range(1, 31):
            assert client.get(f"/api/v1/learning/practice/chapter-{n:02}").status_code == 404
        assert (
            client.post(
                "/api/v1/learning/practice/chapter-01/x/check", json={"option_id": "x"}
            ).status_code
            == 404
        )


def test_nested_diagram_metadata_is_not_serialized():
    block = {
        "diagram": {
            "core": {
                "kanji": "木",
                "meaning_th": "ต้นไม้",
                "pdf_page": 100,
                "source": {"filename": "PRIVATE.pdf"},
            },
            "related": [],
            "comparison_pairs": [],
        }
    }
    safe = learner_block(block)
    assert safe["diagram"]["core"] == {"kanji": "木", "meaning_th": "ต้นไม้"}


def test_public_sample_uses_distinct_readings_instead_of_ambiguous_forest_glosses():
    settings = Settings(_env_file=None, content_source="sample")
    questions = practice(None, settings, None, "chapter-02")
    assert len(questions) == 3 and all(q["kind"] == "reading" for q in questions)
    with TestClient(create_app(settings)) as client:
        assert len(client.get("/api/v1/learning/practice/chapter-02").json()) == 3
        for q in questions:
            result = client.post(
                f"/api/v1/learning/practice/chapter-02/{q['id']}/check",
                json={"option_id": q["correct_option_id"]},
            )
            assert result.status_code == 200 and result.json()["correct"] is True
        assert client.get("/api/v1/learning/practice/chapter-01").status_code == 404


def test_preview_snapshot_is_exact_and_database_enforced_readonly(edition, tmp_path):
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    from app.editorial_preview_snapshot import materialize_snapshot

    engine, _ = edition
    with engine.connect() as connection:
        source = snapshot(connection)
    local = materialize_snapshot(source, tmp_path)
    try:
        with local.connect() as connection:
            assert snapshot(connection) == source
            with pytest.raises(OperationalError, match="readonly|read-only"):
                connection.execute(text("UPDATE lessons SET catalog_visible = 1"))
    finally:
        local.dispose()


def test_published_guest_practice_does_not_promote_private_source_c(edition):
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace
    from uuid import uuid4

    import jwt
    from cryptography.hazmat.primitives.asymmetric import ec

    from app.content_revision import digest

    engine, audit = edition
    with engine.connect() as connection:
        data = snapshot(connection)
    first = next(row for row in data["lessons"] if row["chapter"] == 1)
    first.update(status="published", access_tier="free", catalog_visible=True)
    for row in data["lesson_sections"]:
        if row["lesson_id"] == first["id"]:
            row.update(status="published", access_tier="free")
    for row in data["quiz_questions"]:
        if row["lesson_id"] == first["id"] and row["stable_key"] != "comparison-c":
            row["status"] = "published"
    kanji_id = next(
        row["kanji_id"] for row in data["lesson_kanjis"] if row["lesson_id"] == first["id"]
    )
    kanji = next(row for row in data["kanjis"] if row["id"] == kanji_id)
    kanji.update(review_status="published", access_tier="free")
    isolated = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(isolated)
    with isolated.begin() as connection:
        for name, table in TABLES.items():
            if data[name]:
                connection.execute(insert(table), data[name])
    settings = Settings(
        _env_file=None,
        content_source="database",
        enable_user_writes=True,
        supabase_url="https://auth.example.test",
        database_url="postgresql+psycopg://fixture:fixture@pooler.example.test:6543/postgres",
        cors_origins=["https://frontend.example.test"],
        vercel=True,
        vercel_env="production",
    )
    app = create_app(settings, isolated)
    key = ec.generate_private_key(ec.SECP256R1())
    app.state.jwks_client = SimpleNamespace(
        get_signing_key_from_jwt=lambda _: SimpleNamespace(key=key.public_key())
    )

    def bearer(owner):
        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": str(owner),
                "iss": "https://auth.example.test/auth/v1",
                "aud": "authenticated",
                "role": "authenticated",
                "iat": now,
                "exp": now + timedelta(minutes=5),
                "session_id": str(uuid4()),
            },
            key,
            algorithm="ES256",
            headers={"kid": "fixture"},
        )
        return {"Authorization": f"Bearer {token}"}

    first_owner, second_owner = uuid4(), uuid4()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/learning/practice/chapter-01")
            assert response.status_code == 200 and len(response.json()) == 14
            assert all(q["kind"] != "shape" for q in response.json())
            public_q = audit["chapters"][0]["objective_questions"][0]
            assert (
                client.post(
                    f"/api/v1/learning/practice/chapter-01/{public_q['id']}/check",
                    json={"option_id": public_q["correct_option_id"]},
                ).json()["correct"]
                is True
            )
            private_c = audit["chapters"][0]["objective_questions"][-1]
            assert (
                client.post(
                    f"/api/v1/learning/practice/chapter-01/{private_c['id']}/check",
                    json={"option_id": private_c["correct_option_id"]},
                ).status_code
                == 404
            )
            route = f"/api/v1/me/practice/chapter-01/{public_q['id']}/attempt"
            preloaded = {
                q["id"]: q["feedback"]
                for q in client.get(
                    "/api/v1/learning/practice/chapter-01?include_feedback=true"
                ).json()
            }
            assert private_c["id"] not in preloaded
            data_in = {
                "option_id": preloaded[public_q["id"]]["correct_option_id"],
                "submission_id": str(uuid4()),
            }
            assert client.post(route, json=data_in).status_code == 401
            headers = bearer(first_owner)
            assert (
                client.post(route, json={**data_in, "correct": False}, headers=headers).status_code
                == 422
            )
            assert (
                client.post(
                    route, json={**data_in, "owner_id": str(second_owner)}, headers=headers
                ).status_code
                == 422
            )
            assert (
                client.post(
                    route, json={**data_in, "option_id": "not-an-option"}, headers=headers
                ).status_code
                == 422
            )
            saved = client.post(route, json=data_in, headers=headers)
            assert saved.status_code == 200
            assert saved.json()["persisted"] is True and saved.json()["correct"] is True
            assert client.post(route, json=data_in, headers=headers).json() == saved.json()
            other_option = next(
                option["id"]
                for option in public_q["options"]
                if option["id"] != data_in["option_id"]
            )
            assert (
                client.post(
                    route, json={**data_in, "option_id": other_option}, headers=headers
                ).status_code
                == 409
            )
            assert (
                client.put(
                    "/api/v1/me/progress/chapter-01",
                    json={"expected_version": 0, "progress": 100},
                    headers=headers,
                ).status_code
                == 200
            )
            assert (
                client.put(
                    f"/api/v1/me/reviews/{kanji['character']}",
                    json={"expected_version": 0, "knew": True},
                    headers=headers,
                ).status_code
                == 200
            )
            assert client.get("/api/v1/me/dashboard").status_code == 401
            second = client.get("/api/v1/me/dashboard", headers=bearer(second_owner)).json()
            assert (
                second["quiz"]["recent"] == [] and second["lessons"] == [] and second["cards"] == {}
            )
            assert (
                client.put(
                    "/api/v1/me/progress/chapter-01",
                    json={"expected_version": 1, "progress": 0},
                    headers=bearer(second_owner),
                ).status_code
                == 409
            )
            assert (
                client.put(
                    f"/api/v1/me/reviews/{kanji['character']}",
                    json={"expected_version": 1, "knew": False},
                    headers=bearer(second_owner),
                ).status_code
                == 409
            )
        with TestClient(app) as new_client:
            headers = bearer(first_owner)
            for _ in range(2):
                dashboard = new_client.get("/api/v1/me/dashboard", headers=headers)
                assert dashboard.headers["cache-control"] == "private, no-store"
                payload = dashboard.json()
                assert payload["quiz"]["graded"] == payload["quiz"]["correct"] == 1
                recent = payload["quiz"]["recent"][0]
                assert recent["id"] == data_in["submission_id"]
                assert recent["prompt"] == public_q["prompt"]
                assert recent["answer"] == recent["expected"] == saved.json()["correct_text"]
                assert recent["explanation"] == saved.json()["explanation"]
                assert payload["lessons"][0]["progress"] == 100
                assert payload["cards"][kanji["character"]]["reviews"] == 1
        with isolated.connect() as connection:
            assert digest(snapshot(connection)) == digest(data)
    finally:
        isolated.dispose()
