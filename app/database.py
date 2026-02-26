import libsql
from contextlib import contextmanager
from app.config import DB_PATH, DATA_DIR, TURSO_DATABASE_URL, TURSO_AUTH_TOKEN


# ---------------------------------------------------------------------------
# Row factory compatibility layer
# ---------------------------------------------------------------------------
# libsql does not support sqlite3.Row or row_factory. We wrap the cursor
# and connection to automatically convert rows to dict-like objects that
# support row["col"], dict(row), and row[index] — all patterns in the codebase.

class _DictRow(dict):
    """A dict subclass that also supports index-based access."""
    def __init__(self, keys, values):
        super().__init__(zip(keys, values))
        self._keys = keys
        self._values_list = list(values)

    def keys(self):
        return self._keys

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values_list[key]
        return super().__getitem__(key)


class _CursorWrapper:
    """Wraps a libsql cursor to return _DictRow objects from fetch methods."""
    def __init__(self, cursor):
        self._cursor = cursor

    def _make_row(self, raw_row):
        if raw_row is None:
            return None
        keys = [col[0] for col in self._cursor.description]
        return _DictRow(keys, raw_row)

    def fetchone(self):
        return self._make_row(self._cursor.fetchone())

    def fetchall(self):
        if not self._cursor.description:
            return []
        keys = [col[0] for col in self._cursor.description]
        return [_DictRow(keys, row) for row in self._cursor.fetchall()]

    def fetchmany(self, size=None):
        if not self._cursor.description:
            return []
        keys = [col[0] for col in self._cursor.description]
        rows = self._cursor.fetchmany(size) if size else self._cursor.fetchmany()
        return [_DictRow(keys, row) for row in rows]

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description

    def close(self):
        return self._cursor.close()

    def __iter__(self):
        return self

    def __next__(self):
        row = self._cursor.fetchone()
        if row is None:
            raise StopIteration
        keys = [col[0] for col in self._cursor.description]
        return _DictRow(keys, row)


class _ConnectionWrapper:
    """Wraps a libsql connection to return _CursorWrapper from execute methods."""
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, parameters=()):
        return _CursorWrapper(self._conn.execute(sql, parameters))

    def executemany(self, sql, parameters):
        return _CursorWrapper(self._conn.executemany(sql, parameters))

    def executescript(self, sql):
        return self._conn.executescript(sql)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def sync(self):
        return self._conn.sync()

    def cursor(self):
        return _CursorWrapper(self._conn.cursor())


# ---------------------------------------------------------------------------
# Re-export IntegrityError so other modules import it from here
# ---------------------------------------------------------------------------
try:
    from libsql import IntegrityError
except ImportError:
    import sqlite3
    IntegrityError = sqlite3.IntegrityError


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


def _create_connection():
    """Create a libsql connection (embedded replica with Turso sync)."""
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        conn = libsql.connect(
            database=str(DB_PATH),
            sync_url=TURSO_DATABASE_URL,
            auth_token=TURSO_AUTH_TOKEN,
        )
    else:
        # Fallback: local-only mode (for development without Turso)
        conn = libsql.connect(database=str(DB_PATH))
    return conn


def init_db():
    """Initialize the database and create tables."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = _create_connection()
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

    # Sync schema to Turso remote
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        conn.sync()

    conn.close()


def get_connection():
    """Get a database connection with dict-based row wrapping."""
    conn = _create_connection()
    conn.execute("PRAGMA foreign_keys=ON")
    return _ConnectionWrapper(conn)


@contextmanager
def get_db():
    """Context manager for database connections."""
    wrapper = get_connection()
    try:
        yield wrapper
        wrapper.commit()
        if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
            wrapper.sync()
    except Exception:
        wrapper.rollback()
        raise
    finally:
        wrapper.close()
