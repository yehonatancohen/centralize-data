import re
from datetime import datetime, date


def normalize_date_of_birth(raw: str | None) -> tuple[str | None, int | None]:
    """Normalize date of birth to dd/mm/yyyy format. Returns (date_str, age)."""
    if not raw:
        return None, None

    raw = str(raw).strip()
    if not raw:
        return None, None

    parsed = None

    # Try common date formats
    formats = [
        "%d/%m/%Y",    # 25/12/1990
        "%d-%m-%Y",    # 25-12-1990
        "%d.%m.%Y",    # 25.12.1990
        "%Y-%m-%d",    # 1990-12-25 (ISO)
        "%d/%m/%y",    # 25/12/90
        "%d-%m-%y",    # 25-12-90
        "%d.%m.%y",    # 25.12.90
        "%m/%d/%Y",    # 12/25/1990 (US format, fallback)
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(raw, fmt).date()
            # Sanity check: if day > 12 and we parsed as US format, it was actually dd/mm
            if fmt == "%m/%d/%Y" and parsed.month > 12:
                continue
            break
        except ValueError:
            continue

    if not parsed:
        return None, None

    # Calculate age
    today = date.today()
    age = today.year - parsed.year - ((today.month, today.day) < (parsed.month, parsed.day))

    # Sanity check age
    if age < 0 or age > 120:
        return None, None

    return parsed.strftime("%d/%m/%Y"), age


def normalize_gender(raw: str | None) -> str | None:
    """Normalize gender to 'male', 'female', or 'other'."""
    if not raw:
        return None

    raw = str(raw).strip().lower()
    if not raw:
        return None

    male_values = {"male", "m", "זכר", "ז", "man", "boy"}
    female_values = {"female", "f", "נקבה", "נ", "woman", "girl"}

    if raw in male_values:
        return "male"
    if raw in female_values:
        return "female"
    if raw:
        return "other"
    return None


def normalize_phone(raw: str | None) -> str | None:
    """Normalize an Israeli phone number to 05XXXXXXXX format.
    Returns normalized string or None if invalid.
    """
    if not raw:
        return None

    raw = str(raw).strip()
    if not raw:
        return None

    # Strip all non-digit characters except leading +
    cleaned = re.sub(r"[^\d+]", "", raw)

    # Handle +972 prefix
    if cleaned.startswith("+972"):
        cleaned = "0" + cleaned[4:]
    elif cleaned.startswith("972") and len(cleaned) > 9:
        cleaned = "0" + cleaned[3:]

    # Remove doubled leading zeros
    if cleaned.startswith("00"):
        cleaned = cleaned[1:]

    # Validate Israeli patterns
    if re.match(r"^05\d{8}$", cleaned):
        return cleaned  # Mobile
    if re.match(r"^0[2-489]\d{7,8}$", cleaned):
        return cleaned  # Landline
    if re.match(r"^07[1-9]\d{7}$", cleaned):
        return cleaned  # VoIP / newer

    # Return cleaned version even if not standard pattern (user might have international)
    if len(cleaned) >= 7:
        return cleaned

    return None


def normalize_name(raw: str | None) -> str | None:
    """Normalize a name: trim, collapse whitespace, title case for English."""
    if not raw:
        return None

    raw = str(raw).strip()
    if not raw:
        return None

    # Collapse multiple spaces
    name = re.sub(r"\s+", " ", raw).strip()

    # Don't title-case if the name contains Hebrew characters
    if re.search(r"[\u0590-\u05FF]", name):
        return name

    return name.title()


def normalize_email(raw: str | None) -> str | None:
    """Normalize email: lowercase, strip."""
    if not raw:
        return None
    email = str(raw).strip().lower()
    if "@" in email and "." in email:
        return email
    return None


def normalize_instagram(raw: str | None) -> str | None:
    """Normalize Instagram handle: strip @, lowercase."""
    if not raw:
        return None
    handle = str(raw).strip().lower()
    handle = handle.lstrip("@")
    # Remove URL prefix if they pasted a full URL
    if "instagram.com/" in handle:
        handle = handle.split("instagram.com/")[-1].strip("/")
    if handle:
        return handle
    return None


def normalize_row(row: dict, column_mapping: dict) -> dict:
    """Apply column mapping and normalization to a data row.
    column_mapping: {source_col: canonical_field_or_None}
    Returns dict with canonical field names and normalized values.
    """
    result = {}

    for source_col, canonical in column_mapping.items():
        if canonical is None:
            continue
        value = row.get(source_col)
        if value is None or (isinstance(value, float) and str(value) == "nan"):
            continue
        value = str(value).strip()
        if not value or value.lower() == "nan":
            continue

        if canonical == "phone":
            result["phone"] = normalize_phone(value)
            result["phone_raw"] = value
        elif canonical in ("full_name", "first_name", "last_name", "full_name_alt"):
            result[canonical] = normalize_name(value)
        elif canonical == "email":
            result["email"] = normalize_email(value)
        elif canonical == "instagram":
            result["instagram"] = normalize_instagram(value)
        elif canonical == "date_of_birth":
            dob, age = normalize_date_of_birth(value)
            if dob:
                result["date_of_birth"] = dob
                result["age"] = age
        elif canonical == "age":
            try:
                result["age"] = int(float(value))
            except (ValueError, TypeError):
                pass
        elif canonical == "gender":
            result["gender"] = normalize_gender(value)
        elif canonical == "amount_paid":
            try:
                result["amount_paid"] = float(re.sub(r"[^\d.]", "", str(value)))
            except (ValueError, TypeError):
                pass
        else:
            result[canonical] = value

    # Construct full_name from first + last if not directly provided
    if "full_name" not in result and ("first_name" in result or "last_name" in result):
        parts = [result.get("first_name", ""), result.get("last_name", "")]
        result["full_name"] = " ".join(p for p in parts if p).strip()

    return result
