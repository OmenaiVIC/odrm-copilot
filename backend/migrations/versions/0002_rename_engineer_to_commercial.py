"""rename engineer role to commercial

Revision ID: 0002_rename_engineer_commercial
Revises: 0001_create_users
Create Date: 2026-11-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_rename_engineer_commercial"
down_revision: str | None = "0001_create_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _set_role_server_default(value: str) -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column(
                "role",
                existing_type=sa.String(length=32),
                existing_nullable=False,
                server_default=value,
            )
        return

    op.alter_column(
        "users",
        "role",
        existing_type=sa.String(length=32),
        existing_nullable=False,
        server_default=value,
    )


def upgrade() -> None:
    op.execute("UPDATE users SET role = 'commercial' WHERE role = 'engineer'")
    _set_role_server_default("commercial")


def downgrade() -> None:
    op.execute("UPDATE users SET role = 'engineer' WHERE role = 'commercial'")
    _set_role_server_default("engineer")
