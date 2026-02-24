from pydantic import BaseModel
from datetime import date, datetime


class PersonBase(BaseModel):
    full_name: str | None = None
    full_name_alt: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    instagram: str | None = None
    city: str | None = None
    date_of_birth: str | None = None
    age: int | None = None
    gender: str | None = None
    notes: str | None = None


class PersonCreate(PersonBase):
    pass


class PersonUpdate(PersonBase):
    pass


class PersonOut(PersonBase):
    id: int
    source_file: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class PersonWithScore(PersonOut):
    total_score: float = 0
    recency_score: float = 0
    frequency_score: float = 0
    monetary_score: float = 0
    events_attended: int = 0
    total_spent: float = 0
    days_since_last: int | None = None
    segment: str = "inactive"


class EventBase(BaseModel):
    name: str
    event_date: date | None = None
    venue: str | None = None
    notes: str | None = None


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    name: str | None = None
    event_date: date | None = None
    venue: str | None = None
    notes: str | None = None


class EventOut(EventBase):
    id: int
    created_at: str | None = None


class ColumnMapping(BaseModel):
    mapping: dict[str, str | None]  # source_col -> canonical_field or None
    event_id: int | None = None
    event_name: str | None = None
    event_date: str | None = None


class MergeDecision(BaseModel):
    candidate_id: int
    action: str  # "merge" or "skip"


class ImportReviewSubmit(BaseModel):
    decisions: list[MergeDecision]


class ExportRequest(BaseModel):
    segment: str | None = None
    min_score: float | None = None
    event_id: int | None = None
    search: str | None = None
