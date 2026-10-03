import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from backend.app.auth.clerk import clerk_jwks_url, decode_session_token
from backend.app.core.config import settings
from backend.app.main import app


class FakeJwksClient:
    def __init__(self, public_key) -> None:
        self.public_key = public_key

    def get_signing_key_from_jwt(self, token: str):
        return SimpleNamespace(key=self.public_key)


class ClerkAuthenticationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.public_key = cls.private_key.public_key()
        cls.client = TestClient(app)

    def make_token(self, **extra_claims: object) -> str:
        now = int(time.time())
        claims = {
            "sub": "user_test_123",
            "sid": "sess_test_123",
            "iat": now,
            "nbf": now - 1,
            "exp": now + 300,
            **extra_claims,
        }
        return jwt.encode(claims, self.private_key, algorithm="RS256", headers={"kid": "test"})

    def test_auth_endpoint_rejects_requests_without_session_cookie(self) -> None:
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 401)

    def test_profile_endpoint_rejects_requests_without_session_cookie(self) -> None:
        response = self.client.get("/api/v1/profile")
        self.assertEqual(response.status_code, 401)

    def test_auth_endpoint_accepts_a_valid_signed_session(self) -> None:
        token = self.make_token(azp=settings.allowed_origins[0])
        with patch(
            "backend.app.auth.clerk.get_jwks_client",
            return_value=FakeJwksClient(self.public_key),
        ):
            with TestClient(app, cookies={"__session": token}) as client:
                response = client.get("/api/auth/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"user_id": "user_test_123", "session_id": "sess_test_123"},
        )

    def test_session_verification_rejects_untrusted_authorized_party(self) -> None:
        token = self.make_token(azp="https://untrusted.example")
        with patch(
            "backend.app.auth.clerk.get_jwks_client",
            return_value=FakeJwksClient(self.public_key),
        ):
            with self.assertRaises(jwt.InvalidTokenError):
                decode_session_token(token)

    def test_session_verification_rejects_pending_clerk_sessions(self) -> None:
        token = self.make_token(sts="pending")
        with patch(
            "backend.app.auth.clerk.get_jwks_client",
            return_value=FakeJwksClient(self.public_key),
        ):
            with self.assertRaises(jwt.InvalidTokenError):
                decode_session_token(token)

    def test_jwks_url_is_derived_from_the_public_clerk_key(self) -> None:
        import base64

        encoded_host = base64.urlsafe_b64encode(b"clerk.example.accounts.dev$").decode("ascii").rstrip("=")
        self.assertEqual(
            clerk_jwks_url(f"pk_test_{encoded_host}"),
            "https://clerk.example.accounts.dev/.well-known/jwks.json",
        )