"""Tests for the Weblate promotion helper."""

from __future__ import annotations

import importlib.util
from pathlib import Path


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
