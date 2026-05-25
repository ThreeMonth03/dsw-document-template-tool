"""Checks for the checked-in KM/template translation workspace."""

from __future__ import annotations

import re
from pathlib import Path

from dsw_document_template_tool.config import load_workflow_config
from dsw_document_template_tool.template_transform import (
    _extract_translatable_jinja_block_literals,
    compact_template_dir,
    expand_template_dir,
    snapshot_tree,
)
from dsw_document_template_tool.translation_tree import export_translation_tree

JINJA_BLOCK_PATTERN = re.compile(r"\{%\s*(?P<body>.*?)\s*%\}", re.DOTALL)


def test_workspace_assets_exist(repo_root: Path) -> None:
    """The repository should keep both KM and template workspaces checked in."""

    km_path = repo_root / "workspace" / "knowledge-models" / "root-zh-hant-2.7.0.km"
    compact_dir = (
        repo_root / "workspace" / "document-templates" / "compact" / "dsw-science-europe-1.30.0"
    )
    expanded_dir = (
        repo_root / "workspace" / "document-templates" / "expanded" / "dsw-science-europe-1.30.0"
    )
    translation_tree_dir = (
        repo_root / "workspace" / "document-templates" / "translation" / "dsw-science-europe-1.30.0"
    )
    font_asset = (
        repo_root
        / "workspace"
        / "document-templates"
        / "assets"
        / "fonts"
        / "NotoSansTC-Variable.ttf"
    )

    assert km_path.is_file()
    assert compact_dir.is_dir()
    assert expanded_dir.is_dir()
    assert translation_tree_dir.is_dir()
    assert font_asset.is_file()
    assert (expanded_dir / "src" / "fonts" / "NotoSansTC-Variable.ttf").is_file()
    assert not any(expanded_dir.rglob("_segments"))
    assert not any(
        "@i18n" in path.read_text(encoding="utf-8") for path in expanded_dir.rglob("*.j2")
    )
    assert not any(
        "{% set __tr_block_" in path.read_text(encoding="utf-8")
        for path in expanded_dir.rglob("*.j2")
    )
    assert any(
        "{# __tr_block_" in path.read_text(encoding="utf-8") for path in expanded_dir.rglob("*.j2")
    )
    assert any(translation_tree_dir.rglob("translation.md"))
    assert "root-zh-hant" in (expanded_dir / "template.json").read_text(encoding="utf-8")
    assert "DSW Document Template Tool CJK font fallback:start" in (
        expanded_dir / "src" / "style.css"
    ).read_text(encoding="utf-8")
    assert "68c26e34-5e77-4e15-9bf7-06ff92582257" in (expanded_dir / "src" / "style.css").read_text(
        encoding="utf-8"
    )
    assert 'assets("src/fonts/NotoSansTC-Variable.ttf")' in (
        expanded_dir / "src" / "style.css"
    ).read_text(encoding="utf-8")
    assert "data:font/ttf;base64" in (expanded_dir / "src" / "style.css").read_text(
        encoding="utf-8"
    )
    assert '"DSW Noto Sans TC", {% endif %}"Open Sans", sans-serif' in (
        expanded_dir / "src" / "style.css"
    ).read_text(encoding="utf-8")


def test_checked_in_expanded_workspace_matches_transform_output(
    repo_root: Path, tmp_path: Path
) -> None:
    """`make transform` output should match the checked-in expanded workspace."""

    compact_dir = (
        repo_root / "workspace" / "document-templates" / "compact" / "dsw-science-europe-1.30.0"
    )
    expanded_dir = (
        repo_root / "workspace" / "document-templates" / "expanded" / "dsw-science-europe-1.30.0"
    )
    generated_dir = tmp_path / "expanded"

    expand_template_dir(source_dir=compact_dir, output_dir=generated_dir)

    assert snapshot_tree(generated_dir) == snapshot_tree(expanded_dir)


def test_checked_in_expanded_workspace_compacts_back_to_original(
    repo_root: Path, tmp_path: Path
) -> None:
    """The expanded workspace should rebuild to the checked-in compact template."""

    compact_dir = (
        repo_root / "workspace" / "document-templates" / "compact" / "dsw-science-europe-1.30.0"
    )
    expanded_dir = (
        repo_root / "workspace" / "document-templates" / "expanded" / "dsw-science-europe-1.30.0"
    )
    rebuilt_dir = tmp_path / "rebuilt"

    compact_template_dir(source_dir=expanded_dir, output_dir=rebuilt_dir)

    assert snapshot_tree(rebuilt_dir) == snapshot_tree(compact_dir)


