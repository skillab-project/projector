
import os
import requests
from dotenv import load_dotenv

load_dotenv(".env")

res = requests.post(
    f"{os.environ['TRACKER_API']}/login",
    json={
        "username": os.environ["TRACKER_USERNAME"],
        "password": os.environ["TRACKER_PASSWORD"],
    },
    timeout=30,
)
res.raise_for_status()
print(res.text.replace('"', '').strip())
