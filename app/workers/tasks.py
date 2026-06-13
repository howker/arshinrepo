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
from app.models.enums import JobStatus, FileObjectType, JobItemStatus
from app.excel.parser import TemplateDrivenParser
from app.clients.arshin import arshin_client
from app.services.comparator import compare_device_with_arshin
from app.excel.annotator import ExcelAnnotator

logger = logging.getLogger(__name__)

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
            
            job.total_items = len(devices)
            db.commit()

            results = []
            issue_count = 0
            
            # 3. Сверяем с Аршином
            for dev in devices:
                arshin_records = arshin_client.search_device(dev.type_val, dev.serial_number)
                comp_res = compare_device_with_arshin(dev, arshin_records)
                results.append(comp_res)
                issue_count += len(comp_res.issues)
                
                job.processed_items += 1
                if comp_res.status == JobItemStatus.MATCHED:
                    job.matched_items += 1
                elif comp_res.status == JobItemStatus.NOT_FOUND:
                    job.not_found_items += 1
                else:
                    job.mismatched_items += 1
            
            job.issue_count = issue_count

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
            job.status = JobStatus.COMPLETED
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
            
    except Exception as e:
        logger.exception("Job processing failed")
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()
        
    return "Job Finished Successfully"
