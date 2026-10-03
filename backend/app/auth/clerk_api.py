from urllib.parse import quote

import httpx
from fastapi import HTTPException, status

from backend.app.core.config import settings

_CLERK_API = "https://api.clerk.com/v1/users"


def get_verified_clerk_email(clerk_user_id: str) -> str:
    """Read a verified email from Clerk's server-side user record."""
    secret_key = settings.clerk_secret_key
    if secret_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account profile service is not configured.",
        )

    try:
        response = httpx.get(
            f"{_CLERK_API}/{quote(clerk_user_id, safe='')}",
            headers={"Authorization": f"Bearer {secret_key.get_secret_value()}"},
            timeout=httpx.Timeout(5.0, connect=2.0),
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account profile service is temporarily unavailable.",
        ) from exc

    if response.status_code == status.HTTP_404_NOT_FOUND:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The signed-in account could not be found.",
        )
    if not response.is_success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account profile service is temporarily unavailable.",
        )

    try:
        clerk_user = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account profile service returned an invalid response.",
        ) from exc

    if not isinstance(clerk_user, dict):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account profile service returned an invalid response.",
        )

    email_addresses = clerk_user.get("email_addresses")
    if not isinstance(email_addresses, list):
        email_addresses = []

    primary_id = clerk_user.get("primary_email_address_id")
    candidates = sorted(
        (address for address in email_addresses if isinstance(address, dict)),
        key=lambda address: address.get("id") != primary_id,
    )
    for address in candidates:
        verification = address.get("verification")
        email = address.get("email_address")
        if (
            isinstance(email, str)
            and email.strip()
            and isinstance(verification, dict)
            and verification.get("status") == "verified"
        ):
            return email.strip()

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Verify an email address in your account before creating a profile.",
    )