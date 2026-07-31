"""Add role enum and inactive-user support.

Revision ID: 0002_auth_hardening
Revises: 0001_initial_schema
Create Date: 2026-06-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_auth_hardening"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = sa.Enum("Admin", "Editor", "Reader", name="user_role")


def upgrade() -> None:
    op.execute(
        """
        UPDATE users
        SET role = 'Reader'
        WHERE role IS NULL OR role NOT IN ('Admin', 'Editor', 'Reader')
        """
    )
    user_role.create(op.get_bind(), checkfirst=False)
    op.alter_column(
        "users",
        "role",
        existing_type=sa.String(length=50),
        server_default=None,
    )
    op.alter_column(
        "users",
        "role",
        existing_type=sa.String(length=50),
        type_=user_role,
        postgresql_using="role::text::user_role",
        nullable=False,
        server_default="Reader",
    )
    op.add_column(
        "users",
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_active")
    op.alter_column(
        "users",
        "role",
        existing_type=user_role,
        server_default=None,
    )
    op.alter_column(
        "users",
        "role",
        existing_type=user_role,
        type_=sa.String(length=50),
        postgresql_using="role::text",
        nullable=True,
        server_default="Reader",
    )
    user_role.drop(op.get_bind(), checkfirst=False)
