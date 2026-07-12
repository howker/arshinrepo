"""Celery задача обработки Excel (ТЗ раздел 15)."""
from __future__ import annotations

import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from celery import shared_task

from app.core.db import SessionLocal
from app.core.config import get_settings
from app.core.storage import storage
from app.models.job import Job
from app.models.job_item import JobItem
from app.models.file_object import FileObject
from app.models.job_item_check import JobItemCheck
from app.models.job_issue import JobIssue
from app.models.arshin_audit import ArshinAudit
from app.models.enums import (
    JobStatus,
    FileObjectType,
    JobItemStatus,
    JobIssueSeverity,
    IssueCode,
    CheckResultClass,
)
from app.excel.parser import TemplateDrivenParser, TemplateNotMatchedError
from app.excel.annotator import ExcelAnnotator
from app.clients.arshin import arshin_client, ArshinRateLimitError, ArshinUpstreamUnavailableError
from app.services.matcher import select_best_match, ensure_date
from app.services.mitnumber_registry import mitnumber_resolver
from app.services.comparator import compare_device
from app.services.report import build_report, save_report_to_json

logger = logging.getLogger(__name__)


@shared_task(name="process_excel_job")
def process_excel_job(job_id_str: str) -> str:
    """Основная задача обработки Excel (последовательный пайплайн)."""
    db = SessionLocal()
    settings = get_settings()
    job = db.query(Job).filter(Job.id == job_id_str).first()
    if not job:
        logger.error("Job %s not found", job_id_str)
        db.close()
        return "Job not found"

    logger.info("Starting processing job %s", job_id_str)

    job.status = JobStatus.PROCESSING
    job.started_at = datetime.now(timezone.utc)
    job.error_message = None
    db.commit()

    counts = {
        "matched": 0,
        "mismatch": 0,
        "ambiguous": 0,
        "source_uncertain": 0,
        "placeholder": 0,
    }

    try:
        # 1. Получаем путь к исходному файлу
        source_path = job.source_file_path
        full_source_path = get_settings().storage_root / source_path

        if not full_source_path.exists():
            raise FileNotFoundError(f"Source file not found: {full_source_path}")

        # 2. Парсинг Excel
        parser = TemplateDrivenParser(template_code="pril_1_main")
        devices = parser.parse_workspace_file(str(full_source_path))

        if not devices:
            logger.warning("No devices found in file %s", job_id_str)
            job.status = JobStatus.COMPLETED
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
            db.close()
            return "No devices found"

        job.total_items = len(devices)
        db.commit()

        # 3. Последовательная обработка каждого прибора
        arshin_client.clear_cache()
        all_results = []

        for idx, device in enumerate(devices, 1):
            db.refresh(job)
            if job.status == JobStatus.CANCELLED:
                logger.info("Job %s cancelled before device %d/%d", job_id_str, idx, len(devices))
                job.finished_at = datetime.now(timezone.utc)
                db.commit()
                db.close()
                return f"Cancelled after {idx - 1} of {len(devices)} devices"

            try:
                logger.info("Processing device %d/%d: %s", idx, len(devices), device.get('serial_norm'))

                # 3a. Определяем семейство госреестра по типу из файла.
                # Без этого короткий серийник даёт тысячи чужих приборов,
                # и нужный может вообще не попасть в выдачу.
                serial_norm = device.get('serial_norm')
                type_norm = device.get('type_norm')
                type_raw = device.get('type_raw')

                mitnumbers = None
                try:
                    mitnumbers, fam_info = mitnumber_resolver.resolve(db, type_raw or type_norm)
                    if mitnumbers:
                        logger.info(
                            "Device %s: family %s -> %s", serial_norm, fam_info, mitnumbers
                        )
                    else:
                        logger.warning(
                            "Device %s: family not resolved (%s)", serial_norm, fam_info
                        )
                except Exception as e:
                    logger.warning("Mitnumber resolve failed for %s: %s", serial_norm, e)

                # 3b. Живой запрос к Аршину (с фильтром по семейству, если он есть)
                arshin_result = arshin_client.search_by_serial(
                    serial_norm=serial_norm,
                    type_norm=type_norm,
                    job_id=job.id,
                    mitnumbers=mitnumbers,
                )

                # 3c. Матчинг по строгому контракту
                match_result = select_best_match(
                    item_serial_norm=serial_norm,
                    item_type_norm=type_norm,
                    arshin_result=arshin_result,
                    item_type_raw=type_raw,
                    owner_context=device.get('context', {}),
                )

                # 3d. Сравнение
                comp_result = compare_device(device, match_result)

                # 3d. Сохраняем JobItem
                job_item = JobItem(
                    job_id=job.id,
                    sheet_name=device.get('sheet_name', ''),
                    excel_row=device.get('excel_row', 0),
                    device_kind=device.get('device_kind', ''),
                    block_code=device.get('block_code', ''),
                    type_raw=device.get('type_raw'),
                    type_norm=device.get('type_norm'),
                    serial_raw=device.get('serial_raw'),
                    serial_norm=device.get('serial_norm'),
                    accuracy_class_raw=device.get('accuracy_class_raw'),
                    verification_date_file_raw=device.get('verification_date_raw'),
                    verification_date_file_norm=device.get('verification_date_norm') if isinstance(device.get('verification_date_norm'), datetime) else device.get('verification_date_norm'),
                    next_date_file_raw=device.get('next_date_raw'),
                    next_date_file_norm=device.get('next_date_norm') if isinstance(device.get('next_date_norm'), datetime) else device.get('next_date_norm'),
                    link_file_raw=device.get('link_raw'),
                    link_file_vri=device.get('link_vri'),
                    cell_type=device.get('cell_refs', {}).get('type'),
                    cell_serial=device.get('cell_refs', {}).get('serial'),
                    cell_verification_date=device.get('cell_refs', {}).get('verification_date'),
                    cell_next_date=device.get('cell_refs', {}).get('next_date'),
                    cell_link=device.get('cell_refs', {}).get('link'),
                    context_json=device.get('context', {}),
                    status=comp_result.status,
                )
                db.add(job_item)
                db.flush()

                # 3e. Сохраняем JobItemCheck
                selected = match_result.selected or {}
                job_check = JobItemCheck(
                    job_item_id=job_item.id,
                    arshin_found=bool(selected),
                    selected_vri_id=selected.get("vri_id"),
                    selected_url=selected.get("card_url"),
                    arshin_type=selected.get("mi_type"),
                    arshin_serial=selected.get("mi_number"),
                    arshin_verification_date=ensure_date(selected.get("verification_date")),
                    arshin_valid_date=ensure_date(selected.get("valid_date")),
                    arshin_applicability=selected.get("applicability"),
                    candidates_count=match_result.candidates_count,
                    decision_reason=match_result.decision_reason,
                    result_class=match_result.result_class,
                )
                db.add(job_check)

                # 3f. Сохраняем JobIssues
                for issue in comp_result.issues:
                    job_issue = JobIssue(
                        job_id=job.id,
                        job_item_id=job_item.id,
                        sheet_name=device.get('sheet_name'),
                        cell=issue.cell_ref,
                        severity=issue.severity,
                        code=issue.code,
                        message=issue.message,
                    )
                    db.add(job_issue)

                # 3g. Сохраняем аудит запроса (ТЗ §4.7)
                arshin_audit = ArshinAudit(
                    job_id=job.id,
                    job_item_id=job_item.id,
                    attempt_no=arshin_result.attempts,
                    endpoint_mode=get_settings().arshin_api_mode,
                    request_url=arshin_result.request_url or "",
                    request_params_json=arshin_result.request_params,
                    http_status=arshin_result.http_status,
                    response_time_ms=arshin_result.response_time_ms,
                    response_body_json=arshin_result.raw_response,
                    transport_error=arshin_result.transport_error,
                    result_class=arshin_result.result_class,
                )
                db.add(arshin_audit)

                # 3h. Сохраняем результат для аннотации
                result_for_annot = {
                    'excel_row': device.get('excel_row'),
                    'device_kind': device.get('device_kind'),
                    'issues': [
                        {
                            'cell_ref': issue.cell_ref,
                            'severity': issue.severity,
                            'message': issue.message,
                        }
                        for issue in comp_result.issues
                    ],
                    'selected_url': comp_result.selected_url,
                }
                all_results.append(result_for_annot)

                # 3i. Обновляем счётчики
                if comp_result.status == JobItemStatus.MATCHED:
                    counts['matched'] += 1
                elif comp_result.status == JobItemStatus.MISMATCH:
                    counts['mismatch'] += 1
                elif comp_result.status == JobItemStatus.AMBIGUOUS:
                    counts['ambiguous'] += 1
                elif comp_result.status == JobItemStatus.SOURCE_UNCERTAIN:
                    counts['source_uncertain'] += 1
                elif comp_result.status == JobItemStatus.PLACEHOLDER:
                    counts['placeholder'] += 1

                # Сохраняем прогресс
                job.matched_count = counts['matched']
                job.mismatch_count = counts['mismatch']
                job.ambiguous_count = counts['ambiguous']
                job.source_uncertain_count = counts['source_uncertain']
                job.placeholder_count = counts['placeholder']
                db.commit()

            except Exception as e:
                logger.error("Device processing failed: %s", str(e), extra={"device": device})
                # Создаём запись о неудачном приборе
                job_item = JobItem(
                    job_id=job.id,
                    sheet_name=device.get('sheet_name', ''),
                    excel_row=device.get('excel_row', 0),
                    device_kind=device.get('device_kind', ''),
                    block_code=device.get('block_code', ''),
                    type_raw=device.get('type_raw'),
                    type_norm=device.get('type_norm'),
                    serial_raw=device.get('serial_raw'),
                    serial_norm=device.get('serial_norm'),
                    status=JobItemStatus.SOURCE_UNCERTAIN,
                )
                db.add(job_item)
                db.flush()

                job_issue = JobIssue(
                    job_id=job.id,
                    job_item_id=job_item.id,
                    sheet_name=device.get('sheet_name'),
                    cell=device.get('cell_refs', {}).get('serial'),
                    severity=JobIssueSeverity.YELLOW,
                    code=IssueCode.SOURCE_UNCERTAIN,
                    message=f"Ошибка обработки прибора: {str(e)}",
                )
                db.add(job_issue)
                counts['source_uncertain'] += 1
                job.source_uncertain_count = counts['source_uncertain']
                db.commit()
                continue

        # 4. Аннотация Excel
        annotator = ExcelAnnotator(template_code="pril_1_main")
        result_filename = f"RESULT_{job.source_filename}"
        result_relative_path = f"results/{job.id}/{result_filename}"
        full_result_path = get_settings().storage_root / result_relative_path

        full_result_path.parent.mkdir(parents=True, exist_ok=True)

        annotator.annotate_and_save(
            input_path=str(full_source_path),
            output_path=str(full_result_path),
            results=all_results,
        )

        job.result_file_path = result_relative_path

        # Регистрируем результат как FileObject, чтобы его можно было скачать
        result_size = full_result_path.stat().st_size
        result_file_obj = FileObject(
            job_id=job.id,
            kind=FileObjectType.RESULT,
            path=result_relative_path,
            size_bytes=result_size,
        )
        db.add(result_file_obj)

        # 5. Генерация отчёта
        report = build_report(
            job_id=job.id,
            status=job.status,
            source_filename=job.source_filename,
            total_items=job.total_items,
            counts=counts,
            issues_by_item={},
            started_at=job.started_at,
            finished_at=datetime.now(timezone.utc),
        )
        job.report_json = report

        # 6. Финальный статус
        if counts['mismatch'] > 0 or counts['ambiguous'] > 0 or counts['source_uncertain'] > 0 or counts['placeholder'] > 0:
            job.status = JobStatus.COMPLETED_WITH_ISSUES
        else:
            job.status = JobStatus.COMPLETED

        job.finished_at = datetime.now(timezone.utc)
        db.commit()

        logger.info("Job %s completed", job_id_str)
        db.close()
        return "Job completed"

    except TemplateNotMatchedError as e:
        logger.error("Template not matched: %s", e)
        job.status = JobStatus.FAILED
        job.error_message = f"Template not matched: {e}"
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.close()
        return f"Failed: {e}"

    except (ArshinRateLimitError, ArshinUpstreamUnavailableError) as e:
        logger.error("Arshin upstream error: %s", e)
        job.status = JobStatus.FAILED_SOURCE_UNAVAILABLE
        job.error_message = f"Arshin unavailable: {e}"
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.close()
        return f"Failed: {e}"

    except Exception as e:
        logger.exception("Job processing failed")
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.close()
        return f"Failed: {e}"
