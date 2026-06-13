import json
import os
import openpyxl
from openpyxl.styles import PatternFill
from openpyxl.comments import Comment
from typing import List
from app.schemas.comparison import ComparisonResult

RED_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

class ExcelAnnotator:
    def __init__(self, template_code: str = "pril_1_main"):
        self.template_code = template_code
        self.config = self._load_template_config(template_code)

    def _load_template_config(self, code: str) -> dict:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        config_path = os.path.join(base_dir, "templates", f"{code}.json")
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _map_issue_to_col_key(self, issue_code: str) -> str:
        # Связываем код ошибки с конкретной колонкой в JSON-конфиге
        mapping = {
            "VERIFICATION_DATE_MISMATCH": "verification_date",
            "NEXT_VERIFICATION_DATE_MISMATCH": "next_verification_date",
            "ARSHIN_NOT_FOUND": "serial_number",
            "MULTIPLE_MATCHES": "serial_number"
        }
        return mapping.get(issue_code, "serial_number")

    def annotate_and_save(self, input_path: str, output_path: str, results: List[ComparisonResult]):
        wb = openpyxl.load_workbook(input_path)
        sheet_name = self.config.get("sheet_name")
        ws = wb[sheet_name] if sheet_name in wb.sheetnames else wb.active

        for res in results:
            row = res.device.row_number
            group = res.device.group_name
            
            # Ищем колонки именно для этой группы приборов (Счетчик, ТТ или ТН)
            try:
                g_cfg = next(g for g in self.config["device_groups"] if g["group_name"] == group)
            except StopIteration:
                continue
                
            cols = g_cfg["columns"]

            # 1. Записываем ссылку на Аршин (если найдена)
            if res.matched_record and res.matched_record.public_url:
                link_col = cols.get("arshin_link")
                if link_col:
                    ws.cell(row=row, column=link_col, value=res.matched_record.public_url)

            # 2. Красим ячейки и пишем комментарии по каждой ошибке
            for issue in res.issues:
                target_col_key = self._map_issue_to_col_key(issue.code)
                c_idx = cols.get(target_col_key)
                if c_idx:
                    cell = ws.cell(row=row, column=c_idx)
                    cell.fill = RED_FILL
                    cell.comment = Comment(issue.message, "Arshin SaaS")

        wb.save(output_path)
