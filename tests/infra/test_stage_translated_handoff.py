from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "ci" / "stage_translated_handoff.py"
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from dsw_document_template_tool.template_transform import expand_template_dir  # noqa: E402
from dsw_document_template_tool.translation_tree import export_translation_tree  # noqa: E402


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
  control_branch: ops
  version_branch_prefix: sync/

tooling:
  repository: ThreeMonth03/dsw-document-template-tool
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
  branch_prefix: publish/
""".lstrip(),
        encoding="utf-8",
    )


def write_minimal_version_workspace(repo: Path, version: str) -> None:
    version_number = version.removeprefix("v")
    workspace_name = f"dsw-science-europe-{version_number}"
    compact_dir = repo / "workspace" / "document-templates" / "compact" / workspace_name
    compact_dir.mkdir(parents=True)
    (compact_dir / "template.json").write_text(
        f"""
{{
  "organizationId": "dsw",
  "templateId": "science-europe",
  "version": "{version_number}"
}}
""".lstrip(),
        encoding="utf-8",
    )
    (compact_dir / "src").mkdir()
    (compact_dir / "src" / "content.html.j2").write_text(
        "<p>Hello world.</p>\n",
        encoding="utf-8",
    )

    expanded_dir = repo / "workspace" / "document-templates" / "expanded" / workspace_name
    tree_dir = repo / "workspace" / "document-templates" / "translation" / workspace_name
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    public_readme = repo / "workspace" / "document-templates" / "public-readme" / "README.md"
    public_readme.parent.mkdir(parents=True)
    public_readme.write_text(
        "Upstream: https://github.com/ds-wizard/science-europe-template/blob/v"
        "{template_version}/README.md\n",
        encoding="utf-8",
    )


def test_stage_translated_handoff_replaces_target_contents(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "template.json").write_text('{"name": "Translated"}\n', encoding="utf-8")
    (source / "src").mkdir()
    (source / "src" / "content.html.j2").write_text("<p>ok</p>\n", encoding="utf-8")
    (source / ".transform").mkdir()
    (source / ".transform" / "manifest.json").write_text("{}\n", encoding="utf-8")
    (source / "UPSTREAM-README.md").write_text("upstream\n", encoding="utf-8")

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
            "publish/v1.30.1",
        ]
    )

    assert "Updated local target checkout" in result.stdout
    assert (target / "template.json").read_text(encoding="utf-8") == '{"name": "Translated"}\n'
    assert (target / "src" / "content.html.j2").read_text(encoding="utf-8") == "<p>ok</p>\n"
    assert not (target / ".transform").exists()
    assert not (target / "UPSTREAM-README.md").exists()
    assert not (target / "stale.txt").exists()
    assert run(["git", "branch", "--show-current"], cwd=target).stdout.strip() == "publish/v1.30.1"


def test_stage_translated_handoff_synthesizes_source_from_workspace(
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

    run(["git", "checkout", "-b", "sync/v1.30.1"], cwd=translation_repo)
    write_minimal_version_workspace(translation_repo, "v1.30.1")
    run(["git", "add", "-A"], cwd=translation_repo)
    run(["git", "commit", "-m", "workspace only"], cwd=translation_repo)
    run(["git", "push", "origin", "sync/v1.30.1"], cwd=translation_repo)
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
    assert not (target / "old.txt").exists()
    assert not (target / ".transform").exists()
    assert not (target / "UPSTREAM-README.md").exists()
    template_payload = (target / "template.json").read_text(encoding="utf-8")
    assert '"templateId": "science-europe-zh-hant"' in template_payload
    assert '"version": "1.30.1"' in template_payload
    assert "blob/v1.30.1/README.md" in (target / "README.md").read_text(encoding="utf-8")
    assert "{template_version}" not in (target / "README.md").read_text(encoding="utf-8")


def test_stage_translated_handoff_can_read_translation_version_branch(
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

    run(["git", "checkout", "-b", "sync/v1.30.1"], cwd=translation_repo)
    template_dir = (
        translation_repo / "outputs/document-templates/dsw-science-europe/v1.30.1/zh-Hant/"
        "dsw-science-europe-zh-hant-1.30.1"
    )
    template_dir.mkdir(parents=True)
    (template_dir / "template.json").write_text('{"name": "From branch"}\n', encoding="utf-8")
    run(["git", "add", "-A"], cwd=translation_repo)
    run(["git", "commit", "-m", "translated output"], cwd=translation_repo)
    run(["git", "push", "origin", "sync/v1.30.1"], cwd=translation_repo)
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
    assert run(["git", "branch", "--show-current"], cwd=target).stdout.strip() == "publish/v1.30.1"

    worktree_list = run(["git", "worktree", "list", "--porcelain"], cwd=translation_repo).stdout
    assert "dsw-template-handoff-" not in worktree_list


def test_stage_translated_handoff_pushes_when_target_branch_is_open_elsewhere(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "template.json").write_text('{"name": "Translated"}\n', encoding="utf-8")

    origin = tmp_path / "target-origin.git"
    run(["git", "init", "--bare", str(origin)])
    target = tmp_path / "target"
    init_repo(target)
    run(["git", "remote", "add", "origin", str(origin)], cwd=target)
    (target / "README.md").write_text("base\n", encoding="utf-8")
    run(["git", "add", "-A"], cwd=target)
    run(["git", "commit", "-m", "base"], cwd=target)
    run(["git", "push", "-u", "origin", "main"], cwd=target)

    run(["git", "checkout", "-b", "publish/v1.30.1"], cwd=target)
    (target / "old.txt").write_text("old\n", encoding="utf-8")
    run(["git", "add", "-A"], cwd=target)
    run(["git", "commit", "-m", "old handoff branch"], cwd=target)
    run(["git", "push", "-u", "origin", "publish/v1.30.1"], cwd=target)
    run(["git", "checkout", "main"], cwd=target)

    open_worktree = tmp_path / "open-handoff-branch"
    run(["git", "worktree", "add", str(open_worktree), "publish/v1.30.1"], cwd=target)
    try:
        result = run(
            [
                sys.executable,
                str(SCRIPT),
                "--source-dir",
                str(source),
                "--target-repo",
                str(target),
                "--target-branch",
                "publish/v1.30.1",
                "--push",
            ]
        )
    finally:
        run(["git", "worktree", "remove", "--force", str(open_worktree)], cwd=target)

    assert "Pushed translated handoff" in result.stdout
    assert _git_show_bare(origin, "publish/v1.30.1:template.json") == '{"name": "Translated"}\n'
    assert not _git_path_exists(origin, "publish/v1.30.1:old.txt")


def test_stage_translated_handoff_local_mode_preserves_existing_local_branch(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "template.json").write_text('{"name": "Translated"}\n', encoding="utf-8")

    origin = tmp_path / "target-origin.git"
    run(["git", "init", "--bare", str(origin)])
    target = tmp_path / "target"
    init_repo(target)
    run(["git", "remote", "add", "origin", str(origin)], cwd=target)
    (target / "README.md").write_text("base\n", encoding="utf-8")
    run(["git", "add", "-A"], cwd=target)
    run(["git", "commit", "-m", "base"], cwd=target)
    run(["git", "push", "-u", "origin", "main"], cwd=target)

    run(["git", "checkout", "-b", "publish/v1.30.1"], cwd=target)
    (target / "local-only.txt").write_text("local base\n", encoding="utf-8")
    run(["git", "add", "-A"], cwd=target)
    run(["git", "commit", "-m", "local handoff branch"], cwd=target)
    local_branch_sha = _git_output(target, "rev-parse", "publish/v1.30.1")

    run(["git", "checkout", "main"], cwd=target)
    run(["git", "checkout", "-b", "remote-handoff", "main"], cwd=target)
    (target / "remote-only.txt").write_text("remote base\n", encoding="utf-8")
    run(["git", "add", "-A"], cwd=target)
    run(["git", "commit", "-m", "remote handoff branch"], cwd=target)
    run(["git", "push", "origin", "remote-handoff:refs/heads/publish/v1.30.1"], cwd=target)
    run(["git", "checkout", "main"], cwd=target)

    result = run(
        [
            sys.executable,
            str(SCRIPT),
            "--source-dir",
            str(source),
            "--target-repo",
            str(target),
            "--target-branch",
            "publish/v1.30.1",
        ]
    )

    assert "Updated local target checkout" in result.stdout
    assert _git_output(target, "rev-parse", "HEAD^") == local_branch_sha
    assert not (target / "remote-only.txt").exists()
    assert run(["git", "branch", "--show-current"], cwd=target).stdout.strip() == "publish/v1.30.1"


def _git_show_bare(repo: Path, revision: str) -> str:
    return subprocess.run(
        ["git", "--git-dir", str(repo), "show", revision],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout


def _git_path_exists(repo: Path, revision: str) -> bool:
    result = subprocess.run(
        ["git", "--git-dir", str(repo), "cat-file", "-e", revision],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _git_output(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.strip()
