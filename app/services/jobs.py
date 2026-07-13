from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.storage import storage
from app.models.enums import FileObjectType, JobStatus
from app.models.file_object import FileObject
from app.models.job import Job
from app.models.job_issue import JobIssue
from app.models.user import User
from app.workers.tasks import process_excel_job

logger = logging.getLogger(__name__)


def _source_relative_path(job_id: uuid.UUID, filename: str) -> str:
    """Путь к исходнику относительно storage_root (ТЗ §5)."""
    return f"uploads/{job_id}/source/{filename}"


def _result_relative_path(job_id: uuid.UUID, filename: str) -> str:
    """Путь к результату относительно storage_root (ТЗ §5)."""
    return f"results/{job_id}/{filename}"


def process_job_upload(
    db: Session,
    user: User,
    file: UploadFile,
    template_code: str,
) -> Job:
    """Загрузка .xlsx файла и создание Job в статусе UPLOADED (ТЗ §13)."""
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are allowed")

    settings = get_settings()
    file_data = file.file.read()
    file_size = len(file_data)

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max {settings.max_upload_mb} MB",
        )

    job_uuid = uuid.uuid4()
    relative_path = _source_relative_path(job_uuid, file.filename)

    try:
        storage.upload_file(relative_path=relative_path, data=file_data)
    except Exception as e:
        logger.error("Job %s file upload failed: %s", job_uuid, e)
        raise HTTPException(status_code=500, detail="Storage upload failed")

    job = Job(
        id=job_uuid,
        user_id=user.id,
        status=JobStatus.UPLOADED,
        source_filename=file.filename,
        source_file_path=relative_path,
    )
    db.add(job)
    db.flush()  # Job вставлен в jobs — job_id теперь существует для FK

    file_obj = FileObject(
        job_id=job_uuid,
        kind=FileObjectType.SOURCE,
        path=relative_path,
        size_bytes=file_size,
    )
    db.add(file_obj)

    db.commit()
    db.refresh(job)

    return job


def list_jobs_for_user(db: Session, user: User) -> list[Job]:
    stmt = (
        select(Job)
        .where(Job.user_id == user.id)
        .order_by(Job.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def get_job_for_user(db: Session, user: User, job_id: uuid.UUID) -> Job:
    stmt = (
        select(Job)
        .where(Job.id == job_id, Job.user_id == user.id)
    )
    job = db.execute(stmt).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def run_job_for_user(db: Session, user: User, job_id: uuid.UUID) -> Job:
    """Постановка задачи в очередь (ТЗ §13)."""
    job = get_job_for_user(db, user, job_id)

    if job.status in {JobStatus.QUEUED, JobStatus.PROCESSING}:
        return job

    if job.status not in {JobStatus.UPLOADED, JobStatus.FAILED, JobStatus.FAILED_SOURCE_UNAVAILABLE}:
        raise HTTPException(
            status_code=409,
            detail=f"Job with status '{job.status.value}' cannot be re-queued",
        )

    # Приоритет по размеру файла: короткие проверки не должны ждать
    # часами за чужим большим файлом (защита времени метролога).
    from datetime import datetime, timezone
    from app.core.config import get_settings
    from app.services.queue import count_devices_in_file, priority_for_items

    settings = get_settings()
    full_path = settings.storage_root / job.source_file_path
    total = count_devices_in_file(str(full_path), settings.default_template_code)
    priority = priority_for_items(total)

    job.status = JobStatus.QUEUED
    job.error_message = None
    job.priority = priority
    job.queued_at = datetime.now(timezone.utc)
    if total:
        job.total_items = total
    db.add(job)
    db.commit()
    db.refresh(job)

    logger.info(
        "Job %s поставлен в очередь: приборов=%s, приоритет=%s", job.id, total, priority
    )
    process_excel_job.apply_async(args=[str(job.id)], priority=priority)
    return job


def cancel_job_for_user(db: Session, user: User, job_id: uuid.UUID) -> Job:
    """Отмена задачи (кооперативная, проверяется воркером перед каждым СИ)."""
    job = get_job_for_user(db, user, job_id)

    if job.status not in {JobStatus.QUEUED, JobStatus.PROCESSING}:
        raise HTTPException(
            status_code=409,
            detail=f"Job with status '{job.status.value}' cannot be cancelled",
        )

    job.status = JobStatus.CANCELLED
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info("Job %s cancellation requested by user %s", job.id, user.id)
    return job


def get_job_issues_for_user(
    db: Session,
    user: User,
    job_id: uuid.UUID,
) -> list[JobIssue]:
    get_job_for_user(db, user, job_id)

    stmt = (
        select(JobIssue)
        .where(JobIssue.job_id == job_id)
        .order_by(
            JobIssue.cell.asc().nullslast(),
            JobIssue.created_at.asc(),
        )
    )
    return list(db.execute(stmt).scalars().all())


def get_job_file_for_user(
    db: Session,
    user: User,
    job_id: uuid.UUID,
    kind: FileObjectType,
) -> FileObject:
    """Найти FileObject по job_id + kind (ТЗ §4.3)."""
    get_job_for_user(db, user, job_id)

    stmt = select(FileObject).where(
        FileObject.job_id == job_id,
        FileObject.kind == kind,
    )
    file_obj = db.execute(stmt).scalar_one_or_none()
    if file_obj is None:
        raise HTTPException(status_code=404, detail="File not found")
    return file_obj


def download_job_file_for_user(
    db: Session,
    user: User,
    job_id: uuid.UUID,
    kind: FileObjectType,
) -> tuple[FileObject, bytes]:
    """Скачать файл из локального хранилища (ТЗ §5, §13)."""
    file_obj = get_job_file_for_user(db, user, job_id, kind)

    try:
        payload = storage.download_file(file_obj.path)
    except FileNotFoundError:
        logger.error("File not found on disk: %s", file_obj.path)
        raise HTTPException(status_code=404, detail="File not found on storage")
    except Exception as e:
        logger.error("File download failed for job %s (%s): %s", job_id, kind.value, e)
        raise HTTPException(status_code=500, detail="Storage download failed")

    return file_obj, payload
