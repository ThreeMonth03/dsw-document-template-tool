"""Tests for reversible compact <-> expanded template transforms."""

from __future__ import annotations

import itertools
import os
import random
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from jinja2 import Environment, StrictUndefined

from dsw_document_template_tool.template_transform import (
    compact_template_dir,
    expand_template_dir,
    snapshot_tree,
)

FUZZ_SEED = 20260522
FUZZ_ITEM_COUNTS = range(6)
FUZZ_ROW_COUNTS = range(6)
FUZZ_REASON_COUNTS = range(1, 5)
FUZZ_MODES = ("public", "restricted", "unknown")
FUZZ_TEMPLATE_BUILDERS = (
    "scope",
    "mutation",
    "cardinality",
    "loop",
    "branch_closed_html",
    "nested_list",
)
FUZZ_CONTEXT_COUNT = (
    len(FUZZ_ITEM_COUNTS)
    * sum(2**row_count for row_count in FUZZ_ROW_COUNTS)
    * len(FUZZ_REASON_COUNTS)
    * 2
    * len(FUZZ_MODES)
)
FUZZ_LOGICAL_SHAPE_CHECK_COUNT = FUZZ_CONTEXT_COUNT * len(FUZZ_TEMPLATE_BUILDERS)
FUZZ_WORKERS = int(os.environ.get("DSW_TEMPLATE_FUZZ_WORKERS", str(min(8, os.cpu_count() or 1))))
FUZZ_CHUNK_SIZE = 128


def _render_template(source_text: str, context: dict) -> str:
    environment = Environment(
        extensions=["jinja2.ext.do"],
        undefined=StrictUndefined,
    )
    return environment.from_string(source_text).render(**context)


