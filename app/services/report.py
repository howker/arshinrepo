"""Генерация JSON-отчёта по результатам проверки (ТЗ раздел 13)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.models.enums import JobStatus, JobItemStatus, IssueCode


def build_report(
    job_id: UUID,
    status: JobStatus,
    source_filename: str,
    total_items: int,
    counts: dict,
    issues_by_item: dict,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    error_message: str | None = None,
) -> dict:
    """Сборка JSON-отчёта по ТЗ §13, §20."""
    report = {
        "job_id": str(job_id),
        "status": status.value,
        "source_filename": source_filename,
        "started_at": started_at.isoformat() if started_at else None,
        "finished_at": finished_at.isoformat() if finished_at else None,
        "error_message": error_message,
        "summary": {
            "total_items": total_items,
            "matched": counts.get("matched", 0),
            "mismatch": counts.get("mismatch", 0),
            "ambiguous": counts.get("ambiguous", 0),
            "source_uncertain": counts.get("source_uncertain", 0),
            "placeholder": counts.get("placeholder", 0),
        },
        "issues": []
    }

    # Собираем проблемы по каждому item
    for item_id, issues in issues_by_item.items():
        for issue in issues:
            report["issues"].append({
                "item_id": str(item_id),
                "cell": issue.get("cell_ref"),
                "code": issue.get("code", "").value if hasattr(issue.get("code", ""), "value") else str(issue.get("code", "")),
                "severity": issue.get("severity", "").value if hasattr(issue.get("severity", ""), "value") else str(issue.get("severity", "")),
                "message": issue.get("message", ""),
            })

    return report


def save_report_to_json(report: dict, file_path: str) -> None:
    """Сохранить отчёт в JSON-файл."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
