"""add cancelled job status

Revision ID: 7a1b2c3d4e5f
Revises: 6044c5e668bd
Create Date: 2026-07-10

"""
from typing import Sequence, Union

from alembic import op

revision: str = "7a1b2c3d4e5f"
down_revision: Union[str, None] = "6044c5e668bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE job_status_enum ADD VALUE IF NOT EXISTS 'CANCELLED'")


def downgrade() -> None:
    # PostgreSQL не поддерживает безопасное удаление значения enum.
    pass
