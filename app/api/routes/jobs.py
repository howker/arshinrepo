from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.jobs import JobResponse
from app.services.jobs import process_job_upload

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.post("/upload", response_model=JobResponse)
def upload_excel_job(
    file: UploadFile = File(...),
    template_code: str = Form("pril_1_main"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = process_job_upload(db, current_user, file, template_code)
    return job
