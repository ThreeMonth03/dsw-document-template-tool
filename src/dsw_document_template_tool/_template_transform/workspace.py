"""Filesystem helpers for expanded template workspaces."""

from __future__ import annotations

import shutil
from pathlib import Path

from .models import TemplateTransformError

MANIFEST_PATH = Path(".transform") / "manifest.json"
UPSTREAM_README_NAME = "UPSTREAM-README.md"


def reset_dir(path: Path) -> None:
    """Replace one directory with an empty directory."""

    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def validate_template_dir(source_dir: Path) -> None:
    """Ensure one directory looks like a DSW document template."""

    template_json = source_dir / "template.json"
    if not template_json.is_file():
        raise TemplateTransformError(f"Missing template.json in {source_dir}")


def snapshot_tree(root_dir: Path) -> dict[str, bytes]:
    """Return one deterministic file snapshot for content comparisons."""

    snapshot: dict[str, bytes] = {}
    for path in sorted(root_dir.rglob("*")):
        if not path.is_file():
            continue
        relative_path = path.relative_to(root_dir).as_posix()
        snapshot[relative_path] = path.read_bytes()
    return snapshot


def rewrite_workspace_readme(*, source_dir: Path, output_dir: Path) -> None:
    """Write the translator-facing README while preserving the upstream README."""

    source_readme = source_dir / "README.md"
    output_readme = output_dir / "README.md"
    upstream_readme = output_dir / UPSTREAM_README_NAME
    if source_readme.is_file():
        upstream_readme.write_text(source_readme.read_text(encoding="utf-8"), encoding="utf-8")

    output_readme.write_text(
        "\n".join(
            [
                "# Translation Workspace",
                "",
                "This folder is the sentence-preserving workspace generated from the",
                "compact DSW template.",
                "",
                "- Edit `src/**/*.j2` in place.",
                "- Generated `__tr_block_####` comment markers keep whole headings,",
                "  paragraphs, and list items together so later string extraction can work",
                "  on complete units without changing Jinja scope.",
                "- The older `src/_segments/...` split-file layout is obsolete and should not",
                "  exist in this workspace anymore.",
                "- Run `make compact-template` to rebuild a DSW-uploadable template.",
                "- Do not edit `.transform/manifest.json` manually.",
                "",
                f"The original upstream README is preserved in `{UPSTREAM_README_NAME}`.",
                "",
            ]
        ),
        encoding="utf-8",
    )
