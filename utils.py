import json
import os
from pathlib import Path
import time

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

class GitHubAPIError(Exception):
    """Raised for GitHub errors we can explain clearly to the user."""


def rate_limit_wait_seconds(response):
    """If this response is a rate limit, return how long to wait. Otherwise None."""
    if "Retry-After" in response.headers: 
        return int(response.headers["Retry-After"])
    if response.headers.get("X-RateLimit-Remaining") == "0":  
        reset_at = int(response.headers["X-RateLimit-Reset"])
        return max(reset_at - int(time.time()), 0) + 1
    return None


def github_get(session, url, params=None, max_retries=3):
    """GET a GitHub URL with clear errors, rate-limit waiting and retries."""
    for attempt in range(1, max_retries + 1):
        response = session.get(url, params=params, timeout=30)

        if response.status_code == 401:
            raise GitHubAPIError("GitHub rejected the token (401). Check GITHUB_TOKEN in .env: it may be wrong or expired.")
        if response.status_code == 404:
            raise GitHubAPIError(f"Not found (404): {url}\nCheck GITHUB_REPO in .env.")

        if response.status_code in (403, 429):
            wait = rate_limit_wait_seconds(response)
            if wait is not None and attempt < max_retries:
                print(f"Rate limit reached. Waiting {wait} seconds before retrying...")
                time.sleep(wait)
                continue

        if response.status_code >= 500 and attempt < max_retries:
            wait = 2 ** attempt  
            print(f"GitHub server error ({response.status_code}). Retrying in {wait}s...")
            time.sleep(wait)
            continue

        response.raise_for_status()  
        return response




def get_all_pages(session, url, params=None, items_key=None):
    """
    Fetch every page of a paginated GitHub endpoint and return one combined list.

    items_key: some endpoints return a list directly (e.g. reviews);
    others wrap it in a dict (e.g. {"check_runs": [...]}). Pass the key for those.
    """
    results = []
    params = {"per_page": 100, **(params or {})}

    while url:
        response = github_get(session, url, params=params)
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