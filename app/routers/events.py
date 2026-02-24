from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.database import get_db
from app.schemas import EventCreate, EventUpdate

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/events-page")
def events_page(request: Request):
    return templates.TemplateResponse("events.html", {"request": request})


@router.get("/api/events")
def list_events():
    with get_db() as db:
        events = db.execute("""
            SELECT e.*, COUNT(a.id) as attendee_count
            FROM events e LEFT JOIN attendance a ON e.id = a.event_id
            GROUP BY e.id
            ORDER BY e.event_date DESC
        """).fetchall()
    return {"events": [dict(e) for e in events]}


@router.post("/api/events")
def create_event(body: EventCreate):
    with get_db() as db:
        cursor = db.execute(
            "INSERT INTO events (name, event_date, venue, notes) VALUES (?, ?, ?, ?)",
            (body.name, str(body.event_date) if body.event_date else None, body.venue, body.notes)
        )
        return {"id": cursor.lastrowid}


@router.get("/api/events/{event_id}")
def get_event(event_id: int):
    with get_db() as db:
        event = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if not event:
            return {"error": "Event not found"}

        attendees = db.execute("""
            SELECT p.id, p.full_name, p.phone, p.instagram, a.amount_paid, a.ticket_type
            FROM attendance a JOIN persons p ON a.person_id = p.id
            WHERE a.event_id = ?
            ORDER BY p.full_name
        """, (event_id,)).fetchall()

    return {
        "event": dict(event),
        "attendees": [dict(a) for a in attendees]
    }


@router.put("/api/events/{event_id}")
def update_event(event_id: int, body: EventUpdate):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return {"error": "No fields to update"}

    # Convert date to string for SQLite
    if "event_date" in updates and updates["event_date"]:
        updates["event_date"] = str(updates["event_date"])

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [event_id]

    with get_db() as db:
        db.execute(f"UPDATE events SET {set_clause} WHERE id = ?", values)
    return {"success": True}


@router.delete("/api/events/{event_id}")
def delete_event(event_id: int):
    with get_db() as db:
        db.execute("DELETE FROM attendance WHERE event_id = ?", (event_id,))
        db.execute("DELETE FROM events WHERE id = ?", (event_id,))
    return {"success": True}
