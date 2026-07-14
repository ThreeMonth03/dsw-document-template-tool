"""Tests for GitHub pull-request check helpers."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest


def test_check_gate_requires_sync_check_and_all_checks_to_pass(repo_root: Path) -> None:
    """The gate should wait for translation-sync and block any reported failure."""

    module = _load_github_prs_module(repo_root)

    assert module.evaluate_pull_request_checks([]) is None
    assert (
        module.evaluate_pull_request_checks([{"name": "skip-fork-pr", "bucket": "skipping"}])
        is None
    )
    assert (
        module.evaluate_pull_request_checks(
            [
                {"name": "translation-sync", "bucket": "pending"},
                {"name": "skip-fork-pr", "bucket": "skipping"},
            ]
        )
        is None
    )
    assert (
        module.evaluate_pull_request_checks(
            [
                {"name": "translation-sync", "bucket": "pass"},
                {"name": "skip-fork-pr", "bucket": "skipping"},
            ]
        )
        is module.PullRequestCheckOutcome.PASSED
    )
    assert (
        module.evaluate_pull_request_checks(
            [
                {"name": "translation-sync", "bucket": "pass"},
                {"name": "lint", "bucket": "fail"},
            ]
        )
        is module.PullRequestCheckOutcome.FAILED
    )


def test_pull_request_checks_fail_fast_on_gh_error(
    repo_root: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Authentication and API errors should not look like an empty check list."""

    module = _load_github_prs_module(repo_root)

    def fake_subprocess_run(*_args, **_kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["gh", "pr", "checks"],
            returncode=1,
            stdout="",
            stderr="GraphQL: authentication failed",
        )

    monkeypatch.setattr(module.subprocess, "run", fake_subprocess_run)

    with pytest.raises(RuntimeError, match="authentication failed"):
        module.pull_request_checks(checkout=tmp_path, pull_request_number="42")


def _load_github_prs_module(repo_root: Path) -> ModuleType:
    module_path = repo_root / "scripts" / "ci" / "github_prs.py"
    spec = importlib.util.spec_from_file_location("github_prs_test_module", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
