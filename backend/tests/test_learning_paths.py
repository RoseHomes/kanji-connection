import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_migrations import config

from app.config import Settings
from app.main import create_app
from app.models import (
    ExampleSentence,
    JLPTAssignment,
    JLPTReferenceRelease,
    KanjiRecord,
    LearningPath,
    LearningPathItem,
    LearningUnit,
    Vocabulary,
)
from app.seed import seed


@pytest.fixture
def material(db_engine):
    with Session(db_engine) as db, db.begin():
        seed(db, include_samples=False)

        def add(model, **values):
            row = model(**values)
            db.add(row)
            db.flush()
            return row.id

        public = {"status": "published", "access_tier": "free"}

        def kanji(glyph, tier="free"):
            return add(
                KanjiRecord,
                character=glyph,
                meaning_th="จำนวน",
                readings={"on": ["イチ"]},
                review_status="published",
                access_tier=tier,
                source={},
            )

        one, two, private_kanji = kanji("一"), kanji("二"), kanji("三", "private")
        word = add(
            Vocabulary,
            written_form="一人",
            reading="ひとり",
            meaning_th="หนึ่งคน",
            provenance={},
            **public,
        )
        sentence = add(
            ExampleSentence,
            text_ja="8時に家を出ます。",
            reading="はちじにいえをでます。",
            meaning_th="ออกจากบ้านตอนแปดโมง",
            provenance={"private": "never-serialize"},
            **public,
        )
        draft_sentence = add(
            ExampleSentence, text_ja="二人", meaning_th="draft target", access_tier="free"
        )
        release = add(
            JLPTReferenceRelease,
            source_key="reference",
            version="one",
            source_url="https://example.com",
            license="CC BY-SA 4.0",
            attribution="Reference",
            manifest_sha256="a" * 64,
            manifest={
                "counts": {"N5": {"kanji": 84, "vocabulary": 674}},
                "private": "never-serialize",
            },
        )
        alternate = add(
            JLPTReferenceRelease,
            source_key="reference",
            version="two",
            source_url="https://example.com",
            license="CC BY-SA 4.0",
            attribution="Reference",
            manifest_sha256="b" * 64,
            manifest={},
        )
        cat = add(
            LearningPath, kind="category", slug="public", title_th="Public category", **public
        )
        draft = add(
            LearningPath,
            kind="category",
            slug="draft",
            title_th="Draft category",
            access_tier="free",
        )
        private = add(
            LearningPath,
            kind="category",
            slug="private",
            title_th="Private category",
            status="published",
        )
        n5 = add(
            LearningPath,
            kind="jlpt",
            slug="n5",
            title_th="N5",
            jlpt_level=5,
            jlpt_release_id=release,
            **public,
        )
        n4 = add(
            LearningPath,
            kind="jlpt",
            slug="n4",
            title_th="N4",
            jlpt_level=4,
            jlpt_release_id=release,
            **public,
        )
        unit = add(
            LearningUnit, path_id=cat, unit_key="unit", title_th="Public unit", status="published"
        )
        hidden_unit = add(LearningUnit, path_id=cat, unit_key="hidden", title_th="Draft unit")
        empty_unit = add(
            LearningUnit,
            path_id=cat,
            unit_key="empty",
            title_th="Unavailable unit",
            status="published",
        )
        n5_unit = add(
            LearningUnit, path_id=n5, unit_key="unit", title_th="N5 unit", status="published"
        )
        n4_unit = add(
            LearningUnit, path_id=n4, unit_key="unit", title_th="N4 unit", status="published"
        )

        for path_id, unit_id, targets in (
            (cat, unit, ({"kanji_id": one}, {"vocabulary_id": word}, {"sentence_id": sentence})),
            (cat, hidden_unit, ({"kanji_id": two},)),
            (cat, empty_unit, ({"kanji_id": private_kanji}, {"sentence_id": draft_sentence})),
            (draft, None, ({"kanji_id": one},)),
            (private, None, ({"vocabulary_id": word},)),
            (
                n5,
                n5_unit,
                (
                    {"kanji_id": one},
                    {"kanji_id": two},
                    {"vocabulary_id": word},
                    {"sentence_id": sentence},
                ),
            ),
            (n4, n4_unit, ({"kanji_id": one}, {"vocabulary_id": word})),
        ):
            for order, target in enumerate(targets):
                add(LearningPathItem, path_id=path_id, unit_id=unit_id, sort_order=order, **target)
        for release_id, level, key, order, target in (
            (release, 5, "kanji:one", 9, {"kanji_id": one}),
            (release, 4, "kanji:one-n4", 3, {"kanji_id": one}),
            (alternate, 5, "kanji:two", 2, {"kanji_id": two}),
            (release, 5, "vocab:one", 1, {"vocabulary_id": word}),
        ):
            add(
                JLPTAssignment,
                release_id=release_id,
                level=level,
                reference_key=key,
                match_provenance={"reference_order": order},
                **target,
            )
    return cat, unit, n4, n5, one, private_kanji, word, sentence, release


