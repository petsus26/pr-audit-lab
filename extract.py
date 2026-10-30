from datetime import datetime, timedelta, timezone

from utils import (
    API_URL, REPO, DAYS_BACK, RAW_DIR,
    get_session, get_all_pages, github_get, save_json,
)


def fetch_merged_prs(session, days):
    """Fetch PRs merged within the last `days` days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    merged = []
    page = 1

    while True:
        response = github_get(
            session,
            f"{API_URL}/repos/{REPO}/pulls",
            params={
                "state": "closed",
                "sort": "updated",
                "direction": "desc",
                "per_page": 100,
                "page": page,
            },
        )
        prs = response.json()

        if not prs:
            break

        for pr in prs:

            if pr["merged_at"] and datetime.fromisoformat(pr["merged_at"]) >= since:
                merged.append(pr)

  
        if datetime.fromisoformat(prs[-1]["updated_at"]) < since:
            break

        page += 1

    return merged


def fetch_branch_rules(session, branch):
    """Fetch the active ruleset rules for a branch (includes required status checks)."""
    response = github_get(session, f"{API_URL}/repos/{REPO}/rules/branches/{branch}")
    return response.json()


def fetch_reviews(session, pr_number):
    """All reviews on a PR (APPROVED, CHANGES_REQUESTED, COMMENTED, DISMISSED...)."""
    return get_all_pages(session, f"{API_URL}/repos/{REPO}/pulls/{pr_number}/reviews")


def fetch_check_runs(session, sha):
    """Check runs (e.g. GitHub Actions) reported on a commit."""
    return get_all_pages(
        session,
        f"{API_URL}/repos/{REPO}/commits/{sha}/check-runs",
        items_key="check_runs",
    )


def fetch_statuses(session, sha):
    """Commit statuses (older system, used by e.g. Home Assistant's bot). Latest per context."""
    return get_all_pages(
        session,
        f"{API_URL}/repos/{REPO}/commits/{sha}/status",
        items_key="statuses",
    )


def run_extract():
    session = get_session()


    prs = fetch_merged_prs(session, DAYS_BACK)
    print(f"Found {len(prs)} merged PRs in {REPO} from the last {DAYS_BACK} days")
    save_json(prs, RAW_DIR / "merged_prs.json")

   
    branches = {pr["base"]["ref"] for pr in prs}
    rules = {branch: fetch_branch_rules(session, branch) for branch in branches}
    save_json(rules, RAW_DIR / "branch_rules.json")

 
    reviews, check_runs, statuses = {}, {}, {}

    for i, pr in enumerate(prs, start=1):
        number = str(pr["number"])
        sha = pr["head"]["sha"]  
        print(f"[{i}/{len(prs)}] PR #{number}")

        reviews[number] = fetch_reviews(session, number)
        check_runs[number] = fetch_check_runs(session, sha)
        statuses[number] = fetch_statuses(session, sha)

    save_json(reviews, RAW_DIR / "reviews.json")
    save_json(check_runs, RAW_DIR / "check_runs.json")
    save_json(statuses, RAW_DIR / "statuses.json")

    print(f"Raw data saved to {RAW_DIR}/")


if __name__ == "__main__":
    run_extract()