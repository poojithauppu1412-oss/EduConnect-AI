import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import SecretStr

from backend.app.auth.clerk_api import get_verified_clerk_email
from backend.app.core.config import settings


class ClerkBackendApiTests(unittest.TestCase):
    def test_returns_primary_email_only_when_clerk_marks_it_verified(self) -> None:
        response = SimpleNamespace(
            status_code=200,
            is_success=True,
            json=lambda: {
                "primary_email_address_id": "primary",
                "email_addresses": [
                    {
                        "id": "secondary",
                        "email_address": "secondary@example.test",
                        "verification": {"status": "verified"},
                    },
                    {
                        "id": "primary",
                        "email_address": "student@example.test",
                        "verification": {"status": "verified"},
                    },
                ],
            },
        )
        with (
            patch.object(settings, "clerk_secret_key", SecretStr("test-only-secret")),
            patch("backend.app.auth.clerk_api.httpx.get", return_value=response) as request,
        ):
            email = get_verified_clerk_email("user_profile_test")

        self.assertEqual(email, "student@example.test")
        self.assertEqual(
            request.call_args.args[0],
            "https://api.clerk.com/v1/users/user_profile_test",
        )
        self.assertEqual(
            request.call_args.kwargs["headers"]["Authorization"],
            "Bearer test-only-secret",
        )

    def test_refuses_to_create_a_local_profile_without_a_verified_email(self) -> None:
        response = SimpleNamespace(
            status_code=200,
            is_success=True,
            json=lambda: {
                "primary_email_address_id": "primary",
                "email_addresses": [
                    {
                        "id": "primary",
                        "email_address": "student@example.test",
                        "verification": {"status": "unverified"},
                    }
                ],
            },
        )
        with (
            patch.object(settings, "clerk_secret_key", SecretStr("test-only-secret")),
            patch("backend.app.auth.clerk_api.httpx.get", return_value=response),
        ):
            with self.assertRaises(HTTPException) as raised:
                get_verified_clerk_email("user_profile_test")

        self.assertEqual(raised.exception.status_code, 403)

    def test_missing_server_key_fails_explicitly(self) -> None:
        with (
            patch.object(settings, "clerk_secret_key", None),
            patch("backend.app.auth.clerk_api.httpx.get") as request,
        ):
            with self.assertRaises(HTTPException) as raised:
                get_verified_clerk_email("user_profile_test")

        self.assertEqual(raised.exception.status_code, 503)
        request.assert_not_called()

    def test_clerk_outage_does_not_expose_upstream_response(self) -> None:
        response = SimpleNamespace(
            status_code=503,
            is_success=False,
            json=lambda: {"error": "internal upstream detail"},
        )
        with (
            patch.object(settings, "clerk_secret_key", SecretStr("test-only-secret")),
            patch("backend.app.auth.clerk_api.httpx.get", return_value=response),
        ):
            with self.assertRaises(HTTPException) as raised:
                get_verified_clerk_email("user_profile_test")

        self.assertEqual(raised.exception.status_code, 503)
        self.assertNotIn("upstream", raised.exception.detail)


if __name__ == "__main__":
    unittest.main()