def test_checked_in_translation_tree_matches_export_output(repo_root: Path, tmp_path: Path) -> None:
    """`make export-translation-tree` output should match the checked-in tree."""

    expanded_dir = (
        repo_root / "workspace" / "document-templates" / "expanded" / "dsw-science-europe-1.30.0"
    )
    translation_tree_dir = (
        repo_root / "workspace" / "document-templates" / "translation" / "dsw-science-europe-1.30.0"
    )
    generated_dir = tmp_path / "translation-tree"

    export_translation_tree(source_dir=expanded_dir, output_dir=generated_dir)

    assert snapshot_tree(generated_dir) == snapshot_tree(translation_tree_dir)


def test_checked_in_translation_tree_surfaces_needed_text_and_excludes_noise(
    repo_root: Path,
) -> None:
    """The shipped tree should expose known output literals without noisy dynamic rows."""

    translation_tree_dir = (
        repo_root / "workspace" / "document-templates" / "translation" / "dsw-science-europe-1.30.0"
    )
    tree_text = _read_translation_tree_sentence_text(translation_tree_dir)
    header_docs = _read_translation_tree_sentence_text(
        translation_tree_dir / "tree" / "src" / "header.html.j2"
    )

    required_literals = [
        "grant number not yet given",
        "questionnaires",
        "case report forms",
        "electronic patient records",
        "Dublin Core",
        "DataCite",
        "DDI (Data Documentation Initiative)",
        'We will collect data related to individuals, i.e. "personal data".',
        "We explored General Data Protection Regulation (GDPR) considerations",
        "The consent form will be available for re-users.",
        "We need to conduct a data protection impact assessment (DPIA).",
        "responsible for reviewing, enhancing, cleaning, or standardizing metadata",
        "responsible for implementing the DMP, and ensuring it is reviewed and revised.",
        "ensuring findability",
        "ensuring accessibility",
        "ensuring interoperability",
        "ensuring reusability",
        "supporting management",
    ]
    forbidden_literals = [
        "%d %b %Y",
        "%d %B %Y",
        "src/questions/",
        "src/macros.html.j2",
        "IntegrationType",
        "PlainType",
        "orcid-id",
        "machine-key",
    ]

    missing_required = [literal for literal in required_literals if literal not in tree_text]
    found_forbidden = [literal for literal in forbidden_literals if literal in tree_text]

    assert missing_required == []
    assert found_forbidden == []
    assert "formatEmail" not in header_docs
    assert "formatOrcid" not in header_docs
    assert "integrationROR" not in header_docs
    assert "{value}, {value}" not in header_docs


def test_checked_in_translation_tree_covers_user_facing_jinja_block_literals(
    repo_root: Path,
) -> None:
    """Jinja append literals that feed rendered text should be translator-facing."""

    expanded_dir = (
        repo_root / "workspace" / "document-templates" / "expanded" / "dsw-science-europe-1.30.0"
    )
    translation_tree_dir = (
        repo_root / "workspace" / "document-templates" / "translation" / "dsw-science-europe-1.30.0"
    )
    tree_text = _read_translation_tree_sentence_text(translation_tree_dir)
    missing_literals: list[str] = []

    for source_path in sorted(expanded_dir.rglob("*.j2")):
        source_text = source_path.read_text(encoding="utf-8")
        relative_path = source_path.relative_to(expanded_dir).as_posix()
        for match in JINJA_BLOCK_PATTERN.finditer(source_text):
            for literal in _extract_translatable_jinja_block_literals(match.group("body")):
                if literal not in tree_text:
                    line = source_text.count("\n", 0, match.start()) + 1
                    missing_literals.append(f"{relative_path}:{line}: {literal}")

    assert missing_literals == []


def _read_translation_tree_sentence_text(root: Path) -> str:
    parts: list[str] = []
    for document_path in sorted(root.rglob("translation.md")):
        markdown_text = document_path.read_text(encoding="utf-8")
        before_translation = markdown_text.split("\n### Translation (zh_Hant)\n", 1)[0]
        sentence = before_translation.split("```text\n", 1)[1].rsplit("\n```", 1)[0]
        parts.append(sentence)
    return "\n".join(parts)


