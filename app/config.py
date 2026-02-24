from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
DB_PATH = DATA_DIR / "customers.db"
SYNONYMS_PATH = BASE_DIR / "column_synonyms.json"

# Deduplication thresholds
AUTO_MERGE_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.60

# Scoring weights
RECENCY_WEIGHT = 0.40
FREQUENCY_WEIGHT = 0.35
MONETARY_WEIGHT = 0.25

# Recency decay period in days
RECENCY_DECAY_DAYS = 365

# Churn threshold in days
CHURN_DAYS = 180
