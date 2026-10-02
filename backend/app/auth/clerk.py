import base64
import re
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Cookie, HTTPException, status
from jwt import InvalidTokenError
from jwt.exceptions import PyJWKClientError
from jwt import PyJWKClient
from pydantic import BaseModel

from backend.app.core.config import settings

_FRONTEND_API_HOST_PATTERN = re.compile(r"^[a-zA-Z0-9.-]+$")


class ClerkIdentity(BaseModel):
    user_id: str
    session_id: str | None = None


def clerk_jwks_url(publishable_key: str) -> str:
    """Derive Clerk's public JWKS endpoint from its public publishable key."""
    try:
        encoded_host = publishable_key.split("_", maxsplit=2)[2]
        padded_host = encoded_host + ("=" * (-len(encoded_host) % 4))
        frontend_api_host = base64.urlsafe_b64decode(padded_host).decode("ascii").rstrip("$")
    except (IndexError, ValueError, UnicodeDecodeError) as exc:
        raise ValueError("The Clerk publishable key is not valid.") from exc

    if not _FRONTEND_API_HOST_PATTERN.fullmatch(frontend_api_host):
        raise ValueError("The Clerk publishable key does not contain a valid frontend API host.")

    return f"https://{frontend_api_host}/.well-known/jwks.json"


@lru_cache(maxsize=1)
def get_jwks_client() -> PyJWKClient:
    publishable_key = settings.clerk_publishable_key
    if publishable_key is None:
        raise RuntimeError("Clerk authentication is not configured.")
    return PyJWKClient(clerk_jwks_url(publishable_key.get_secret_value()))


def decode_session_token(token: str) -> dict[str, Any]:
    signing_key = get_jwks_client().get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        options={
            "require": ["exp", "nbf", "sub"],
            "verify_aud": False,
        },
        leeway=30,
    )

    authorized_party = claims.get("azp")
    if authorized_party and authorized_party not in settings.allowed_origins:
        raise InvalidTokenError("The token was issued for an untrusted origin.")
    if claims.get("sts") == "pending":
        raise InvalidTokenError("The Clerk session is not active.")

    return claims


def get_current_clerk_identity(
    session_token: str | None = Cookie(default=None, alias="__session"),
) -> ClerkIdentity:
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = decode_session_token(session_token)
    except (InvalidTokenError, PyJWKClientError, ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The sign-in session is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return ClerkIdentity(user_id=claims["sub"], session_id=claims.get("sid"))