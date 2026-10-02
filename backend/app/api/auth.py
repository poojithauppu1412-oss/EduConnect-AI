from fastapi import APIRouter, Depends

from backend.app.auth.clerk import ClerkIdentity, get_current_clerk_identity

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/me")
def current_session(identity: ClerkIdentity = Depends(get_current_clerk_identity)) -> dict[str, str | None]:
    return {
        "user_id": identity.user_id,
        "session_id": identity.session_id,
    }