import os
from dotenv import load_dotenv

load_dotenv()

TRACKER_API = os.getenv("TRACKER_API")
TRACKER_USERNAME = os.getenv("TRACKER_USERNAME")
TRACKER_PASSWORD = os.getenv("TRACKER_PASSWORD")