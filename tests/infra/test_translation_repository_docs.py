"""Tests for public translated-template repository documentation checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_check_translation_repository_docs_accepts_complete_docs(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """Complete downstream docs should cover required operations topics."""

    translation_repo = tmp_path / "translation-repo"
    docs_dir = translation_repo / "docs"
    docs_dir.mkdir(parents=True)
    (translation_repo / "README.md").write_text(
        """
# Translation Repo

The operations branch owns configuration. Work happens on sync/v* branches.
Release assets are the reviewed package and preview PDF delivery path.
Public DSW import is manual.
""",
        encoding="utf-8",
    )
    (docs_dir / "security-and-policy.md").write_text(
        """
# Security and Policy

Set TRANSLATION_AUTOMATION_TOKEN when workflow scope is needed:

```shell
gh secret set TRANSLATION_AUTOMATION_TOKEN --repo OWNER/REPOSITORY
```

```yaml
state: available
refresh: false
migrate_into: false
publish_release: false
```

```yaml
state: active
refresh: artifact
migrate_into: auto
publish_release: true
```

```yaml
state: published
refresh: false
migrate_into: false
publish_release: true
```

```yaml
state: archived
refresh: false
migrate_into: false
publish_release: false
```
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "check_translation_repository_docs.py"),
            "--repo",
            str(translation_repo),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "SUCCESS" in result.stdout


def test_check_translation_repository_docs_reports_missing_topics(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """Missing handover topics should fail with actionable output."""

    repo = tmp_path / "translation-repo"
    repo.mkdir()
    (repo / "README.md").write_text(
        "# Translation Repo\n\nThis repository has sync/v* branches.\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "check_translation_repository_docs.py"),
            "--repo",
            str(repo),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "workflow synchronization token" in result.stderr
    assert "version policy snippets" in result.stderr
