"""Custom source identities must opt in without masquerading as upstream."""

import json
from pathlib import Path

import pytest

from dsw_document_template_tool.template_transform import (
    TemplateTransformError,
    compact_template_dir,
    expand_template_dir,
    snapshot_tree,
)


def test_explicit_profile_localizes_custom_identity_and_roundtrips(tmp_path: Path):
    source = tmp_path / "source"
    (source / "src").mkdir(parents=True)
    (source / "template.json").write_text(
        json.dumps(
            {
                "organizationId": "example",
                "templateId": "custom",
                "version": "1.0.0",
                "allowedPackages": [
                    {
                        "orgId": "dsw",
                        "kmId": "root",
                        "minVersion": "2.7.0",
                        "maxVersion": None,
                    }
                ],
            },
            indent=2,
        )
        + "\n"
    )
    (source / "src/index.html.j2").write_text('<html lang="en"><p>Example.</p></html>\n')
    (source / "src/style.css").write_text('body { font-family: "Open Sans", sans-serif; }\n')
    expanded = tmp_path / "expanded"
    expand_template_dir(source_dir=source, output_dir=expanded, profile="science-europe")
    identity = json.loads((expanded / "template.json").read_text())
    assert identity["organizationId"] == "example"
    assert identity["templateId"] == "custom"
    assert 'lang="zh-Hant"' in (expanded / "src/index.html.j2").read_text()
    assert "DSW Noto Sans TC" in (expanded / "src/style.css").read_text()
    compact_template_dir(source_dir=expanded, output_dir=tmp_path / "rebuilt")
    assert snapshot_tree(source) == snapshot_tree(tmp_path / "rebuilt")


def test_profile_exclusion_is_per_file_and_traced(tmp_path: Path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    (source / "template.json").write_text(
        json.dumps(
            {
                "organizationId": "example",
                "templateId": "custom",
                "version": "1.0.0",
            }
        )
    )
    for name in ("owned.j2", "inherited.j2"):
        (source / name).write_text("<p>Example.</p>")
    seen = []

    def rewrite(text, *, context, trace, phase):
        seen.append((context.relative_path, phase))
        return text

    monkeypatch.setattr(
        "dsw_document_template_tool.template_transform.rewrite_science_europe_source",
        rewrite,
    )
    expand_template_dir(
        source_dir=source,
        output_dir=tmp_path / "expanded",
        profile="science-europe",
        exclude_profile_paths=("owned.j2",),
    )
    assert seen == [("inherited.j2", "balanced"), ("inherited.j2", "unbalanced")]
    manifest = json.loads((tmp_path / "expanded/.transform/manifest.json").read_text())
    assert manifest["excluded_profile_paths"] == ["owned.j2"]


@pytest.mark.parametrize(
    "options", [{"profile": "typo"}, {"exclude_profile_paths": ("absent.j2",)}]
)
def test_invalid_profile_options_fail_before_output_mutation(tmp_path: Path, options):
    source = tmp_path / "source"
    source.mkdir()
    (source / "template.json").write_text(
        json.dumps(
            {
                "organizationId": "example",
                "templateId": "custom",
                "version": "1.0.0",
            }
        )
    )
    with pytest.raises(TemplateTransformError):
        expand_template_dir(source_dir=source, output_dir=tmp_path / "out", **options)
    assert not (tmp_path / "out").exists()
