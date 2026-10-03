from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.auth.clerk_api import get_verified_clerk_email
from backend.app.models.identity import Role, User, UserRole

_DEFAULT_ROLES = (
    ("USER", "Standard EduConnect account"),
    ("ADMIN", "EduConnect administrator"),
    ("SUPER_ADMIN", "EduConnect super-administrator"),
)


def _find_by_clerk_id(db: Session, clerk_user_id: str) -> User | None:
    return db.scalar(
        select(User).where(
            User.auth_provider == "clerk",
            User.auth_provider_user_id == clerk_user_id,
        )
    )


def _ensure_default_role(db: Session, user: User) -> None:
    user_role = db.scalar(
        select(UserRole.role_id)
        .join(Role, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user.id, Role.name == "USER")
    )
    if user_role is not None:
        return

    db.execute(
        pg_insert(Role)
        .values(
            [
                {"id": uuid4(), "name": name, "description": description}
                for name, description in _DEFAULT_ROLES
            ]
        )
        .on_conflict_do_nothing(index_elements=[Role.name])
    )
    role = db.scalar(select(Role).where(Role.name == "USER"))
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The account role could not be initialized.",
        )

    db.execute(
        pg_insert(UserRole)
        .values(user_id=user.id, role_id=role.id)
        .on_conflict_do_nothing(index_elements=[UserRole.user_id, UserRole.role_id])
    )


def get_or_create_local_user(db: Session, clerk_user_id: str) -> User:
    """Bridge a verified Clerk identity to this app's private PostgreSQL user."""
    user = _find_by_clerk_id(db, clerk_user_id)
    if user is None:
        email = get_verified_clerk_email(clerk_user_id)
        user_with_email = db.scalar(
            select(User).where(func.lower(User.email) == email.casefold())
        )

        if user_with_email is not None:
            if user_with_email.auth_provider_user_id not in (None, clerk_user_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This verified email is already linked to another account.",
                )
            user_with_email.auth_provider = "clerk"
            user_with_email.auth_provider_user_id = clerk_user_id
            user_with_email.email = email
            user_with_email.is_verified = True
            user = user_with_email
            try:
                db.flush()
            except IntegrityError as exc:
                db.rollback()
                linked_user = _find_by_clerk_id(db, clerk_user_id)
                if linked_user is None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="This account could not be linked safely.",
                    ) from exc
                user = linked_user
        else:
            user = User(
                email=email,
                auth_provider="clerk",
                auth_provider_user_id=clerk_user_id,
                is_active=True,
                is_verified=True,
                last_login_at=datetime.now(timezone.utc),
            )
            db.add(user)
            try:
                db.flush()
            except IntegrityError as exc:
                db.rollback()
                linked_user = _find_by_clerk_id(db, clerk_user_id)
                if linked_user is None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="This account could not be linked safely.",
                    ) from exc
                user = linked_user

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )

    _ensure_default_role(db, user)
    return user