import sqlite3
from contextlib import contextmanager
from app.config import DB_PATH, DATA_DIR


SCHEMA = """
CREATE TABLE IF NOT EXISTS persons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT,
    full_name_alt TEXT,
    first_name TEXT,
    last_name TEXT,
    phone TEXT UNIQUE,
    phone_raw TEXT,
    email TEXT,
    instagram TEXT,
    city TEXT,
    date_of_birth TEXT,
    age INTEGER,
    gender TEXT,
    notes TEXT,
    source_file TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_persons_phone ON persons(phone);
CREATE INDEX IF NOT EXISTS idx_persons_email ON persons(email);
CREATE INDEX IF NOT EXISTS idx_persons_instagram ON persons(instagram);
CREATE INDEX IF NOT EXISTS idx_persons_name ON persons(full_name);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    event_date DATE,
    venue TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL REFERENCES persons(id),
    event_id INTEGER NOT NULL REFERENCES events(id),
    amount_paid REAL DEFAULT 0,
    ticket_type TEXT,
    source_file TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(person_id, event_id)
);

CREATE INDEX IF NOT EXISTS idx_attendance_person ON attendance(person_id);
CREATE INDEX IF NOT EXISTS idx_attendance_event ON attendance(event_id);

CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    row_count INTEGER,
    new_persons INTEGER DEFAULT 0,
    merged_persons INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    column_mapping TEXT,
    event_id INTEGER REFERENCES events(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS merge_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_id INTEGER NOT NULL REFERENCES imports(id),
    existing_person_id INTEGER NOT NULL REFERENCES persons(id),
    incoming_data TEXT NOT NULL,
    match_score REAL NOT NULL,
    match_field TEXT,
    status TEXT DEFAULT 'pending',
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS column_synonyms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_field TEXT NOT NULL,
    synonym TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db():
    """Initialize the database and create tables."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)

    # Migrations: add columns if they don't exist (for existing databases)
    cursor = conn.execute("PRAGMA table_info(persons)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    migrations = {
        "date_of_birth": "ALTER TABLE persons ADD COLUMN date_of_birth TEXT",
        "age": "ALTER TABLE persons ADD COLUMN age INTEGER",
        "gender": "ALTER TABLE persons ADD COLUMN gender TEXT",
    }
    for col, sql in migrations.items():
        if col not in existing_cols:
            conn.execute(sql)

    conn.commit()
    conn.close()


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
