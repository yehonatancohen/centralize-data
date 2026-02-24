from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json
import uuid
import shutil
import logging
import traceback

from app.config import UPLOADS_DIR
from app.database import get_db
from app.schemas import ColumnMapping, ImportReviewSubmit
from app.services.file_parser import parse_file
from app.services.column_mapper import auto_map_columns
from app.services.importer import process_import, finalize_import

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/upload")
def upload_page(request: Request):
    with get_db() as db:
        events = db.execute("SELECT id, name, event_date FROM events ORDER BY event_date DESC").fetchall()
    return templates.TemplateResponse("upload.html", {"request": request, "events": events})


@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Save uploaded file
        ext = Path(file.filename).suffix.lower()
        if ext not in (".xlsx", ".xls", ".csv"):
            return JSONResponse(
                status_code=400,
                content={"error": "Unsupported file type. Please upload Excel (.xlsx) or CSV (.csv) files."}
            )

        saved_name = f"{uuid.uuid4().hex}{ext}"
        save_path = UPLOADS_DIR / saved_name
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Parse file and detect columns
        df, columns = parse_file(str(save_path))
        row_count = len(df)

        # Auto-map columns
        mapping = auto_map_columns(columns)

        # Create import record
        with get_db() as db:
            cursor = db.execute(
                "INSERT INTO imports (filename, original_filename, row_count, status, column_mapping) VALUES (?, ?, ?, 'mapped', ?)",
                (saved_name, file.filename, row_count, json.dumps({k: v["field"] for k, v in mapping.items()}))
            )
            import_id = cursor.lastrowid

        # Return preview data (first 5 rows only)
        preview_rows = df.head(5).fillna("").to_dict(orient="records")

        return {
            "import_id": import_id,
            "filename": file.filename,
            "row_count": row_count,
            "columns": columns,
            "mapping": mapping,
            "preview": preview_rows
        }
    except Exception as e:
        logger.error(f"Upload failed: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to process file: {str(e)}"}
        )


@router.post("/api/imports/{import_id}/mapping")
def confirm_mapping(import_id: int, mapping: ColumnMapping):
    try:
        with get_db() as db:
            db.execute(
                "UPDATE imports SET column_mapping = ?, event_id = ?, status = 'processing' WHERE id = ?",
                (json.dumps(mapping.mapping), mapping.event_id, import_id)
            )

        # If event_name provided but no event_id, create the event
        event_id = mapping.event_id
        if not event_id and mapping.event_name:
            with get_db() as db:
                cursor = db.execute(
                    "INSERT INTO events (name, event_date) VALUES (?, ?)",
                    (mapping.event_name, mapping.event_date)
                )
                event_id = cursor.lastrowid
                db.execute("UPDATE imports SET event_id = ? WHERE id = ?", (event_id, import_id))

        # Process the import
        result = process_import(import_id, mapping.mapping, event_id)
        return result
    except Exception as e:
        logger.error(f"Import failed: {traceback.format_exc()}")
        # Mark import as failed
        try:
            with get_db() as db:
                db.execute("UPDATE imports SET status = 'failed' WHERE id = ?", (import_id,))
        except Exception:
            pass
        return JSONResponse(
            status_code=500,
            content={"error": f"Import processing failed: {str(e)}"}
        )


@router.get("/api/imports/{import_id}/review")
def get_review_candidates(import_id: int):
    with get_db() as db:
        candidates = db.execute("""
            SELECT mc.id, mc.existing_person_id, mc.incoming_data, mc.match_score, mc.match_field,
                   p.full_name, p.phone, p.email, p.instagram, p.city
            FROM merge_candidates mc
            JOIN persons p ON p.id = mc.existing_person_id
            WHERE mc.import_id = ? AND mc.status = 'pending'
            ORDER BY mc.match_score DESC
        """, (import_id,)).fetchall()

    result = []
    for c in candidates:
        result.append({
            "id": c["id"],
            "match_score": c["match_score"],
            "match_field": c["match_field"],
            "existing": {
                "id": c["existing_person_id"],
                "full_name": c["full_name"],
                "phone": c["phone"],
                "email": c["email"],
                "instagram": c["instagram"],
                "city": c["city"],
            },
            "incoming": json.loads(c["incoming_data"])
        })
    return {"candidates": result}


@router.post("/api/imports/{import_id}/review")
def submit_review(import_id: int, body: ImportReviewSubmit):
    return finalize_import(import_id, body.decisions)


@router.get("/api/imports")
def list_imports():
    with get_db() as db:
        imports = db.execute("""
            SELECT i.*, e.name as event_name
            FROM imports i LEFT JOIN events e ON i.event_id = e.id
            ORDER BY i.created_at DESC
        """).fetchall()
    return {"imports": [dict(i) for i in imports]}
