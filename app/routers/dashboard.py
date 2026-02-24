from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.database import get_db
from app.services.scoring import calculate_score

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/api/dashboard/summary")
def dashboard_summary():
    with get_db() as db:
        total_persons = db.execute("SELECT COUNT(*) as cnt FROM persons").fetchone()["cnt"]
        total_events = db.execute("SELECT COUNT(*) as cnt FROM events").fetchone()["cnt"]
        total_imports = db.execute("SELECT COUNT(*) as cnt FROM imports").fetchone()["cnt"]

        # Calculate segments
        persons = db.execute("SELECT id FROM persons").fetchall()
        segments = {"vip": 0, "regular": 0, "new": 0, "churned": 0, "inactive": 0, "never": 0}
        for p in persons:
            score_data = calculate_score(p["id"], db)
            seg = score_data["segment"]
            if seg in segments:
                segments[seg] += 1

    return {
        "total_persons": total_persons,
        "total_events": total_events,
        "total_imports": total_imports,
        "segments": segments
    }


@router.get("/api/dashboard/top-customers")
def top_customers(limit: int = 10):
    with get_db() as db:
        persons = db.execute("SELECT * FROM persons").fetchall()
        scored = []
        for p in persons:
            person = dict(p)
            score_data = calculate_score(p["id"], db)
            person.update(score_data)
            scored.append(person)

    scored.sort(key=lambda x: x["total_score"], reverse=True)
    return {"persons": scored[:limit]}


@router.get("/api/dashboard/churned")
def churned_customers():
    with get_db() as db:
        persons = db.execute("SELECT * FROM persons").fetchall()
        churned = []
        for p in persons:
            score_data = calculate_score(p["id"], db)
            if score_data["segment"] == "churned":
                person = dict(p)
                person.update(score_data)
                churned.append(person)

    churned.sort(key=lambda x: x["events_attended"], reverse=True)
    return {"persons": churned}


@router.get("/api/dashboard/segments")
def segment_distribution():
    with get_db() as db:
        persons = db.execute("SELECT id FROM persons").fetchall()
        segments = {"vip": 0, "regular": 0, "new": 0, "churned": 0, "inactive": 0, "never": 0}
        for p in persons:
            score_data = calculate_score(p["id"], db)
            seg = score_data["segment"]
            if seg in segments:
                segments[seg] += 1

    return {"segments": segments}
