import math
from datetime import date, datetime

from app.config import RECENCY_WEIGHT, FREQUENCY_WEIGHT, MONETARY_WEIGHT, RECENCY_DECAY_DAYS, CHURN_DAYS


def calculate_score(person_id: int, db) -> dict:
    """Calculate RFM-based customer value score."""
    attendances = db.execute("""
        SELECT e.event_date, a.amount_paid
        FROM attendance a JOIN events e ON a.event_id = e.id
        WHERE a.person_id = ?
        ORDER BY e.event_date DESC
    """, (person_id,)).fetchall()

    if not attendances:
        return {
            "total_score": 0,
            "recency_score": 0,
            "frequency_score": 0,
            "monetary_score": 0,
            "events_attended": 0,
            "total_spent": 0,
            "days_since_last": None,
            "segment": "never",
        }

    today = date.today()

    # Recency
    last_date_str = attendances[0]["event_date"]
    if last_date_str:
        try:
            last_date = datetime.strptime(str(last_date_str), "%Y-%m-%d").date()
        except ValueError:
            last_date = today
        days_since = (today - last_date).days
    else:
        days_since = 999
    recency_score = max(0, 100 - (days_since / RECENCY_DECAY_DAYS * 100))

    # Frequency
    frequency_count = len(attendances)
    frequency_score = min(100, (math.log(frequency_count + 1) / math.log(21)) * 100)

    # Monetary
    total_spent = sum(a["amount_paid"] or 0 for a in attendances)
    if total_spent > 0:
        monetary_score = min(100, (math.log(total_spent + 1) / math.log(10001)) * 100)
    else:
        monetary_score = 0

    # Weighted total
    total_score = (
        recency_score * RECENCY_WEIGHT +
        frequency_score * FREQUENCY_WEIGHT +
        monetary_score * MONETARY_WEIGHT
    )

    # Segment
    segment = get_segment(days_since, frequency_count)

    return {
        "total_score": round(total_score, 1),
        "recency_score": round(recency_score, 1),
        "frequency_score": round(frequency_score, 1),
        "monetary_score": round(monetary_score, 1),
        "events_attended": frequency_count,
        "total_spent": round(total_spent, 2),
        "days_since_last": days_since,
        "segment": segment,
    }


def get_segment(days_since: int, frequency: int) -> str:
    """Determine customer segment based on recency and frequency."""
    if days_since > CHURN_DAYS and frequency >= 2:
        return "churned"
    if days_since <= 90 and frequency >= 3:
        return "vip"
    if frequency == 1 and days_since <= 90:
        return "new"
    if frequency >= 2:
        return "regular"
    if frequency == 1:
        return "inactive"
    return "never"
