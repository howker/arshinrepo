"""rewrite schema for TZ v3

Revision ID: 20260626_0002
Revises: 20260626_0001
Create Date: 2026-06-26 12:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260626_0002"
down_revision: Union[str, Sequence[str], None] = "20260626_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Создаём недостающие enum-типы ДО использования
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'issue_code_enum') THEN
                CREATE TYPE issue_code_enum AS ENUM (
                    'MATCH', 'TYPE_MISMATCH', 'SERIAL_MISMATCH',
                    'VERIFICATION_DATE_MISMATCH', 'NEXT_VERIFICATION_DATE_MISMATCH',
                    'LINK_MISMATCH', 'LINK_FILLED', 'PLACEHOLDER_VALUE_DETECTED',
                    'MISSING_REQUIRED_FIELD', 'ARSHIN_NOT_FOUND', 'SOURCE_UNCERTAIN',
                    'MULTIPLE_MATCHES'
                );
            END IF;
        END $$;
    """)

    # 2. Дропаем все старые таблицы с CASCADE
    op.execute("DROP TABLE IF EXISTS job_issues CASCADE")
    op.execute("DROP TABLE IF EXISTS job_item_checks CASCADE")
    op.execute("DROP TABLE IF EXISTS job_items CASCADE")
    op.execute("DROP TABLE IF EXISTS jobs CASCADE")
    op.execute("DROP TABLE IF EXISTS file_objects CASCADE")
    op.execute("DROP TABLE IF EXISTS audit_logs CASCADE")

    # 3. Создаём новые таблицы по ТЗ v3

    # jobs (ТЗ §4.2)
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", postgresql.ENUM(name="job_status_enum", create_type=False), nullable=False, index=True),
        sa.Column("source_filename", sa.String(512), nullable=False),
        sa.Column("source_file_path", sa.String(1024), nullable=False),
        sa.Column("result_file_path", sa.String(1024), nullable=True),
        sa.Column("report_json", postgresql.JSONB, nullable=True),
        sa.Column("total_items", sa.Integer, default=0, nullable=False),
        sa.Column("matched_count", sa.Integer, default=0, nullable=False),
        sa.Column("mismatch_count", sa.Integer, default=0, nullable=False),
        sa.Column("ambiguous_count", sa.Integer, default=0, nullable=False),
        sa.Column("source_uncertain_count", sa.Integer, default=0, nullable=False),
        sa.Column("placeholder_count", sa.Integer, default=0, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
    )

    # job_files (ТЗ §4.3) - переименовано из file_objects
    op.create_table(
        "job_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("kind", postgresql.ENUM(name="file_object_type_enum", create_type=False), nullable=False),
        sa.Column("path", sa.String(1024), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # job_items (ТЗ §4.4)
    op.create_table(
        "job_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("sheet_name", sa.String(255), nullable=False),
        sa.Column("excel_row", sa.Integer, nullable=False),
        sa.Column("device_kind", sa.String(10), nullable=False),
        sa.Column("block_code", sa.String(50), nullable=False),
        sa.Column("type_raw", sa.String(255), nullable=True),
        sa.Column("type_norm", sa.String(255), nullable=True),
        sa.Column("serial_raw", sa.String(255), nullable=True),
        sa.Column("serial_norm", sa.String(255), nullable=True),
        sa.Column("accuracy_class_raw", sa.String(50), nullable=True),
        sa.Column("verification_date_file_raw", sa.String(50), nullable=True),
        sa.Column("verification_date_file_norm", sa.Date, nullable=True),
        sa.Column("next_date_file_raw", sa.String(50), nullable=True),
        sa.Column("next_date_file_norm", sa.Date, nullable=True),
        sa.Column("link_file_raw", sa.String(1024), nullable=True),
        sa.Column("link_file_vri", sa.String(255), nullable=True),
        sa.Column("cell_type", sa.String(20), nullable=True),
        sa.Column("cell_serial", sa.String(20), nullable=True),
        sa.Column("cell_verification_date", sa.String(20), nullable=True),
        sa.Column("cell_next_date", sa.String(20), nullable=True),
        sa.Column("cell_link", sa.String(20), nullable=True),
        sa.Column("context_json", postgresql.JSONB, nullable=True),
        sa.Column("status", postgresql.ENUM(name="job_item_status_enum", create_type=False), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # job_item_checks (ТЗ §4.5)
    op.create_table(
        "job_item_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_items.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("arshin_found", sa.Boolean, default=False, nullable=False),
        sa.Column("selected_vri_id", sa.String(255), nullable=True),
        sa.Column("selected_url", sa.String(1024), nullable=True),
        sa.Column("arshin_type", sa.String(255), nullable=True),
        sa.Column("arshin_serial", sa.String(255), nullable=True),
        sa.Column("arshin_verification_date", sa.Date, nullable=True),
        sa.Column("arshin_valid_date", sa.Date, nullable=True),
        sa.Column("arshin_applicability", sa.Boolean, nullable=True),
        sa.Column("candidates_count", sa.Integer, default=0, nullable=False),
        sa.Column("decision_reason", sa.Text, nullable=True),
        sa.Column("result_class", postgresql.ENUM(name="check_result_class_enum", create_type=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # job_issues (ТЗ §4.6)
    op.create_table(
        "job_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_items.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("sheet_name", sa.String(255), nullable=True),
        sa.Column("cell", sa.String(20), nullable=True),
        sa.Column("severity", postgresql.ENUM(name="job_issue_severity_enum", create_type=False), nullable=False, index=True),
        sa.Column("code", postgresql.ENUM(name="issue_code_enum", create_type=False), nullable=False, index=True),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # arshin_audit (ТЗ §4.7)
    op.create_table(
        "arshin_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("job_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_items.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("attempt_no", sa.Integer, nullable=False),
        sa.Column("endpoint_mode", sa.String(10), nullable=False),
        sa.Column("request_url", sa.String(1024), nullable=False),
        sa.Column("request_params_json", postgresql.JSONB, nullable=True),
        sa.Column("http_status", sa.Integer, nullable=True),
        sa.Column("response_time_ms", sa.Integer, nullable=True),
        sa.Column("response_body_json", postgresql.JSONB, nullable=True),
        sa.Column("transport_error", sa.Text, nullable=True),
        sa.Column("result_class", postgresql.ENUM(name="check_result_class_enum", create_type=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # audit_logs (ТЗ §4.9)
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity", sa.String(100), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("meta_json", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    # В обратном порядке
    op.execute("DROP TABLE IF EXISTS audit_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS arshin_audit CASCADE")
    op.execute("DROP TABLE IF EXISTS job_issues CASCADE")
    op.execute("DROP TABLE IF EXISTS job_item_checks CASCADE")
    op.execute("DROP TABLE IF EXISTS job_items CASCADE")
    op.execute("DROP TABLE IF EXISTS job_files CASCADE")
    op.execute("DROP TABLE IF EXISTS jobs CASCADE")
    
    # Удаляем issue_code_enum
    op.execute("DROP TYPE IF EXISTS issue_code_enum")
    
    # Пересоздаём старые таблицы (упрощённо)
    op.create_table(
        "file_objects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("object_type", postgresql.ENUM(name="file_object_type_enum", create_type=False), nullable=False),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("storage_bucket", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=True),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("result_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", postgresql.ENUM(name="job_status_enum", create_type=False), nullable=False),
        sa.Column("template_code", sa.String(100), nullable=False),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("total_rows", sa.Integer, default=0, nullable=False),
        sa.Column("total_items", sa.Integer, default=0, nullable=False),
        sa.Column("processed_items", sa.Integer, default=0, nullable=False),
        sa.Column("matched_items", sa.Integer, default=0, nullable=False),
        sa.Column("mismatched_items", sa.Integer, default=0, nullable=False),
        sa.Column("not_found_items", sa.Integer, default=0, nullable=False),
        sa.Column("multiple_match_items", sa.Integer, default=0, nullable=False),
        sa.Column("issue_count", sa.Integer, default=0, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
