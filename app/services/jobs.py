import uuid
import logging
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.storage import storage
from app.models.user import User
from app.models.file_object import FileObject
from app.models.job import Job
from app.models.enums import FileObjectType, JobStatus
from app.workers.tasks import process_excel_job

logger = logging.getLogger(__name__)

def process_job_upload(
    db: Session,
    user: User,
    file: UploadFile,
    template_code: str
) -> Job:
    if not file.filename or not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Only .xlsx files are allowed")

    settings = get_settings()
    file_data = file.file.read() 
    file_size = len(file_data)
    file_type = file.content_type or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    
    job_uuid = uuid.uuid4()
    storage_key = f"{user.id}/{job_uuid}/{file.filename}"

    try:
        storage.upload_file(
            bucket_name=settings.minio_bucket_source,
            object_name=storage_key,
            data=file_data,
            content_type=file_type
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
        content_type=file_type
    )
    db.add(file_obj)
    db.flush()

    job = Job(
        id=job_uuid,
        user_id=user.id,
        source_file_id=file_obj.id,
        status=JobStatus.UPLOADED,
        template_code=template_code,
        original_filename=file.filename
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Отправляем задачу в фоновый воркер Celery
    process_excel_job.delay(str(job.id))

    return job
