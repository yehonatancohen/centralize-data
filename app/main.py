from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.database import init_db
from app.config import UPLOADS_DIR
from app.routers import upload, persons, events, dashboard, export

app = FastAPI(title="Centralized Customer Database")

# Static files and templates
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# Include routers
app.include_router(upload.router)
app.include_router(persons.router)
app.include_router(events.router)
app.include_router(dashboard.router)
app.include_router(export.router)


@app.on_event("startup")
def startup():
    init_db()
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})
