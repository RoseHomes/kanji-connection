"""Real JWT signature/claim checks; no network or Supabase calls."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def signed():
    key = ec.generate_private_key(ec.SECP256R1())
    settings = Settings(_env_file=None, supabase_url="https://auth.example.test")
    claims = {
        "sub": str(uuid4()),
        "iss": "https://auth.example.test/auth/v1",
        "aud": "authenticated",
        "role": "authenticated",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    app = create_app(settings)
    app.state.jwks_client = SimpleNamespace(
        get_signing_key_from_jwt=lambda token: SimpleNamespace(key=key.public_key())
    )
    return key, claims, TestClient(app)


def test_valid_signed_identity_and_missing_bearer(signed):
    key, claims, client = signed
    assert client.get("/api/v1/me").status_code == 401
    token = jwt.encode(claims, key, algorithm="ES256", headers={"kid": "fixture"})
    assert client.get("/api/v1/me", headers={"Authorization": "Bearer " + token}).json() == {
        "id": claims["sub"]
    }


@pytest.mark.parametrize(
    "damage",
    [
        "expired",
        "issuer",
        "audience",
        "role",
        "uuid",
        "signature",
        "algorithm",
        "missing_claim",
        "malformed",
    ],
)
def test_invalid_identity_fails_closed(signed, damage):
    key, claims, client = signed
    if damage == "expired":
        claims["exp"] = datetime.now(timezone.utc) - timedelta(minutes=1)
    if damage == "issuer":
        claims["iss"] = "https://other.test/auth/v1"
    if damage == "audience":
        claims["aud"] = "service_role"
    if damage == "role":
        claims["role"] = "service_role"
    if damage == "uuid":
        claims["sub"] = "not-an-id"
    if damage == "missing_claim":
        del claims["exp"]
    if damage == "signature":
        key = ec.generate_private_key(ec.SECP256R1())
    token = jwt.encode(
        claims,
        "test-only-key-with-at-least-32-bytes" if damage == "algorithm" else key,
        algorithm="HS256" if damage == "algorithm" else "ES256",
        headers={"kid": "fixture"},
    )
    if damage == "malformed":
        token = "malformed"
    response = client.get("/api/v1/me", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 401
    assert token not in response.text


def test_cors_supports_writes_only_from_configured_origin(signed):
    _, _, client = signed
    ok = client.options(
        "/api/v1/me/progress/chapter-02",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )
    assert ok.status_code == 200
    bad = client.options(
        "/api/v1/me/progress/chapter-02",
        headers={"Origin": "https://evil.test", "Access-Control-Request-Method": "PUT"},
    )
    assert bad.status_code == 400


def test_legacy_tokens_require_authoritative_auth_server_verification(monkeypatch):
    from app import auth

    settings = Settings(
        _env_file=None,
        supabase_url="https://auth.example.test",
        supabase_publishable_key="sb_publishable_fixture",
    )
    claims = {
        "sub": str(uuid4()),
        "iss": settings.supabase_url + "/auth/v1",
        "role": "authenticated",
        "aud": "authenticated",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    token = jwt.encode(claims, "a-test-signing-secret-with-32-bytes", algorithm="HS256")
    calls = []

    def verify_remote(url, **kwargs):
        calls.append(url)
        assert kwargs["headers"]["Authorization"] == "Bearer " + token
        assert kwargs["follow_redirects"] is False
        return SimpleNamespace(status_code=200, json=lambda: {"id": claims["sub"]})

    monkeypatch.setattr(auth.httpx, "get", verify_remote)
    client = TestClient(create_app(settings))
    assert client.get("/api/v1/me", headers={"Authorization": "Bearer " + token}).status_code == 200
    assert calls == [settings.supabase_url + "/auth/v1/user"]
    monkeypatch.setattr(auth.httpx, "get", lambda *a, **k: SimpleNamespace(status_code=401))
    assert client.get("/api/v1/me", headers={"Authorization": "Bearer " + token}).status_code == 401
