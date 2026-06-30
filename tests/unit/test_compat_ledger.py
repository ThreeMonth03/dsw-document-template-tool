"""Tests for offline upstream compatibility ledgers."""

from __future__ import annotations

import json
from pathlib import Path

from dsw_document_template_tool.compat_ledger import write_compat_ledger


def test_write_compat_ledger_records_expanded_tree_and_translation_stats(
    tmp_path: Path,
) -> None:
    """The ledger should fingerprint built workspaces without starting DSW."""

    workspace_root = tmp_path / "outputs/upstream-workspaces/dsw-science-europe"
    version_root = workspace_root / "v1.30.1"
    workspace_name = "dsw-science-europe-1.30.1"
    compact_dir = version_root / "compact" / workspace_name
    expanded_dir = version_root / "expanded" / workspace_name
    regression_expanded_dir = version_root / "expanded-regression" / workspace_name
    tree_dir = version_root / "translation" / workspace_name
    package_path = (
        tmp_path
        / "outputs/document-templates/dsw-science-europe/v1.30.1/zh-Hant/scaffold"
        / "dsw-science-europe-scaffold.zip"
    )

    _write_template_json(compact_dir)
    _write_jinja(
        expanded_dir,
        "{# __tr_block_0001:start #}<p>Hello {{ name }}.</p>{# __tr_block_0001:end #}",
    )
    _write_jinja(
        regression_expanded_dir,
        "{# __tr_block_0001:start #}<p>Hello {{ name }}.</p>{# __tr_block_0001:end #}",
    )
    _write_translation_tree(tree_dir)
    package_path.parent.mkdir(parents=True)
    package_path.write_bytes(b"fake zip")
    (version_root / "upstream.json").write_text(
        json.dumps({"requested_ref": "v1.30.1", "commit_sha": "abc123"}),
        encoding="utf-8",
    )

    output_dir = tmp_path / "outputs/compat-ledger/dsw-science-europe"
    (output_dir / "v1.29.1.json").parent.mkdir(parents=True)
    (output_dir / "v1.29.1.json").write_text("{}\n", encoding="utf-8")

    entries = write_compat_ledger(
        workspace_root=workspace_root,
        output_dir=output_dir,
        source_template_id="dsw-science-europe",
        scaffold_root=tmp_path / "outputs/document-templates/dsw-science-europe",
    )

    assert len(entries) == 1
    entry = entries[0]
    assert entry["version"] == "v1.30.1"
    assert entry["template"]["metamodel_version"] == "18.0"
    assert entry["expanded"]["generated_block_count"] == 1
    assert entry["translation_tree"]["unit_count"] == 1
    assert entry["translation_tree"]["translated_unit_count"] == 1
    assert entry["translation_tree"]["placeholder_inventory"] == {"name": 1}
    assert entry["scaffold_packages"][0]["bytes"] == len(b"fake zip")

    version_json = json.loads((output_dir / "v1.30.1.json").read_text(encoding="utf-8"))
    summary = (output_dir / "summary.md").read_text(encoding="utf-8")
    assert not (output_dir / "v1.29.1.json").exists()
    assert version_json["expanded"]["tree_digest"]
    assert "| v1.30.1 | 18.0 |" in summary
    assert "Full DSW preview/PDF behavior is still covered" in summary


def _write_template_json(template_dir: Path) -> None:
    template_dir.mkdir(parents=True)
    (template_dir / "template.json").write_text(
        json.dumps(
            {
                "organizationId": "dsw",
                "templateId": "science-europe",
                "version": "1.30.1",
                "metamodelVersion": "18.0",
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _write_jinja(template_dir: Path, text: str) -> None:
    (template_dir / "src").mkdir(parents=True)
    (template_dir / "template.json").write_text("{}\n", encoding="utf-8")
    (template_dir / "src/index.html.j2").write_text(text + "\n", encoding="utf-8")


def _write_translation_tree(tree_dir: Path) -> None:
    document_path = tree_dir / "tree/src/index.html.j2/wrapper/unit/translation.md"
    document_path.parent.mkdir(parents=True)
    document_path.write_text(
        "\n".join(
            [
                "# Translation Unit",
                "",
                "### Sentence (en)",
                "",
                "```text",
                "Hello {name}.",
                "```",
                "",
                "### Translation (zh_Hant)",
                "",
                "~~~jinja",
                "你好 {name}。",
                "~~~",
                "",
            ]
        ),
        encoding="utf-8",
    )
    manifest_path = tree_dir / ".translation-tree/manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": 2,
                "units": [
                    {
                        "source_file": "src/index.html.j2",
                        "wrapper_key": "wrapper",
                        "document_path": document_path.relative_to(tree_dir).as_posix(),
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
