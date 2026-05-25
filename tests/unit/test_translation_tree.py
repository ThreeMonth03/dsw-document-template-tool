"""Tests for translator-facing unit tree export and sync."""

from __future__ import annotations

from pathlib import Path

import pytest

from dsw_document_template_tool.template_transform import expand_template_dir
from dsw_document_template_tool.translation_tree import (
    TranslationTreeError,
    export_translation_tree,
    sync_translation_tree,
)


def _write_compact_template(tmp_path: Path, source_text: str) -> Path:
    compact_dir = tmp_path / "compact"
    (compact_dir / "src").mkdir(parents=True)
    (compact_dir / "template.json").write_text(
        """
{
  "organizationId": "demo",
  "templateId": "sample",
  "version": "1.0.0"
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (compact_dir / "src" / "index.html.j2").write_text(
        source_text.lstrip(),
        encoding="utf-8",
    )
    return compact_dir


def _read_translation_docs(tree_dir: Path) -> list[str]:
    return [path.read_text(encoding="utf-8") for path in sorted(tree_dir.rglob("translation.md"))]


def _extract_sentence_sections(markdown_docs: list[str]) -> str:
    sections: list[str] = []
    for markdown_text in markdown_docs:
        before_translation = markdown_text.split("\n### Translation (zh_Hant)\n", 1)[0]
        sentence_block = before_translation.split("```text\n", 1)[1].rsplit("\n```", 1)[0]
        sections.append(sentence_block)
    return "\n".join(sections)


def _extract_sentence_list(markdown_docs: list[str]) -> list[str]:
    sentences: list[str] = []
    for markdown_text in markdown_docs:
        before_translation = markdown_text.split("\n### Translation (zh_Hant)\n", 1)[0]
        sentence_block = before_translation.split("```text\n", 1)[1].rsplit("\n```", 1)[0]
        sentences.append(sentence_block)
    return sentences


def _write_translation_block(document_path: Path, translation_text: str) -> None:
    original_doc = document_path.read_text(encoding="utf-8")
    empty_translation_block = "\n### Translation (zh_Hant)\n\n~~~jinja\n\n~~~"
    translated_block = f"\n### Translation (zh_Hant)\n\n~~~jinja\n{translation_text}\n~~~"
    document_path.write_text(
        original_doc.replace(empty_translation_block, translated_block),
        encoding="utf-8",
    )


def test_export_translation_tree_creates_one_document_per_unit(tmp_path: Path) -> None:
    """Expanded wrapper units should become standalone translation documents."""

    compact_dir = tmp_path / "compact"
    (compact_dir / "src").mkdir(parents=True)
    (compact_dir / "template.json").write_text(
        """
{
  "organizationId": "demo",
  "templateId": "sample",
  "version": "1.0.0"
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (compact_dir / "src" / "index.html.j2").write_text(
        """
<h1>Hello</h1>
<p>World.</p>
""".lstrip(),
        encoding="utf-8",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    docs = sorted(tree_dir.rglob("translation.md"))
    outline = (tree_dir / "outline.md").read_text(encoding="utf-8")
    assert len(docs) == 2
    first_doc = docs[0].read_text(encoding="utf-8")
    assert "### Sentence (en)" in first_doc
    assert "### Source (en)" not in first_doc
    assert "### Translation (zh_Hant)" in first_doc
    assert "Hello" in first_doc or "World." in first_doc
    assert "- [ ] [file] src/index.html.j2 (0/2)" in outline
    assert "[T] [translation](<tree/src/index.html.j2/" in outline


def test_export_translation_tree_splits_nested_wrapper_into_multiple_units(
    tmp_path: Path,
) -> None:
    """Nested loop/fallback sentences should become separate translation documents."""

    compact_dir = tmp_path / "compact"
    (compact_dir / "src").mkdir(parents=True)
    (compact_dir / "template.json").write_text(
        """
{
  "organizationId": "demo",
  "templateId": "sample",
  "version": "1.0.0"
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (compact_dir / "src" / "index.html.j2").write_text(
        """
<ul>
{%- for item in items -%}
<li>
  {%- if show_tools -%}
    <br>Need tools:
    <ul>
    {%- for tool in tools -%}
      <p><strong>{{ tool }}</strong>
      {%- if tool_pid -%}, available at {{ tool_pid }}</p>{%- else -%}.{%- endif -%}
    {%- endfor -%}
    </ul>
  {%- else -%}
    <p>No tools.</p>
  {%- endif -%}
</li>
{%- endfor -%}
</ul>
""".lstrip(),
        encoding="utf-8",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    docs = sorted(tree_dir.rglob("translation.md"))
    joined_docs = "\n".join(path.read_text(encoding="utf-8") for path in docs)
    outline = (tree_dir / "outline.md").read_text(encoding="utf-8")
    assert "Need tools:" in joined_docs
    assert "available at" in joined_docs
    assert "No tools." in joined_docs
    assert "Need tools:" in outline
    assert "{tool}, available at {tool_pid}." in joined_docs
    assert len(docs) >= 3


def test_export_translation_tree_skips_dynamic_contact_rows(tmp_path: Path) -> None:
    """Dynamic contact details should not become noisy translator-facing units."""

    compact_dir = tmp_path / "compact"
    (compact_dir / "src").mkdir(parents=True)
    (compact_dir / "template.json").write_text(
        """
{
  "organizationId": "demo",
  "templateId": "sample",
  "version": "1.0.0"
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (compact_dir / "src" / "index.html.j2").write_text(
        """
<dd>
  <ul>
    <li>
      {%- if contributorName -%}
        <span class="contact-name">{{ contributorName }}</span>
      {%- else -%}
        <span class="contact-name missing">(name not given)</span>
      {%- endif -%}
      {%- if contributorEmail and contributorOrcid %}
        <br>{{ macros.formatEmail(contributorEmail) }}, {{ macros.formatOrcid(contributorOrcid) }}
      {%- elif contributorEmail %}
        <br>{{ macros.formatEmail(contributorEmail) }}
      {%- elif contributorOrcid %}
        <br>{{ macros.formatOrcid(contributorOrcid) }}
      {%- endif -%}
    </li>
  </ul>
</dd>
""".lstrip(),
        encoding="utf-8",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    docs = sorted(tree_dir.rglob("translation.md"))
    joined_docs = "\n".join(path.read_text(encoding="utf-8") for path in docs)
    outline = (tree_dir / "outline.md").read_text(encoding="utf-8")
    assert len(docs) == 1
    assert "(name not given)" in joined_docs
    assert "(name not given)" in outline
    assert "formatEmail" not in joined_docs
    assert "{value}, {value}" not in joined_docs


def test_export_translation_tree_includes_user_facing_jinja_literals(
    tmp_path: Path,
) -> None:
    """Output string literals inside Jinja expressions should not be missed."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
{{ contributorsResponsibility(contributorsItems, uuids.roleAUuid, "responsible for curation.") }}
{%- set collectedTypes = [] -%}
{%- do collectedTypes.append("questionnaires") -%}
<dd>{{ projectNumber if projectNumber else "N/A" }}</dd>
<p>
  {{ "Additional" if qualityCount > 0 else "Our" }}
  quality processes are: {{ mdQualityOther|dot }}
</p>
<p>{{ collectedTypes|join(" ") }}</p>
<p>We train{{" "}}on: {{ topic }}</p>
{%- if projectKind == "internal" -%}
<p>Visible branch.</p>
{%- endif -%}
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    docs = _read_translation_docs(tree_dir)
    joined_docs = "\n".join(docs)
    sentence_sections = _extract_sentence_sections(docs)
    assert "responsible for curation." in joined_docs
    assert "questionnaires" in joined_docs
    assert "N/A" in joined_docs
    assert "Additional quality processes are:" in sentence_sections
    assert "Our quality processes are:" in sentence_sections
    assert "We train on: {topic}" in sentence_sections
    assert "Visible branch." in joined_docs
    assert "contributorsResponsibility" not in sentence_sections
    assert "projectKind" not in joined_docs
    assert "internal" not in joined_docs


def test_export_translation_tree_keeps_control_flow_sentence_parts_together(
    tmp_path: Path,
) -> None:
    """Jinja branches should not create standalone connector translation units."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>
  We collect data from
  {% if count == 1 -%}
    {{ first }}.
  {%- elif count == 2 -%}
    {{ first }} and {{ second }}.
  {%- else -%}
    {{ first }}, {{ second }}, and {{ third }}.
  {%- endif %}
</p>
<p>
  We will train existing staff
  {%- if topic -%}
    {{" "}}on: {{ topic }}
  {%- endif -%}
  .
</p>
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    sentences = _extract_sentence_list(_read_translation_docs(tree_dir))
    assert any("We collect data from" in sentence for sentence in sentences)
    assert any("We will train existing staff on: {topic}." in sentence for sentence in sentences)
    assert "{value} and {value}." not in sentences
    assert "on: {topic}" not in sentences


def test_export_translation_tree_splits_branch_alternatives_into_units(tmp_path: Path) -> None:
    """Mutually exclusive branches should be separate translator-facing units."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<dt>{% if roles|length == 0 %}Role{% else %}Roles{% endif %}:</dt>
<li>{% if status == "planned" %}(planned){% elif status == "applied" %}(applied){% endif %}</li>
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    sentences = _extract_sentence_list(_read_translation_docs(tree_dir))
    assert "Role" in sentences
    assert "Roles" in sentences
    assert "(planned)" in sentences
    assert "(applied)" in sentences
    assert "RoleRoles:" not in sentences
    assert not any(" / " in sentence for sentence in sentences)


def test_export_translation_tree_splits_glued_branch_alternatives_without_slash(
    tmp_path: Path,
) -> None:
    """Fallbacks and adjacent branch groups should not be collapsed with slash delimiters."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<li>
  <strong>{{ datasetName if datasetName else "(no name given)" }}</strong>
  {% if description -%}<span class="separator">&ndash;</span> {{ description }}{%- endif -%}
</li>
<li>
  {% if share == "open" %}Open{% elif share == "closed" %}Closed{% endif %}
  using
  {% if repository == "domain" %}
    a domain-specific repository
  {% else %}
    a general-purpose repository
  {% endif %}.
</li>
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    sentences = _extract_sentence_list(_read_translation_docs(tree_dir))
    assert "(no name given)" in sentences
    assert "Open" in sentences
    assert "Closed" in sentences
    assert "a domain-specific repository" in sentences
    assert "a general-purpose repository" in sentences
    assert not any(" / " in sentence or sentence.startswith("/ ") for sentence in sentences)


def test_export_translation_tree_splits_single_choice_optional_fragments(
    tmp_path: Path,
) -> None:
    """Known single-choice optional fragments should become complete sentence units."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
{% if selected_count == 1 %}
<p>
  We will be using
  {% if calibrating %}calibrating measurements{% endif %}
  {% if repetition %}repeat samples/measurements{% endif %}
  {% if standardized %}standardized data capture/recording{% endif %}
  as part of the quality process.
</p>
{% endif %}
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    sentences = _extract_sentence_list(_read_translation_docs(tree_dir))
    assert "We will be using calibrating measurements as part of the quality process." in sentences
    assert (
        "We will be using repeat samples/measurements as part of the quality process." in sentences
    )
    assert (
        "We will be using standardized data capture/recording as part of the quality process."
        in sentences
    )
    assert not any(
        sentence.startswith("We will be using calibrating measurements repeat")
        for sentence in sentences
    )


def test_export_translation_tree_splits_complete_if_elif_else_sentences(
    tmp_path: Path,
) -> None:
    """A shared branch site with complete alternatives should not use slash separators."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
{% if mode == "new" -%}
<p>We will collect new interview data.</p>
{%- elif mode == "reuse" -%}
<p>We will re-use an existing dataset.</p>
{%- else -%}
<p>We will not collect or re-use data.</p>
{%- endif %}
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    sentences = _extract_sentence_list(_read_translation_docs(tree_dir))
    assert "We will collect new interview data." in sentences
    assert "We will re-use an existing dataset." in sentences
    assert "We will not collect or re-use data." in sentences
    assert not any(" / " in sentence for sentence in sentences)


def test_export_translation_tree_ignores_machine_only_jinja_literals(tmp_path: Path) -> None:
    """Subscript keys and hidden Jinja block literals are not translator-facing text."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>{{ replyObject["orcid-id"] }}</p>
{{ getValue(config["machine-key"]) }}
{% include "src/questions/example.html.j2" with context %}
<p>{{ createdAt|datetime_format("%d %b %Y") }}</p>
{%- do contributors.append({'name': contributorName, 'email': contributorEmail}) -%}
{%- set hidden = "machine only" -%}
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    assert _read_translation_docs(tree_dir) == []


def test_export_translation_tree_skips_connector_only_fragments(tmp_path: Path) -> None:
    """List lead-ins such as `of:` should not become standalone translation files."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>
  The data cannot become completely open because
  {% if one_reason %}
    of legal reasons.
  {% else %}
    of:
    <ul>
      <li>legal reasons</li>
      <li>patent-related business reasons</li>
    </ul>
  {% endif %}
</p>
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    sentences = _extract_sentence_list(_read_translation_docs(tree_dir))
    assert "/ of:" not in sentences
    assert "legal reasons" in "\n".join(sentences)
    assert "patent-related business reasons" in "\n".join(sentences)


def test_export_translation_tree_excludes_html_entity_punctuation_units(
    tmp_path: Path,
) -> None:
    """Punctuation entities such as angle quotes and dashes are not text to translate."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>Created in &laquo;<a href="{{ serviceUrl }}">{{ serviceName }}</a>&raquo;</p>
<span class="separator">&ndash;</span>
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    docs = _read_translation_docs(tree_dir)
    joined_docs = "\n".join(docs)
    sentence_sections = _extract_sentence_sections(docs)
    assert "Created in" in joined_docs
    assert "»" not in sentence_sections
    assert "–" not in sentence_sections
    assert "raquo" not in joined_docs
    assert "ndash" not in joined_docs


def test_sync_translation_tree_applies_translations_back_to_template(tmp_path: Path) -> None:
    """Translator edits should rebuild a translated expanded template."""

    compact_dir = tmp_path / "compact"
    (compact_dir / "src").mkdir(parents=True)
    (compact_dir / "template.json").write_text(
        """
{
  "organizationId": "demo",
  "templateId": "sample",
  "version": "1.0.0"
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (compact_dir / "src" / "index.html.j2").write_text(
        """
<p>Hello world.</p>
""".lstrip(),
        encoding="utf-8",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    translated_expanded_dir = tmp_path / "translated-expanded"

    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    document_path = next(tree_dir.rglob("translation.md"))
    original_doc = document_path.read_text(encoding="utf-8")
    empty_translation_block = "\n### Translation (zh_Hant)\n\n~~~jinja\n\n~~~"
    translated_block = "\n### Translation (zh_Hant)\n\n~~~jinja\n<p>你好，世界。</p>\n~~~"
    document_path.write_text(
        original_doc.replace(empty_translation_block, translated_block),
        encoding="utf-8",
    )

    sync_translation_tree(
        tree_dir=tree_dir,
        source_dir=expanded_dir,
        output_dir=translated_expanded_dir,
    )

    translated_text = (translated_expanded_dir / "src" / "index.html.j2").read_text(
        encoding="utf-8"
    )
    assert "你好，世界。" in translated_text


def test_sync_translation_tree_keeps_source_text_when_translation_is_blank(tmp_path: Path) -> None:
    """Blank translation fences should fall back to the exported English source unit."""

    compact_dir = tmp_path / "compact"
    (compact_dir / "src").mkdir(parents=True)
    (compact_dir / "template.json").write_text(
        """
{
  "organizationId": "demo",
  "templateId": "sample",
  "version": "1.0.0"
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (compact_dir / "src" / "index.html.j2").write_text(
        """
<p>Hello world.</p>
""".lstrip(),
        encoding="utf-8",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    translated_expanded_dir = tmp_path / "translated-expanded"

    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)
    sync_translation_tree(
        tree_dir=tree_dir,
        source_dir=expanded_dir,
        output_dir=translated_expanded_dir,
    )

    original_text = (expanded_dir / "src" / "index.html.j2").read_text(encoding="utf-8")
    translated_text = (translated_expanded_dir / "src" / "index.html.j2").read_text(
        encoding="utf-8"
    )
    assert translated_text == original_text


def test_sync_translation_tree_restores_translator_placeholders_to_jinja(
    tmp_path: Path,
) -> None:
    """Translator-friendly placeholders should write back as original Jinja variables."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>Available via {{ pid }} for {{ usage }}.</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    translated_expanded_dir = tmp_path / "translated-expanded"

    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    document_path = next(tree_dir.rglob("translation.md"))
    _write_translation_block(
        document_path,
        "<p>為了 {usage}，可透過 {pid} 取得。</p>",
    )

    sync_translation_tree(
        tree_dir=tree_dir,
        source_dir=expanded_dir,
        output_dir=translated_expanded_dir,
    )

    translated_text = (translated_expanded_dir / "src" / "index.html.j2").read_text(
        encoding="utf-8"
    )
    assert "<p>為了 {{ usage }}，可透過 {{ pid }} 取得。</p>" in translated_text


def test_sync_translation_tree_rejects_missing_required_placeholder(
    tmp_path: Path,
) -> None:
    """Sync should fail before output generation when a translation drops a variable."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>Available via {{ pid }} for {{ usage }}.</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    translated_expanded_dir = tmp_path / "translated-expanded"

    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    document_path = next(tree_dir.rglob("translation.md"))
    _write_translation_block(document_path, "<p>可取得。</p>")

    with pytest.raises(TranslationTreeError, match=r"\{pid\}") as exc_info:
        sync_translation_tree(
            tree_dir=tree_dir,
            source_dir=expanded_dir,
            output_dir=translated_expanded_dir,
        )

    assert "translation.md" in str(exc_info.value)
    assert "tree/src/index.html.j2/" in str(exc_info.value)
    assert translated_expanded_dir.exists() is False


def test_sync_translation_tree_rejects_unknown_translator_placeholder(
    tmp_path: Path,
) -> None:
    """Typos such as `{pdi}` should not leak into generated template output."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>Available via {{ pid }}.</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    translated_expanded_dir = tmp_path / "translated-expanded"

    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    document_path = next(tree_dir.rglob("translation.md"))
    _write_translation_block(document_path, "<p>可透過 {pdi} 取得。</p>")

    with pytest.raises(TranslationTreeError, match=r"\{pdi\}"):
        sync_translation_tree(
            tree_dir=tree_dir,
            source_dir=expanded_dir,
            output_dir=translated_expanded_dir,
        )


def test_sync_translation_tree_rejects_unexpected_raw_jinja_placeholder(
    tmp_path: Path,
) -> None:
    """New raw Jinja variables should not be introduced from translation text."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>Available via {{ pid }}.</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    translated_expanded_dir = tmp_path / "translated-expanded"

    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    document_path = next(tree_dir.rglob("translation.md"))
    _write_translation_block(
        document_path,
        "<p>可透過 {{ pid }} / {{ unexpectedPid }} 取得。</p>",
    )

    with pytest.raises(TranslationTreeError, match=r"\{unexpectedPid\}"):
        sync_translation_tree(
            tree_dir=tree_dir,
            source_dir=expanded_dir,
            output_dir=translated_expanded_dir,
        )


def test_export_translation_tree_preserves_existing_translation_text(tmp_path: Path) -> None:
    """Re-export should keep prior translator edits for unchanged unit keys."""

    compact_dir = tmp_path / "compact"
    (compact_dir / "src").mkdir(parents=True)
    (compact_dir / "template.json").write_text(
        """
{
  "organizationId": "demo",
  "templateId": "sample",
  "version": "1.0.0"
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (compact_dir / "src" / "index.html.j2").write_text(
        """
<p>Hello world.</p>
""".lstrip(),
        encoding="utf-8",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"

    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    document_path = next(tree_dir.rglob("translation.md"))
    original_doc = document_path.read_text(encoding="utf-8")
    empty_translation_block = "\n### Translation (zh_Hant)\n\n~~~jinja\n\n~~~"
    translated_block = "\n### Translation (zh_Hant)\n\n~~~jinja\n<p>你好，世界。</p>\n~~~"
    updated_doc = original_doc.replace(
        empty_translation_block,
        translated_block,
    )
    document_path.write_text(updated_doc, encoding="utf-8")

    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    preserved_doc = document_path.read_text(encoding="utf-8")
    outline = (tree_dir / "outline.md").read_text(encoding="utf-8")
    assert "<p>你好，世界。</p>" in preserved_doc
    assert "- [x] [file] src/index.html.j2 (1/1)" in outline
    assert "- [x] [unit]" in outline


def test_export_translation_tree_recovers_deleted_and_malformed_documents(
    tmp_path: Path,
) -> None:
    """Re-export should rebuild damaged unit files while preserving valid translations."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>Hello world.</p>
<p>Available via {{ pid }}.</p>
<p>Goodbye world.</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"

    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    docs = sorted(tree_dir.rglob("translation.md"))
    assert len(docs) == 3
    _write_translation_block(docs[0], "<p>你好，世界。</p>")
    docs[1].write_text("# broken document\n", encoding="utf-8")
    docs[2].unlink()

    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    recovered_docs = sorted(tree_dir.rglob("translation.md"))
    recovered_text = "\n".join(path.read_text(encoding="utf-8") for path in recovered_docs)
    assert len(recovered_docs) == 3
    assert "<p>你好，世界。</p>" in recovered_text
    assert "# broken document" not in recovered_text
    assert recovered_text.count("### Translation (zh_Hant)") == 3


def test_sync_translation_tree_reports_deleted_translation_document(
    tmp_path: Path,
) -> None:
    """Sync should fail with a recovery hint when a unit file is missing."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>Hello world.</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    translated_expanded_dir = tmp_path / "translated-expanded"

    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)
    next(tree_dir.rglob("translation.md")).unlink()

    with pytest.raises(TranslationTreeError, match="make export-translation-tree"):
        sync_translation_tree(
            tree_dir=tree_dir,
            source_dir=expanded_dir,
            output_dir=translated_expanded_dir,
        )
