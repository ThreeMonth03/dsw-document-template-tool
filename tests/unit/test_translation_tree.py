"""Tests for translator-facing unit tree export and sync."""

from __future__ import annotations

import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from dsw_document_template_tool._translation_tree.output_polish import (
    polish_zh_hant_template_text,
)
from dsw_document_template_tool.template_transform import expand_template_dir
from dsw_document_template_tool.translation_tree import (
    TranslationTreeError,
    audit_translated_template_structure,
    audit_translation_tree,
    export_translation_tree,
    export_xliff,
    import_xliff,
    merge_translation_tree,
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
    template_path = compact_dir / "template.json"
    template = json.loads(template_path.read_text(encoding="utf-8"))
    template.update({"organizationId": "dsw", "templateId": "science-europe"})
    template_path.write_text(
        json.dumps(template, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
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


def _find_translation_doc(tree_dir: Path, sentence_text: str) -> Path:
    for document_path in sorted(tree_dir.rglob("translation.md")):
        if sentence_text in document_path.read_text(encoding="utf-8"):
            return document_path
    raise AssertionError(f"Could not find translation document for {sentence_text!r}")


def _xml_elements(root: ET.Element, local_name: str) -> list[ET.Element]:
    return [element for element in root.iter() if element.tag.rsplit("}", 1)[-1] == local_name]


def test_polish_zh_hant_template_text_normalizes_punctuation_outside_units() -> None:
    """Hard-coded English punctuation around Jinja should not leak to zh-Hant output."""

    source = (
        "角色: 其他, 聯絡人\n"
        "通用型資料儲存庫: {{ macros.integrationFairSharing(repo) }}.\n"
        "特定學科資料儲存庫\n"
        "    : {{ macros.integrationFairSharing(repo) }}.\n"
        "{%- else -%}.\n"
        '{{ ", " if not loop.last else "." }}\n'
        '{{ values|join(", ") }}\n'
        '{{ metadataSentences|join(" ") }}\n'
        "{% if not loop.last %}, {% endif %}\n"
        '資料溯源紀錄{{ ": " ~ value|markdown if value else "." }}\n'
        "這是標準化格式。 這是適合長期保存的格式。\n"
        "第一句。\n"
        "第二句。\n"
        "開放（與任何人共享） 並使用通用型資料儲存庫。\n"
        "開放（與任何人共享）\n"
        "{%- endif %}\n"
        "{% if use_repo %}\n"
        "並使用通用型資料儲存庫。\n"
        "開放（與任何人共享）{{ suffix }}\n"
        "{%- elif use_repo %}\n"
        "並使用通用型資料儲存庫。\n"
        "資料集 （將發布）\n"
        "<strong>資料集</strong> （將發布）\n"
        "自 2023-12-21 起： 可自由使用。\n"
        "並維護 depositar 資料集頁面所需的人力。.\n"
        "ORCID： 0000-0002-1825-0097\n"
        "此資源分配用於確保資料可被找到, 確保資料可被取用與支援資料管理。"
    )

    assert polish_zh_hant_template_text(source) == (
        "角色：其他、聯絡人\n"
        "通用型資料儲存庫：{{ macros.integrationFairSharing(repo) }}。特定學科資料儲存庫\n"
        "    ：{{ macros.integrationFairSharing(repo) }}。\n"
        "{%- else -%}。\n"
        '{{ "、" if not loop.last else "。" }}\n'
        '{{ values|join("、") }}\n'
        '{{ metadataSentences|join("") }}\n'
        "{% if not loop.last %}、{% endif %}\n"
        '資料溯源紀錄{{ "：" ~ value|markdown if value else "。" }}\n'
        "這是標準化格式。這是適合長期保存的格式。第一句。第二句。"
        "開放（與任何人共享）並使用通用型資料儲存庫。"
        "開放（與任何人共享）{%- endif %}{% if use_repo %}並使用通用型資料儲存庫。"
        "開放（與任何人共享）{{ suffix }}{%- elif use_repo %}並使用通用型資料儲存庫。"
        "資料集（將發布）\n"
        "<strong>資料集</strong>（將發布）"
        "自 2023-12-21 起：可自由使用。"
        "並維護 depositar 資料集頁面所需的人力。\n"
        "ORCID： 0000-0002-1825-0097\n"
        "此資源分配用於確保資料可被找到、確保資料可被取用與支援資料管理。"
    )


def test_polish_zh_hant_template_text_replaces_dot_filters_inside_chinese_sentences() -> None:
    """The English `dot` filter can double-punctuate translated zh-Hant clauses."""

    source = (
        "<p>資料將可透過 {{ swPIDReply|dot }} 取得。</p>\n"
        "<p>延後開放期限為 {{ embargoPeriod|dot }}</p>\n"
        '<p>資料溯源紀錄{{ ": " ~ provenanceOther|dot if provenanceOther else "." }}</p>\n'
        "<p>各資料夾將採用以下慣例：{{ scFSysAnalysisFoldersConvs|dot }}</p>\n"
        '<p>{{" - "+projectCostItemDescriptionReply|dot}}</p>\n'
    )

    result = polish_zh_hant_template_text(source)

    assert "{{ swPIDReply|trim }}" in result
    assert "{{ embargoPeriod|trim }}" in result
    assert '{{ "：" ~ provenanceOther|trim if provenanceOther else "。" }}' in result
    assert "{{ scFSysAnalysisFoldersConvs|trim }}" in result
    assert "{%- set __tr_dot_value = projectCostItemDescriptionReply|trim -%}" in result
    assert '{{ "。" if __tr_dot_value[-1] not in ".。!！?？" else "" }}' in result
    assert "|dot" not in result


def test_polish_zh_hant_template_text_collapses_silent_jinja_before_parenthesis() -> None:
    """Silent Jinja between an inline tag and zh-Hant parenthesis must not emit spaces."""

    source = (
        "<strong>資料集</strong>\n{# status #}\n{% if published %}（將發布）\n{# end #}{% endif %}"
    )

    assert polish_zh_hant_template_text(source) == (
        "<strong>資料集</strong>{# status #}{% if published %}（將發布）\n{# end #}{% endif %}"
    )


def _write_compact_template_file(
    *,
    root_dir: Path,
    relative_path: str,
    source_text: str,
) -> Path:
    compact_dir = root_dir
    file_path = compact_dir / "src" / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
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
    file_path.write_text(source_text.lstrip(), encoding="utf-8")
    return compact_dir


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
    assert "<summary>Machine metadata</summary>" in first_doc
    assert "Source Hash" in first_doc
    assert "Hello" in first_doc or "World." in first_doc
    assert "- [ ] [file] src/index.html.j2 (0/2)" in outline
    assert "[T] [translation](<tree/src/index.html.j2/" in outline


def test_translation_document_preserves_collapsed_metadata_when_synced(
    tmp_path: Path,
) -> None:
    """Translator-facing files should stay readable without losing metadata."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>Hello {{ name }}.</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    output_dir = tmp_path / "translated"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    document_path = _find_translation_doc(tree_dir, "Hello {name}.")
    _write_translation_block(document_path, "你好 {name}。")

    document_text = document_path.read_text(encoding="utf-8")
    assert "你好 {name}。" in document_text
    assert "<summary>Machine metadata</summary>" in document_text

    sync_translation_tree(tree_dir=tree_dir, source_dir=expanded_dir, output_dir=output_dir)

    assert "你好 {{ name }}。" in (output_dir / "src" / "index.html.j2").read_text(
        encoding="utf-8",
    )


def test_xliff_round_trip_updates_translation_document(tmp_path: Path) -> None:
    """XLIFF exchange files should update only the editable translation block."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>Hello {{ name }}.</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    xliff_path = tmp_path / "xliff" / "science-europe.zh-Hant.xlf"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    document_path = _find_translation_doc(tree_dir, "Hello {name}.")
    _write_translation_block(document_path, "你好 {name}。")

    export_xliff(
        tree_dir=tree_dir,
        output_path=xliff_path,
        source_lang="en",
        target_lang="zh_Hant",
    )

    root = ET.parse(xliff_path).getroot()
    trans_units = _xml_elements(root, "trans-unit")
    assert len(trans_units) == 1
    assert xliff_path.read_text(encoding="utf-8").startswith(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
    )
    assert trans_units[0].attrib["{http://www.w3.org/XML/1998/namespace}space"] == "preserve"
    assert _xml_elements(root, "source")[0].text == "Hello {name}."
    assert _xml_elements(root, "target")[0].text == "你好 {name}。"
    _xml_elements(root, "target")[0].text = "哈囉 {name}。"
    ET.ElementTree(root).write(xliff_path, encoding="utf-8", xml_declaration=True)

    report = import_xliff(
        tree_dir=tree_dir,
        xliff_path=xliff_path,
        source_lang="en",
        target_lang="zh_Hant",
    )

    assert report.imported_units == 1
    document_text = document_path.read_text(encoding="utf-8")
    assert "哈囉 {name}。" in document_text
    assert "### Sentence (en)" in document_text
    assert "<summary>Machine metadata</summary>" in document_text
    outline = (tree_dir / "outline.md").read_text(encoding="utf-8")
    assert "- [x] [file] src/index.html.j2 (1/1)" in outline


def test_xliff_import_rejects_stale_source_hash(tmp_path: Path) -> None:
    """Stale XLIFF files must not be imported into a changed translation tree."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>Hello {{ name }}.</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    xliff_path = tmp_path / "xliff" / "science-europe.zh-Hant.xlf"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)
    export_xliff(
        tree_dir=tree_dir,
        output_path=xliff_path,
        source_lang="en",
        target_lang="zh_Hant",
    )

    root = ET.parse(xliff_path).getroot()
    for note in _xml_elements(root, "note"):
        if note.attrib.get("from") == "unit_source_hash":
            note.text = "stale-source-hash"
    ET.ElementTree(root).write(xliff_path, encoding="utf-8", xml_declaration=True)

    with pytest.raises(TranslationTreeError, match="source hash does not match"):
        import_xliff(
            tree_dir=tree_dir,
            xliff_path=xliff_path,
            source_lang="en",
            target_lang="zh_Hant",
        )


def test_merge_translation_tree_reuses_exact_unit_key_matches(tmp_path: Path) -> None:
    """Regenerated trees should recover translations for unchanged units."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>Hello {{ name }}.</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    old_tree_dir = tmp_path / "old-tree"
    new_tree_dir = tmp_path / "new-tree"
    output_tree_dir = tmp_path / "merged-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=old_tree_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=new_tree_dir)

    _write_translation_block(_find_translation_doc(old_tree_dir, "Hello {name}."), "你好 {name}。")

    report = merge_translation_tree(
        old_tree_dir=old_tree_dir,
        new_tree_dir=new_tree_dir,
        output_dir=output_tree_dir,
        source_lang="en",
        target_lang="zh_Hant",
    )

    assert report.migrated_units == 1
    assert report.exact_key_matches == 1
    assert "你好 {name}。" in _find_translation_doc(
        output_tree_dir,
        "Hello {name}.",
    ).read_text(encoding="utf-8")
    outline = (output_tree_dir / "outline.md").read_text(encoding="utf-8")
    assert "- [x] [file] src/index.html.j2 (1/1)" in outline
    assert "- [x] [unit]" in outline


def test_merge_translation_tree_preserves_existing_translation_by_default(
    tmp_path: Path,
) -> None:
    """A normal scaffold refresh must not overwrite translator edits."""

    compact_dir = _write_compact_template(tmp_path, "<p>Hello.</p>\n")
    expanded_dir = tmp_path / "expanded"
    old_tree_dir = tmp_path / "old-tree"
    new_tree_dir = tmp_path / "new-tree"
    output_tree_dir = tmp_path / "merged-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=old_tree_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=new_tree_dir)
    _write_translation_block(_find_translation_doc(old_tree_dir, "Hello."), "來源譯文。")
    _write_translation_block(_find_translation_doc(new_tree_dir, "Hello."), "目標譯文。")

    report = merge_translation_tree(
        old_tree_dir=old_tree_dir,
        new_tree_dir=new_tree_dir,
        output_dir=output_tree_dir,
        source_lang="en",
        target_lang="zh_Hant",
    )

    assert report.preserved_units == 1
    assert report.migrated_units == 0
    assert report.updated_units == 0
    assert "目標譯文。" in _find_translation_doc(
        output_tree_dir,
        "Hello.",
    ).read_text(encoding="utf-8")


def test_merge_translation_tree_replaces_exact_existing_translation(
    tmp_path: Path,
) -> None:
    """Cross-version sync may update an existing exact-source translation."""

    compact_dir = _write_compact_template(tmp_path, "<p>Hello.</p>\n")
    expanded_dir = tmp_path / "expanded"
    source_tree_dir = tmp_path / "source-tree"
    target_tree_dir = tmp_path / "target-tree"
    output_tree_dir = tmp_path / "synchronized-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=source_tree_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=target_tree_dir)
    _write_translation_block(_find_translation_doc(source_tree_dir, "Hello."), "新譯文。")
    _write_translation_block(_find_translation_doc(target_tree_dir, "Hello."), "舊譯文。")

    report = merge_translation_tree(
        old_tree_dir=source_tree_dir,
        new_tree_dir=target_tree_dir,
        output_dir=output_tree_dir,
        source_lang="en",
        target_lang="zh_Hant",
        existing_translation_policy="replace",
    )

    assert report.preserved_units == 0
    assert report.migrated_units == 0
    assert report.updated_units == 1
    assert report.exact_key_matches == 1
    assert "新譯文。" in _find_translation_doc(
        output_tree_dir,
        "Hello.",
    ).read_text(encoding="utf-8")


def test_merge_translation_tree_replace_requires_exact_structure(
    tmp_path: Path,
) -> None:
    """Replacement must not cross a changed source structure."""

    source_compact_dir = _write_compact_template_file(
        root_dir=tmp_path / "source-compact",
        relative_path="index.html.j2",
        source_text="<p>Hello <strong>{{ name }}</strong>.</p>\n",
    )
    target_compact_dir = _write_compact_template_file(
        root_dir=tmp_path / "target-compact",
        relative_path="index.html.j2",
        source_text="<p>Hello {{ name }}.</p>\n",
    )
    source_expanded_dir = tmp_path / "source-expanded"
    target_expanded_dir = tmp_path / "target-expanded"
    source_tree_dir = tmp_path / "source-tree"
    target_tree_dir = tmp_path / "target-tree"
    output_tree_dir = tmp_path / "synchronized-tree"
    expand_template_dir(source_dir=source_compact_dir, output_dir=source_expanded_dir)
    expand_template_dir(source_dir=target_compact_dir, output_dir=target_expanded_dir)
    export_translation_tree(source_dir=source_expanded_dir, output_dir=source_tree_dir)
    export_translation_tree(source_dir=target_expanded_dir, output_dir=target_tree_dir)
    _write_translation_block(
        _find_translation_doc(source_tree_dir, "Hello {name}."), "新譯文 {name}。"
    )
    _write_translation_block(
        _find_translation_doc(target_tree_dir, "Hello {name}."), "舊譯文 {name}。"
    )

    report = merge_translation_tree(
        old_tree_dir=source_tree_dir,
        new_tree_dir=target_tree_dir,
        output_dir=output_tree_dir,
        source_lang="en",
        target_lang="zh_Hant",
        existing_translation_policy="replace",
    )

    assert report.preserved_units == 1
    assert report.updated_units == 0
    assert "舊譯文 {name}。" in _find_translation_doc(
        output_tree_dir,
        "Hello {name}.",
    ).read_text(encoding="utf-8")


def test_merge_translation_tree_rejects_fuzzy_replacement(tmp_path: Path) -> None:
    """Existing translations cannot be replaced using visible-sentence matching."""

    tree_dir = tmp_path / "tree"
    tree_dir.mkdir()

    with pytest.raises(TranslationTreeError, match="cannot be combined"):
        merge_translation_tree(
            old_tree_dir=tree_dir,
            new_tree_dir=tree_dir,
            output_dir=tmp_path / "output",
            source_lang="en",
            target_lang="zh_Hant",
            allow_sentence_matches=True,
            existing_translation_policy="replace",
        )


def test_merge_translation_tree_rejects_stale_exact_key_matches(
    tmp_path: Path,
) -> None:
    """Same file/key is not enough if the source structure changed."""

    old_compact_dir = _write_compact_template_file(
        root_dir=tmp_path / "old-compact",
        relative_path="index.html.j2",
        source_text="<p>Hello <strong>{{ name }}</strong>.</p>\n",
    )
    new_compact_dir = _write_compact_template_file(
        root_dir=tmp_path / "new-compact",
        relative_path="index.html.j2",
        source_text="<p>Hello {{ name }}.</p>\n",
    )
    old_expanded_dir = tmp_path / "old-expanded"
    new_expanded_dir = tmp_path / "new-expanded"
    old_tree_dir = tmp_path / "old-tree"
    new_tree_dir = tmp_path / "new-tree"
    output_tree_dir = tmp_path / "merged-tree"
    expand_template_dir(source_dir=old_compact_dir, output_dir=old_expanded_dir)
    expand_template_dir(source_dir=new_compact_dir, output_dir=new_expanded_dir)
    export_translation_tree(source_dir=old_expanded_dir, output_dir=old_tree_dir)
    export_translation_tree(source_dir=new_expanded_dir, output_dir=new_tree_dir)

    _write_translation_block(_find_translation_doc(old_tree_dir, "Hello {name}."), "你好 {name}。")

    report = merge_translation_tree(
        old_tree_dir=old_tree_dir,
        new_tree_dir=new_tree_dir,
        output_dir=output_tree_dir,
        source_lang="en",
        target_lang="zh_Hant",
    )

    assert report.migrated_units == 0
    assert report.exact_key_matches == 0
    assert report.untranslated_units == 1
    assert "你好 {name}。" not in _find_translation_doc(
        output_tree_dir,
        "Hello {name}.",
    ).read_text(encoding="utf-8")


def test_merge_translation_tree_reuses_unique_source_hash_matches(
    tmp_path: Path,
) -> None:
    """Moved source files can still reuse translations when the unit text is identical."""

    old_compact_dir = _write_compact_template_file(
        root_dir=tmp_path / "old-compact",
        relative_path="index.html.j2",
        source_text="<p>Moved sentence.</p>\n",
    )
    new_compact_dir = _write_compact_template_file(
        root_dir=tmp_path / "new-compact",
        relative_path="nested/page.html.j2",
        source_text="<p>Moved sentence.</p>\n",
    )
    old_expanded_dir = tmp_path / "old-expanded"
    new_expanded_dir = tmp_path / "new-expanded"
    old_tree_dir = tmp_path / "old-tree"
    new_tree_dir = tmp_path / "new-tree"
    output_tree_dir = tmp_path / "merged-tree"
    expand_template_dir(source_dir=old_compact_dir, output_dir=old_expanded_dir)
    expand_template_dir(source_dir=new_compact_dir, output_dir=new_expanded_dir)
    export_translation_tree(source_dir=old_expanded_dir, output_dir=old_tree_dir)
    export_translation_tree(source_dir=new_expanded_dir, output_dir=new_tree_dir)

    _write_translation_block(
        _find_translation_doc(old_tree_dir, "Moved sentence."), "已搬移的句子。"
    )

    report = merge_translation_tree(
        old_tree_dir=old_tree_dir,
        new_tree_dir=new_tree_dir,
        output_dir=output_tree_dir,
        source_lang="en",
        target_lang="zh_Hant",
    )

    assert report.migrated_units == 1
    assert report.source_hash_matches == 1
    assert report.exact_key_matches == 0
    assert "已搬移的句子。" in _find_translation_doc(
        output_tree_dir,
        "Moved sentence.",
    ).read_text(encoding="utf-8")


def test_merge_translation_tree_does_not_reuse_sentence_matches_by_default(
    tmp_path: Path,
) -> None:
    """Same visible sentence text is not enough proof for automatic migration."""

    old_compact_dir = _write_compact_template_file(
        root_dir=tmp_path / "old-compact",
        relative_path="index.html.j2",
        source_text="<p>Hello <strong>team</strong>.</p>\n",
    )
    new_compact_dir = _write_compact_template_file(
        root_dir=tmp_path / "new-compact",
        relative_path="index.html.j2",
        source_text="<p>Hello team.</p>\n",
    )
    old_expanded_dir = tmp_path / "old-expanded"
    new_expanded_dir = tmp_path / "new-expanded"
    old_tree_dir = tmp_path / "old-tree"
    new_tree_dir = tmp_path / "new-tree"
    output_tree_dir = tmp_path / "merged-tree"
    expand_template_dir(source_dir=old_compact_dir, output_dir=old_expanded_dir)
    expand_template_dir(source_dir=new_compact_dir, output_dir=new_expanded_dir)
    export_translation_tree(source_dir=old_expanded_dir, output_dir=old_tree_dir)
    export_translation_tree(source_dir=new_expanded_dir, output_dir=new_tree_dir)

    _write_translation_block(_find_translation_doc(old_tree_dir, "Hello team."), "哈囉團隊。")

    report = merge_translation_tree(
        old_tree_dir=old_tree_dir,
        new_tree_dir=new_tree_dir,
        output_dir=output_tree_dir,
        source_lang="en",
        target_lang="zh_Hant",
    )

    assert report.migrated_units == 0
    assert report.sentence_matches == 0
    assert "哈囉團隊。" not in _find_translation_doc(
        output_tree_dir,
        "Hello team.",
    ).read_text(encoding="utf-8")


def test_merge_translation_tree_can_opt_into_sentence_matches(tmp_path: Path) -> None:
    """Riskier visible-sentence matches must be explicitly enabled."""

    old_compact_dir = _write_compact_template_file(
        root_dir=tmp_path / "old-compact",
        relative_path="index.html.j2",
        source_text="<p>Hello <strong>team</strong>.</p>\n",
    )
    new_compact_dir = _write_compact_template_file(
        root_dir=tmp_path / "new-compact",
        relative_path="index.html.j2",
        source_text="<p>Hello team.</p>\n",
    )
    old_expanded_dir = tmp_path / "old-expanded"
    new_expanded_dir = tmp_path / "new-expanded"
    old_tree_dir = tmp_path / "old-tree"
    new_tree_dir = tmp_path / "new-tree"
    output_tree_dir = tmp_path / "merged-tree"
    expand_template_dir(source_dir=old_compact_dir, output_dir=old_expanded_dir)
    expand_template_dir(source_dir=new_compact_dir, output_dir=new_expanded_dir)
    export_translation_tree(source_dir=old_expanded_dir, output_dir=old_tree_dir)
    export_translation_tree(source_dir=new_expanded_dir, output_dir=new_tree_dir)

    _write_translation_block(_find_translation_doc(old_tree_dir, "Hello team."), "哈囉團隊。")

    report = merge_translation_tree(
        old_tree_dir=old_tree_dir,
        new_tree_dir=new_tree_dir,
        output_dir=output_tree_dir,
        source_lang="en",
        target_lang="zh_Hant",
        allow_sentence_matches=True,
    )

    assert report.migrated_units == 1
    assert report.sentence_matches == 1
    assert "哈囉團隊。" in _find_translation_doc(
        output_tree_dir,
        "Hello team.",
    ).read_text(encoding="utf-8")


def test_merge_translation_tree_skips_unsafe_old_placeholder_edits(
    tmp_path: Path,
) -> None:
    """Broken old translations should be repaired as blank units, not migrated."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>Hello {{ name }}.</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    old_tree_dir = tmp_path / "old-tree"
    new_tree_dir = tmp_path / "new-tree"
    output_tree_dir = tmp_path / "merged-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=old_tree_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=new_tree_dir)

    _write_translation_block(_find_translation_doc(old_tree_dir, "Hello {name}."), "你好。")

    report = merge_translation_tree(
        old_tree_dir=old_tree_dir,
        new_tree_dir=new_tree_dir,
        output_dir=output_tree_dir,
        source_lang="en",
        target_lang="zh_Hant",
    )

    output_doc = _find_translation_doc(output_tree_dir, "Hello {name}.").read_text(encoding="utf-8")
    assert report.migrated_units == 0
    assert report.skipped_unsafe_old_units == 1
    assert "你好。" not in output_doc


def test_merge_translation_tree_skips_ambiguous_fuzzy_matches(tmp_path: Path) -> None:
    """Ambiguous old candidates should stay untranslated rather than guessed."""

    old_compact_dir = _write_compact_template_file(
        root_dir=tmp_path / "old-compact",
        relative_path="index.html.j2",
        source_text="""
<p>Repeat.</p>
<p>Repeat.</p>
""",
    )
    new_compact_dir = _write_compact_template_file(
        root_dir=tmp_path / "new-compact",
        relative_path="moved.html.j2",
        source_text="<p>Repeat.</p>\n",
    )
    old_expanded_dir = tmp_path / "old-expanded"
    new_expanded_dir = tmp_path / "new-expanded"
    old_tree_dir = tmp_path / "old-tree"
    new_tree_dir = tmp_path / "new-tree"
    output_tree_dir = tmp_path / "merged-tree"
    expand_template_dir(source_dir=old_compact_dir, output_dir=old_expanded_dir)
    expand_template_dir(source_dir=new_compact_dir, output_dir=new_expanded_dir)
    export_translation_tree(source_dir=old_expanded_dir, output_dir=old_tree_dir)
    export_translation_tree(source_dir=new_expanded_dir, output_dir=new_tree_dir)
    for index, document_path in enumerate(sorted(old_tree_dir.rglob("translation.md")), start=1):
        _write_translation_block(document_path, f"重複翻譯 {index}。")

    report = merge_translation_tree(
        old_tree_dir=old_tree_dir,
        new_tree_dir=new_tree_dir,
        output_dir=output_tree_dir,
        source_lang="en",
        target_lang="zh_Hant",
    )

    assert report.migrated_units == 0
    assert report.untranslated_units == 1
    assert "重複翻譯" not in _find_translation_doc(
        output_tree_dir,
        "Repeat.",
    ).read_text(encoding="utf-8")


def test_merge_translation_tree_recovers_from_broken_old_manifest(
    tmp_path: Path,
) -> None:
    """A corrupted old tree should not block regenerating a clean new tree."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>Fresh sentence.</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    old_tree_dir = tmp_path / "old-tree"
    new_tree_dir = tmp_path / "new-tree"
    output_tree_dir = tmp_path / "merged-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=old_tree_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=new_tree_dir)
    (old_tree_dir / ".translation-tree" / "manifest.json").write_text(
        "{not valid json",
        encoding="utf-8",
    )

    report = merge_translation_tree(
        old_tree_dir=old_tree_dir,
        new_tree_dir=new_tree_dir,
        output_dir=output_tree_dir,
        source_lang="en",
        target_lang="zh_Hant",
    )

    assert report.migrated_units == 0
    assert report.untranslated_units == 1
    assert _find_translation_doc(output_tree_dir, "Fresh sentence.").is_file()


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


def test_export_translation_tree_does_not_expose_raw_jinja_blocks(
    tmp_path: Path,
) -> None:
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


def test_export_translation_tree_translates_rendered_list_initializer(
    tmp_path: Path,
) -> None:
    """A static seed in a rendered sentence list should round-trip as one safe unit."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
{%- set hidden = ['Internal machine sentence.'] -%}
{%- set sentences = ['Visible opening sentence.'] -%}
{%- do sentences.append('Visible closing sentence.') -%}
<p>{{ sentences|join(' ') }}</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    translated_expanded_dir = tmp_path / "translated-expanded"

    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    docs = _read_translation_docs(tree_dir)
    sentences = _extract_sentence_list(docs)
    assert "Visible opening sentence." in sentences
    assert "Visible closing sentence." in sentences
    assert "Internal machine sentence." not in sentences

    document_path = next(
        path
        for path in tree_dir.rglob("translation.md")
        if "Visible opening sentence." in path.read_text(encoding="utf-8")
    )
    _write_translation_block(document_path, "可見的開頭句子。")
    sync_translation_tree(
        tree_dir=tree_dir,
        source_dir=expanded_dir,
        output_dir=translated_expanded_dir,
    )

    translated_text = (translated_expanded_dir / "src" / "index.html.j2").read_text(
        encoding="utf-8"
    )
    assert "set sentences = ['可見的開頭句子。']" in translated_text
    assert "Internal machine sentence." in translated_text
    assert (
        audit_translated_template_structure(
            source_dir=expanded_dir,
            output_dir=translated_expanded_dir,
        )
        == []
    )


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


def test_export_translation_tree_splits_branch_alternatives_into_units(
    tmp_path: Path,
) -> None:
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


def test_export_translation_tree_keeps_science_europe_markdown_variants_complete(
    tmp_path: Path,
) -> None:
    """Science Europe v1.30.1 markdown variants should not fragment labels."""

    compact_dir = _write_compact_template_raw(
        tmp_path,
        (
            """
            <p>We will re-use this standard reference data
            {%- if refDataWhere -%}
              {{" "}}available via:{{" "}}
              {%- if refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://") -%}
                <a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>.
              {%- else -%}
                {{ refDataWhere }}
             {%- endif -%}
            {%- endif -%}
"""
            "    \n"
            """            {# usage #}
            {%- set refDataUsageQ = [ refDataUsedPrefix, uuids.refDataUsageQUuid]|reply_path -%}
            {%- set refDataUsageReply = repliesMap[refDataUsageQ]|reply_str_value  -%}
            {%- if refDataUsageReply -%}
                {{+" "}}in order to {{ refDataUsageReply|markdown }}
            {%- else -%}.
            {%- endif -%}
            </p>

            {%- set refDataConditions = [refDataUsedPrefix, uuids.refDataConditionsQUuid]|reply_path -%}
            {%- set refDataConditionsReply = repliesMap[refDataConditions]|reply_str_value -%}
            {%- set refDataConditionsOther = [refDataConditions, uuids.refDataConditionsOtherAUuid, uuids.refDataConditionsOtherQUuid]|reply_path -%}
            {%- set refDataConditionsOtherReply = repliesMap[refDataConditionsOther]|reply_str_value -%}
            {%- if refDataConditionsReply %}
             <p>This standard reference data are{{+" "}}
              {%- if refDataConditionsReply == uuids.refDataConditionsCC0AUuid -%}
                freely available for any use.
              {%- elif refDataConditionsReply == uuids.refDataConditionsCCBYAUuid -%}
                freely available with obligation to quote the source.
              {%- elif refDataConditionsReply == uuids.refDataConditionsOtherAUuid -%}
                available with {{" "}}
                  {%- if refDataConditionsOtherReply -%}
                    following restrictions: {{refDataConditionsOtherReply|markdown}}
                  {%- else -%}
                    {{" "}}restrictions, that will be specified.
                  {%- endif -%}
              {%- endif -%}
             </p>
            {%- endif -%}

          <p>We will re-use this non-referece data"""
            " \n"
            """          {%- if nrefDataWhere -%}
         {{" "}} available via:{{" "}}
            {%- if nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://") -%}
              <a href="{{ nrefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>.
            {%- else -%}
              {{ nrefDataWhere }}
            {%- endif -%}
          {%- endif -%}
"""
            "    \n"
            """          {# usage #}
          {%- set nrefDataUsageQ = [nrefDataUsedPrefix, uuids.nrefDataUsageQUuid]|reply_path  -%}
          {%- set nrefDataUsageReply = repliesMap[nrefDataUsageQ]|reply_str_value -%}
          {%- if nrefDataUsageReply -%}
            {{+" "}}in order to {{ nrefDataUsageReply|markdown }}
          {%- endif -%}
          .</p>

          {%- if nrefDataConditionsReply %}
            <p>This data are{{+" "}}
            {%- if nrefDataConditionsReply == uuids.nrefDataConditionsCC0AUuid -%}
              freely available for any use.
            {%- elif nrefDataConditionsReply == uuids.nrefDataConditionsCCBYAUuid -%}
              freely available with obligation to quote the source.
            {%- elif nrefDataConditionsReply == uuids.nrefDataConditionsOtherAUuid  -%}
              {%- set nrefDataConditionsOther = [nrefDataConditions, uuids.nrefDataConditionsOtherAUuid, uuids.nrefDataConditionsOtherQUuid]|reply_path -%}
              {%- set nrefDataConditionsOtherReply = repliesMap[nrefDataConditionsOther]|reply_str_value -%}
              {%- if nrefDataConditionsOtherReply -%}
                available with{{" "}}
                  {%- if nrefDataConditionsOtherReply -%}
                   following restrictions: {{nrefDataConditionsOtherReply|markdown}}
                  {%- else -%}
                    {{" "}}restrictions, that will be specified.
                  {%- endif -%}
              {%- endif -%}
            {%- endif -%}
            </p>
          {%- endif -%}
"""
        ),
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    sentences = _extract_sentence_list(_read_translation_docs(tree_dir))
    assert "available via:" not in sentences
    assert "We will re-use this standard reference data" not in sentences
    assert "We will re-use this non-referece data" not in sentences
    assert "This standard reference data are" not in sentences
    assert "This data are" not in sentences
    assert any(
        sentence.startswith(
            "We will re-use this standard reference data available via: {refDataWhere}"
        )
        and "in order to {refDataUsageReply}" in sentence
        for sentence in sentences
    )
    assert any(
        sentence.startswith("We will re-use this non-referece data available via: {nrefDataWhere}")
        and "in order to {nrefDataUsageReply}" in sentence
        for sentence in sentences
    )
    assert (
        "This standard reference data are available with following restrictions: "
        "{refDataConditionsOtherReply}"
    ) in sentences
    assert (
        "This data are available with following restrictions: {nrefDataConditionsOtherReply}"
    ) in sentences


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


def test_export_translation_tree_keeps_external_ownership_arrangement_complete(
    tmp_path: Path,
) -> None:
    """The Science Europe external-ownership fallback should become translatable."""

    compact_dir = _write_compact_template_raw(
        tmp_path,
        """
              <p>
                This dataset will be collected by an external party.
                {% if mdExternalOwnershipAUuid == uuids.mdExternalOwnershipPartyAUuid -%}
                  The ownership of the resulting data will remain with the external party.
                {%- elif mdExternalOwnershipAUuid == uuids.mdExternalOwnershipPartnersAUuid -%}
                  The project partners acquire full ownership of the data.
                {%- elif mdExternalOwnershipAUuid == uuids.mdExternalOwnershipOtherAUuid -%}
                  {%- set mdExternalOwnershipOtherPath = [mdExternalOwnershipPath, uuids.mdExternalOwnershipOtherAUuid, uuids.mdExternalOwnershipOtherQUuid]|reply_path -%}
                  {%- set mdExternalOwnershipOther = repliesMap[mdExternalOwnershipOtherPath]|reply_str_value -%}
                  {%- if mdExternalOwnershipOther -%}
                    For the ownership of the data we have made the following arrangements: {{ mdExternalOwnershipOther|dot }}
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
    assert "For the ownership of the data we have made the following arrangements:" not in (
        sentences
    )
    assert any(
        "This dataset will be collected by an external party. For the ownership "
        "of the data we have made the following arrangements: {mdExternalOwnershipOther}"
        in sentence
        for sentence in sentences
    )
    assert audit_translation_tree(tree_dir=tree_dir, source_dir=expanded_dir) == []


@pytest.mark.parametrize("value_filter", ["dot", "markdown"])
def test_export_translation_tree_keeps_open_reason_branches_complete(
    tmp_path: Path,
    value_filter: str,
) -> None:
    """Not-open reason branches stay complete across upstream filter variants."""

    source = """
      {%- if nReasons > 0 -%}
        <p>
        The data cannot become completely open because 
        {%- if nReasons == 1 -%}
          {%- if legalReasons %}
            of legal reasons.
          {%- elif businessReasonsPatents %}
            of patent-related business reasons.
          {%- elif businessReasonsOther %}
            of non-patent business reasons{{  ": " ~ notOpenBusinessReasonsOther|VALUE_FILTER if notOpenBusinessReasonsOther else "." }}
          {%- elif otherReasonsPapers %}
            we want to publish a paper first.
          {%- elif otherReasonsOther %}
            we have other than paper-publishing reasons{{ ": " ~ notOpenOtherReasonsOther|VALUE_FILTER if notOpenOtherReasonsOther else "." }}
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
              <li>non-patent business reasons{{ ": " ~ notOpenBusinessReasonsOther|LIST_FILTER if notOpenBusinessReasonsOther else "" }}</li>
            {%- endif -%}
            {%- if otherReasonsPapers %}
              <li>we want to publish a paper first</li>
            {%- elif otherReasonsOther -%}
              <li>we have other than paper-publishing reasons{{ ": " ~ notOpenOtherReasonsOther|LIST_FILTER if notOpenOtherReasonsOther else "" }}</li>
            {%- endif -%}
          </ul>
        {%- endif -%}
""".replace("VALUE_FILTER", value_filter).replace(
        "|LIST_FILTER",
        "" if value_filter == "dot" else "|markdown",
    )
    compact_dir = _write_compact_template_raw(
        tmp_path,
        source,
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
    assert "The data cannot become completely open because of:" in sentences
    assert audit_translation_tree(tree_dir=tree_dir, source_dir=expanded_dir) == []


def test_export_translation_tree_keeps_nonstandard_format_reason_complete(
    tmp_path: Path,
) -> None:
    """The Science Europe non-standard-format reason should not split after comma."""

    compact_dir = _write_compact_template_raw(
        tmp_path,
        """
                We are not using a standardized format
                {%- if formatsWhyNSAnotherReason -%}
                  , because: {{ formatsWhyNSAnotherReason|capitalize }}
                {%- endif -%}
                .
""",
    )

    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    sentences = _extract_sentence_list(_read_translation_docs(tree_dir))
    assert "We are not using a standardized format." in sentences
    assert "because: {formatsWhyNSAnotherReason}" not in sentences
    assert (
        "We are not using a standardized format, because: {formatsWhyNSAnotherReason}." in sentences
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


def test_export_translation_tree_ignores_machine_only_jinja_literals(
    tmp_path: Path,
) -> None:
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


def test_export_translation_tree_preserves_url_like_sentence_text(
    tmp_path: Path,
) -> None:
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


def test_sync_translation_tree_applies_translations_back_to_template(
    tmp_path: Path,
) -> None:
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


def test_sync_translation_tree_keeps_source_text_when_translation_is_blank(
    tmp_path: Path,
) -> None:
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


def test_sync_translation_tree_accepts_text_only_translation_for_html_unit(
    tmp_path: Path,
) -> None:
    """Text-only translations should preserve simple outer HTML structure."""

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
    _write_translation_block(document_path, "為了 {usage}，可透過 {pid} 取得。")

    sync_translation_tree(
        tree_dir=tree_dir,
        source_dir=expanded_dir,
        output_dir=translated_expanded_dir,
    )

    translated_text = (translated_expanded_dir / "src" / "index.html.j2").read_text(
        encoding="utf-8"
    )
    assert "<p>為了 {{ usage }}，可透過 {{ pid }} 取得。</p>" in translated_text


def test_sync_translation_tree_preserves_single_inner_inline_markup(
    tmp_path: Path,
) -> None:
    """Text-only translations should not drop simple emphasis inside a block tag."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p><em>There are no named versions.</em></p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    translated_expanded_dir = tmp_path / "translated-expanded"

    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    document_path = next(tree_dir.rglob("translation.md"))
    _write_translation_block(document_path, "沒有命名版本。")

    sync_translation_tree(
        tree_dir=tree_dir,
        source_dir=expanded_dir,
        output_dir=translated_expanded_dir,
    )

    translated_text = (translated_expanded_dir / "src" / "index.html.j2").read_text(
        encoding="utf-8"
    )
    assert "<p><em>沒有命名版本。</em></p>" in translated_text


def test_sync_translation_tree_preserves_standalone_inline_markup(
    tmp_path: Path,
) -> None:
    """Standalone inline structural wrappers such as status spans should survive."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<span class="empty-value">There is no contact person specified yet</span>
""",
    )
    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    translated_expanded_dir = tmp_path / "translated-expanded"

    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    document_path = next(tree_dir.rglob("translation.md"))
    _write_translation_block(document_path, "尚未指定聯絡人")

    sync_translation_tree(
        tree_dir=tree_dir,
        source_dir=expanded_dir,
        output_dir=translated_expanded_dir,
    )

    translated_text = (translated_expanded_dir / "src" / "index.html.j2").read_text(
        encoding="utf-8"
    )
    assert '<span class="empty-value">' in translated_text
    assert "尚未指定聯絡人" in translated_text
    assert "</span>" in translated_text


def test_translation_placeholder_validation_ignores_html_attribute_only_duplicates(
    tmp_path: Path,
) -> None:
    """Links expose one visible placeholder and keep machine href wiring."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>Available via <a href="{{ pid }}" target="_blank">{{ pid }}</a> for {{ usage }}.</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    translated_expanded_dir = tmp_path / "translated-expanded"

    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    document_path = next(tree_dir.rglob("translation.md"))
    _write_translation_block(document_path, "為了 {usage}，可透過 {pid} 取得。")

    issues = audit_translation_tree(source_dir=expanded_dir, tree_dir=tree_dir)
    assert issues == []

    sync_translation_tree(
        tree_dir=tree_dir,
        source_dir=expanded_dir,
        output_dir=translated_expanded_dir,
    )

    translated_text = (translated_expanded_dir / "src" / "index.html.j2").read_text(
        encoding="utf-8"
    )
    assert (
        '為了 {{ usage }}，可透過 <a href="{{ pid }}" target="_blank">{{ pid }}</a> 取得。'
        in translated_text
    )


def test_sync_translation_tree_preserves_distinct_href_placeholder(
    tmp_path: Path,
) -> None:
    """Attribute-only URL placeholders should survive text-only translations."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>Created in &laquo;<a href="{{ serviceUrl }}" target="_blank">{{ serviceDomain }}</a>&raquo;.</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    translated_expanded_dir = tmp_path / "translated-expanded"

    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    document_path = next(tree_dir.rglob("translation.md"))
    _write_translation_block(document_path, "建立於 {serviceDomain}。")

    issues = audit_translation_tree(source_dir=expanded_dir, tree_dir=tree_dir)
    assert issues == []

    sync_translation_tree(
        tree_dir=tree_dir,
        source_dir=expanded_dir,
        output_dir=translated_expanded_dir,
    )

    translated_text = (translated_expanded_dir / "src" / "index.html.j2").read_text(
        encoding="utf-8"
    )
    assert (
        '建立於 <a href="{{ serviceUrl }}" target="_blank">{{ serviceDomain }}</a>。'
        in translated_text
    )


def test_sync_translation_tree_preserves_nested_inline_placeholder_markup(
    tmp_path: Path,
) -> None:
    """Nested inline markup around identifiers should not disappear during sync."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<li>DOI: <strong><a href="https://doi.org/{{ identifierValue }}" target="_blank">{{ identifierValue }}</a></strong></li>
""",
    )
    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    translated_expanded_dir = tmp_path / "translated-expanded"

    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    document_path = next(tree_dir.rglob("translation.md"))
    _write_translation_block(document_path, "DOI：{identifierValue}")

    issues = audit_translation_tree(source_dir=expanded_dir, tree_dir=tree_dir)
    assert issues == []

    sync_translation_tree(
        tree_dir=tree_dir,
        source_dir=expanded_dir,
        output_dir=translated_expanded_dir,
    )

    translated_text = (translated_expanded_dir / "src" / "index.html.j2").read_text(
        encoding="utf-8"
    )
    assert (
        'DOI：<strong><a href="https://doi.org/{{ identifierValue }}" '
        'target="_blank">{{ identifierValue }}</a></strong>' in translated_text
    )


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


def test_sync_translation_tree_translates_jinja_expression_literals_in_place(
    tmp_path: Path,
) -> None:
    """Function-call expressions must survive when only their literal is translated."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
{{ renderResponsibility("responsible for maintaining the finished resource.") }}
""",
    )
    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    translated_expanded_dir = tmp_path / "translated-expanded"

    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    docs = list(tree_dir.rglob("translation.md"))
    assert len(docs) == 1
    assert "renderResponsibility" not in docs[0].read_text(encoding="utf-8")
    _write_translation_block(docs[0], "負責維護已完成的資源。")

    sync_translation_tree(
        tree_dir=tree_dir,
        source_dir=expanded_dir,
        output_dir=translated_expanded_dir,
    )

    translated_text = (translated_expanded_dir / "src" / "index.html.j2").read_text(
        encoding="utf-8"
    )
    assert '{{ renderResponsibility("負責維護已完成的資源。") }}' in translated_text


def test_audit_translated_template_structure_allows_text_and_literal_translation(
    tmp_path: Path,
) -> None:
    """Output audit should permit prose translation while keeping machine shape."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
{% set types = [] %}
{%- do types.append("questionnaires") -%}
{% if enabled %}
<p>Available via <a href="{{ pid }}" target="_blank">{{ pid }}</a>.</p>
{% else %}
<p>{{ "(no name given)" }}</p>
{% endif %}
""",
    )
    expanded_dir = tmp_path / "expanded"
    translated_dir = tmp_path / "translated"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    shutil.copytree(expanded_dir, translated_dir)

    translated_file = translated_dir / "src" / "index.html.j2"
    translated_file.write_text(
        translated_file.read_text(encoding="utf-8")
        .replace('"questionnaires"', '"問卷"')
        .replace("Available via ", "可透過 ")
        .replace('{{ "(no name given)" }}', "（未提供名稱）"),
        encoding="utf-8",
    )

    assert (
        audit_translated_template_structure(
            source_dir=expanded_dir,
            output_dir=translated_dir,
        )
        == []
    )


def test_audit_translated_template_structure_allows_registered_output_polish(
    tmp_path: Path,
) -> None:
    """Final zh-Hant punctuation polish should not fail structural audit."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>Software PID: {{ swPIDReply|dot }}</p>
<p>{{" - "+projectCostItemDescriptionReply|dot}}</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    translated_dir = tmp_path / "translated"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    shutil.copytree(expanded_dir, translated_dir)

    translated_file = translated_dir / "src" / "index.html.j2"
    translated_file.write_text(
        polish_zh_hant_template_text(translated_file.read_text(encoding="utf-8")),
        encoding="utf-8",
    )

    assert (
        audit_translated_template_structure(
            source_dir=expanded_dir,
            output_dir=translated_dir,
        )
        == []
    )


def test_audit_translated_template_structure_reports_lost_link_attribute(
    tmp_path: Path,
) -> None:
    """Dropping href/src wiring is a structural regression, not translation."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>Available via <a href="{{ pid }}" target="_blank">{{ pid }}</a>.</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    translated_dir = tmp_path / "translated"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    shutil.copytree(expanded_dir, translated_dir)

    translated_file = translated_dir / "src" / "index.html.j2"
    translated_file.write_text(
        translated_file.read_text(encoding="utf-8").replace('href="{{ pid }}" ', ""),
        encoding="utf-8",
    )

    issues = audit_translated_template_structure(
        source_dir=expanded_dir,
        output_dir=translated_dir,
    )

    assert "changed-html-structure" in {issue.code for issue in issues}
    html_issue = next(issue for issue in issues if issue.code == "changed-html-structure")
    assert "HTML tag structure changed" in html_issue.message


def test_audit_translated_template_structure_reports_changed_placeholder(
    tmp_path: Path,
) -> None:
    """Manual output edits must not silently swap Jinja variables."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>Available via {{ pid }}.</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    translated_dir = tmp_path / "translated"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    shutil.copytree(expanded_dir, translated_dir)

    translated_file = translated_dir / "src" / "index.html.j2"
    translated_file.write_text(
        translated_file.read_text(encoding="utf-8").replace("{{ pid }}", "{{ pdi }}"),
        encoding="utf-8",
    )

    issues = audit_translated_template_structure(
        source_dir=expanded_dir,
        output_dir=translated_dir,
    )

    assert [issue.code for issue in issues] == ["changed-jinja-expression-structure"]
    assert "pid" in issues[0].message


def test_audit_translated_template_structure_reports_protected_literal_change(
    tmp_path: Path,
) -> None:
    """Machine literals such as lookup keys are protected even inside Jinja."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
{% set answer = repliesMap["machineKey"] %}
<p>{{ answer }}</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    translated_dir = tmp_path / "translated"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    shutil.copytree(expanded_dir, translated_dir)

    translated_file = translated_dir / "src" / "index.html.j2"
    translated_file.write_text(
        translated_file.read_text(encoding="utf-8").replace('"machineKey"', '"機器鍵"'),
        encoding="utf-8",
    )

    issues = audit_translated_template_structure(
        source_dir=expanded_dir,
        output_dir=translated_dir,
    )

    assert "changed-protected-jinja-literal" in {issue.code for issue in issues}
    literal_issue = next(
        issue for issue in issues if issue.code == "changed-protected-jinja-literal"
    )
    assert "machineKey" in literal_issue.message


def test_export_translation_tree_preserves_existing_translation_text(
    tmp_path: Path,
) -> None:
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


def test_sync_translation_tree_can_patch_output_template_metadata(
    tmp_path: Path,
) -> None:
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
        template_description="Sample Template 的繁體中文化版本",
        template_version="1.0.0-zh-hant",
    )

    payload = json.loads((translated_expanded_dir / "template.json").read_text(encoding="utf-8"))
    assert payload["organizationId"] == "dsw"
    assert payload["templateId"] == "sample-zh-hant"
    assert payload["name"] == "Sample Template (zh-Hant)"
    assert payload["description"] == "Sample Template 的繁體中文化版本"
    assert payload["version"] == "1.0.0-zh-hant"

    readme = (translated_expanded_dir / "README.md").read_text(encoding="utf-8")
    assert readme.startswith("# Sample Template (zh-Hant)\n")
    assert "Template ID: `dsw:sample-zh-hant:1.0.0-zh-hant`" in readme
    assert "Translation Workspace" not in readme


def test_sync_translation_tree_uses_public_readme_when_available(
    tmp_path: Path,
) -> None:
    """Translated outputs should use the user-facing README curated by translators."""

    compact_dir = _write_compact_template(
        tmp_path,
        """
<p>Hello world.</p>
""",
    )
    expanded_dir = tmp_path / "expanded"
    tree_dir = tmp_path / "translation-tree"
    translated_expanded_dir = tmp_path / "translated-expanded"
    public_readme = tmp_path / "public-readme.md"
    public_readme.write_text(
        "# Science Europe DMP 範本（繁體中文）\n\n"
        "版本：{template_version}\n\n"
        "Template ID：{template_full_id}\n",
        encoding="utf-8",
    )

    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    export_translation_tree(source_dir=expanded_dir, output_dir=tree_dir)

    sync_translation_tree(
        tree_dir=tree_dir,
        source_dir=expanded_dir,
        output_dir=translated_expanded_dir,
        template_organization_id="dsw",
        template_id="sample-zh-hant",
        template_name="Sample Template (zh-Hant)",
        template_version="1.0.0",
        public_readme_path=public_readme,
    )

    assert (translated_expanded_dir / "README.md").read_text(encoding="utf-8") == (
        "# Science Europe DMP 範本（繁體中文）\n\n"
        "版本：1.0.0\n\n"
        "Template ID：dsw:sample-zh-hant:1.0.0\n"
    )


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

    with pytest.raises(TranslationTreeError, match="Refresh the translation tree"):
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
