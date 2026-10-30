# Key Prompts

Prompts used during development, in order. Lightly edited for readability.

## 1. Understanding the assignment
> Here is the assignment brief for a GitHub merged-PR audit. Map each requirement to a
> project structure and point out any requirements that are easy to misinterpret.

**Outcome:** identified that "required status checks" means only the checks enforced by
branch rules, not every check that runs on a PR.

## 2. Finding the required checks
> Classic branch protection for home-assistant/core returns "enabled: false" with no checks.
> Here is the output of the rulesets endpoint. What does it tell me?

**Outcome:** required checks are defined in rulesets: 8 checks from two different apps.

## 3. Locating check results
> Here are the check runs and commit statuses for one merged PR. Where do the 8 required
> checks appear?

**Outcome:** 3 appear as check runs (GitHub Actions) and 5 as commit statuses, so both
endpoints are needed.

## 4. Audit logic
> Write transform logic that decides CR_PASSED and CHECKS_PASSED per PR. Handle re-run
> checks, reviews after merge, dismissed approvals, and missing checks.

## 5. Robustness
> What edge cases could break this pipeline, and how should each be handled?

**Outcome:** added timeouts, retries with exponential backoff, rate-limit waiting,
clear error messages, and safe handling of empty results.