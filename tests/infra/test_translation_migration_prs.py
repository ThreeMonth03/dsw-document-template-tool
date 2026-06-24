"""Tests for migration PR automation helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def test_manual_pull_request_url_uses_github_environment(
    repo_root: Path,
    monkeypatch,
) -> None:
    """Manual fallback URLs should point at a compare page with both branches."""

    module = _load_migration_pr_module(repo_root)
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_REPOSITORY", "ThreeMonth03/example")

    url = module.manual_pull_request_url(
        base_branch="translation/v1.29.1",
        head_branch="automation/migrate-v1.30.1-to-v1.29.1",
    )

    assert url == (
        "https://github.com/ThreeMonth03/example/compare/"
        "translation%2Fv1.29.1...automation%2Fmigrate-v1.30.1-to-v1.29.1?expand=1"
    )


def test_pr_command_permission_failure_is_warning(
    repo_root: Path,
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    """PR creation can be blocked by repository settings without failing migration."""

    module = _load_migration_pr_module(repo_root)
    monkeypatch.setenv("GITHUB_REPOSITORY", "ThreeMonth03/example")

    module._run_pr_command(
        ["bash", "-lc", "exit 1"],
        checkout=tmp_path,
        bot_branch="automation/migrate-v1.30.1-to-v1.29.1",
        target_branch="translation/v1.29.1",
    )

    captured = capsys.readouterr()
    assert "WARNING: Could not create or update migration PR" in captured.err
    assert "https://github.com/ThreeMonth03/example/compare/" in captured.err


def _load_migration_pr_module(repo_root: Path) -> ModuleType:
    module_path = repo_root / "scripts" / "ci" / "create_translation_migration_prs.py"
    spec = importlib.util.spec_from_file_location("create_translation_migration_prs", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
