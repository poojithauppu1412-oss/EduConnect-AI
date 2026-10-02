"""replace local password storage with Clerk identity mapping

Revision ID: 5d8a1e7c2b4f
Revises: 9da934854408
Create Date: 2026-10-02 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "5d8a1e7c2b4f"
down_revision: Union[str, None] = "9da934854408"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("auth_provider", sa.String(length=40), server_default="clerk", nullable=False),
    )
    op.add_column("users", sa.Column("auth_provider_user_id", sa.String(length=255), nullable=True))
    op.create_unique_constraint(
        "uq_users_auth_provider_identity",
        "users",
        ["auth_provider", "auth_provider_user_id"],
    )
    op.drop_column("users", "password_hash")


def downgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.drop_constraint("uq_users_auth_provider_identity", "users", type_="unique")
    op.drop_column("users", "auth_provider_user_id")
    op.drop_column("users", "auth_provider")