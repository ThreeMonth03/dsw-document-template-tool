"""GitHub pull-request check helpers shared by CI orchestration scripts."""

from __future__ import annotations

import json
import subprocess
import time
from enum import Enum
from pathlib import Path

PULL_REQUEST_CHECK_POLL_SECONDS = 10.0
PULL_REQUEST_CHECK_TIMEOUT_SECONDS = 15 * 60.0
REQUIRED_TRANSLATION_CHECK = "translation-sync"


class PullRequestCheckOutcome(Enum):
    """Terminal outcome of a pull-request check gate."""

    PASSED = "passed"
    FAILED = "failed"
    TIMED_OUT = "timed out"


def wait_for_pull_request_checks(
    *,
    checkout: Path,
    pull_request_number: str,
    required_check_name: str = REQUIRED_TRANSLATION_CHECK,
    timeout_seconds: float = PULL_REQUEST_CHECK_TIMEOUT_SECONDS,
    poll_interval_seconds: float = PULL_REQUEST_CHECK_POLL_SECONDS,
) -> PullRequestCheckOutcome:
    """Wait until the required PR check and all reported checks finish safely."""

    deadline = time.monotonic() + timeout_seconds
    while True:
        checks = pull_request_checks(
            checkout=checkout,
            pull_request_number=pull_request_number,
        )
        outcome = evaluate_pull_request_checks(
            checks,
            required_check_name=required_check_name,
        )
        if outcome is not None:
            return outcome
        if time.monotonic() >= deadline:
            return PullRequestCheckOutcome.TIMED_OUT
        print(f"INFO: Waiting for PR #{pull_request_number} check {required_check_name!r} to pass.")
        time.sleep(poll_interval_seconds)


def pull_request_checks(
    *,
    checkout: Path,
    pull_request_number: str,
) -> list[dict[str, object]]:
    """Read the current GitHub check states for one pull request."""

    args = [
        "gh",
        "pr",
        "checks",
        pull_request_number,
        "--json",
        "name,state,bucket",
    ]
    print("+ " + " ".join(args))
    result = subprocess.run(
        args,
        cwd=checkout,
        text=True,
        check=False,
        capture_output=True,
    )
    raw_checks = result.stdout.strip()
    if not raw_checks:
        error_message = result.stderr.strip()
        if result.returncode == 0 or "no checks reported" in error_message.lower():
            return []
        raise RuntimeError(
            "Could not read pull-request checks with gh: "
            f"{error_message or f'exit code {result.returncode}'}"
        )
    try:
        parsed_checks = json.loads(raw_checks)
    except json.JSONDecodeError as error:
        raise RuntimeError("gh pr checks returned invalid JSON") from error
    if not isinstance(parsed_checks, list) or not all(
        isinstance(check, dict) for check in parsed_checks
    ):
        raise RuntimeError("gh pr checks returned an unexpected JSON payload")
    return parsed_checks


def evaluate_pull_request_checks(
    checks: list[dict[str, object]],
    *,
    required_check_name: str = REQUIRED_TRANSLATION_CHECK,
) -> PullRequestCheckOutcome | None:
    """Evaluate reported checks, returning ``None`` while the gate is pending."""

    if not any(check.get("name") == required_check_name for check in checks):
        return None

    buckets = {str(check.get("bucket", "")) for check in checks}
    if buckets & {"cancel", "fail"}:
        return PullRequestCheckOutcome.FAILED
    if buckets and buckets <= {"pass", "skipping"}:
        return PullRequestCheckOutcome.PASSED
    return None
