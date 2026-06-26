"""add new statuses and enums

Revision ID: 20260626_0001
Revises: 20260612_0001
Create Date: 2026-06-26 10:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260626_0001"
down_revision: Union[str, Sequence[str], None] = "20260612_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Расширяем существующие enum-типы
    op.execute("ALTER TYPE job_status_enum ADD VALUE IF NOT EXISTS 'FAILED_SOURCE_UNAVAILABLE'")
    op.execute("ALTER TYPE job_item_status_enum ADD VALUE IF NOT EXISTS 'AMBIGUOUS'")
    op.execute("ALTER TYPE job_item_status_enum ADD VALUE IF NOT EXISTS 'SOURCE_UNCERTAIN'")
    op.execute("ALTER TYPE job_item_status_enum ADD VALUE IF NOT EXISTS 'PLACEHOLDER'")
    op.execute("ALTER TYPE job_item_status_enum ADD VALUE IF NOT EXISTS 'MISSING_DATA'")

    # 2. Меняем job_issue_severity_enum (INFO/WARNING/ERROR -> RED/YELLOW/ORANGE/INFO)
    # Сначала переводим колонку в TEXT, чтобы снять привязку к старому enum
    op.execute("ALTER TABLE job_issues ALTER COLUMN severity TYPE TEXT USING severity::text")
    # Удаляем старый тип
    op.execute("DROP TYPE IF EXISTS job_issue_severity_enum")
    # Создаём новый тип с значениями в верхнем регистре (как принято в SQLAlchemy Enum)
    op.execute("CREATE TYPE job_issue_severity_enum AS ENUM ('RED', 'YELLOW', 'ORANGE', 'INFO')")
    # Маппим старые значения в новые
    op.execute("""
        UPDATE job_issues SET severity = CASE
            WHEN UPPER(severity) = 'ERROR'   THEN 'RED'
            WHEN UPPER(severity) = 'WARNING' THEN 'YELLOW'
            ELSE 'INFO'
        END
    """)
    # Возвращаем колонке тип enum
    op.execute("ALTER TABLE job_issues ALTER COLUMN severity TYPE job_issue_severity_enum USING severity::job_issue_severity_enum")

    # 3. Создаём check_result_class_enum и добавляем колонку result_class
    op.execute("CREATE TYPE check_result_class_enum AS ENUM ('SUCCESS_WITH_MATCH', 'SUCCESS_EMPTY', 'TEMPORARY_SOURCE_FAILURE', 'AMBIGUOUS_MULTIPLE_MATCHES')")
    op.add_column(
        'job_item_checks',
        sa.Column('result_class', postgresql.ENUM(name='check_result_class_enum', create_type=False), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('job_item_checks', 'result_class')
    op.execute("DROP TYPE IF EXISTS check_result_class_enum")

    op.execute("ALTER TABLE job_issues ALTER COLUMN severity TYPE TEXT USING severity::text")
    op.execute("DROP TYPE IF EXISTS job_issue_severity_enum")
    op.execute("CREATE TYPE job_issue_severity_enum AS ENUM ('INFO', 'WARNING', 'ERROR')")
    op.execute("""
        UPDATE job_issues SET severity = CASE
            WHEN severity = 'RED' THEN 'ERROR'
            WHEN severity = 'YELLOW' THEN 'WARNING'
            ELSE 'INFO'
        END
    """)
    op.execute("ALTER TABLE job_issues ALTER COLUMN severity TYPE job_issue_severity_enum USING severity::job_issue_severity_enum")
