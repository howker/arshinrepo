"""Аннотация Excel: заливка, комментарии, ссылки (ТЗ раздел 12)."""
from __future__ import annotations
from pathlib import Path

import logging
from copy import copy
from openpyxl import load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import PatternFill
from openpyxl.utils import get_column_letter, range_boundaries

from app.models.enums import JobIssueSeverity

logger = logging.getLogger(__name__)

# Цвета заливки по ТЗ раздел 12
COLOR_MAP = {
    JobIssueSeverity.RED: 'FFFFC7CE',
    JobIssueSeverity.YELLOW: 'FFFFEB9C',
    JobIssueSeverity.ORANGE: 'FFFFCC99',
    JobIssueSeverity.INFO: None,  # без заливки
}


class ExcelAnnotator:
    """Аннотатор Excel с поддержкой merged-ячеек."""

    def __init__(self, template_code: str, profiles_dir: str = "app/templates_profiles"):
        self.template_code = template_code
        self.profiles_dir = Path(profiles_dir)
        self.config = self._load_profile()

    def _load_profile(self) -> dict:
        import json
        profile_path = self.profiles_dir / f"{self.template_code}.json"
        with open(profile_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def annotate_and_save(self, input_path: str, output_path: str, results: list[dict]):
        """Основной метод: чтение, аннотация, запись (два прохода)."""
        # Первый проход: чтение данных (data_only=True)
        wb_data = load_workbook(input_path, data_only=True)
        # Второй проход: запись аннотации (без data_only, чтобы сохранить стили)
        wb = load_workbook(input_path, data_only=False)
        sheet = self._find_sheet(wb)
        if sheet is None:
            raise ValueError("Лист не найден")

        # Группируем результаты по строкам
        for result in results:
            row = result.get('excel_row')
            if not row:
                continue
            self._annotate_device(sheet, row, result)

        # Сохраняем
        wb.save(output_path)

    def _find_sheet(self, wb):
        patterns = self.config.get('sheet_patterns', [])
        for sheet in wb.worksheets:
            for pattern in patterns:
                if pattern in sheet.title:
                    return sheet
        return None

    def _get_anchor_cell(self, sheet, cell_ref: str):
        """Находит верхнюю левую ячейку merged-диапазона (ТЗ 12.4)."""
        from openpyxl.utils.cell import coordinate_from_string, column_index_from_string
        col_letter, row = coordinate_from_string(cell_ref)
        col = column_index_from_string(col_letter)

        for merged_range in sheet.merged_cells.ranges:
            if col >= merged_range.min_col and col <= merged_range.max_col \
               and row >= merged_range.min_row and row <= merged_range.max_row:
                return f"{get_column_letter(merged_range.min_col)}{merged_range.min_row}"
        return cell_ref

    def _annotate_device(self, sheet, row: int, result: dict):
        """Аннотация одного прибора."""
        group_config = self._find_group_config(result['device_kind'])
        if not group_config:
            return

        cols = group_config['columns']
        issues = result.get('issues', [])
        selected_url = result.get('selected_url')
        link_overwrite_policy = self.config.get('link_overwrite_policy', 'replace')

        # 1. Заливка и комментарии для каждого поля
        for issue in issues:
            cell_ref = issue.get('cell_ref')
            if not cell_ref:
                continue
            severity = issue.get('severity')
            color = COLOR_MAP.get(severity)
            anchor = self._get_anchor_cell(sheet, cell_ref)
            cell = sheet[anchor]
            # Заливка
            if color:
                cell.fill = PatternFill(fill_type="solid", fgColor=color)
            # Комментарий (с автоподбором размера окна, чтобы текст был виден целиком)
            message = issue.get('message', '')
            if message:
                if cell.comment:
                    text = f"{cell.comment.text}\n\n{message}"
                else:
                    text = message
                cell.comment = self._make_comment(text)

        # 2. Ссылка на Аршин в столбце arshin_link
        link_col = cols.get('arshin_link')
        if link_col and selected_url:
            cell_ref = f"{get_column_letter(link_col)}{row}"
            anchor = self._get_anchor_cell(sheet, cell_ref)
            cell = sheet[anchor]
            if link_overwrite_policy == 'replace' or not cell.value:
                cell.value = selected_url
            elif link_overwrite_policy == 'append' and cell.value:
                cell.value = f"{cell.value}; {selected_url}"

    def _make_comment(self, text: str) -> Comment:
        """Комментарий с размером окна под объём текста.

        openpyxl по умолчанию делает крошечный квадратик, в котором длинное
        сообщение обрезается, и метрологу приходится растягивать его вручную.
        Считаем размер по числу строк с учётом переносов.
        """
        CHARS_PER_LINE = 45
        lines = 0
        for para in text.split("\n"):
            lines += max(1, -(-len(para) // CHARS_PER_LINE))  # ceil

        width = 380
        height = max(90, min(20 * lines + 30, 600))

        comment = Comment(text, "Проверка по ФГИС «Аршин»")
        comment.width = width
        comment.height = height
        return comment

    def _find_group_config(self, device_kind: str):
        for group in self.config.get('device_groups', []):
            if group['device_kind'] == device_kind:
                return group
        return None
