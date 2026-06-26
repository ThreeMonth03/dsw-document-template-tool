from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "ci" / "publish_translated_template.py"


def run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=True, text=True, capture_output=True)


def init_repo(path: Path) -> None:
    path.mkdir()
    run(["git", "init"], cwd=path)
    run(["git", "config", "user.name", "test"], cwd=path)
    run(["git", "config", "user.email", "test@example.invalid"], cwd=path)
    run(["git", "checkout", "-b", "main"], cwd=path)


def write_translation_config(path: Path, target_repo: Path) -> None:
    path.write_text(
        f"""
schema_version: 1

template:
  organization_id: dsw
  template_id: science-europe
  upstream_repository: https://github.com/ds-wizard/science-europe-template.git
  supported_ref_spec: v1.30.1+
  supported_versions:
    - v1.30.1

translation:
  source_language: en
  target_language: zh_Hant
  target_language_label: zh-Hant
  translated_template_organization_id: dsw
  translated_template_id: science-europe-zh-hant
  translated_template_name: Science Europe DMP Template (zh-Hant)

branches:
  version_branch_prefix: translation/

tooling:
  repository: ThreeMonth03/DSW-document-template-tool
  ref: master

migration:
  mode: exact-only
  non_exact_policy: leave_empty_needs_translation
  auto_pr_enabled: true
  auto_pr_branch_prefix: automation/migrate
  auto_merge_when_clean: false

publish:
  enabled: false
  target_repository: {target_repo.as_posix()}
  branch_prefix: sync/
""".lstrip(),
        encoding="utf-8",
    )


def test_publish_translated_template_replaces_target_contents(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "template.json").write_text('{"name": "Translated"}\n', encoding="utf-8")
    (source / "src").mkdir()
    (source / "src" / "content.html.j2").write_text("<p>ok</p>\n", encoding="utf-8")

    target = tmp_path / "target"
    init_repo(target)
    (target / "stale.txt").write_text("remove me\n", encoding="utf-8")
    run(["git", "add", "-A"], cwd=target)
    run(["git", "commit", "-m", "initial"], cwd=target)

    result = run(
        [
            sys.executable,
            str(SCRIPT),
            "--source-dir",
            str(source),
            "--target-repo",
            str(target),
            "--target-branch",
            "sync/v1.30.1",
        ]
    )

    assert "Updated local target checkout" in result.stdout
    assert (target / "template.json").read_text(encoding="utf-8") == '{"name": "Translated"}\n'
    assert (target / "src" / "content.html.j2").read_text(encoding="utf-8") == "<p>ok</p>\n"
    assert not (target / "stale.txt").exists()
    assert run(["git", "branch", "--show-current"], cwd=target).stdout.strip() == "sync/v1.30.1"


def test_publish_translated_template_can_read_translation_version_branch(
    tmp_path: Path,
) -> None:
    origin = tmp_path / "translation-origin.git"
    run(["git", "init", "--bare", str(origin)])

    translation_repo = tmp_path / "translation-repo"
    run(["git", "clone", str(origin), str(translation_repo)])
    run(["git", "config", "user.name", "test"], cwd=translation_repo)
    run(["git", "config", "user.email", "test@example.invalid"], cwd=translation_repo)

    target = tmp_path / "target"
    init_repo(target)
    (target / "old.txt").write_text("old\n", encoding="utf-8")
    run(["git", "add", "-A"], cwd=target)
    run(["git", "commit", "-m", "initial"], cwd=target)

    run(["git", "checkout", "-b", "master"], cwd=translation_repo)
    write_translation_config(translation_repo / "translation-config.yml", target)
    run(["git", "add", "-A"], cwd=translation_repo)
    run(["git", "commit", "-m", "config"], cwd=translation_repo)
    run(["git", "push", "origin", "master"], cwd=translation_repo)

    run(["git", "checkout", "-b", "translation/v1.30.1"], cwd=translation_repo)
    template_dir = (
        translation_repo / "outputs/document-templates/dsw-science-europe/v1.30.1/zh-Hant/"
        "dsw-science-europe-zh-hant-1.30.1"
    )
    template_dir.mkdir(parents=True)
    (template_dir / "template.json").write_text('{"name": "From branch"}\n', encoding="utf-8")
    run(["git", "add", "-A"], cwd=translation_repo)
    run(["git", "commit", "-m", "translated output"], cwd=translation_repo)
    run(["git", "push", "origin", "translation/v1.30.1"], cwd=translation_repo)
    run(["git", "checkout", "master"], cwd=translation_repo)

    result = run(
        [
            sys.executable,
            str(SCRIPT),
            "--translation-repo",
            str(translation_repo),
            "--version",
            "v1.30.1",
        ]
    )

    assert "Updated local target checkout" in result.stdout
    assert (target / "template.json").read_text(encoding="utf-8") == '{"name": "From branch"}\n'
    assert not (target / "old.txt").exists()
    assert run(["git", "branch", "--show-current"], cwd=target).stdout.strip() == "sync/v1.30.1"

    worktree_list = run(["git", "worktree", "list", "--porcelain"], cwd=translation_repo).stdout
    assert "dsw-template-publish-" not in worktree_list
