import os
import tempfile
import logging
from datetime import datetime, timezone
from celery import shared_task
from app.core.db import SessionLocal
from app.core.config import get_settings
from app.core.storage import storage
from app.models.job import Job
from app.models.file_object import FileObject
from app.models.job_item import JobItem
from app.models.job_issue import JobIssue
from app.models.enums import (
    DeviceType,
    FileObjectType,
    JobIssueSeverity,
    JobItemStatus,
    JobStatus,
)
from app.excel.parser import TemplateDrivenParser
from app.clients.arshin import ArshinRateLimitError, ArshinUpstreamUnavailableError, arshin_client
from app.services.comparator import compare_device_with_arshin
from app.excel.annotator import ExcelAnnotator
from app.utils.dates import parse_excel_date

logger = logging.getLogger(__name__)


def _map_issue_severity(value: str | None) -> JobIssueSeverity:
    normalized = (value or "error").strip().lower()
    if normalized == "info":
        return JobIssueSeverity.INFO
    if normalized == "warning":
        return JobIssueSeverity.WARNING
    return JobIssueSeverity.ERROR

@shared_task(name="process_excel_job")
def process_excel_job(job_id_str: str):
    db = SessionLocal()
    settings = get_settings()
    job = db.query(Job).filter(Job.id == job_id_str).first()
    if not job:
        db.close()
        return "Job not found"
    
    job.status = JobStatus.PROCESSING
    job.started_at = datetime.now(timezone.utc)
    job.finished_at = None
    job.error_message = None
    job.result_file_id = None

    job.total_items = 0
    job.processed_items = 0
    job.matched_items = 0
    job.mismatched_items = 0
    job.not_found_items = 0
    job.multiple_match_items = 0
    job.issue_count = 0

    db.query(JobIssue).filter(JobIssue.job_id == job.id).delete(synchronize_session=False)
    db.query(JobItem).filter(JobItem.job_id == job.id).delete(synchronize_session=False)
    db.commit()

    try:
        source_file = db.query(FileObject).filter(FileObject.id == job.source_file_id).first()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.xlsx")
            output_path = os.path.join(tmpdir, "result.xlsx")
            
            # 1. Качаем файл из MinIO
            response = storage.client.get_object(source_file.storage_bucket, source_file.storage_key)
            with open(input_path, "wb") as f:
                f.write(response.read())
            response.close()
            response.release_conn()

            # 2. Парсим файл
            parser = TemplateDrivenParser(template_code=job.template_code)
            devices = parser.parse_workspace_file(input_path)
            
            unique_rows = {dev.row_number for dev in devices}
            job.total_rows = len(unique_rows)
            job.total_items = len(devices)
            db.commit()

            results = []
            sheet_name = parser.config.get("sheet_name") or "active"

            # 3. Сверяем с Аршином
            for dev in devices:
                arshin_records = arshin_client.search_device(dev.type_val, dev.serial_number)
                comp_res = compare_device_with_arshin(dev, arshin_records)
                results.append(comp_res)

                has_multiple_matches = any(issue.code == "MULTIPLE_MATCHES" for issue in comp_res.issues)
                comment_summary = "; ".join(issue.message for issue in comp_res.issues) or None

                job_item = JobItem(
                    job_id=job.id,
                    sheet_name=sheet_name,
                    row_number=dev.row_number,
                    row_key=f"{sheet_name}:{dev.row_number}:{dev.group_name}",
                    device_group=dev.group_name,
                    device_type=DeviceType.SI,
                    type_raw=dev.type_val,
                    type_normalized=dev.type_val.strip() if dev.type_val else None,
                    serial_raw=dev.serial_number,
                    serial_normalized=dev.serial_number.strip(),
                    verification_date_file=parse_excel_date(dev.verification_date_raw),
                    next_verification_date_file=parse_excel_date(dev.next_verification_date_raw),
                    arshin_url_file=dev.arshin_link_raw,
                    status=comp_res.status,
                    comment_summary=comment_summary,
                )
                db.add(job_item)
                db.flush()

                matched_record_payload = (
                    comp_res.matched_record.model_dump(mode="json")
                    if comp_res.matched_record
                    else None
                )

                for issue in comp_res.issues:
                    db.add(
                        JobIssue(
                            job_id=job.id,
                            job_item_id=job_item.id,
                            code=issue.code,
                            severity=_map_issue_severity(issue.severity),
                            sheet_name=sheet_name,
                            row_number=dev.row_number,
                            cell_ref=None,
                            message=issue.message,
                            details={
                                "group_name": dev.group_name,
                                "serial_number": dev.serial_number,
                                "type_val": dev.type_val,
                                "sub_company": dev.sub_company,
                                "object_name": dev.object_name,
                                "connection_point": dev.connection_point,
                                "matched_record": matched_record_payload,
                            },
                        )
                    )

                job.processed_items += 1
                job.issue_count += len(comp_res.issues)

                if comp_res.status == JobItemStatus.MATCHED:
                    job.matched_items += 1
                elif comp_res.status == JobItemStatus.NOT_FOUND:
                    job.not_found_items += 1
                else:
                    job.mismatched_items += 1

                if has_multiple_matches:
                    job.multiple_match_items += 1

                db.commit()

            # 4. Размечаем итоговый Excel
            annotator = ExcelAnnotator(template_code=job.template_code)
            annotator.annotate_and_save(input_path, output_path, results)
            
            # 5. Грузим результат обратно в MinIO
            with open(output_path, "rb") as f:
                result_data = f.read()
                
            result_key = f"{job.user_id}/{job.id}/RESULT_{job.original_filename}"
            storage.upload_file(
                bucket_name=settings.minio_bucket_result,
                object_name=result_key,
                data=result_data,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            res_file = FileObject(
                user_id=job.user_id,
                object_type=FileObjectType.RESULT,
                original_filename=f"RESULT_{job.original_filename}",
                storage_bucket=settings.minio_bucket_result,
                storage_key=result_key,
                size_bytes=len(result_data),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            db.add(res_file)
            db.flush()
            
            job.result_file_id = res_file.id
            job.status = (
                JobStatus.COMPLETED_WITH_ISSUES
                if job.issue_count > 0
                else JobStatus.COMPLETED
            )
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
            
    except ArshinRateLimitError as e:
        logger.warning("Job processing failed due to Arshin rate limit", extra={"job_id": job_id_str})
        job.status = JobStatus.FAILED
        job.error_message = f"ARSHIN_RATE_LIMIT: {e}"
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
    except ArshinUpstreamUnavailableError as e:
        logger.warning("Job processing failed due to Arshin upstream unavailability", extra={"job_id": job_id_str})
        job.status = JobStatus.FAILED
        job.error_message = f"ARSHIN_UPSTREAM_UNAVAILABLE: {e}"
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as e:
        logger.exception("Job processing failed", extra={"job_id": job_id_str})
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()
        
    return "Job Finished Successfully"
