"""Сравнение данных файла с выбранной записью Аршина (ТЗ раздел 11)."""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from app.models.enums import IssueCode, JobIssueSeverity, JobItemStatus, CheckResultClass
from app.excel.normalize import to_canonical_date, extract_vri_from_link
from app.services.matcher import normalize_serial_for_gate, normalize_type_for_score, ensure_date

logger = logging.getLogger(__name__)


class Issue:
    def __init__(self, code: IssueCode, severity: JobIssueSeverity, message: str, cell_ref: str | None = None):
        self.code = code
        self.severity = severity
        self.message = message
        self.cell_ref = cell_ref


class ComparisonResult:
    def __init__(self, status: JobItemStatus, issues: list[Issue], selected_url: str | None = None):
        self.status = status
        self.issues = issues
        self.selected_url = selected_url


def compare_device(
    device: dict,
    match_result,
) -> ComparisonResult:
    """Сравнение прибора с выбранной записью Аршина (ТЗ 11)."""
    issues = []
    selected = match_result.selected
    status = JobItemStatus.MATCHED

    if not selected:
        if match_result.result_class == CheckResultClass.SUCCESS_EMPTY:
            status = JobItemStatus.SOURCE_UNCERTAIN
            issues.append(Issue(
                code=IssueCode.ARSHIN_NOT_FOUND,
                severity=JobIssueSeverity.YELLOW,
                message="Не удалось найти запись в Аршине после ретраев. Возможно, прибор отсутствует в реестре.",
                cell_ref=device.get('cell_refs', {}).get('serial'),
            ))
        elif match_result.result_class == CheckResultClass.AMBIGUOUS_MULTIPLE_MATCHES:
            status = JobItemStatus.AMBIGUOUS
            issues.append(Issue(
                code=IssueCode.MULTIPLE_MATCHES,
                severity=JobIssueSeverity.ORANGE,
                message=f"Неоднозначный выбор: {match_result.decision_reason}",
                cell_ref=device.get('cell_refs', {}).get('serial'),
            ))
        else:
            status = JobItemStatus.SOURCE_UNCERTAIN
            issues.append(Issue(
                code=IssueCode.SOURCE_UNCERTAIN,
                severity=JobIssueSeverity.YELLOW,
                message="Аршин вернул пустой ответ (транзиентная ошибка). Проверьте позже.",
                cell_ref=device.get('cell_refs', {}).get('serial'),
            ))
        return ComparisonResult(status, issues)

    # FIX: при AMBIGUOUS добавляем issue, но НЕ делаем ранний return —
    # проверки дат и ссылок выполняются всегда.
    if match_result.result_class == CheckResultClass.AMBIGUOUS_MULTIPLE_MATCHES:
        status = JobItemStatus.AMBIGUOUS
        issues.append(Issue(
            code=IssueCode.MULTIPLE_MATCHES,
            severity=JobIssueSeverity.ORANGE,
            message=f"Неоднозначный выбор: {match_result.decision_reason}",
            cell_ref=device.get('cell_refs', {}).get('serial'),
        ))

    file_type = device.get('type_norm')
    arshin_type = normalize_type_for_score(selected.get('mi_type', ''))
    if file_type and arshin_type:
        if normalize_type_for_score(file_type) != arshin_type:
            status = JobItemStatus.MISMATCH
            issues.append(Issue(
                code=IssueCode.TYPE_MISMATCH,
                severity=JobIssueSeverity.RED,
                message=f"Несовпадение типа: в файле {file_type}, в Аршине {arshin_type}",
                cell_ref=device.get('cell_refs', {}).get('type'),
            ))

    file_serial = device.get('serial_norm')
    arshin_serial = normalize_serial_for_gate(selected.get('mi_number', ''))
    if file_serial and arshin_serial:
        if file_serial != arshin_serial:
            status = JobItemStatus.MISMATCH
            issues.append(Issue(
                code=IssueCode.SERIAL_MISMATCH,
                severity=JobIssueSeverity.RED,
                message=f"Несовпадение серийного номера: в файле {file_serial}, в Аршине {arshin_serial}",
                cell_ref=device.get('cell_refs', {}).get('serial'),
            ))

    # FIX: даты нормализуются через ensure_date() перед сравнением
    file_vd = device.get('verification_date_norm')
    arshin_vd_raw = selected.get('verification_date')

    if file_vd == "INVALID":
        status = JobItemStatus.MISMATCH
        issues.append(Issue(
            code=IssueCode.PLACEHOLDER_VALUE_DETECTED,
            severity=JobIssueSeverity.RED,
            message="Некорректное значение даты в файле (заглушка: 31.12.1899 или 0)",
            cell_ref=device.get('cell_refs', {}).get('verification_date'),
        ))
    else:
        file_vd_date = ensure_date(file_vd)
        arshin_vd_date = ensure_date(arshin_vd_raw)
        if file_vd_date and arshin_vd_date:
            if file_vd_date != arshin_vd_date:
                status = JobItemStatus.MISMATCH
                issues.append(Issue(
                    code=IssueCode.VERIFICATION_DATE_MISMATCH,
                    severity=JobIssueSeverity.RED,
                    message=f"Несовпадение даты поверки: в файле {file_vd_date}, в Аршине {arshin_vd_date}",
                    cell_ref=device.get('cell_refs', {}).get('verification_date'),
                ))

    file_nd = device.get('next_date_norm')
    arshin_valid_raw = selected.get('valid_date')

    if file_nd == "INVALID":
        status = JobItemStatus.MISMATCH
        issues.append(Issue(
            code=IssueCode.PLACEHOLDER_VALUE_DETECTED,
            severity=JobIssueSeverity.RED,
            message="Некорректное значение даты след. поверки в файле (заглушка)",
            cell_ref=device.get('cell_refs', {}).get('next_date'),
        ))
    else:
        file_nd_date = ensure_date(file_nd)
        arshin_valid_date = ensure_date(arshin_valid_raw)
        if file_nd_date and arshin_valid_date:
            if file_nd_date != arshin_valid_date:
                status = JobItemStatus.MISMATCH
                issues.append(Issue(
                    code=IssueCode.NEXT_VERIFICATION_DATE_MISMATCH,
                    severity=JobIssueSeverity.RED,
                    message=f"Несовпадение даты след. поверки: в файле {file_nd_date}, в Аршине {arshin_valid_date}",
                    cell_ref=device.get('cell_refs', {}).get('next_date'),
                ))

    # FIX: сравниваем и извлечённый VRI, и сырую ссылку (если VRI не извлёкся — это MISMATCH)
    selected_url = selected.get('card_url')
    file_link_vri = device.get('link_vri')
    file_link_raw = device.get('link_raw')

    if file_link_vri and selected_url:
        arshin_vri_num = extract_vri_from_link(selected_url)
        if arshin_vri_num and file_link_vri != arshin_vri_num:
            status = JobItemStatus.MISMATCH
            issues.append(Issue(
                code=IssueCode.LINK_MISMATCH,
                severity=JobIssueSeverity.RED,
                message=f"Несовпадение ссылки на карточку СИ: в файле VRI={file_link_vri}, в Аршине VRI={arshin_vri_num}",
                cell_ref=device.get('cell_refs', {}).get('link'),
            ))
    elif file_link_raw and selected_url and not file_link_vri:
        file_link_str = str(file_link_raw).strip()
        if file_link_str and file_link_str not in ('-', '—', '+', 'нет', 'Нет', 'паспорт', 'Паспорт'):
            status = JobItemStatus.MISMATCH
            issues.append(Issue(
                code=IssueCode.LINK_MISMATCH,
                severity=JobIssueSeverity.RED,
                message=f"Некорректная ссылка в файле: '{file_link_str}'. Ожидалась: {selected_url}",
                cell_ref=device.get('cell_refs', {}).get('link'),
            ))
    elif not file_link_raw and selected_url:
        issues.append(Issue(
            code=IssueCode.LINK_FILLED,
            severity=JobIssueSeverity.INFO,
            message=f"Ссылка обновлена: {selected_url}",
            cell_ref=device.get('cell_refs', {}).get('link'),
        ))

    if not issues and status == JobItemStatus.MATCHED:
        issues.append(Issue(
            code=IssueCode.MATCH,
            severity=JobIssueSeverity.INFO,
            message="Все данные совпадают",
            cell_ref=None,
        ))

    return ComparisonResult(status, issues, selected_url)
