"""Tests for DSW compatibility source parsing."""

from __future__ import annotations

import pytest

from dsw_document_template_tool.dsw_compat import (
    DswCompatSourceError,
    parse_template_metamodel_support,
    runtime_candidate_message,
)


def test_parse_template_metamodel_support_from_official_style_html() -> None:
    """The DSW guide's heading format should yield metamodel mappings."""

    support = parse_template_metamodel_support(
        """
        <h3>Version 18.1 (since 4.31.0)</h3>
        <h3>Version 18.0 (since 4.29.0)</h3>
        <h3>Version 17.1 (since 4.26.0)</h3>
        """,
        source_url="https://example.test/specification.html",
    )

    assert support["18.1"].minimum_dsw_version == "4.31.0"
    assert support["18.0"].minimum_dsw_version == "4.29.0"
    assert support["17.1"].source_url == "https://example.test/specification.html"


def test_parse_template_metamodel_support_requires_rows() -> None:
    """A changed source format should fail loudly instead of guessing."""

    with pytest.raises(DswCompatSourceError):
        parse_template_metamodel_support(
            "<h3>Document Template Metamodels</h3>",
            source_url="https://example.test/specification.html",
        )


def test_runtime_candidate_message_uses_official_minimum_dsw_version() -> None:
    """Unsupported metamodels should produce a useful maintainer hint."""

    support = parse_template_metamodel_support(
        "<h3>Version 19.0 (since 4.35.0)</h3>",
        source_url="https://example.test/specification.html",
    )

    message = runtime_candidate_message("19.0", support)

    assert "metamodel 19.0" in message
    assert "DSW 4.35.0" in message
    assert "smoke-testing" in message
