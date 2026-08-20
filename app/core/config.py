import os
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_PATH)

TRACKER_API = os.getenv("TRACKER_API")
TRACKER_USERNAME = os.getenv("TRACKER_USERNAME")
TRACKER_PASSWORD = os.getenv("TRACKER_PASSWORD")
DATABASE_URL = os.getenv("DATABASE_URL")


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


TRACKER_CACHE_TTL_DAYS = _int_env("TRACKER_CACHE_TTL_DAYS", 30)
USE_LOCAL_SECTOR_FILES = os.getenv("SKILLAB_USE_LOCAL_SECTOR_FILES", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
