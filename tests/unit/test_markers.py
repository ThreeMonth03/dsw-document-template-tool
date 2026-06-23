"""Tests for transform marker helpers."""

from __future__ import annotations

from dsw_document_template_tool._template_transform.markers import (
    decode_marker_payload,
    encode_marker_payload,
)


def test_marker_payload_round_trips_source_text() -> None:
    source_text = "<p>資料 {{ value }} / text</p>"

    payload = encode_marker_payload(source_text)

    assert "/" not in payload
    assert decode_marker_payload(payload) == source_text
