import sqlite3
from rapidfuzz import fuzz


# In-memory cache of persons for fuzzy matching, rebuilt per import
_persons_cache = None


def reset_cache():
    """Reset the persons cache. Call at the start of each import."""
    global _persons_cache
    _persons_cache = None


def _get_persons_cache(db: sqlite3.Connection) -> list[dict]:
    """Get or build the in-memory persons cache for fuzzy matching."""
    global _persons_cache
    if _persons_cache is None:
        rows = db.execute(
            "SELECT id, full_name, full_name_alt, phone, email, instagram FROM persons"
        ).fetchall()
        _persons_cache = [dict(r) for r in rows]
    return _persons_cache


def add_to_cache(person: dict):
    """Add a newly created person to the cache."""
    global _persons_cache
    if _persons_cache is not None:
        _persons_cache.append(person)


def find_match(normalized_row: dict, db: sqlite3.Connection) -> tuple[int | None, float, str]:
    """Find a matching person in the database for the given normalized row.
    Returns (person_id_or_None, match_score, match_field).
    """
    # Step 1: Exact key matches (fast path via indexed queries)
    phone = normalized_row.get("phone")
    if phone:
        row = db.execute("SELECT id FROM persons WHERE phone = ?", (phone,)).fetchone()
        if row:
            return row["id"], 1.0, "phone"

    email = normalized_row.get("email")
    if email:
        row = db.execute("SELECT id FROM persons WHERE email = ?", (email,)).fetchone()
        if row:
            return row["id"], 0.95, "email"

    instagram = normalized_row.get("instagram")
    if instagram:
        row = db.execute("SELECT id FROM persons WHERE instagram = ?", (instagram,)).fetchone()
        if row:
            return row["id"], 0.90, "instagram"

    # Step 2: Fuzzy name matching (using cached persons list)
    name = normalized_row.get("full_name")
    if not name or len(name) < 2:
        return None, 0.0, ""

    persons = _get_persons_cache(db)
    if not persons:
        return None, 0.0, ""

    best_id = None
    best_score = 0.0
    best_field = ""

    for person in persons:
        score = _compute_match_score(normalized_row, person)
        if score > best_score:
            best_score = score
            best_id = person["id"]
            best_field = "name"

    if best_id and best_score > 0.0:
        return best_id, best_score, best_field

    return None, 0.0, ""


def _compute_match_score(incoming: dict, existing: dict) -> float:
    """Compute weighted match score between incoming data and existing person."""
    scores = []
    weights = []

    # Phone comparison
    if incoming.get("phone") and existing.get("phone"):
        phone_score = 1.0 if incoming["phone"] == existing["phone"] else 0.0
        scores.append(phone_score)
        weights.append(5.0)

    # Email comparison
    if incoming.get("email") and existing.get("email"):
        email_score = 1.0 if incoming["email"] == existing["email"] else 0.0
        scores.append(email_score)
        weights.append(4.0)

    # Instagram comparison
    if incoming.get("instagram") and existing.get("instagram"):
        ig_score = 1.0 if incoming["instagram"] == existing["instagram"] else 0.0
        scores.append(ig_score)
        weights.append(3.5)

    # Name comparison
    if incoming.get("full_name") and existing.get("full_name"):
        name_score = fuzz.token_sort_ratio(
            incoming["full_name"], existing["full_name"]
        ) / 100.0

        # Also check alt name
        if existing.get("full_name_alt"):
            alt_score = fuzz.token_sort_ratio(
                incoming["full_name"], existing["full_name_alt"]
            ) / 100.0
            name_score = max(name_score, alt_score)

        scores.append(name_score)
        weights.append(3.0)

    if not scores:
        return 0.0

    return sum(s * w for s, w in zip(scores, weights)) / sum(weights)