def test_public_projection_pagination_and_scope(db_engine, material):
    settings = Settings(_env_file=None, content_source="database", enable_user_writes=False)
    with TestClient(create_app(settings, db_engine)) as client:
        root = "/api/v1/learning/paths"
        assert [p["slug"] for p in client.get(root, params={"kind": "category"}).json()] == [
            "public"
        ]
        for slug in ("draft", "private"):
            assert client.get(f"{root}/category/{slug}").status_code == 404
            assert client.get(f"{root}/category/{slug}/items").status_code == 404
        detail = client.get(f"{root}/category/public").json()
        assert [u["unit_key"] for u in detail["units"]] == ["unit"]
        assert detail["counts"] == {"kanji": 1, "vocabulary": 1, "sentence": 1}
        for key in ("hidden", "empty"):
            assert client.get(f"{root}/category/public/units/{key}").status_code == 404
        unit = client.get(f"{root}/category/public/units/unit").json()
        assert [i["type"] for i in unit["items"]] == ["kanji", "vocabulary", "sentence"]
        assert not unit["practice_available"]
        assert "never-serialize" not in str(unit)

        result = client.get(f"{root}/jlpt/n5").json()
        assert result["counts"] == detail["counts"]
        assert result["reference"]["totals"]["kanji"] == 84
        assert "never-serialize" not in str(result)
        route = f"{root}/jlpt/n5/items"
        first = client.get(route, params={"sort": "reference", "limit": 1}).json()
        assert first["items"][0]["type"] == "vocabulary"
        second = client.get(
            route, params={"sort": "reference", "limit": 1, "cursor": first["next_cursor"]}
        ).json()
        assert second["items"][0]["type"] == "kanji"
        third = client.get(
            route, params={"sort": "reference", "cursor": second["next_cursor"]}
        ).json()
        assert third["items"][0]["level"] is None and third["next_cursor"] is None
        assert client.get(route, params={"cursor": first["next_cursor"]}).status_code == 422
        assert client.get(route, params={"cursor": "not-a-valid-cursor"}).status_code == 422
        assert client.get(route, params={"type": "invalid"}).status_code == 422
        assert client.get(route, params={"q": "%"}).json()["total"] == 0
        assert client.get(route, params={"q": "ヒトリ", "type": "vocabulary"}).json()["total"] == 1
        assert client.get(route, params={"q": "いち", "type": "kanji"}).json()["total"] == 1
        cumulative = client.get(
            f"{root}/jlpt/n4/items", params={"include_prerequisites": True}
        ).json()
        assert [(i["type"], i["level"]) for i in cumulative["items"]] == [
            ("vocabulary", 5),
            ("sentence", None),
            ("kanji", 4),
        ]
        explorer = "/api/v1/learning/kanjis"
        assert len(client.get(explorer).json()) == 2
        assert [
            i["character"] for i in client.get(explorer, params={"category": "public"}).json()
        ] == ["一"]
        assert client.get(explorer, params={"category": "private"}).json() == []
        assert [
            i["character"]
            for i in client.get(
                explorer, params={"jlpt": "N4", "include_prerequisites": True}
            ).json()
        ] == ["一"]


