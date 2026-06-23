from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.enums import FileObjectType
from app.models.user import User
from app.schemas.jobs import JobIssueResponse, JobResponse
from app.services.jobs import (
    download_job_file_for_user,
    get_job_for_user,
    get_job_issues_for_user,
    process_job_upload,
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def build_download_headers(filename: str) -> dict[str, str]:
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


@router.post("/upload", response_model=JobResponse)
def upload_excel_job(
    file: UploadFile = File(...),
    template_code: str = Form("pril_1_main"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = process_job_upload(db, current_user, file, template_code)
    return job


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_job_for_user(db, current_user, job_id)


@router.get("/{job_id}/issues", response_model=list[JobIssueResponse])
def get_job_issues(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_job_issues_for_user(db, current_user, job_id)


@router.get("/{job_id}/download/source")
def download_job_source(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_obj, payload = download_job_file_for_user(
        db,
        current_user,
        job_id,
        FileObjectType.SOURCE,
    )
    media_type = (
        file_obj.content_type
        or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    headers = build_download_headers(file_obj.original_filename)
    return Response(content=payload, media_type=media_type, headers=headers)


@router.get("/{job_id}/download/result")
def download_job_result(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_obj, payload = download_job_file_for_user(
        db,
        current_user,
        job_id,
        FileObjectType.RESULT,
    )
    media_type = (
        file_obj.content_type
        or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    headers = build_download_headers(file_obj.original_filename)
    return Response(content=payload, media_type=media_type, headers=headers)
