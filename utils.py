import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()


API_URL = "https://api.github.com"
REPO = os.getenv("GITHUB_REPO", "home-assistant/core")
DAYS_BACK = int(os.getenv("DAYS_BACK", "7"))


RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
OUTPUT_DIR = Path("output")


def get_session():
    """Create a requests session with the GitHub token attached to every call."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN missing: copy .env.example to .env and add your token")

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    return session


def get_all_pages(session, url, params=None, items_key=None):
    """
    Fetch every page of a paginated GitHub endpoint and return one combined list.

    items_key: some endpoints return a list directly (e.g. reviews);
    others wrap it in a dict (e.g. {"check_runs": [...]}). Pass the key for those.
    """
    results = []
    params = {"per_page": 100, **(params or {})}

    while url:
        response = session.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        results.extend(data[items_key] if items_key else data)


        url = response.links.get("next", {}).get("url")
        params = None  

    return results


def save_json(data, path):
    """Save data as nicely formatted JSON, creating folders if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)