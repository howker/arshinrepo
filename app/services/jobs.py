import logging
import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.storage import storage
from app.models.enums import FileObjectType, JobStatus
from app.models.file_object import FileObject
from app.models.job import Job
from app.models.job_issue import JobIssue
from app.models.user import User
from app.workers.tasks import process_excel_job

logger = logging.getLogger(__name__)


def process_job_upload(
    db: Session,
    user: User,
    file: UploadFile,
    template_code: str,
) -> Job:
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are allowed")

    settings = get_settings()
    file_data = file.file.read()
    file_size = len(file_data)
    file_type = (
        file.content_type
        or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    job_uuid = uuid.uuid4()
    storage_key = f"{user.id}/{job_uuid}/{file.filename}"

    try:
        storage.upload_file(
            bucket_name=settings.minio_bucket_source,
            object_name=storage_key,
            data=file_data,
            content_type=file_type,
        )
    except Exception as e:
        logger.error(f"Job {job_uuid} file upload failed: {e}")
        raise HTTPException(status_code=500, detail="Storage upload failed")

    file_obj = FileObject(
        user_id=user.id,
        object_type=FileObjectType.SOURCE,
        original_filename=file.filename,
        storage_bucket=settings.minio_bucket_source,
        storage_key=storage_key,
        size_bytes=file_size,
        content_type=file_type,
    )
    db.add(file_obj)
    db.flush()

    job = Job(
        id=job_uuid,
        user_id=user.id,
        source_file_id=file_obj.id,
        status=JobStatus.UPLOADED,
        template_code=template_code,
        original_filename=file.filename,
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    process_excel_job.delay(str(job.id))
    return job


def get_job_for_user(db: Session, user: User, job_id: uuid.UUID) -> Job:
    stmt = (
        select(Job)
        .options(
            selectinload(Job.source_file),
            selectinload(Job.result_file),
        )
        .where(Job.id == job_id, Job.user_id == user.id)
    )
    job = db.execute(stmt).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
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
            JobIssue.row_number.asc().nullslast(),
            JobIssue.created_at.asc(),
        )
    )
    return list(db.execute(stmt).scalars().all())


def get_job_file_for_user(
    db: Session,
    user: User,
    job_id: uuid.UUID,
    object_type: FileObjectType,
) -> FileObject:
    job = get_job_for_user(db, user, job_id)

    file_obj = job.source_file if object_type == FileObjectType.SOURCE else job.result_file
    if file_obj is None:
        raise HTTPException(status_code=404, detail="File not found")

    return file_obj


def download_job_file_for_user(
    db: Session,
    user: User,
    job_id: uuid.UUID,
    object_type: FileObjectType,
) -> tuple[FileObject, bytes]:
    file_obj = get_job_file_for_user(db, user, job_id, object_type)

    try:
        payload = storage.download_file(
            bucket_name=file_obj.storage_bucket,
            object_name=file_obj.storage_key,
        )
    except Exception as e:
        logger.error(
            "File download failed for job %s (%s): %s",
            job_id,
            object_type.value,
            e,
        )
        raise HTTPException(status_code=500, detail="Storage download failed")

    return file_obj, payload
