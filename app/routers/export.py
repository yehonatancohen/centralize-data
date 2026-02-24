from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from pathlib import Path

from app.database import get_db
from app.services.scoring import calculate_score
from app.services.exporter import export_persons_to_excel

router = APIRouter()


@router.get("/api/export")
def export_data(
    segment: str = Query(default="", description="Filter by segment"),
    min_score: float = Query(default=0, description="Minimum score"),
    event_id: int = Query(default=0, description="Filter by event attendance"),
    search: str = Query(default="", description="Search query"),
):
    with get_db() as db:
        if event_id:
            rows = db.execute("""
                SELECT DISTINCT p.* FROM persons p
                JOIN attendance a ON p.id = a.person_id
                WHERE a.event_id = ?
                ORDER BY p.full_name
            """, (event_id,)).fetchall()
        elif search:
            s = f"%{search}%"
            rows = db.execute(
                """SELECT * FROM persons
                   WHERE full_name LIKE ? OR phone LIKE ? OR email LIKE ? OR instagram LIKE ?
                   ORDER BY full_name""",
                (s, s, s, s)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM persons ORDER BY full_name").fetchall()

        # Score and filter
        persons = []
        for row in rows:
            person = dict(row)
            score_data = calculate_score(row["id"], db)
            person.update(score_data)
            if segment and person["segment"] != segment:
                continue
            if min_score and person["total_score"] < min_score:
                continue
            persons.append(person)

    file_path = export_persons_to_excel(persons)
    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="customers_export.xlsx"
    )
