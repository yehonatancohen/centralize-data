import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists (for local development)
env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
SYNONYMS_PATH = BASE_DIR / "column_synonyms.json"

# Turso database configuration
# On Hugging Face Spaces, set these as Secrets in Settings
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

# Local replica path (embedded replica syncs with Turso remote)
DB_PATH = DATA_DIR / "local_replica.db"

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
