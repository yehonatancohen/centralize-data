from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates
from pathlib import Path

from typing import Optional
from app.database import get_db
from app.schemas import PersonUpdate
from app.services.scoring import calculate_score, get_segment

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/persons")
def persons_page(request: Request):
    return templates.TemplateResponse("persons.html", {"request": request})


@router.get("/persons/{person_id}")
def person_detail_page(request: Request, person_id: int):
    return templates.TemplateResponse("person_detail.html", {"request": request, "person_id": person_id})


@router.get("/api/persons")
def list_persons(
    q: str = Query(default="", description="Search query"),
    segment: str = Query(default="", description="Filter by segment"),
    city: str = Query(default="", description="Filter by city"),
    gender: str = Query(default="", description="Filter by gender"),
    min_score: Optional[float] = Query(default=None, description="Minimum score"),
    max_score: Optional[float] = Query(default=None, description="Maximum score"),
    min_events: Optional[int] = Query(default=None, description="Minimum events attended"),
    has_phone: Optional[bool] = Query(default=None, description="Has phone number"),
    has_email: Optional[bool] = Query(default=None, description="Has email"),
    has_instagram: Optional[bool] = Query(default=None, description="Has instagram"),
    sort_by: str = Query(default="updated_at", description="Sort field"),
    sort_dir: str = Query(default="desc", description="Sort direction"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
):
    offset = (page - 1) * per_page

    with get_db() as db:
        # Build dynamic WHERE clauses
        conditions = []
        params = []

        if q:
            search = f"%{q}%"
            conditions.append("(full_name LIKE ? OR first_name LIKE ? OR last_name LIKE ? OR phone LIKE ? OR email LIKE ? OR instagram LIKE ? OR city LIKE ?)")
            params.extend([search] * 7)

        if city:
            conditions.append("city LIKE ?")
            params.append(f"%{city}%")

        if gender:
            conditions.append("gender = ?")
            params.append(gender)

        if has_phone is True:
            conditions.append("phone IS NOT NULL AND phone != ''")
        elif has_phone is False:
            conditions.append("(phone IS NULL OR phone = '')")

        if has_email is True:
            conditions.append("email IS NOT NULL AND email != ''")
        elif has_email is False:
            conditions.append("(email IS NULL OR email = '')")

        if has_instagram is True:
            conditions.append("instagram IS NOT NULL AND instagram != ''")
        elif has_instagram is False:
            conditions.append("(instagram IS NULL OR instagram = '')")

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        # Validate sort field to prevent injection
        allowed_sort = {"full_name", "phone", "email", "city", "created_at", "updated_at"}
        if sort_by not in allowed_sort:
            sort_by = "updated_at"
        direction = "ASC" if sort_dir.lower() == "asc" else "DESC"

        rows = db.execute(
            f"SELECT * FROM persons {where} ORDER BY {sort_by} {direction} LIMIT ? OFFSET ?",
            params + [per_page, offset]
        ).fetchall()
        count_row = db.execute(
            f"SELECT COUNT(*) as cnt FROM persons {where}",
            params
        ).fetchone()

        total = count_row["cnt"]

        # Calculate scores for each person
        persons = []
        for row in rows:
            person = dict(row)
            # Build display_name: prefer first+last, fall back to full_name
            if person.get("first_name") or person.get("last_name"):
                parts = [person.get("first_name") or "", person.get("last_name") or ""]
                person["display_name"] = " ".join(p for p in parts if p)
            else:
                person["display_name"] = person.get("full_name") or "-"
            score_data = calculate_score(row["id"], db)
            person.update(score_data)
            persons.append(person)

        # Filter by segment (computed field, must filter after scoring)
        if segment:
            persons = [p for p in persons if p["segment"] == segment]

        # Filter by score range (computed field)
        if min_score is not None:
            persons = [p for p in persons if p.get("total_score", 0) >= min_score]
        if max_score is not None:
            persons = [p for p in persons if p.get("total_score", 0) <= max_score]

        # Filter by min events (computed field)
        if min_events is not None:
            persons = [p for p in persons if p.get("events_attended", 0) >= min_events]

    return {
        "persons": persons,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/api/persons/{person_id}")
def get_person(person_id: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM persons WHERE id = ?", (person_id,)).fetchone()
        if not row:
            return {"error": "Person not found"}

        person = dict(row)
        # Build display_name
        if person.get("first_name") or person.get("last_name"):
            parts = [person.get("first_name") or "", person.get("last_name") or ""]
            person["display_name"] = " ".join(p for p in parts if p)
        else:
            person["display_name"] = person.get("full_name") or "-"

        score_data = calculate_score(person_id, db)
        person.update(score_data)

        # Get attendance history
        attendance = db.execute("""
            SELECT a.*, e.name as event_name, e.event_date
            FROM attendance a JOIN events e ON a.event_id = e.id
            WHERE a.person_id = ?
            ORDER BY e.event_date DESC
        """, (person_id,)).fetchall()
        person["attendance"] = [dict(a) for a in attendance]

    return person


@router.put("/api/persons/{person_id}")
def update_person(person_id: int, body: PersonUpdate):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return {"error": "No fields to update"}

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [person_id]

    with get_db() as db:
        db.execute(
            f"UPDATE persons SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            values
        )
    return {"success": True}


@router.delete("/api/persons/{person_id}")
def delete_person(person_id: int):
    with get_db() as db:
        db.execute("DELETE FROM attendance WHERE person_id = ?", (person_id,))
        db.execute("DELETE FROM merge_candidates WHERE existing_person_id = ?", (person_id,))
        db.execute("DELETE FROM persons WHERE id = ?", (person_id,))
    return {"success": True}


@router.post("/api/persons/bulk-delete")
def bulk_delete_persons(request: dict):
    """Delete multiple persons by ID list."""
    ids = request.get("ids", [])
    if not ids:
        return {"error": "No IDs provided"}

    placeholders = ",".join("?" for _ in ids)
    with get_db() as db:
        db.execute(f"DELETE FROM attendance WHERE person_id IN ({placeholders})", ids)
        db.execute(f"DELETE FROM merge_candidates WHERE existing_person_id IN ({placeholders})", ids)
        db.execute(f"DELETE FROM persons WHERE id IN ({placeholders})", ids)
    return {"success": True, "deleted": len(ids)}


@router.post("/api/persons/bulk-update")
def bulk_update_persons(request: dict):
    """Update a field for multiple persons at once."""
    ids = request.get("ids", [])
    field = request.get("field")
    value = request.get("value")

    if not ids or not field:
        return {"error": "Missing ids or field"}

    allowed_fields = {"city", "gender", "notes"}
    if field not in allowed_fields:
        return {"error": f"Field '{field}' is not allowed for bulk update"}

    placeholders = ",".join("?" for _ in ids)
    with get_db() as db:
        db.execute(
            f"UPDATE persons SET {field} = ?, updated_at = CURRENT_TIMESTAMP WHERE id IN ({placeholders})",
            [value] + ids
        )
    return {"success": True, "updated": len(ids)}


@router.post("/api/persons/merge")
def merge_persons(person_a_id: int = Query(...), person_b_id: int = Query(...)):
    """Merge person B into person A. A is kept, B is deleted."""
    with get_db() as db:
        a = db.execute("SELECT * FROM persons WHERE id = ?", (person_a_id,)).fetchone()
        b = db.execute("SELECT * FROM persons WHERE id = ?", (person_b_id,)).fetchone()
        if not a or not b:
            return {"error": "Person not found"}

        # Fill gaps: update A with B's data where A is empty
        fields = ["full_name", "full_name_alt", "first_name", "last_name", "phone", "email", "instagram", "city", "date_of_birth", "age", "gender", "notes"]
        for field in fields:
            if not a[field] and b[field]:
                db.execute(f"UPDATE persons SET {field} = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                           (b[field], person_a_id))

        # Move B's attendance to A
        db.execute("UPDATE OR IGNORE attendance SET person_id = ? WHERE person_id = ?", (person_a_id, person_b_id))
        db.execute("DELETE FROM attendance WHERE person_id = ?", (person_b_id,))

        # Delete B
        db.execute("DELETE FROM merge_candidates WHERE existing_person_id = ?", (person_b_id,))
        db.execute("DELETE FROM persons WHERE id = ?", (person_b_id,))

    return {"success": True}
