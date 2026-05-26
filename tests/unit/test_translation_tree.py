"""Tests for translator-facing unit tree export and sync."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dsw_document_template_tool.template_transform import expand_template_dir
from dsw_document_template_tool.translation_tree import (
    TranslationTreeError,
    audit_translation_tree,
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


def _write_compact_template_raw(tmp_path: Path, source_text: str) -> Path:
    compact_dir = _write_compact_template(tmp_path, "")
    (compact_dir / "src" / "index.html.j2").write_text(source_text, encoding="utf-8")
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
    assert "available at {tool_pid}" in joined_docs
    assert "{%" not in joined_docs
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


def test_export_translation_tree_does_not_expose_raw_jinja_blocks(tmp_path: Path) -> None:
    """Translator-facing blocks should not ask translators to preserve Jinja code."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>
  {% set fragments = [] %}
  {% do fragments.append("machine literal") %}
  Visible prefix:
  {% if enabled %}
    enabled sentence.
  {% else %}
    disabled sentence.
  {% endif %}
</p>
<p>Plain {{ value }} sentence.</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"

    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    docs = _read_translation_docs(tree_dir)
    assert docs
    assert all("{%" not in doc for doc in docs)
    assert all("{{" not in doc for doc in docs)
    assert audit_translation_tree(tree_dir=tree_dir, source_dir=expanded_dir) == []


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


def test_export_translation_tree_keeps_appended_concat_sentences_together(
    tmp_path: Path,
) -> None:
    """Jinja-built append sentences should expose placeholders in one unit."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
{%- set sentences = [] -%}
{%- do sentences.append("We will document data with " ~ standard ~ " metadata standard.") -%}
<p>{{ sentences|join(" ") }}</p>
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    translated_expanded_dir = tmp_path / "translated-expanded"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    docs = sorted(tree_dir.rglob("translation.md"))
    sentences = _extract_sentence_list(_read_translation_docs(tree_dir))
    assert "We will document data with {standard} metadata standard." in sentences
    assert "We will document data with" not in [sentence.strip() for sentence in sentences]

    document_path = next(
        path
        for path in docs
        if "We will document data with {standard} metadata standard."
        in path.read_text(encoding="utf-8")
    )
    _write_translation_block(document_path, "會使用 {standard} 中繼資料標準描述資料。")

    sync_translation_tree(
        tree_dir=tree_dir,
        source_dir=expanded_dir,
        output_dir=translated_expanded_dir,
    )

    translated_text = (translated_expanded_dir / "src" / "index.html.j2").read_text(
        encoding="utf-8"
    )
    assert "會使用 {{ standard }} 中繼資料標準描述資料。" in translated_text


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


def test_export_translation_tree_keeps_nested_optional_link_with_label(
    tmp_path: Path,
) -> None:
    """Nested URL/non-URL branches should not expose `available via:` alone."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>
  We will re-use this data
  {%- if where -%}
    {{" "}}available via:{{" "}}
    {%- if where.startswith("http://") or where.startswith("https://") -%}
      <a href="{{ where }}">{{ where }}</a>.
    {%- else -%}
      {{ where }}
    {%- endif -%}
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
    assert "available via:" not in sentences
    assert any("available via: {where}" in sentence for sentence in sentences)
    assert audit_translation_tree(tree_dir=tree_dir, source_dir=expanded_dir) == []


def test_export_translation_tree_keeps_nested_restriction_with_label(
    tmp_path: Path,
) -> None:
    """Audit should reject nested restriction branches if the prefix still splits off."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>
  This data are
  {%- if condition == "other" -%}
    {%- set restriction = other -%}
    available with
    {%- if restriction -%}
      following restrictions: "{{ restriction }}".
    {%- else -%}
      {{" "}}restrictions, that will be specified.
    {%- endif -%}
  {%- endif -%}
</p>
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    sentences = _extract_sentence_list(_read_translation_docs(tree_dir))
    assert "available with" not in sentences
    assert any("available with following restrictions" in sentence for sentence in sentences)
    assert any("available with restrictions" in sentence for sentence in sentences)
    issues = audit_translation_tree(tree_dir=tree_dir, source_dir=expanded_dir)

    assert [issue.code for issue in issues] == [
        "hard-to-translate-source-fragment",
        "hard-to-translate-source-fragment",
    ]


def test_audit_translation_tree_reports_unmerged_reason_prefix_fragments(
    tmp_path: Path,
) -> None:
    """CI should reject generic nested reason branches if the prefix still splits."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>
  We considered reusing this data
  {%- if reason -%}
    , but decided not to reuse it
    {%- if reason == "data" -%}
      {{" "}}because it misses data we need
    {%- elif reason == "quality" -%}
      {{" "}}becauseit is not sufficient quality
    {%- endif -%}
    .
  {%- endif -%}
