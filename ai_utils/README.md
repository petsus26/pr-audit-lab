# AI Utilities

This folder contains the AI resources used while building this project.

| File | Purpose |
|---|---|
| `project_context.md` | Describes the project's structure, data flow, audit rules and assumptions. Give it to any AI coding assistant before asking it to work on this repo. |
| `prompts.md` | The key prompts used during development, with what each one led to. |

## How AI was used

I used Claude as a pair programmer, tutor and debugger throughout the project:

- **Setup:** repo structure, virtual environment and secrets handling.
- **API research:** understanding the GitHub endpoints for PRs, reviews, check runs and commit statuses.
- **Debugging:** diagnosing environment and code issues from error output, including pip failing to install
  pyarrow (caused by the wrong Python installation), an inactive virtual environment, an incorrect
  `requirements.txt`, and indentation and syntax errors.
- **Edge cases:** identifying failure modes (rate limits, missing data, re-run checks) and how to handle them.

## What I verified myself

- Queried both branch protection endpoints for `home-assistant/core` and found that required
  checks are defined in **rulesets**, not classic branch protection (which reports no required checks).
- Inspected a real merged PR and found the required checks are split between **check runs**
  (GitHub Actions) and **commit statuses** (Home Assistant's bot), so both must be fetched.
- Tested each error case: invalid token, invalid repository, missing raw data, and no PRs in the time window.
- Ran a fresh clone of the repository to confirm the setup instructions work. This caught an
  incorrect `requirements.txt`, which I regenerated from the project's virtual environment.