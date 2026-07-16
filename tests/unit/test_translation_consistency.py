"""Tests for read-only cross-version translation consistency reporting."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from dsw_document_template_tool.translation_repository import (
    TranslationVersionRecord,
    analyze_translation_records,
    consistency,
    inspect_translation_repository,
    load_translation_repository_config,
    render_consistency_markdown,
    report_as_json,
)


def test_consistency_report_separates_gaps_from_wording_drift() -> None:
    """Blank targets and different wording should remain distinct review signals."""

    report = analyze_translation_records(
        {
            "v1.30.0": (
                _record("v1.30.0", "Shared exact source.", "hash-a", "共用譯文。", "a"),
                _record("v1.30.0", "Visible source only.", "hash-b", "舊版譯文。", "b"),
                _record("v1.30.0", "Version-specific source.", "hash-c", "單版譯文。", "c"),
            ),
            "v1.30.1": (
                _record("v1.30.1", "Shared exact source.", "hash-a", "", "d"),
                _record("v1.30.1", "Visible source only.", "hash-d", "新版譯文。", "e"),
            ),
        }
    )

    assert report.versions == ("v1.30.0", "v1.30.1")
    assert report.units_by_version == {"v1.30.0": 3, "v1.30.1": 2}
    assert report.shared_source_count == 2
    assert report.translation_gap_count == 1
    assert report.wording_drift_count == 1
    assert [(item.source_match, item.issues) for item in report.findings] == [
        ("exact-source", ("translation-gap",)),
        ("visible-source-only", ("wording-drift",)),
    ]


def test_consistency_report_ignores_matching_or_all_blank_targets() -> None:
    """Matching translations and untranslated scaffolds should not create noise."""

    report = analyze_translation_records(
        {
            "v1.29.1": (
                _record("v1.29.1", "Translated.", "same", "相同。", "a"),
                _record("v1.29.1", "Not started.", "blank", "", "b"),
            ),
            "v1.30.0": (
                _record("v1.30.0", "Translated.", "same", "相同。", "c"),
                _record("v1.30.0", "Not started.", "blank", "", "d"),
            ),
        }
    )

    assert report.shared_source_count == 2
    assert report.findings == ()


def test_consistency_report_accepts_a_single_working_version() -> None:
    """A repository should remain healthy before a second version is opted in."""

    report = analyze_translation_records(
        {"v1.30.1": (_record("v1.30.1", "Only version.", "hash", "唯一版本。", "a"),)}
    )

    assert report.versions == ("v1.30.1",)
    assert report.shared_source_count == 0
    assert report.findings == ()


def test_consistency_report_outputs_stable_json_and_capped_markdown() -> None:
    """Artifacts should be complete while the job summary may stay concise."""

    report = analyze_translation_records(
        {
            "v1.30.0": (
                _record("v1.30.0", "First | source.", "a", "第一版", "a"),
                _record("v1.30.0", "Second source.", "b", "第二版", "b"),
            ),
            "v1.30.1": (
                _record("v1.30.1", "First | source.", "a", "不同第一版", "c"),
                _record("v1.30.1", "Second source.", "b", "不同第二版", "d"),
            ),
        }
    )

    json_report = report_as_json(report)
    summary = render_consistency_markdown(report, max_findings=1)

    assert '"finding_count": 2' in json_report
    assert "## 1. wording-drift (exact-source)" in summary
    assert "omits 1 additional findings" in summary
    assert "First | source." in summary


def test_consistency_report_reads_version_branches_without_checkout(tmp_path: Path) -> None:
    """Repository inspection should use Git objects and leave the current branch unchanged."""

    repo = tmp_path / "translation-repo"
    repo.mkdir()
    _git(repo, "init", "-b", "operations")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "Tests")
    (repo / "translation-config.yml").write_text(_translation_config(), encoding="utf-8")
    _git(repo, "add", "translation-config.yml")
    _git(repo, "commit", "-m", "operations")

    for version, translation in (("v1.30.0", "舊版。"), ("v1.30.1", "新版。")):
        _git(repo, "checkout", "operations")
        _git(repo, "checkout", "-b", f"sync/{version}")
        _write_tree(repo, version=version, translation=translation)
        _git(repo, "add", "workspace")
        _git(repo, "commit", "-m", f"add {version}")
    _git(repo, "checkout", "operations")

    config = load_translation_repository_config(repo / "translation-config.yml")
    report = inspect_translation_repository(repo=repo, config=config)

    assert report.wording_drift_count == 1
    assert report.findings[0].source_match == "exact-source"
    assert _git_output(repo, "branch", "--show-current") == "operations"


def test_consistency_fetch_uses_configured_branch_prefix(tmp_path: Path, monkeypatch) -> None:
    """CI fetches must not hard-code the example repository's sync/ prefix."""

    repo = tmp_path / "translation-repo"
    repo.mkdir()
    config_path = repo / "translation-config.yml"
    config_text = _translation_config().replace(
        "version_branch_prefix: sync/",
        "version_branch_prefix: work/",
    )
    config_path.write_text(
        config_text,
        encoding="utf-8",
    )
    config = load_translation_repository_config(config_path)
    calls: list[tuple[Path, tuple[str, ...]]] = []

    def fake_git(path: Path, *args: str, text: bool = True):
        calls.append((path, args))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(consistency, "_git", fake_git)

    consistency.fetch_version_branches(repo=repo, config=config)

    assert calls == [
        (
            repo.resolve(),
            (
                "fetch",
                "--prune",
                "origin",
                "+refs/heads/work/*:refs/remotes/origin/work/*",
            ),
        )
    ]


