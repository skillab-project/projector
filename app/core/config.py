import os
from dotenv import load_dotenv

load_dotenv()

TRACKER_API = os.getenv("TRACKER_API")
TRACKER_USERNAME = os.getenv("TRACKER_USERNAME")
TRACKER_PASSWORD = os.getenv("TRACKER_PASSWORD")
USE_LOCAL_SECTOR_FILES = os.getenv("SKILLAB_USE_LOCAL_SECTOR_FILES", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