</p>
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    sentences = _extract_sentence_list(_read_translation_docs(tree_dir))
    assert "because it misses data we need" not in sentences
    assert "because it is not sufficient quality" not in sentences
    assert any(
        "but decided not to reuse it because it misses data we need" in sentence
        for sentence in sentences
    )
    assert any(
        "but decided not to reuse it because it is not sufficient quality" in sentence
        for sentence in sentences
    )
    issues = audit_translation_tree(tree_dir=tree_dir, source_dir=expanded_dir)
    assert [issue.code for issue in issues] == [
        "hard-to-translate-source-fragment",
        "hard-to-translate-source-fragment",
        "hard-to-translate-source-fragment",
    ]


def test_export_translation_tree_merges_inline_expression_sentence_split(
    tmp_path: Path,
) -> None:
    """A placeholder in the middle of a sentence should stay in one unit."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>
  {%- if version -%}
    We will use version "{{ version }}" of this dataset.
  {%- endif -%}
</p>
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    sentences = _extract_sentence_list(_read_translation_docs(tree_dir))

    assert 'We will use version "{version}" of this dataset.' in sentences
    assert 'We will use version "' not in sentences
    assert '" of this dataset.' not in sentences
    assert audit_translation_tree(tree_dir=tree_dir, source_dir=expanded_dir) == []


def test_export_translation_tree_merges_multiple_inline_expression_splits(
    tmp_path: Path,
) -> None:
    """Multiple placeholders inside one sentence should remain one translation unit."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>
  {%- if size and count -%}
    We expect to have {{ count }} files of average size {{ size }} GB in total.
  {%- endif -%}
</p>
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    sentences = _extract_sentence_list(_read_translation_docs(tree_dir))

    assert "We expect to have {count} files of average size {size} GB in total." in sentences
    assert "We expect to have" not in sentences
    assert "GB in total." not in sentences
    assert audit_translation_tree(tree_dir=tree_dir, source_dir=expanded_dir) == []


def test_export_translation_tree_prefers_placeholder_region_over_text_fragment(
    tmp_path: Path,
) -> None:
    """Overlapping regions should keep placeholders needed by translators."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<li>
  {% if licenseStart %}
    Starting {{ licenseStart }}:
  {% endif %}
  {% if license == "cc0" %}
    Freely available for any use.
  {% else %}
    Available under restrictions.
  {% endif %}
</li>
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    sentences = _extract_sentence_list(_read_translation_docs(tree_dir))

    assert "Starting {licenseStart}:" in sentences
    assert "Starting" not in sentences
    assert audit_translation_tree(tree_dir=tree_dir, source_dir=expanded_dir) == []


def test_export_translation_tree_keeps_inline_reason_suffix_with_prefix(
    tmp_path: Path,
) -> None:
    """The Science Europe measured-data reason should stay attached to its prefix."""

    compact_dir = _write_compact_template_raw(
        tmp_path,
        """
                <p>Researchers working in other fields will be interested in re-using this data
                
                {%- if measuredDataReuseOtherFieldHowReply -%}
                
                 {{" "}}because: {{measuredDataReuseOtherFieldHowReply|dot}}</p>
                {%- else -%}
                .
                {%- endif -%}
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    sentences = _extract_sentence_list(_read_translation_docs(tree_dir))
    assert "because: {measuredDataReuseOtherFieldHowReply}" not in sentences
    assert any(
        "Researchers working in other fields will be interested in re-using this data because:"
        in sentence
        for sentence in sentences
    )
    assert audit_translation_tree(tree_dir=tree_dir, source_dir=expanded_dir) == []


