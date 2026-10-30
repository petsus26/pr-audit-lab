# Project Context: Merged PR Audit

## Goal
Audit merged pull requests in a GitHub repository and report, per PR, whether it:
- was approved by at least one reviewer (`CR_PASSED`)
- passed all required status checks before merging (`CHECKS_PASSED`)

## Pipeline (ETL)
1. `extract.py`: calls the GitHub REST API and saves raw, unmodified JSON to `data/raw/`
2. `transform.py`: reads only from `data/raw/`, applies the audit logic, saves to `data/processed/`
3. `main.py`: runs the pipeline and writes the final report (CSV + Parquet) to `output/`
4. `utils.py`: settings, authenticated session, safe requests (retries, rate limits), pagination, file helpers

## Configuration
Set in `.env` (see `.env.example`): `GITHUB_TOKEN`, `GITHUB_REPO`, `DAYS_BACK`.

## GitHub endpoints used
| Data | Endpoint |
|---|---|
| Merged PRs | `GET /repos/{repo}/pulls?state=closed` (filtered on `merged_at`) |
| Required checks | `GET /repos/{repo}/rules/branches/{branch}` |
| Reviews | `GET /repos/{repo}/pulls/{number}/reviews` |
| Check runs | `GET /repos/{repo}/commits/{head_sha}/check-runs` |
| Commit statuses | `GET /repos/{repo}/commits/{head_sha}/status` |

## Audit rules
**CR_PASSED**
- Use each reviewer's latest verdict (`APPROVED`, `CHANGES_REQUESTED`, `DISMISSED`) submitted before the merge.
- `COMMENTED` reviews don't change a verdict. The PR author's own reviews are ignored.
- Passes if at least one reviewer's latest verdict is `APPROVED`.

**CHECKS_PASSED**
- Required checks come from the branch's ruleset (`required_status_checks`), not classic branch protection, which is disabled on `home-assistant/core`.
- Look up each required check in check runs (match name + app ID) and in commit statuses (match context name).
- Use the latest result that finished before the merge.
- `success`, `skipped` and `neutral` count as passing. Missing, failed, pending or finished-after-merge count as failing.

## Conventions
- Extract never processes; transform never calls the API.
- Raw data is saved keyed by PR number (as a string).
- Expected errors raise `GitHubAPIError` or `FileNotFoundError` with a clear message; `main.py` catches these and exits with code 1.
- All network calls go through `github_get` (timeout, retries, rate-limit handling).

## Known assumptions
- Required checks are taken from the *current* ruleset, which may differ from the rules when older PRs were merged.
- Commit statuses don't expose an app ID, so they are matched by name only.