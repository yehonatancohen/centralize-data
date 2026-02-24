import openpyxl
from pathlib import Path
from datetime import datetime

from app.config import UPLOADS_DIR


def export_persons_to_excel(persons: list[dict]) -> str:
    """Export a list of person dicts to an Excel file. Returns file path."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Customers"

    # Headers
    headers = [
        "Name", "Phone", "Email", "Instagram", "City",
        "Date of Birth", "Age", "Gender",
        "Events Attended", "Total Spent", "Score", "Segment",
        "Days Since Last Event", "Notes"
    ]
    ws.append(headers)

    # Style header row
    for cell in ws[1]:
        cell.font = openpyxl.styles.Font(bold=True)

    # Data rows
    for p in persons:
        ws.append([
            p.get("full_name", ""),
            p.get("phone", ""),
            p.get("email", ""),
            p.get("instagram", ""),
            p.get("city", ""),
            p.get("date_of_birth", ""),
            p.get("age", ""),
            p.get("gender", ""),
            p.get("events_attended", 0),
            p.get("total_spent", 0),
            p.get("total_score", 0),
            p.get("segment", ""),
            p.get("days_since_last", ""),
            p.get("notes", ""),
        ])

    # Auto-width columns
    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except Exception:
                pass
        ws.column_dimensions[col_letter].width = min(max_length + 2, 40)

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = UPLOADS_DIR / f"export_{timestamp}.xlsx"
    wb.save(str(file_path))
    return str(file_path)
