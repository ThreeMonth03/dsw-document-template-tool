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
