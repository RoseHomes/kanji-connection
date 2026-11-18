"""Supabase asymmetric JWT validation; only the configured project's keys are trusted."""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import httpx
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Identity:
    id: UUID


def validate_claims(token, key, settings, *, remotely_verified=False):
    claims = jwt.decode(
        token,
        key,
        algorithms=["RS256", "ES256"],
        audience=settings.supabase_jwt_audience,
        issuer=f"{settings.supabase_url}/auth/v1",
        leeway=5,
        options={
            "require": ["exp", "iat", "sub", "aud", "iss", "role"],
            "verify_signature": not remotely_verified,
            "verify_exp": True,
            "verify_iat": True,
            "verify_aud": True,
            "verify_iss": True,
            "verify_sub": True,
        },
    )
    if claims["role"] != "authenticated":
        raise jwt.InvalidTokenError("Wrong token role")
    return Identity(UUID(claims["sub"]))


def legacy_identity(token, settings):
    """Supabase-recommended remote signature validation for shared-secret projects."""
    if not settings.supabase_publishable_key:
        raise jwt.InvalidTokenError("Legacy verification is not configured")
    # This only prechecks claims. No identity is returned until the Auth server
    # has independently verified this exact token's signature and user.
    identity = validate_claims(token, None, settings, remotely_verified=True)
    try:
        response = httpx.get(
            settings.supabase_url + "/auth/v1/user",
            headers={
                "Authorization": "Bearer " + token,
                "apikey": settings.supabase_publishable_key.get_secret_value(),
            },
            timeout=5,
            follow_redirects=False,
        )
        if response.status_code in (401, 403):
            raise jwt.InvalidTokenError("Session rejected")
        if response.status_code != 200:
            raise HTTPException(503, "Authentication temporarily unavailable")
        if UUID(response.json()["id"]) != identity.id:
            raise jwt.InvalidTokenError("User does not match session")
        return identity
    except (httpx.HTTPError, KeyError):
        raise HTTPException(503, "Authentication temporarily unavailable") from None


def optional_identity(
    request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
):
    if credentials is None:
        if request.headers.get("Authorization"):
            raise HTTPException(
                401, "Invalid authorization", headers={"WWW-Authenticate": "Bearer"}
            )
        return None
    settings = request.app.state.settings
    if not settings.supabase_url:
        raise HTTPException(503, "Authentication is not configured")
    token = credentials.credentials
    if len(token) > 16384:
        raise HTTPException(401, "Invalid session")
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") == "HS256":
            return legacy_identity(token, settings)
        if header.get("alg") not in {"RS256", "ES256"} or not header.get("kid"):
            raise jwt.InvalidTokenError("Unsupported signing key")
        client = request.app.state.jwks_client
        key = client.get_signing_key_from_jwt(token).key
        return validate_claims(token, key, settings)
    except jwt.PyJWKClientConnectionError:
        raise HTTPException(503, "Authentication temporarily unavailable") from None
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(
            401, "Invalid or expired session", headers={"WWW-Authenticate": "Bearer"}
        ) from None


def require_identity(identity: Annotated[Identity | None, Depends(optional_identity)]):
    if identity is None:
        raise HTTPException(401, "Sign in required", headers={"WWW-Authenticate": "Bearer"})
    return identity


CurrentUser = Annotated[Identity, Depends(require_identity)]
OptionalUser = Annotated[Identity | None, Depends(optional_identity)]
