from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

client = TestClient(create_app(Settings(_env_file=None, content_source="sample")))


def test_health_reports_sample_mode_and_no_database_claim():
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok"
    assert body["database"] == "not_connected"


def test_catalog_is_metadata_and_only_sample_is_accessible():
    items = client.get("/api/v1/lessons").json()
    assert len(items) == 30
    assert sum(x["available_count"] for x in items) == 3
    assert client.get("/api/v1/lessons/chapter-01").status_code == 404
    assert len(client.get("/api/v1/lessons/chapter-02").json()["kanjis"]) == 3


def test_catalog_filters_and_validation():
    assert len(client.get("/api/v1/lessons?part=2").json()) == 5
    assert len(client.get("/api/v1/lessons?limit=2&offset=1").json()) == 2
    assert client.get("/api/v1/lessons?part=7").status_code == 422
    assert len(client.get("/api/v1/lessons?status=sample").json()) == 1


def test_search_thai_kana_romaji_component():
    for query, expected in [("ต้นไม้", "木"), ("はやし", "林"), ("mori", "森")]:
        assert client.get("/api/v1/search", params={"q": query}).json()[0]["character"] == expected
    assert len(client.get("/api/v1/kanjis", params={"q": "木"}).json()) == 3


def test_compare_rejects_unknown_and_limits_selection():
    assert len(client.get("/api/v1/compare?characters=木,林,森").json()) == 3
    assert client.get("/api/v1/compare?characters=木").status_code == 422
    assert client.get("/api/v1/compare?characters=木,人").status_code == 404
    assert client.get("/api/v1/compare?characters=木,林,森,本,末").status_code == 422


def test_relations_bounded_and_errors_consistent():
    body = client.get("/api/v1/kanjis/木/relations").json()
    assert body["related"] == ["林", "森"]
    assert client.get("/api/v1/kanjis/人").json()["error"]["code"] == "404"
    assert "error" in client.get("/api/v1/lessons?limit=0").json()


def test_cors_does_not_allow_unknown_origins():
    response = client.get("/api/v1/health", headers={"Origin": "https://untrusted.example"})
    assert "access-control-allow-origin" not in response.headers


def test_openapi_available():
    assert "/api/v1/compare" in client.get("/openapi.json").json()["paths"]