def test_export_translation_tree_keeps_shared_workspace_branches_complete(
    tmp_path: Path,
) -> None:
    """The Science Europe shared-workspace prefix should stay attached to branches."""

    compact_dir = _write_compact_template_raw(
        tmp_path,
        """
    {%- if sharedWorkspaceReply == uuids.sharedWorkspaceYesAUuid and sharedWorkspaceReliablePreventLossReply -%}
     <p>During the project we will use shared working space to work with our data{{+" "}}
      {%- if sharedWorkspaceReliablePreventLossReply == uuids.sharedReliablePreventLossSufficientAUuid  -%}
        that ensures the prevention of complete data loss.
      {%- elif sharedWorkspaceReliablePreventLossReply == uuids.sharedReliablePreventLossStoredAUuid -%}
        but we will store all essential data elsewhere.
      {%- endif -%}

      {%- set sharedWorkspaceReliableBackupQUuid = [sharedWorkspaceReliableAUuid, uuids.sharedReliableBackupQUuid]|reply_path -%}
      {%- set sharedWorkspaceReliableBackupReply = repliesMap[sharedWorkspaceReliableBackupQUuid]|reply_str_value  -%}
      {%- if sharedWorkspaceReliableBackupReply == uuids.sharedReliableBackupCopyAllSomewhereAUuid -%}
        {{+" "}}And all the data that are stores elsewhere is adequately backed up.
      {%- elif sharedWorkspaceReliableBackupReply == uuids.sharedReliableBackupCopyBackupsAUuid -%}
        {{+" "}}We make (automated) backups of all data stored outside of the working area.
      {%- endif -%}
     </p>

    {%- endif -%}
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    sentences = _extract_sentence_list(_read_translation_docs(tree_dir))
    assert "but we will store all essential data elsewhere." not in sentences
    assert any(
        "During the project we will use shared working space to work with our data "
        "but we will store all essential data elsewhere." in sentence
        for sentence in sentences
    )
    assert audit_translation_tree(tree_dir=tree_dir, source_dir=expanded_dir) == []


def test_export_translation_tree_keeps_software_pid_with_name(
    tmp_path: Path,
) -> None:
    """The Science Europe software PID suffix should keep the software name placeholder."""

    compact_dir = _write_compact_template_raw(
        tmp_path,
        """
                            {%- for swItem in isPublishedSwItems -%}
                                {%- set swNameUuid = [isPublishedSWPath, swItem, uuids.publishedSpecSwUseWhatNameQUuid]|reply_path -%}
                                {%- set swNameReply = repliesMap[swNameUuid]|reply_str_value -%}
                                {%- set swPIDUuid = [isPublishedSWPath, swItem, uuids.publishedSpecSwUseWhatPIDQUuid]|reply_path -%}
                                {%- set swPIDReply = repliesMap[swPIDUuid]|reply_str_value -%}
                                <p><strong>{{ swNameReply if swNameReply else "(no name given)" }}</strong>
                                {%- if swPIDReply -%}
                                , available at {{swPIDReply|dot}}</p>
                                {%- else -%}
                                .
                                {%- endif -%}
                            {%- endfor -%}
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    sentences = _extract_sentence_list(_read_translation_docs(tree_dir))
    assert "{swDisplayName}, available at {swPIDReply}" in sentences
    assert "available at {swPIDReply}" not in sentences
    assert "(no name given)" not in sentences
    assert audit_translation_tree(tree_dir=tree_dir, source_dir=expanded_dir) == []


def test_export_translation_tree_keeps_legal_basis_prefix_with_other_branch(
    tmp_path: Path,
) -> None:
    """The Science Europe GDPR legal-basis branches should include their prefix."""

    compact_dir = _write_compact_template_raw(
        tmp_path,
        """
                    <p> We are collecting and processing personal data{{+" "}}
                    {%- if personalDataLegalBasisReply == uuids.cpersGdprLegalBasisPublicAUuid -%}
                        based on public interest.</p>
                    {%- elif personalDataLegalBasisReply == uuids.cpersGdprLegalBasisAskAUuid -%}
                        based on subject's consent.</p>
                    {%- elif personalDataLegalBasisReply == uuids.cpersGdprLegalBasisOtherAUuid -%}
                        {%- set personalDataLegalBasisOtherQUuid = [personalDataLegalBasisQUuid, uuids.cpersGdprLegalBasisOtherAUuid, uuids. cpersGdprLegalBasisOtherWhichQUuid ]|reply_path -%}
                        {%- set personalDataLegalBasisOtherReply = repliesMap[personalDataLegalBasisOtherQUuid]|reply_str_value  -%}
                        {%- if personalDataLegalBasisOtherReply == uuids.cpersGdprLegalBasisOtherWhichContractAUui -%}
                            in order to fulfil contract.</p>
                        {%- elif personalDataLegalBasisOtherReply == uuids.cpersGdprLegalBasisOtherWhichLegitAUuid -%}
                            based on legitimate interest.</p>
                        {%- elif personalDataLegalBasisOtherReply == uuids.cpersGdprLegalBasisOtherWhichVitalAUuid -%}
                            based on vital interest.</p>
                        {%- elif personalDataLegalBasisOtherReply == uuids.cpersGdprLegalBasisOtherWhichLegalAUuid -%}
                            based on legal requirement.</p>
                        {%- endif -%}
                    {%- endif -%}
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    sentences = _extract_sentence_list(_read_translation_docs(tree_dir))
    assert "in order to fulfil contract." not in sentences
    assert any(
        "We are collecting and processing personal data in order to fulfil contract." in sentence
        for sentence in sentences
    )
    assert audit_translation_tree(tree_dir=tree_dir, source_dir=expanded_dir) == []


def test_export_translation_tree_keeps_open_reason_prefix_with_single_reasons(
    tmp_path: Path,
) -> None:
    """The Science Europe not-open reason branches should be complete sentences."""

    compact_dir = _write_compact_template_raw(
        tmp_path,
        """
      {%- if nReasons > 0 -%}
        <p>
        The data cannot become completely open because 
        {%- if nReasons == 1 -%}
          {%- if legalReasons %}
            of legal reasons.
          {%- elif businessReasonsPatents %}
            of patent-related business reasons.
          {%- elif businessReasonsOther %}
            of non-patent business reasons{{  ": " ~ notOpenBusinessReasonsOther|dot if notOpenBusinessReasonsOther else "." }}
          {%- elif otherReasonsPapers %}
            we want to publish a paper first.
          {%- elif otherReasonsOther %}
            we have other than paper-publishing reasons{{ ": " ~ notOpenOtherReasonsOther|dot if notOpenOtherReasonsOther else "." }}
          {%- endif -%}
        {%- else %}
          of:
          <ul>
            {%- if legalReasons %}
              <li>legal reasons</li>
            {%- endif -%}
            {%- if businessReasonsPatents %}
              <li>patent-related business reasons</li>
            {%- elif businessReasonsOther %}
              <li>non-patent business reasons{{ ": " ~ notOpenBusinessReasonsOther if notOpenBusinessReasonsOther else "" }}</li>
            {%- endif -%}
            {%- if otherReasonsPapers %}
              <li>we want to publish a paper first</li>
            {%- elif otherReasonsOther -%}
              <li>we have other than paper-publishing reasons{{ ": " ~ notOpenOtherReasonsOther if notOpenOtherReasonsOther else "" }}</li>
            {%- endif -%}
          </ul>
        {%- endif -%}
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    sentences = _extract_sentence_list(_read_translation_docs(tree_dir))
    assert "The data cannot become completely open because" not in sentences
    assert "of legal reasons." not in sentences
    assert any(
        "The data cannot become completely open because of legal reasons." in sentence
        for sentence in sentences
    )
    assert any(
        "The data cannot become completely open because of patent-related business reasons."
        in sentence
        for sentence in sentences
    )
    assert audit_translation_tree(tree_dir=tree_dir, source_dir=expanded_dir) == []


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
    sentences = _extract_sentence_list(docs)
    assert "Created in" in joined_docs
    assert "»" not in [sentence.strip() for sentence in sentences]
    assert "–" not in sentence_sections
    assert "raquo" not in joined_docs
    assert "ndash" not in joined_docs


def test_export_translation_tree_preserves_url_like_sentence_text(tmp_path: Path) -> None:
    """Sentence normalization should not corrupt URL-like examples."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>All project web services are accessible via secure HTTP (https://...).</p>
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    sentences = _extract_sentence_list(_read_translation_docs(tree_dir))
    assert sentences == ["All project web services are accessible via secure HTTP (https://...)."]


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
    """Translator edits should use shorthand placeholders instead of raw Jinja."""

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
        "<p>可透過 {{ pid }} 取得。</p>",
    )

    with pytest.raises(TranslationTreeError, match="raw Jinja"):
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


def test_sync_translation_tree_can_patch_output_template_metadata(tmp_path: Path) -> None:
    """Translated output bundles need distinct coordinates from upstream templates."""

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

    sync_translation_tree(
        tree_dir=tree_dir,
        source_dir=expanded_dir,
        output_dir=translated_expanded_dir,
        template_organization_id="dsw",
        template_id="sample-zh-hant",
        template_name="Sample Template (zh-Hant)",
        template_version="1.0.0-zh-hant",
    )

    payload = json.loads((translated_expanded_dir / "template.json").read_text(encoding="utf-8"))
    assert payload["organizationId"] == "dsw"
    assert payload["templateId"] == "sample-zh-hant"
    assert payload["name"] == "Sample Template (zh-Hant)"
    assert payload["version"] == "1.0.0-zh-hant"


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


def test_audit_translation_tree_reports_raw_jinja_translation(tmp_path: Path) -> None:
    """CI should point at translation files that contain executable Jinja."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>Available via {{ pid }}.</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"

    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)
    document_path = next(tree_dir.rglob("translation.md"))
    _write_translation_block(document_path, "<p>可透過 {{ pid }} 取得。</p>")

    issues = audit_translation_tree(tree_dir=tree_dir, source_dir=expanded_dir)

    assert [issue.code for issue in issues] == ["raw-jinja-in-translation"]
    assert "translation.md" in issues[0].location


def test_audit_translation_tree_reports_hard_sentence_fragments(tmp_path: Path) -> None:
    """CI should reject branch leftovers that are too broken for translators."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>and we will make this computer readable form available to others.</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"

    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    issues = audit_translation_tree(tree_dir=tree_dir, source_dir=expanded_dir)

    assert [issue.code for issue in issues] == ["hard-to-translate-source-fragment"]
    assert "and we will make this computer readable form" in issues[0].message
