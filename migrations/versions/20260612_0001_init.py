"""initial schema

Revision ID: 20260612_0001
Revises:
Create Date: 2026-06-12 13:20:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260612_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


user_role_enum = postgresql.ENUM(
    "ADMIN",
    "USER",
    name="user_role_enum",
    create_type=False,
)

job_status_enum = postgresql.ENUM(
    "UPLOADED",
    "QUEUED",
    "PROCESSING",
    "COMPLETED",
    "COMPLETED_WITH_ISSUES",
    "FAILED",
    name="job_status_enum",
    create_type=False,
)

file_object_type_enum = postgresql.ENUM(
    "SOURCE",
    "RESULT",
    name="file_object_type_enum",
    create_type=False,
)

job_item_status_enum = postgresql.ENUM(
    "PENDING",
    "MATCHED",
    "MISMATCH",
    "NOT_FOUND",
    "MULTIPLE_MATCHES",
    "ERROR",
    name="job_item_status_enum",
    create_type=False,
)

job_issue_severity_enum = postgresql.ENUM(
    "INFO",
    "WARNING",
    "ERROR",
    name="job_issue_severity_enum",
    create_type=False,
)

device_type_enum = postgresql.ENUM(
    "SI",
    "CT",
    "VT",
    "OTHER",
    name="device_type_enum",
    create_type=False,
)

check_status_enum = postgresql.ENUM(
    "PENDING",
    "SUCCESS",
    "NOT_FOUND",
    "MULTIPLE_MATCHES",
    "FAILED",
    name="check_status_enum",
    create_type=False,
)

audit_action_enum = postgresql.ENUM(
    "LOGIN",
    "UPLOAD_CREATED",
    "JOB_RUN_REQUESTED",
    "JOB_PROCESSING_STARTED",
    "JOB_PROCESSING_COMPLETED",
    "JOB_PROCESSING_FAILED",
    "FILE_DOWNLOADED",
    name="audit_action_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    user_role_enum.create(bind, checkfirst=True)
    job_status_enum.create(bind, checkfirst=True)
    file_object_type_enum.create(bind, checkfirst=True)
    job_item_status_enum.create(bind, checkfirst=True)
    job_issue_severity_enum.create(bind, checkfirst=True)
    device_type_enum.create(bind, checkfirst=True)
    check_status_enum.create(bind, checkfirst=True)
    audit_action_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "template_profiles",
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("profile_config", sa.JSON(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_template_profiles"),
        sa.UniqueConstraint("code", name="uq_template_profiles_code"),
    )

    op.create_table(
        "file_objects",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("object_type", file_object_type_enum, nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("storage_bucket", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_file_objects_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_file_objects"),
        sa.UniqueConstraint("storage_key", name="uq_file_objects_storage_key"),
    )
    op.create_index("ix_file_objects_user_id", "file_objects", ["user_id"], unique=False)

    op.create_table(
        "jobs",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("result_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", job_status_enum, nullable=False),
        sa.Column("template_code", sa.String(length=100), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column("processed_items", sa.Integer(), nullable=False),
        sa.Column("matched_items", sa.Integer(), nullable=False),
        sa.Column("mismatched_items", sa.Integer(), nullable=False),
        sa.Column("not_found_items", sa.Integer(), nullable=False),
        sa.Column("multiple_match_items", sa.Integer(), nullable=False),
        sa.Column("issue_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["result_file_id"],
            ["file_objects.id"],
            name="fk_jobs_result_file_id_file_objects",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_file_id"],
            ["file_objects.id"],
            name="fk_jobs_source_file_id_file_objects",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_jobs_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_jobs"),
        sa.UniqueConstraint("result_file_id", name="uq_jobs_result_file_id"),
        sa.UniqueConstraint("source_file_id", name="uq_jobs_source_file_id"),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"], unique=False)
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"], unique=False)

    op.create_table(
        "job_items",
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sheet_name", sa.String(length=255), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("row_key", sa.String(length=255), nullable=True),
        sa.Column("device_group", sa.String(length=100), nullable=False),
        sa.Column("device_type", device_type_enum, nullable=False),
        sa.Column("type_raw", sa.String(length=255), nullable=True),
        sa.Column("type_normalized", sa.String(length=255), nullable=True),
        sa.Column("serial_raw", sa.String(length=255), nullable=True),
        sa.Column("serial_normalized", sa.String(length=255), nullable=True),
        sa.Column("verification_date_file", sa.Date(), nullable=True),
        sa.Column("next_verification_date_file", sa.Date(), nullable=True),
        sa.Column("arshin_url_file", sa.String(length=1024), nullable=True),
        sa.Column("excel_cell_type", sa.String(length=20), nullable=True),
        sa.Column("excel_cell_serial", sa.String(length=20), nullable=True),
        sa.Column("excel_cell_verification_date", sa.String(length=20), nullable=True),
        sa.Column("excel_cell_next_verification_date", sa.String(length=20), nullable=True),
        sa.Column("excel_cell_link", sa.String(length=20), nullable=True),
        sa.Column("status", job_item_status_enum, nullable=False),
        sa.Column("comment_summary", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name="fk_job_items_job_id_jobs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_job_items"),
    )
    op.create_index("ix_job_items_job_id", "job_items", ["job_id"], unique=False)
    op.create_index("ix_job_items_status", "job_items", ["status"], unique=False)

    op.create_table(
        "job_item_checks",
        sa.Column("job_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("status", check_status_enum, nullable=False),
        sa.Column("request_url", sa.String(length=1024), nullable=True),
        sa.Column("request_params", sa.JSON(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("response_payload", sa.JSON(), nullable=True),
        sa.Column("transport_error", sa.Text(), nullable=True),
        sa.Column("selected_vri_id", sa.String(length=255), nullable=True),
        sa.Column("selected_mi_type", sa.String(length=255), nullable=True),
        sa.Column("selected_serial_number", sa.String(length=255), nullable=True),
        sa.Column("selected_verification_date", sa.Date(), nullable=True),
        sa.Column("selected_next_verification_date", sa.Date(), nullable=True),
        sa.Column("selected_arshin_url", sa.String(length=1024), nullable=True),
        sa.Column("comparison_payload", sa.JSON(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_item_id"],
            ["job_items.id"],
            name="fk_job_item_checks_job_item_id_job_items",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_job_item_checks"),
    )
    op.create_index("ix_job_item_checks_job_item_id", "job_item_checks", ["job_item_id"], unique=False)
    op.create_index("ix_job_item_checks_status", "job_item_checks", ["status"], unique=False)

    op.create_table(
        "job_issues",
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("severity", job_issue_severity_enum, nullable=False),
        sa.Column("sheet_name", sa.String(length=255), nullable=True),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("cell_ref", sa.String(length=20), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name="fk_job_issues_job_id_jobs",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_item_id"],
            ["job_items.id"],
            name="fk_job_issues_job_item_id_job_items",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_job_issues"),
    )
    op.create_index("ix_job_issues_code", "job_issues", ["code"], unique=False)
    op.create_index("ix_job_issues_job_id", "job_issues", ["job_id"], unique=False)
    op.create_index("ix_job_issues_job_item_id", "job_issues", ["job_item_id"], unique=False)
    op.create_index("ix_job_issues_severity", "job_issues", ["severity"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", audit_action_enum, nullable=False),
        sa.Column("correlation_id", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name="fk_audit_logs_job_id_jobs",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_audit_logs_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index("ix_audit_logs_correlation_id", "audit_logs", ["correlation_id"], unique=False)
    op.create_index("ix_audit_logs_job_id", "audit_logs", ["job_id"], unique=False)
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_job_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_correlation_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_job_issues_severity", table_name="job_issues")
    op.drop_index("ix_job_issues_job_item_id", table_name="job_issues")
    op.drop_index("ix_job_issues_job_id", table_name="job_issues")
    op.drop_index("ix_job_issues_code", table_name="job_issues")
    op.drop_table("job_issues")

    op.drop_index("ix_job_item_checks_status", table_name="job_item_checks")
    op.drop_index("ix_job_item_checks_job_item_id", table_name="job_item_checks")
    op.drop_table("job_item_checks")

    op.drop_index("ix_job_items_status", table_name="job_items")
    op.drop_index("ix_job_items_job_id", table_name="job_items")
    op.drop_table("job_items")

    op.drop_index("ix_jobs_user_id", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_table("jobs")

    op.drop_index("ix_file_objects_user_id", table_name="file_objects")
    op.drop_table("file_objects")

    op.drop_table("template_profiles")
    op.drop_table("users")

    bind = op.get_bind()
    audit_action_enum.drop(bind, checkfirst=True)
    check_status_enum.drop(bind, checkfirst=True)
    device_type_enum.drop(bind, checkfirst=True)
    job_issue_severity_enum.drop(bind, checkfirst=True)
    job_item_status_enum.drop(bind, checkfirst=True)
    file_object_type_enum.drop(bind, checkfirst=True)
    job_status_enum.drop(bind, checkfirst=True)
    user_role_enum.drop(bind, checkfirst=True)
