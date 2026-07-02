"""Tests for the Weblate promotion helper."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


def load_promote_module(repo_root: Path):
    module_path = repo_root / "scripts" / "ci" / "promote_weblate_xliff.py"
    spec = importlib.util.spec_from_file_location("promote_weblate_xliff", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_write_github_output_reports_changed_state(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """The promotion workflow relies on changed=true to dispatch package CI."""

    module = load_promote_module(repo_root)
    output = tmp_path / "github-output.txt"

    module.write_github_output(str(output), {"changed": "true"})
    module.write_github_output(str(output), {"changed": "false"})

    assert output.read_text(encoding="utf-8").splitlines() == [
        "changed=true",
        "changed=false",
    ]


def test_write_github_output_allows_plain_cli_usage(repo_root: Path) -> None:
    """Running the helper outside GitHub Actions should not require an output file."""

    module = load_promote_module(repo_root)

    module.write_github_output(None, {"changed": "true"})


def test_reset_weblate_review_branch_uses_explicit_force_lease(
    repo_root: Path,
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """Review branch resets should not overwrite concurrent Weblate pushes."""

    module = load_promote_module(repo_root)
    commands: list[tuple[str, ...]] = []

    def fake_run(command: list[object], *, cwd: Path | None = None) -> None:
        assert cwd == tmp_path
        commands.append(tuple(str(part) for part in command))

    monkeypatch.setattr(module, "run", fake_run)

    module.reset_weblate_review_branch(
        host_root=tmp_path,
        weblate_branch="weblate/v1.30.1",
        expected_revision="abc123",
    )

    assert commands == [
        (
            "git",
            "push",
            "origin",
            "HEAD:refs/heads/weblate/v1.30.1",
            "--force-with-lease=refs/heads/weblate/v1.30.1:abc123",
        )
    ]


def test_main_resets_weblate_branch_even_without_target_changes(
    repo_root: Path,
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """A no-op import still proves the review branch can be reset safely."""

    module = load_promote_module(repo_root)
    host_root = tmp_path / "host"
    tooling_root = tmp_path / "tooling"
    host_root.mkdir()
    tooling_root.mkdir()
    reset_calls: list[tuple[str, str]] = []

    def fake_run(command: list[object], *, cwd: Path | None = None) -> None:
        command_parts = [str(part) for part in command]
        if "export" in command_parts and "--output" in command_parts:
            output = Path(command_parts[command_parts.index("--output") + 1])
            output.mkdir(parents=True, exist_ok=True)
            (output / "translation.md").write_text("fresh tree\n", encoding="utf-8")

    monkeypatch.setattr(module, "run", fake_run)
    monkeypatch.setattr(module, "ensure_git_identity", lambda _: None)
    monkeypatch.setattr(module, "ensure_clean_worktree", lambda _: None)
    monkeypatch.setattr(module, "ensure_checked_out_target_branch", lambda *_: None)
    monkeypatch.setattr(module, "copy_weblate_xliff", lambda **_: "old-review-sha")
    monkeypatch.setattr(module, "commit_and_push", lambda **_: False)
    monkeypatch.setattr(
        module,
        "reset_weblate_review_branch",
        lambda *, host_root, weblate_branch, expected_revision: reset_calls.append(
            (weblate_branch, expected_revision)
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "promote_weblate_xliff.py",
            "--host-root",
            str(host_root),
            "--tooling-root",
            str(tooling_root),
            "--target-branch",
            "translation/v1.30.1",
            "--weblate-branch",
            "weblate/v1.30.1",
            "--compact-template-dir",
            "compact",
            "--expanded-template-dir",
            "expanded",
            "--translation-tree-dir",
            "translation",
            "--weblate-xliff",
            "weblate/messages.xlf",
            "--translated-template-dir",
            "translated",
            "--template-organization-id",
            "dsw",
            "--template-id",
            "science-europe-zh-hant",
            "--template-name",
            "Science Europe DMP Template (zh-Hant)",
            "--template-version",
            "1.30.1",
            "--public-readme",
            "README.md",
            "--source-lang",
            "en",
            "--target-lang",
            "zh_Hant",
        ],
    )

    module.main()

    assert reset_calls == [("weblate/v1.30.1", "old-review-sha")]
