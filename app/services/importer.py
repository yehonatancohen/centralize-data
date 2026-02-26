import json
import logging
from pathlib import Path

from app.config import UPLOADS_DIR, AUTO_MERGE_THRESHOLD, REVIEW_THRESHOLD
from app.database import get_db, IntegrityError
from app.services.file_parser import parse_file
from app.services.normalizer import normalize_row
from app.services.dedup import find_match, reset_cache, add_to_cache

logger = logging.getLogger(__name__)


def process_import(import_id: int, column_mapping: dict, event_id: int | None) -> dict:
    """Process an import: parse, normalize, deduplicate, insert/merge."""
    # Reset the dedup cache at the start of each import
    reset_cache()

    with get_db() as db:
        imp = db.execute("SELECT * FROM imports WHERE id = ?", (import_id,)).fetchone()
        if not imp:
            return {"error": "Import not found"}

        file_path = str(UPLOADS_DIR / imp["filename"])
        df, _ = parse_file(file_path)

        new_count = 0
        merged_count = 0
        review_count = 0
        skipped = 0

        for idx, raw_row in df.iterrows():
            try:
                row_dict = raw_row.to_dict()
                normalized = normalize_row(row_dict, column_mapping)

                if not normalized.get("full_name") and not normalized.get("phone"):
                    skipped += 1
                    continue  # Skip rows with no identifying info

                # Find match
                person_id, score, match_field = find_match(normalized, db)

                if person_id and score >= AUTO_MERGE_THRESHOLD:
                    # Auto-merge: fill gaps
                    _merge_into_person(db, person_id, normalized)
                    if event_id:
                        _add_attendance(db, person_id, event_id, normalized, imp["original_filename"])
                    merged_count += 1

                elif person_id and score >= REVIEW_THRESHOLD:
                    # Queue for review
                    db.execute(
                        "INSERT INTO merge_candidates (import_id, existing_person_id, incoming_data, match_score, match_field) VALUES (?, ?, ?, ?, ?)",
                        (import_id, person_id, json.dumps(normalized, ensure_ascii=False), score, match_field)
                    )
                    review_count += 1

                else:
                    # Create new person
                    new_person_id = _create_person(db, normalized, imp["original_filename"])
                    if new_person_id:
                        if event_id:
                            _add_attendance(db, new_person_id, event_id, normalized, imp["original_filename"])
                        # Add to dedup cache so subsequent rows can match against it
                        add_to_cache({
                            "id": new_person_id,
                            "full_name": normalized.get("full_name"),
                            "full_name_alt": normalized.get("full_name_alt"),
                            "phone": normalized.get("phone"),
                            "email": normalized.get("email"),
                            "instagram": normalized.get("instagram"),
                        })
                        new_count += 1
                    else:
                        skipped += 1

                # Commit in batches of 500 for large files
                if (idx + 1) % 500 == 0:
                    db.commit()

            except Exception as e:
                logger.warning(f"Row {idx} skipped due to error: {e}")
                skipped += 1
                continue

        # Update import record
        status = "reviewing" if review_count > 0 else "completed"
        db.execute(
            "UPDATE imports SET new_persons = ?, merged_persons = ?, status = ? WHERE id = ?",
            (new_count, merged_count, status, import_id)
        )

    return {
        "import_id": import_id,
        "new_persons": new_count,
        "merged_persons": merged_count,
        "review_needed": review_count,
        "skipped": skipped,
        "status": status
    }


def finalize_import(import_id: int, decisions: list) -> dict:
    """Process manual merge/skip decisions and finalize the import."""
    with get_db() as db:
        imp = db.execute("SELECT * FROM imports WHERE id = ?", (import_id,)).fetchone()
        if not imp:
            return {"error": "Import not found"}

        event_id = imp["event_id"]
        merged = 0
        created = 0

        for decision in decisions:
            candidate = db.execute(
                "SELECT * FROM merge_candidates WHERE id = ? AND import_id = ?",
                (decision.candidate_id, import_id)
            ).fetchone()
            if not candidate:
                continue

            incoming = json.loads(candidate["incoming_data"])

            if decision.action == "merge":
                _merge_into_person(db, candidate["existing_person_id"], incoming)
                if event_id:
                    _add_attendance(db, candidate["existing_person_id"], event_id, incoming, imp["original_filename"])
                merged += 1
            else:  # skip = create new
                new_id = _create_person(db, incoming, imp["original_filename"])
                if new_id and event_id:
                    _add_attendance(db, new_id, event_id, incoming, imp["original_filename"])
                created += 1

            db.execute(
                "UPDATE merge_candidates SET status = ?, resolved_at = CURRENT_TIMESTAMP WHERE id = ?",
                (decision.action + "d", decision.candidate_id)
            )

        db.execute("UPDATE imports SET status = 'completed' WHERE id = ?", (import_id,))

    return {"merged": merged, "created": created}


def _create_person(db, data: dict, source_file: str) -> int | None:
    """Insert a new person record. Returns person_id or None if duplicate."""
    try:
        cursor = db.execute(
            """INSERT INTO persons (full_name, full_name_alt, first_name, last_name, phone, phone_raw, email, instagram, city, date_of_birth, age, gender, notes, source_file)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.get("full_name"),
                data.get("full_name_alt"),
                data.get("first_name"),
                data.get("last_name"),
                data.get("phone"),
                data.get("phone_raw"),
                data.get("email"),
                data.get("instagram"),
                data.get("city"),
                data.get("date_of_birth"),
                data.get("age"),
                data.get("gender"),
                data.get("notes"),
                source_file,
            )
        )
        return cursor.lastrowid
    except IntegrityError:
        # Duplicate phone/unique constraint — find existing and merge instead
        phone = data.get("phone")
        if phone:
            existing = db.execute("SELECT id FROM persons WHERE phone = ?", (phone,)).fetchone()
            if existing:
                _merge_into_person(db, existing["id"], data)
                return None
        return None


def _merge_into_person(db, person_id: int, data: dict):
    """Merge data into existing person (fill gaps only)."""
    existing = db.execute("SELECT * FROM persons WHERE id = ?", (person_id,)).fetchone()
    if not existing:
        return

    fields = ["full_name", "full_name_alt", "first_name", "last_name", "phone", "phone_raw", "email", "instagram", "city", "date_of_birth", "age", "gender", "notes"]
    updates = {}
    for field in fields:
        if data.get(field) and not existing[field]:
            updates[field] = data[field]

    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [person_id]
        db.execute(
            f"UPDATE persons SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            values
        )


def _add_attendance(db, person_id: int, event_id: int, data: dict, source_file: str):
    """Add attendance record (skip if already exists)."""
    try:
        db.execute(
            "INSERT OR IGNORE INTO attendance (person_id, event_id, amount_paid, ticket_type, source_file) VALUES (?, ?, ?, ?, ?)",
            (person_id, event_id, data.get("amount_paid", 0), data.get("ticket_type"), source_file)
        )
    except Exception:
        pass  # Duplicate attendance, ignore
