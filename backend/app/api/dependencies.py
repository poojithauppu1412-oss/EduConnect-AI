from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.clerk import ClerkIdentity, get_current_clerk_identity
from backend.app.auth.local_user import get_or_create_local_user
from backend.app.db.session import get_db
from backend.app.models.identity import Role, User, UserRole


def get_current_local_user(
    identity: ClerkIdentity = Depends(get_current_clerk_identity),
    db: Session = Depends(get_db),
) -> User:
    return get_or_create_local_user(db, identity.user_id)


def get_current_admin_user(
    user: User = Depends(get_current_local_user),
    db: Session = Depends(get_db),
) -> User:
    admin_role_id = db.scalar(
        select(UserRole.role_id)
        .join(Role, Role.id == UserRole.role_id)
        .where(
            UserRole.user_id == user.id,
            Role.name.in_(("ADMIN", "SUPER_ADMIN")),
        )
        .limit(1)
    )
    if admin_role_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required.",
        )
    return user