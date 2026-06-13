from typing import List
from datetime import date
from app.schemas.devices import ExtractedDeviceDTO
from app.schemas.arshin import ArshinRecordDTO
from app.schemas.comparison import ComparisonResult, ComparisonIssue
from app.models.enums import JobItemStatus
from app.utils.dates import parse_excel_date

def compare_device_with_arshin(
    device: ExtractedDeviceDTO, 
    arshin_records: List[ArshinRecordDTO]
) -> ComparisonResult:
    
    if not arshin_records:
        return ComparisonResult(
            device=device,
            status=JobItemStatus.NOT_FOUND,
            issues=[ComparisonIssue(code="ARSHIN_NOT_FOUND", message="Поверки для данного прибора не найдены")]
        )

    # Стратегия выбора: берем самую свежую поверку (сортировка по убыванию даты)
    records_sorted = sorted(
        arshin_records, 
        key=lambda x: x.verification_date or date.min, 
        reverse=True
    )
    best_match = records_sorted[0]

    issues = []
    status = JobItemStatus.MATCHED

    # Проверка на дубли (информационный warning)
    if len(arshin_records) > 1:
        issues.append(ComparisonIssue(
            code="MULTIPLE_MATCHES", 
            message=f"Найдено {len(arshin_records)} записей, выбрана последняя от {best_match.verification_date}",
            severity="warning"
        ))

    # Сверка: Дата поверки
    ex_v_date = parse_excel_date(device.verification_date_raw)
    if ex_v_date and best_match.verification_date:
        if ex_v_date != best_match.verification_date:
            issues.append(ComparisonIssue(
                code="VERIFICATION_DATE_MISMATCH", 
                message=f"Дата поверки: в файле {ex_v_date.strftime('%d.%m.%Y')}, в Аршине {best_match.verification_date.strftime('%d.%m.%Y')}"
            ))

    # Сверка: Действителен до
    ex_nv_date = parse_excel_date(device.next_verification_date_raw)
    if ex_nv_date and best_match.valid_date:
        if ex_nv_date != best_match.valid_date:
            issues.append(ComparisonIssue(
                code="NEXT_VERIFICATION_DATE_MISMATCH", 
                message=f"Срок действия: в файле {ex_nv_date.strftime('%d.%m.%Y')}, в Аршине {best_match.valid_date.strftime('%d.%m.%Y')}"
            ))

    # Определение итогового статуса
    if any(i.severity == "error" for i in issues):
        status = JobItemStatus.MISMATCH

    return ComparisonResult(
        device=device,
        status=status,
        matched_record=best_match,
        issues=issues
    )
