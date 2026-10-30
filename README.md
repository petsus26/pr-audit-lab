# Merged PR Audit

Audits merged pull requests in a GitHub repository and reports whether each one
was **approved by at least one reviewer** and **passed all required status checks
before merging**.

Built for the Scytale Junior Data Engineer home assignment, using
[`home-assistant/core`](https://github.com/home-assistant/core) as the target repository.

## How it works

The project is a small ETL pipeline. Each step saves its output, so steps can be
inspected or rerun independently.

```
GitHub API ──▶ extract.py ──▶ data/raw/ ──▶ transform.py ──▶ data/processed/ ──▶ main.py ──▶ output/
              (fetch raw)      (JSON)       (audit logic)        (JSON)        (report)   (CSV + Parquet)
```

| File | Responsibility |
|---|---|
| `extract.py` | Fetches merged PRs, reviews, check runs, commit statuses and branch rules from GitHub |
| `transform.py` | Decides `CR_PASSED` and `CHECKS_PASSED` for each PR |
| `main.py` | Runs the pipeline and writes the final report |
| `utils.py` | Settings, authentication, safe API requests, pagination, file helpers |
| `ai_utils/` | AI context, prompts and notes on how AI was used |

## Setup

Requires Python 3.11.

```bash
git clone https://github.com/petsus26/pr-audit-lab.git
cd pr-audit-lab

python -m venv venv
source venv/Scripts/activate      # Windows (Git Bash)
# source venv/bin/activate        # macOS / Linux

pip install -r requirements.txt
cp .env.example .env
```

Then add a GitHub personal access token to `.env`. A fine-grained token with
**read-only access to public repositories** is enough.

## Usage

```bash
python main.py                  # full run: fetch from GitHub, audit, write report
python main.py --skip-extract   # reuse data in data/raw/ (no API calls)
python main.py --help
```

### Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `GITHUB_TOKEN` | *(required)* | GitHub personal access token |
| `GITHUB_REPO` | `home-assistant/core` | Repository to audit (`owner/name`) |
| `DAYS_BACK` | `7` | Audit PRs merged in the last N days |

## Output

“A sample report from a real run is included in output/.”  
`output/pr_audit_report.csv` and `output/pr_audit_report.parquet`, one row per merged PR:

| Column | Description |
|---|---|
| `PR_NUMBER` | Pull request number |
| `TITLE` | Pull request title |
| `AUTHOR` | GitHub username of the PR author |
| `MERGE_DATE` | When the PR was merged (UTC) |
| `CR_PASSED` | `True` if at least one reviewer approved before the merge |
| `CHECKS_PASSED` | `True` if every required status check passed before the merge |
| `APPROVERS` | Reviewers whose latest verdict was an approval |
| `FAILED_CHECKS` | Required checks that didn't pass, with the reason (e.g. `cla-bot (missing)`) |

`APPROVERS` and `FAILED_CHECKS` aren't in the brief, but a bare `False` doesn't
tell anyone what to fix. These columns explain each result.

### Example run

```
Processed 51 PRs
  CR_PASSED:     51 / 51
  CHECKS_PASSED: 33 / 51
Report saved to output\pr_audit_report.csv and output\pr_audit_report.parquet
```

## How the audit decides

### Code review (`CR_PASSED`)

1. Take each reviewer's **latest** verdict (`APPROVED`, `CHANGES_REQUESTED` or `DISMISSED`) submitted before the merge.
2. `COMMENTED` reviews are ignored, since on GitHub a comment doesn't cancel an approval.
3. Passed if at least one reviewer's latest verdict is `APPROVED`.

This matches the repository's own rule, which requires one approving review.

### Required checks (`CHECKS_PASSED`)

Finding which checks are *required* was the main research challenge:

- **Classic branch protection** for `dev` returns `enabled: false` with no checks.
  Relying on it would wrongly suggest nothing is required.
- The checks are actually defined in **repository rulesets**
  (`GET /repos/{repo}/rules/branches/{branch}`): 8 required checks from two apps.
- On a real PR, 3 of these appear as **check runs** (GitHub Actions) and 5 as
  **commit statuses** (Home Assistant's bot). Both endpoints are therefore fetched.

For each required check, the audit uses the latest result that finished **before the
merge**, taken from the PR's last commit (`head.sha`). `success`, `skipped` and `neutral`
count as passing, matching how GitHub evaluates required checks. Missing, failed, pending,
or finished-after-merge results count as failing.

Most checks on a PR (tests, mypy, pylint) are not required, so they don't affect the result.

## Assumptions and limitations

- **Current rules.** Required checks come from today's ruleset. PRs merged earlier may
  have been governed by slightly different rules.
- **Statuses matched by name.** Commit statuses don't expose an app ID, so they are
  matched on name only. Check runs are matched on name and app ID.
- **Bypasses show as failures.** Admins can sometimes merge despite failing checks.
  These appear as `CHECKS_PASSED = False`, which is the intended purpose of the audit.

## Error handling and edge cases

| Situation | Behaviour |
|---|---|
| Rate limit reached | Waits until the limit resets, then retries |
| GitHub server error (5xx) | Retries with exponential backoff |
| Network stalls | 30-second timeout per request |
| Invalid or expired token | Clear error message, exit code 1 |
| Invalid repository | Clear error message, exit code 1 |
| No merged PRs in the window | Empty report with headers, no crash |
| `--skip-extract` without raw data | Clear error message, exit code 1 |
| PR with no reviews / missing checks | Reported as `False`, with the reason in `FAILED_CHECKS` |
| Deleted GitHub accounts | Handled without crashing |
| Checks re-run before merge | Latest result before the merge is used |

All of the above were tested manually.

## Possible improvements

- Unit tests for the audit rules in `transform.py`
- Look up the ruleset history so older PRs are judged against the rules active at merge time
- Shared base class so other integrations (e.g. JIRA) can reuse the pipeline