def test_checked_in_translation_tree_has_no_connector_only_units(repo_root: Path) -> None:
    """Checked-in units should not expose sentence fragments such as bare `and`."""

    translation_tree_dir = (
        repo_root / "workspace" / "document-templates" / "translation" / "dsw-science-europe-1.30.0"
    )
    placeholder_pattern = re.compile(r"\{[^}]+\}")
    connectors = {
        "a",
        "an",
        "and",
        "at",
        "by",
        "for",
        "in",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
    }
    fragment_units: list[str] = []

    for document_path in sorted(translation_tree_dir.rglob("translation.md")):
        markdown_text = document_path.read_text(encoding="utf-8")
        before_translation = markdown_text.split("\n### Translation (zh_Hant)\n", 1)[0]
        sentence = before_translation.split("```text\n", 1)[1].rsplit("\n```", 1)[0]
        reduced_sentence = placeholder_pattern.sub(" ", sentence)
        words = re.findall(r"[A-Za-z]+", reduced_sentence)
        substantive_words = [word for word in words if word.lower() not in connectors]
        if not substantive_words:
            fragment_units.append(document_path.relative_to(translation_tree_dir).as_posix())

    assert fragment_units == []


def test_shipped_preview_config_resolves_checked_in_workspace(repo_root: Path, monkeypatch) -> None:
    """The checked-in preview config should resolve to real repo paths."""

    monkeypatch.setenv("DSW_API_URL", "http://localhost:3000/wizard-api")
    monkeypatch.setenv("DSW_API_KEY", "secret-token")

    compact_dir = (
        repo_root / "workspace" / "document-templates" / "compact" / "dsw-science-europe-1.30.0"
    )
    expanded_dir = (
        repo_root / "workspace" / "document-templates" / "expanded" / "dsw-science-europe-1.30.0"
    )

    config = load_workflow_config(repo_root / "config" / "regression.preview.yml")

    assert Path(config.baseline.value).is_dir()
    assert Path(config.candidate.value).is_dir()
    assert Path(config.baseline.value) == compact_dir.resolve()
    assert Path(config.candidate.value) == expanded_dir.resolve()
    assert Path(config.fixtures[0].project.knowledge_model_package_id).is_file()
    assert config.regression.output_dir == (repo_root / "outputs" / "preview").resolve()
    assert config.fixtures[0].events_file is not None
    assert config.fixtures[0].events_file.is_file()


def test_shipped_ci_config_includes_random_render_fixtures(repo_root: Path, monkeypatch) -> None:
    """The CI render job should exercise more than the empty questionnaire."""

    monkeypatch.setenv("DSW_API_URL", "http://localhost:3000/wizard-api")
    monkeypatch.setenv("DSW_EMAIL", "albert.einstein@example.com")
    monkeypatch.setenv("DSW_PASSWORD", "password")

    config = load_workflow_config(repo_root / "config" / "regression.ci.yml")

    assert config.fixtures[0].name == "empty-project"
    assert len(config.generated_fixtures) == 1
    generated = config.generated_fixtures[0]
    assert generated.name_prefix == "random-project"
    assert generated.count == 80
    assert generated.seed == 20260522
    assert generated.max_events >= 300
    assert generated.max_items_per_list == 3
    assert Path(generated.project.knowledge_model_package_id).is_file()


def test_shipped_ci_config_uses_ephemeral_local_dsw(repo_root: Path, monkeypatch) -> None:
    """The CI regression config should not require GitHub Actions secrets."""

    monkeypatch.setenv("DSW_API_URL", "http://localhost:3000/wizard-api")
    monkeypatch.setenv("DSW_EMAIL", "albert.einstein@example.com")
    monkeypatch.setenv("DSW_PASSWORD", "password")

    config = load_workflow_config(repo_root / "config" / "regression.ci.yml")

    assert config.api.url == "http://localhost:3000/wizard-api"
    assert config.api.token is None
    assert config.api.email == "albert.einstein@example.com"
    assert config.api.password == "password"
    assert Path(config.baseline.value).is_dir()
    assert Path(config.candidate.value).is_dir()
    assert Path(config.fixtures[0].project.knowledge_model_package_id).is_file()
    assert config.regression.cleanup_projects is True
    assert config.regression.output_dir == (repo_root / "outputs" / "preview").resolve()
