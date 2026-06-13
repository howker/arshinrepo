import re
from datetime import datetime, date

def parse_excel_date(raw_date: str | None) -> date | None:
    if not raw_date:
        return None
    raw_date = str(raw_date).strip()
    if len(raw_date) >= 10:
        # Формат YYYY-MM-DD (например: 2019-09-12 00:00:00)
        if re.match(r'^\d{4}-\d{2}-\d{2}', raw_date):
            try:
                return datetime.strptime(raw_date[:10], "%Y-%m-%d").date()
            except ValueError:
                pass
        # Формат DD.MM.YYYY (например: 11.11.2022)
        elif re.match(r'^\d{2}\.\d{2}\.\d{4}', raw_date):
            try:
                return datetime.strptime(raw_date[:10], "%d.%m.%Y").date()
            except ValueError:
                pass
    return None