def _write_minimal_template_json(template_dir: Path) -> None:
    (template_dir / "template.json").write_text(
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


def test_expand_then_compact_roundtrips_template_tree(tmp_path: Path) -> None:
    """Synthetic templates should survive one expand/compact round-trip exactly."""

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
    (compact_dir / "README.md").write_text("sample\n", encoding="utf-8")
    (compact_dir / "src" / "index.html.j2").write_text(
        """
<h1>{{ title }}</h1>
{% if enabled %}
  <p>Hello world.</p>
{% endif %}
""".lstrip(),
        encoding="utf-8",
    )

    expanded_dir = tmp_path / "expanded"
    rebuilt_dir = tmp_path / "rebuilt"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    compact_template_dir(source_dir=expanded_dir, output_dir=rebuilt_dir)

    expanded_text = (expanded_dir / "src" / "index.html.j2").read_text(encoding="utf-8")
    assert "__tr_block_0000" in expanded_text
    assert "{% set __tr_block_" not in expanded_text
    assert "{# __tr_block_0000:start #}" in expanded_text
    assert (expanded_dir / "UPSTREAM-README.md").is_file()

    assert snapshot_tree(rebuilt_dir) == snapshot_tree(compact_dir)


def test_expand_applies_reversible_science_europe_localization_patches(
    tmp_path: Path,
) -> None:
    """Science Europe expansion should carry local zh-Hant and CJK font patches."""

    compact_dir = tmp_path / "compact"
    (compact_dir / "src").mkdir(parents=True)
    (compact_dir / "template.json").write_text(
        """
{
  "organizationId": "dsw",
  "templateId": "science-europe",
  "version": "1.30.0",
  "allowedPackages": [
    {
      "orgId": "dsw",
      "kmId": "root",
      "minVersion": "2.7.0",
      "maxVersion": null
    }
  ]
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (compact_dir / "src" / "style.css").write_text(
        """
body {
  font-family: "Open Sans", sans-serif;
}
""".lstrip(),
        encoding="utf-8",
    )
    (compact_dir / "src" / "index.html.j2").write_text(
        "<p>Hello world.</p>\n",
        encoding="utf-8",
    )

    expanded_dir = tmp_path / "expanded"
    rebuilt_dir = tmp_path / "rebuilt"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)

    expanded_template_json = (expanded_dir / "template.json").read_text(encoding="utf-8")
    expanded_style = (expanded_dir / "src" / "style.css").read_text(encoding="utf-8")

    assert '"kmId": "root-zh-hant"' in expanded_template_json
    assert "DSW Document Template Tool CJK font fallback:start" in expanded_style
    assert "68c26e34-5e77-4e15-9bf7-06ff92582257" in expanded_style
    assert 'assets("src/fonts/NotoSansTC-Variable.ttf")' in expanded_style
    assert "data:font/ttf;base64" in expanded_style
    assert '"DSW Noto Sans TC", {% endif %}"Open Sans", sans-serif' in expanded_style
    assert (expanded_dir / "src" / "fonts" / "NotoSansTC-Variable.ttf").is_file()

    compact_template_dir(source_dir=expanded_dir, output_dir=rebuilt_dir)

    assert snapshot_tree(rebuilt_dir) == snapshot_tree(compact_dir)


def test_expand_rewrites_inline_fallback_literals_reversibly(tmp_path: Path) -> None:
    """Inline ternaries with fallback text should become branch-safe Jinja."""

    compact_dir = tmp_path / "compact"
    (compact_dir / "src").mkdir(parents=True)
    _write_minimal_template_json(compact_dir)
    source_text = """
<dl>
  <dt>{{ "Additional" if quality_count > 0 else "Our" }} quality processes are:</dt>
  <dd>{{ projectNumber if projectNumber else "N/A" }}</dd>
</dl>
""".lstrip()
    (compact_dir / "src" / "index.html.j2").write_text(source_text, encoding="utf-8")

    expanded_dir = tmp_path / "expanded"
    rebuilt_dir = tmp_path / "rebuilt"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    compact_template_dir(source_dir=expanded_dir, output_dir=rebuilt_dir)

    expanded_text = (expanded_dir / "src" / "index.html.j2").read_text(encoding="utf-8")
    assert "__tr_inline_if_original:" in expanded_text
    assert '{{ "Additional" }}' in expanded_text
    assert '{{ "Our" }}' in expanded_text
    assert "quality processes are:" in expanded_text
    assert '{% if projectNumber %}{{ projectNumber }}{% else %}{{ "N/A" }}{% endif %}' in (
        expanded_text
    )
    assert snapshot_tree(rebuilt_dir) == snapshot_tree(compact_dir)

    contexts = [
        {"quality_count": 0, "projectNumber": ""},
        {"quality_count": 3, "projectNumber": "P-123"},
    ]
    for context in contexts:
        assert _render_template(expanded_text, context) == _render_template(source_text, context)


def test_expand_rewrites_appended_sentence_literals_reversibly(tmp_path: Path) -> None:
    """Concatenated append strings should expose one reorderable sentence."""

    compact_dir = tmp_path / "compact"
    (compact_dir / "src").mkdir(parents=True)
    _write_minimal_template_json(compact_dir)
    source_text = """
{%- set sentences = [] -%}
{%- do sentences.append("We will document data with " ~ standard ~ " metadata standard.") -%}
{%- set _ = sentences.append("The risk of information " ~ risk ~ " is low.") -%}
<p>{{ sentences|join(" ") }}</p>
""".lstrip()
    (compact_dir / "src" / "index.html.j2").write_text(source_text, encoding="utf-8")

    expanded_dir = tmp_path / "expanded"
    rebuilt_dir = tmp_path / "rebuilt"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    compact_template_dir(source_dir=expanded_dir, output_dir=rebuilt_dir)

    expanded_text = (expanded_dir / "src" / "index.html.j2").read_text(encoding="utf-8")
    assert "__tr_append_sentence_original:" in expanded_text
    assert "We will document data with {{ standard }} metadata standard." in expanded_text
    assert "The risk of information {{ risk }} is low." in expanded_text
    assert snapshot_tree(rebuilt_dir) == snapshot_tree(compact_dir)

    context = {"standard": "Dublin Core", "risk": "loss"}
    assert _render_template(expanded_text, context) == _render_template(source_text, context)


def test_expand_rewrites_simple_common_prefix_branches_reversibly(tmp_path: Path) -> None:
    """Simple suffix alternatives should become complete branch sentences."""

    compact_dir = tmp_path / "compact"
    (compact_dir / "src").mkdir(parents=True)
    _write_minimal_template_json(compact_dir)
    source_text = """
<p>This data are
{% if access == "open" %}
  freely available for any use.
{% elif access == "quote" %}
  freely available with obligation to quote the source.
{% else %}
  available under restrictions.
{% endif %}
</p>
""".lstrip()
    (compact_dir / "src" / "index.html.j2").write_text(source_text, encoding="utf-8")

    expanded_dir = tmp_path / "expanded"
    rebuilt_dir = tmp_path / "rebuilt"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    compact_template_dir(source_dir=expanded_dir, output_dir=rebuilt_dir)

    expanded_text = (expanded_dir / "src" / "index.html.j2").read_text(encoding="utf-8")
    assert "__tr_branch_sentence_original:" in expanded_text
    assert "This data are\n\n  freely available for any use." in expanded_text
    assert "This data are\n\n  freely available with obligation to quote the source." in (
        expanded_text
    )
    assert snapshot_tree(rebuilt_dir) == snapshot_tree(compact_dir)

    contexts = [
        {"access": "open"},
        {"access": "quote"},
        {"access": "closed"},
    ]
    for context in contexts:
        assert _render_template(expanded_text, context) == _render_template(source_text, context)


def test_expand_hoists_setup_blocks_before_rewritten_branch_conditions(tmp_path: Path) -> None:
    """Setup variables inside a sentence must still exist before rewritten branch checks."""

    compact_dir = tmp_path / "compact"
    (compact_dir / "src").mkdir(parents=True)
    _write_minimal_template_json(compact_dir)
    source_text = """
{%- if needs_harmonization -%}
<p>We need to harmonize different sources before reusing them
{%- set availability = harmonization_available -%}
{%- if availability == "yes" -%}
  and we will make the harmonization available to others
{%- elif availability == "no" -%}
  but we will not make the harmonization available to others
{%- endif -%}
.</p>
{%- endif -%}
""".lstrip()
    (compact_dir / "src" / "index.html.j2").write_text(source_text, encoding="utf-8")

    expanded_dir = tmp_path / "expanded"
    rebuilt_dir = tmp_path / "rebuilt"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    compact_template_dir(source_dir=expanded_dir, output_dir=rebuilt_dir)

    expanded_text = (expanded_dir / "src" / "index.html.j2").read_text(encoding="utf-8")
    assert "__tr_branch_sentence_original:" in expanded_text
    setup_index = expanded_text.index("{%- set availability = harmonization_available -%}")
    branch_index = expanded_text.index('{%- if availability == "yes" -%}')
    assert setup_index < branch_index
    assert snapshot_tree(rebuilt_dir) == snapshot_tree(compact_dir)

    contexts = [
        {"needs_harmonization": True, "harmonization_available": "yes"},
        {"needs_harmonization": True, "harmonization_available": "no"},
        {"needs_harmonization": True, "harmonization_available": ""},
        {"needs_harmonization": False, "harmonization_available": "yes"},
    ]
    for context in contexts:
        assert _render_template(expanded_text, context) == _render_template(source_text, context)


def test_expand_rewrites_simple_common_suffix_branches_reversibly(tmp_path: Path) -> None:
    """Simple prefix alternatives should duplicate a shared suffix."""

    compact_dir = tmp_path / "compact"
    (compact_dir / "src").mkdir(parents=True)
    _write_minimal_template_json(compact_dir)
    source_text = """
<p>{% if count > 0 %}Additional{% else %}Our{% endif %} quality processes are: {{ topic }}.</p>
""".lstrip()
    (compact_dir / "src" / "index.html.j2").write_text(source_text, encoding="utf-8")

    expanded_dir = tmp_path / "expanded"
    rebuilt_dir = tmp_path / "rebuilt"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    compact_template_dir(source_dir=expanded_dir, output_dir=rebuilt_dir)

    expanded_text = (expanded_dir / "src" / "index.html.j2").read_text(encoding="utf-8")
    assert "Additional quality processes are:" in expanded_text
    assert "Our quality processes are:" in expanded_text
    assert snapshot_tree(rebuilt_dir) == snapshot_tree(compact_dir)

    contexts = [
        {"count": 0, "topic": "validation"},
        {"count": 2, "topic": "validation"},
    ]
    for context in contexts:
        assert _render_template(expanded_text, context) == _render_template(source_text, context)


def test_expand_rewrites_nested_subject_branches_inside_outer_branches(
    tmp_path: Path,
) -> None:
    """Nested subject alternatives should keep their shared predicate."""

    compact_dir = tmp_path / "compact"
    (compact_dir / "src").mkdir(parents=True)
    _write_minimal_template_json(compact_dir)
    source_text = """
<p>
{% if stored %}Project members store data in the lab. {% endif %}
{% if carry == "none" %}
  {% if stored %}They{% else %}Project members{% endif %} will not carry data home.
{% elif carry == "encrypted" %}
  {% if stored %}They{% else %}Project members{% endif %} can carry encrypted data home.
{% endif %}
</p>
""".lstrip()
    (compact_dir / "src" / "index.html.j2").write_text(source_text, encoding="utf-8")

    expanded_dir = tmp_path / "expanded"
    rebuilt_dir = tmp_path / "rebuilt"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    compact_template_dir(source_dir=expanded_dir, output_dir=rebuilt_dir)

    expanded_text = (expanded_dir / "src" / "index.html.j2").read_text(encoding="utf-8")
    assert "They will not carry data home." in expanded_text
    assert "Project members will not carry data home." in expanded_text
    assert "They can carry encrypted data home." in expanded_text
    assert "Project members can carry encrypted data home." in expanded_text
    assert snapshot_tree(rebuilt_dir) == snapshot_tree(compact_dir)

    contexts = [
        {"stored": True, "carry": "none"},
        {"stored": False, "carry": "none"},
        {"stored": True, "carry": "encrypted"},
        {"stored": False, "carry": "encrypted"},
        {"stored": True, "carry": ""},
    ]
    for context in contexts:
        assert _render_template(expanded_text, context) == _render_template(source_text, context)


def test_expand_rewrites_simple_common_prefix_and_suffix_branches_reversibly(
    tmp_path: Path,
) -> None:
    """Simple middle alternatives should duplicate both surrounding sentence parts."""

    compact_dir = tmp_path / "compact"
    (compact_dir / "src").mkdir(parents=True)
    _write_minimal_template_json(compact_dir)
    source_text = (
        '<p>Dataset access is {% if mode == "open" %}open'
        '{% elif mode == "shared" %}shared'
        "{% else %}closed{% endif %} using repository {{ repo }}.</p>\n"
    )
    (compact_dir / "src" / "index.html.j2").write_text(source_text, encoding="utf-8")

    expanded_dir = tmp_path / "expanded"
    rebuilt_dir = tmp_path / "rebuilt"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    compact_template_dir(source_dir=expanded_dir, output_dir=rebuilt_dir)

    expanded_text = (expanded_dir / "src" / "index.html.j2").read_text(encoding="utf-8")
    assert "Dataset access is open using repository {{ repo }}." in expanded_text
    assert "Dataset access is shared using repository {{ repo }}." in expanded_text
    assert "Dataset access is closed using repository {{ repo }}." in expanded_text
    assert snapshot_tree(rebuilt_dir) == snapshot_tree(compact_dir)

    contexts = [
        {"mode": "open", "repo": "R1"},
        {"mode": "shared", "repo": "R2"},
        {"mode": "closed", "repo": "R3"},
    ]
    for context in contexts:
        assert _render_template(expanded_text, context) == _render_template(source_text, context)


def test_expand_rewrites_single_choice_optional_branches_reversibly(
    tmp_path: Path,
) -> None:
    """Adjacent optional fragments in a known single-choice context become full sentences."""

    compact_dir = tmp_path / "compact"
    (compact_dir / "src").mkdir(parents=True)
    _write_minimal_template_json(compact_dir)
    source_text = """
{% if selected_count == 1 %}
<p>
  We will be using
  {% if calibrating %}calibrating measurements{% endif %}
  {% if repetition %}repeat samples/measurements{% endif %}
  {% if standardized %}standardized data capture/recording{% endif %}
  as part of the quality process.
</p>
{% endif %}
""".lstrip()
    (compact_dir / "src" / "index.html.j2").write_text(source_text, encoding="utf-8")

    expanded_dir = tmp_path / "expanded"
    rebuilt_dir = tmp_path / "rebuilt"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    compact_template_dir(source_dir=expanded_dir, output_dir=rebuilt_dir)

    expanded_text = (expanded_dir / "src" / "index.html.j2").read_text(encoding="utf-8")
    normalized_expanded = " ".join(expanded_text.split())
    assert "We will be using calibrating measurements as part" in normalized_expanded
    assert "We will be using repeat samples/measurements as part" in normalized_expanded
    assert "We will be using standardized data capture/recording as part" in normalized_expanded
    assert snapshot_tree(rebuilt_dir) == snapshot_tree(compact_dir)

    contexts = [
        {
            "selected_count": 1,
            "calibrating": True,
            "repetition": False,
            "standardized": False,
        },
        {
            "selected_count": 1,
            "calibrating": False,
            "repetition": True,
            "standardized": False,
        },
        {
            "selected_count": 1,
            "calibrating": False,
            "repetition": False,
            "standardized": True,
        },
        {
            "selected_count": 0,
            "calibrating": False,
            "repetition": False,
            "standardized": False,
        },
    ]
    for context in contexts:
        assert _render_template(expanded_text, context) == _render_template(source_text, context)


def test_expand_does_not_cartesian_rewrite_independent_optional_fragments(
    tmp_path: Path,
) -> None:
    """Independent optional fragments should stay grouped instead of exploding."""

    compact_dir = tmp_path / "compact"
    (compact_dir / "src").mkdir(parents=True)
    _write_minimal_template_json(compact_dir)
    source_text = """
<p>
  We will be using
  {% if calibrating %}calibrating measurements{% endif %}
  {% if repetition %}repeat samples/measurements{% endif %}
  as part of the quality process.
</p>
""".lstrip()
    (compact_dir / "src" / "index.html.j2").write_text(source_text, encoding="utf-8")

    expanded_dir = tmp_path / "expanded"
    rebuilt_dir = tmp_path / "rebuilt"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    compact_template_dir(source_dir=expanded_dir, output_dir=rebuilt_dir)

    expanded_text = (expanded_dir / "src" / "index.html.j2").read_text(encoding="utf-8")
    assert "__tr_branch_sentence_original:" not in expanded_text
    assert snapshot_tree(rebuilt_dir) == snapshot_tree(compact_dir)

    contexts = [
        {"calibrating": False, "repetition": False},
        {"calibrating": True, "repetition": False},
        {"calibrating": False, "repetition": True},
        {"calibrating": True, "repetition": True},
    ]
    for context in contexts:
        assert _render_template(expanded_text, context) == _render_template(source_text, context)


def test_expand_does_not_rewrite_branch_with_unsafe_tail_control(
    tmp_path: Path,
) -> None:
    """Branch tails with mutating Jinja should not be moved across conditions."""

    compact_dir = tmp_path / "compact"
    (compact_dir / "src").mkdir(parents=True)
    _write_minimal_template_json(compact_dir)
    source_text = """
{% set fragments = [] %}
<p>
  Data access is {% if open_access %}open{% else %}restricted{% endif %}
  {% do fragments.append("access reviewed") %}.
</p>
<p>{{ fragments|join(", ") }}</p>
""".lstrip()
    (compact_dir / "src" / "index.html.j2").write_text(source_text, encoding="utf-8")

    expanded_dir = tmp_path / "expanded"
    rebuilt_dir = tmp_path / "rebuilt"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    compact_template_dir(source_dir=expanded_dir, output_dir=rebuilt_dir)

    expanded_text = (expanded_dir / "src" / "index.html.j2").read_text(encoding="utf-8")
    assert "__tr_branch_sentence_original:" not in expanded_text
    assert snapshot_tree(rebuilt_dir) == snapshot_tree(compact_dir)

    contexts = [
        {"open_access": False},
        {"open_access": True},
    ]
    for context in contexts:
        assert _render_template(expanded_text, context) == _render_template(source_text, context)


def test_expanded_comment_markers_preserve_rendered_output_across_branch_matrix(
    tmp_path: Path,
) -> None:
    """Generated markers should not alter Jinja scoping, loops, or branches."""

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
    source_text = """
<section>
  <p>
    {% set paragraphStatus = "computed" %}
    Status: {{ paragraphStatus }}.
  </p>
  <p>After paragraph: {{ paragraphStatus }}.</p>

  {% set mutations = [] %}
  <p>
    {% do mutations.append("from paragraph") %}
    Mutations inside paragraph: {{ mutations|length }}.
  </p>
  <p>Mutations after paragraph: {{ mutations|join(", ") }}.</p>

  <p>
    {% if item_count == 0 %}
      No items.
    {% elif item_count == 1 %}
      One item: {{ items[0] }}.
    {% elif item_count == 2 %}
      Two items: {{ items[0] }} and {{ items[1] }}.
    {% else %}
      Many items: {{ items[0] }}, {{ items[1] }}, and {{ items[2] }}.
    {% endif %}
  </p>

  <ul>
  {% for row in rows %}
    <li>
      {{ row.name }}
      {% if row.enabled %}
        is enabled.
      {% else %}
        is disabled.
      {% endif %}
    </li>
  {% else %}
    <li>No rows.</li>
  {% endfor %}
  </ul>
</section>
""".lstrip()
    compact_source_path = compact_dir / "src" / "index.html.j2"
    compact_source_path.write_text(source_text, encoding="utf-8")

    expanded_dir = tmp_path / "expanded"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    expanded_text = (expanded_dir / "src" / "index.html.j2").read_text(encoding="utf-8")

    contexts = [
        {"item_count": 0, "items": [], "rows": []},
        {
            "item_count": 1,
            "items": ["alpha"],
            "rows": [{"name": "Dataset A", "enabled": True}],
        },
        {
            "item_count": 2,
            "items": ["alpha", "beta"],
            "rows": [{"name": "Dataset A", "enabled": False}],
        },
        {
            "item_count": 3,
            "items": ["alpha", "beta", "gamma"],
            "rows": [
                {"name": "Dataset A", "enabled": True},
                {"name": "Dataset B", "enabled": False},
            ],
        },
    ]

    for context in contexts:
        assert _render_template(expanded_text, context) == _render_template(source_text, context)


def test_exhaustive_parallel_fuzz_expanded_render_matches_compact_for_branch_shapes(
    tmp_path: Path,
) -> None:
    """Every generated branch context should render identically after expansion."""

    rng = random.Random(FUZZ_SEED)
    compact_dir = tmp_path / "compact"
    source_dir = compact_dir / "src"
    source_dir.mkdir(parents=True)
    _write_minimal_template_json(compact_dir)

    source_text = "\n".join(
        _build_fuzz_template_source(template_name, index)
        for index, template_name in enumerate(FUZZ_TEMPLATE_BUILDERS)
    )
    source_path = source_dir / "fuzz" / "exhaustive.html.j2"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(source_text, encoding="utf-8")

    expanded_dir = tmp_path / "expanded"
    rebuilt_dir = tmp_path / "rebuilt"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)
    compact_template_dir(source_dir=expanded_dir, output_dir=rebuilt_dir)

    assert snapshot_tree(rebuilt_dir) == snapshot_tree(compact_dir)

    contexts = list(_iter_exhaustive_fuzz_contexts())
    rng.shuffle(contexts)

    assert len(contexts) == FUZZ_CONTEXT_COUNT
    assert FUZZ_LOGICAL_SHAPE_CHECK_COUNT == 54_432

    expanded_text = (expanded_dir / source_path.relative_to(compact_dir)).read_text(
        encoding="utf-8"
    )
    failures = _render_fuzz_contexts(
        source_text=source_text,
        expanded_text=expanded_text,
        contexts=contexts,
    )
    assert failures == []


def _fuzz_scope_template(case_index: int) -> str:
    return f"""
<section data-case="{case_index}">
  <p>
    {{% set scoped_label = label %}}
    Case {{{{ case_id }}}} status: {{{{ scoped_label }}}}.
  </p>
  <p>Outside label: {{{{ scoped_label }}}}.</p>
</section>
""".lstrip()


def _fuzz_mutation_template(case_index: int) -> str:
    return f"""
<section data-case="{case_index}">
  {{% set fragments = [] %}}
  <p>
    {{% do fragments.append("from paragraph") %}}
    {{% if enabled %}}{{% do fragments.append("enabled branch") %}}{{% endif %}}
    Fragments inside paragraph: {{{{ fragments|join(", ") }}}}.
  </p>
  <p>Fragments after paragraph: {{{{ fragments|length }}}}.</p>
</section>
""".lstrip()


def _fuzz_cardinality_template(case_index: int) -> str:
    return f"""
<section data-case="{case_index}">
  <p>
    {{% if item_count == 0 %}}
      No items.
    {{% elif item_count == 1 %}}
      One item: {{{{ items[0] }}}}.
    {{% elif item_count == 2 %}}
      Two items: {{{{ items[0] }}}} and {{{{ items[1] }}}}.
    {{% else %}}
      Many items: {{{{ items[0] }}}}, {{{{ items[1] }}}}, and {{{{ items[2] }}}}.
    {{% endif %}}
  </p>
</section>
""".lstrip()


def _fuzz_loop_template(case_index: int) -> str:
    return f"""
<section data-case="{case_index}">
  <ul>
  {{% for row in rows %}}
    <li>
      {{{{ row.name }}}}
      {{% if row.enabled %}}
        is enabled.
      {{% else %}}
        is disabled.
      {{% endif %}}
    </li>
  {{% else %}}
    <li>No rows.</li>
  {{% endfor %}}
  </ul>
</section>
""".lstrip()


def _fuzz_branch_closed_html_template(case_index: int) -> str:
    return f"""
<section data-case="{case_index}">
  <p>Dataset {{{{ label }}}}
  {{% if mode == "public" %}}
    is public.</p>
  {{% elif mode == "restricted" %}}
    is restricted because {{{{ reason }}}}.</p>
  {{% else %}}
    has unknown access.</p>
  {{% endif %}}
</section>
""".lstrip()


def _fuzz_nested_list_template(case_index: int) -> str:
    return f"""
<section data-case="{case_index}">
  <p>The data cannot become completely open because
  {{% if reasons|length == 1 %}}
    of {{{{ reasons[0] }}}}.
  {{% else %}}
    of:
    <ul>
    {{% for reason in reasons %}}
      <li>{{{{ reason }}}}</li>
    {{% endfor %}}
    </ul>
  {{% endif %}}
</section>
""".lstrip()


def _build_fuzz_template_source(template_name: str, case_index: int) -> str:
    if template_name == "scope":
        return _fuzz_scope_template(case_index)
    if template_name == "mutation":
        return _fuzz_mutation_template(case_index)
    if template_name == "cardinality":
        return _fuzz_cardinality_template(case_index)
    if template_name == "loop":
        return _fuzz_loop_template(case_index)
    if template_name == "branch_closed_html":
        return _fuzz_branch_closed_html_template(case_index)
    if template_name == "nested_list":
        return _fuzz_nested_list_template(case_index)
    raise ValueError(f"Unknown fuzz template builder: {template_name}")


def _iter_exhaustive_fuzz_contexts() -> list[tuple[int, dict[str, Any]]]:
    case_index = 0
    contexts: list[tuple[int, dict[str, Any]]] = []
    for item_count in FUZZ_ITEM_COUNTS:
        for row_flags in _iter_row_flag_sets():
            for reason_count in FUZZ_REASON_COUNTS:
                for enabled in (False, True):
                    for mode in FUZZ_MODES:
                        contexts.append(
                            (
                                case_index,
                                _build_fuzz_context(
                                    case_index=case_index,
                                    enabled=enabled,
                                    item_count=item_count,
                                    mode=mode,
                                    reason_count=reason_count,
                                    row_flags=row_flags,
                                ),
                            )
                        )
                        case_index += 1
    return contexts


def _iter_row_flag_sets() -> list[tuple[bool, ...]]:
    row_flag_sets: list[tuple[bool, ...]] = []
    for row_count in FUZZ_ROW_COUNTS:
        row_flag_sets.extend(itertools.product((False, True), repeat=row_count))
    return row_flag_sets


def _build_fuzz_context(
    *,
    case_index: int,
    enabled: bool,
    item_count: int,
    mode: str,
    reason_count: int,
    row_flags: tuple[bool, ...],
) -> dict[str, Any]:
    return {
        "case_id": case_index,
        "enabled": enabled,
        "items": [f"item-{case_index}-{index}" for index in range(item_count)],
        "item_count": item_count,
        "label": f"label-{case_index}",
        "mode": mode,
        "reason": f"restriction reason {case_index}",
        "reasons": [f"reason {case_index}-{index}" for index in range(reason_count)],
        "rows": [
            {"name": f"Dataset {case_index}-{index}", "enabled": enabled}
            for index, enabled in enumerate(row_flags)
        ],
    }


def _render_fuzz_contexts(
    *,
    source_text: str,
    expanded_text: str,
    contexts: list[tuple[int, dict[str, Any]]],
) -> list[str]:
    chunks = list(_chunked(contexts, FUZZ_CHUNK_SIZE))
    payloads = [(source_text, expanded_text, chunk) for chunk in chunks]
    if FUZZ_WORKERS <= 1:
        return [failure for payload in payloads for failure in _render_fuzz_context_chunk(payload)]

    with ProcessPoolExecutor(max_workers=FUZZ_WORKERS) as executor:
        results = executor.map(_render_fuzz_context_chunk, payloads)
    return [failure for chunk_failures in results for failure in chunk_failures]


def _render_fuzz_context_chunk(
    payload: tuple[str, str, list[tuple[int, dict[str, Any]]]],
) -> list[str]:
    source_text, expanded_text, contexts = payload
    environment = Environment(
        extensions=["jinja2.ext.do"],
        undefined=StrictUndefined,
    )
    original_template = environment.from_string(source_text)
    expanded_template = environment.from_string(expanded_text)
    failures = []
    for case_index, context in contexts:
        try:
            original_render = original_template.render(**context)
            expanded_render = expanded_template.render(**context)
        except Exception as exc:  # pragma: no cover - included in assertion text.
            failures.append(f"seed={FUZZ_SEED} case={case_index}: {type(exc).__name__}: {exc}")
            continue
        if expanded_render != original_render:
            failures.append(f"seed={FUZZ_SEED} case={case_index}: rendered output diverged")
    return failures


def _chunked(
    items: list[tuple[int, dict[str, Any]]],
    size: int,
) -> list[list[tuple[int, dict[str, Any]]]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def test_expand_keeps_one_paragraph_with_inner_condition_as_one_block(tmp_path: Path) -> None:
    """Inner Jinja branches inside one paragraph should stay in one translatable block."""

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
    (compact_dir / "src" / "paragraph.html.j2").write_text(
        """
{% if enabled %}
  <p>
    This dataset will be collected by an external party.
    {% if ownership == "external" %}
      The ownership remains with the external party.
    {% else %}
      The project partners acquire full ownership of the data.
    {% endif %}
  </p>
{% endif %}
""".lstrip(),
        encoding="utf-8",
    )

    expanded_dir = tmp_path / "expanded"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)

    expanded_text = (expanded_dir / "src" / "paragraph.html.j2").read_text(encoding="utf-8")
    assert expanded_text.count("{# __tr_block_") == 2
    assert expanded_text.count(":start #}") == 1
    assert "This dataset will be collected by an external party." in expanded_text
    assert "The project partners acquire full ownership of the data." in expanded_text


def test_expand_keeps_branch_closed_sentence_group_as_one_block(tmp_path: Path) -> None:
    """Branch-specific endings of one sentence should stay in one wrapper block."""

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
    (compact_dir / "src" / "sentence-branches.html.j2").write_text(
        """
<p>We are collecting and processing personal data
{%- if legal_basis == "public" -%}
  based on public interest.</p>
{%- elif legal_basis == "consent" -%}
  based on subject's consent.</p>
{%- elif legal_basis == "contract" -%}
  in order to fulfil contract.</p>
{%- endif -%}
""".lstrip(),
        encoding="utf-8",
    )

    expanded_dir = tmp_path / "expanded"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)

    expanded_text = (expanded_dir / "src" / "sentence-branches.html.j2").read_text(encoding="utf-8")
    assert expanded_text.count(":start #}") == 1
    assert "based on subject's consent." in expanded_text
    assert "in order to fulfil contract." in expanded_text


def test_expand_keeps_unclosed_paragraph_with_if_else_as_one_block(tmp_path: Path) -> None:
    """Malformed-but-renderable paragraph flows should still become one wrapper block."""

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
    (compact_dir / "src" / "reason-list.html.j2").write_text(
        """
<p>
The data cannot become completely open because
{%- if one_reason -%}
  of legal reasons.
{%- else -%}
  of:
  <ul>
    <li>legal reasons</li>
    <li>patent-related business reasons</li>
  </ul>
{%- endif -%}
""".lstrip(),
        encoding="utf-8",
    )

    expanded_dir = tmp_path / "expanded"
    expand_template_dir(source_dir=compact_dir, output_dir=expanded_dir)

    expanded_text = (expanded_dir / "src" / "reason-list.html.j2").read_text(encoding="utf-8")
    assert expanded_text.count(":start #}") == 1
    assert "<ul>" in expanded_text
    assert "patent-related business reasons" in expanded_text
