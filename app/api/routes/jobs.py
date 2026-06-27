from __future__ import annotations

import uuid
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.models.enums import FileObjectType
from app.models.user import User
from app.schemas.jobs import JobIssueResponse, JobResponse, RunJobResponse
from app.services.jobs import (
    download_job_file_for_user,
    get_job_for_user,
    get_job_issues_for_user,
    list_jobs_for_user,
    process_job_upload,
    run_job_for_user,
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def build_download_headers(filename: str) -> dict[str, str]:
    """Создаёт HTTP-заголовки для скачивания файла (ТЗ §13)."""
    ascii_fallback = filename.encode("ascii", errors="ignore").decode("ascii").strip()
    if not ascii_fallback:
        ascii_fallback = "download.xlsx"
    encoded_filename = quote(filename, safe="")
    return {
        "Content-Disposition": (
            f"attachment; filename=\"{ascii_fallback}\"; "
            f"filename*=UTF-8''{encoded_filename}"
        )
    }


def extract_filename_from_path(path: str) -> str:
    """Извлекает имя файла из пути."""
    return Path(path).name


@router.post("/upload", response_model=JobResponse)
def upload_excel_job(
    file: UploadFile = File(...),
    template_code: str = Form(get_settings().default_template_code),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Загрузка .xlsx файла (ТЗ §13)."""
    job = process_job_upload(db, current_user, file, template_code)
    return job


@router.get("", response_model=list[JobResponse])
def list_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Список jobs пользователя (ТЗ §13)."""
    return list_jobs_for_user(db, current_user)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить job по ID (ТЗ §13)."""
    return get_job_for_user(db, current_user, job_id)


@router.post("/{job_id}/run", response_model=RunJobResponse)
def run_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Запустить обработку job (ТЗ §13)."""
    job = run_job_for_user(db, current_user, job_id)
    return RunJobResponse(job_id=job.id, status=job.status)


@router.get("/{job_id}/issues", response_model=list[JobIssueResponse])
def get_job_issues(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить список проблем job (ТЗ §13)."""
    return get_job_issues_for_user(db, current_user, job_id)


@router.get("/{job_id}/download/source")
def download_job_source(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Скачать исходный .xlsx файл (ТЗ §13)."""
    file_obj, payload = download_job_file_for_user(
        db,
        current_user,
        job_id,
        FileObjectType.SOURCE,
    )
    filename = extract_filename_from_path(file_obj.path)
    headers = build_download_headers(filename)
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.get("/{job_id}/download/result")
def download_job_result(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Скачать результат .xlsx файл (ТЗ §13)."""
    file_obj, payload = download_job_file_for_user(
        db,
        current_user,
        job_id,
        FileObjectType.RESULT,
    )
    filename = extract_filename_from_path(file_obj.path)
    headers = build_download_headers(filename)
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
