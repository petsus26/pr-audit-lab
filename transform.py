import json
from datetime import datetime

import pandas as pd

from utils import RAW_DIR, PROCESSED_DIR


PASSING_RESULTS = {"success", "skipped", "neutral"}


VERDICT_STATES = {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}


# ---------- helpers ----------

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_time(timestamp):
    """Turn GitHub's '2026-10-29T23:19:29Z' into a datetime (or None if missing)."""
    return datetime.fromisoformat(timestamp) if timestamp else None



def get_required_checks(branch_rules):
    """Pull the required status checks out of a branch's ruleset rules."""
    required = []
    for rule in branch_rules:
        if rule["type"] == "required_status_checks":
            required.extend(rule["parameters"]["required_status_checks"])
    return required



def evaluate_reviews(reviews, pr_author, merged_at):
    """
    Return (passed, approvers).
    Uses each reviewer's latest verdict submitted before the merge.
    """
    latest_verdict = {}  

    for review in reviews:
        user = review.get("user")
        if user is None:  
            continue

        login = user["login"]
        state = review["state"]
        submitted_at = parse_time(review.get("submitted_at"))

        if login == pr_author:  
            continue
        if state not in VERDICT_STATES:  
            continue
        if submitted_at is None or submitted_at > merged_at:  
            continue

        previous = latest_verdict.get(login)
        if previous is None or submitted_at >= previous[0]:
            latest_verdict[login] = (submitted_at, state)

    approvers = sorted(login for login, (_, state) in latest_verdict.items() if state == "APPROVED")
    return len(approvers) >= 1, approvers




def find_check_result(required_check, check_runs, statuses, merged_at):
    """
    Find the result of one required check as it stood at merge time.
    Returns a result string like 'success', 'failure', 'missing'.
    """
    name = required_check["context"]
    app_id = required_check.get("integration_id")
    candidates = []  

 
    for run in check_runs:
        if run["name"] != name:
            continue
        if app_id and run.get("app") and run["app"]["id"] != app_id:
            continue
        candidates.append((parse_time(run["completed_at"]), run["conclusion"]))

  
    for status in statuses:
        if status["context"] == name:
            candidates.append((parse_time(status["updated_at"]), status["state"]))

    if not candidates:
        return "missing"

    before_merge = [c for c in candidates if c[0] is not None and c[0] <= merged_at]
    if not before_merge:
        return "not_finished_before_merge"

  
    _, result = max(before_merge, key=lambda c: c[0])
    return result


def evaluate_checks(required_checks, check_runs, statuses, merged_at):
    """Return (passed, list of failing checks with reasons)."""
    failing = []
    for required_check in required_checks:
        result = find_check_result(required_check, check_runs, statuses, merged_at)
        if result not in PASSING_RESULTS:
            failing.append(f"{required_check['context']} ({result})")
    return len(failing) == 0, failing



def build_report():
    prs = load_json(RAW_DIR / "merged_prs.json")
    rules = load_json(RAW_DIR / "branch_rules.json")
    reviews = load_json(RAW_DIR / "reviews.json")
    check_runs = load_json(RAW_DIR / "check_runs.json")
    statuses = load_json(RAW_DIR / "statuses.json")

    rows = []
    for pr in prs:
        number = str(pr["number"])
        merged_at = parse_time(pr["merged_at"])
        author = pr["user"]["login"] if pr["user"] else "ghost"

        required_checks = get_required_checks(rules.get(pr["base"]["ref"], []))

        cr_passed, approvers = evaluate_reviews(reviews.get(number, []), author, merged_at)
        checks_passed, failing = evaluate_checks(
            required_checks,
            check_runs.get(number, []),
            statuses.get(number, []),
            merged_at,
        )

        rows.append({
            "PR_NUMBER": pr["number"],
            "TITLE": pr["title"],
            "AUTHOR": author,
            "MERGE_DATE": pr["merged_at"],
            "CR_PASSED": cr_passed,
            "CHECKS_PASSED": checks_passed,
            "APPROVERS": ", ".join(approvers),
            "FAILED_CHECKS": "; ".join(failing),
        })

    df = pd.DataFrame(rows)
    df["MERGE_DATE"] = pd.to_datetime(df["MERGE_DATE"])
    return df


def run_transform():
    df = build_report()

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_json(PROCESSED_DIR / "pr_audit.json", orient="records", indent=2, date_format="iso")

    print(f"Processed {len(df)} PRs")
    print(f"  CR_PASSED:     {df['CR_PASSED'].sum()} / {len(df)}")
    print(f"  CHECKS_PASSED: {df['CHECKS_PASSED'].sum()} / {len(df)}")
    return df


if __name__ == "__main__":
    run_transform()