def _record(
    version: str,
    source: str,
    source_hash: str,
    translation: str,
    suffix: str,
) -> TranslationVersionRecord:
    return TranslationVersionRecord(
        version=version,
        branch=f"sync/{version}",
        document_path=f"tree/{suffix}/translation.md",
        source_file=f"src/{suffix}.j2",
        unit_key=f"unit-{suffix}",
        source_hash=source_hash,
        source_sentence=source,
        translation=translation,
    )


def _write_tree(repo: Path, *, version: str, translation: str) -> None:
    root = (
        repo
        / "workspace"
        / "document-templates"
        / "translation"
        / f"dsw-science-europe-{version.removeprefix('v')}"
    )
    document_path = "tree/unit/translation.md"
    document = root / document_path
    document.parent.mkdir(parents=True)
    document.write_text(
        f"""# Translation Unit

### Sentence (en)

```text
Shared sentence.
```

### Translation (zh_Hant)

~~~jinja
{translation}
~~~
""",
        encoding="utf-8",
    )
    manifest_path = root / ".translation-tree" / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": 2,
                "source_lang": "en",
                "target_lang": "zh_Hant",
                "units": [
                    {
                        "source_file": "src/example.j2",
                        "unit_key": "shared-unit",
                        "unit_source_hash": "same-source-hash",
                        "document_path": document_path,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _translation_config() -> str:
    return """schema_version: 2
template:
  organization_id: dsw
  template_id: science-europe
  upstream_repository: https://example.invalid/upstream.git
  supported_ref_spec: v1.30.0+
  supported_versions: [v1.30.0, v1.30.1]
version_policy:
  defaults:
    state: active
    refresh: artifact
    migrate_into: auto
    publish_release: true
    reason: test
translation:
  source_language: en
  target_language: zh_Hant
  target_language_label: zh-Hant
  translated_template_organization_id: dsw
  translated_template_id: science-europe-zh-hant
  translated_template_name: Science Europe zh-Hant
branches:
  control_branch: operations
  version_branch_prefix: sync/
tooling:
  repository: owner/tool
  ref: master
migration:
  mode: exact-only
  non_exact_policy: leave_empty_needs_translation
  auto_pr_enabled: true
  auto_pr_branch_prefix: automation/migrate
  auto_merge_when_clean: true
"""


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def _git_output(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