def test_content_constraints(db_engine, material):
    cat, unit, n4, n5, kanji, private_kanji, word, sentence, release = material
    candidates = [
        LearningPathItem(path_id=cat, unit_id=unit),
        LearningPathItem(path_id=cat, unit_id=unit, kanji_id=kanji, vocabulary_id=word),
        LearningPathItem(path_id=cat, unit_id=unit, kanji_id=kanji),
        LearningPathItem(path_id=n4, unit_id=unit, sentence_id=sentence),
        LearningPathItem(path_id=n5, kanji_id=private_kanji, required=True),
        LearningPath(
            kind="jlpt", slug="missing-level", jlpt_release_id=release, title_th="Missing level"
        ),
        LearningPath(kind="category", slug="invalid--slug", title_th="Invalid slug"),
        LearningPath(
            kind="jlpt",
            slug="duplicate-level",
            jlpt_level=5,
            jlpt_release_id=release,
            title_th="Duplicate level",
        ),
        JLPTAssignment(
            release_id=release,
            reference_key="invalid",
            level=6,
            kanji_id=kanji,
            match_provenance={},
        ),
        ExampleSentence(text_ja="", meaning_th="", status="published"),
    ]
    for row in candidates:
        with Session(db_engine) as db, pytest.raises(IntegrityError):
            db.add(row)
            db.flush()


def test_additive_migration_preserves_book_and_restricts_browser_roles(db_engine):
    if db_engine.dialect.name != "postgresql":
        pytest.skip("Alembic migration targets PostgreSQL")
    with db_engine.begin() as connection:
        cfg = config()
        cfg.attributes["connection"] = connection
        command.downgrade(cfg, "0002")
        connection.execute(text("ALTER DEFAULT PRIVILEGES GRANT ALL ON TABLES TO authenticated"))
        connection.execute(text("ALTER DEFAULT PRIVILEGES GRANT ALL ON SEQUENCES TO authenticated"))
        with Session(connection) as db:
            seed(db, include_samples=False)
            db.flush()
        sql = text("SELECT chapter, slug, title_th, status FROM lessons ORDER BY chapter")
        before = connection.execute(sql).all()
        original_tables = set(inspect(connection).get_table_names())
        assert len(before) == 30 and len(original_tables) == 17
        command.upgrade(cfg, "0003")
        additions = set(inspect(connection).get_table_names()) - original_tables
        assert additions == {
            "example_sentences",
            "jlpt_reference_releases",
            "jlpt_assignments",
            "learning_paths",
            "learning_units",
            "learning_path_items",
        }
        assert connection.execute(sql).all() == before
        for name in additions:
            assert connection.scalar(
                text("SELECT relrowsecurity FROM pg_class WHERE oid=to_regclass(:name)"),
                {"name": name},
            )
            assert not connection.scalar(
                text(
                    "SELECT has_table_privilege('authenticated', :name, 'SELECT, INSERT, TRUNCATE')"
                ),
                {"name": name},
            )
            assert not connection.scalar(
                text("SELECT has_sequence_privilege('authenticated', :name, 'USAGE')"),
                {"name": name + "_id_seq"},
            )
        connection.execute(text("ALTER DEFAULT PRIVILEGES REVOKE ALL ON TABLES FROM authenticated"))
        connection.execute(
            text("ALTER DEFAULT PRIVILEGES REVOKE ALL ON SEQUENCES FROM authenticated")
        )
        command.downgrade(cfg, "0002")
        assert set(inspect(connection).get_table_names()) == original_tables
        assert connection.execute(sql).all() == before
        command.upgrade(cfg, "head")
        command.check(cfg)
