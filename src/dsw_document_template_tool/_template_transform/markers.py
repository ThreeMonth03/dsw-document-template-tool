"""Generated translation block marker contract."""

from __future__ import annotations

import base64
import re

GENERATED_BLOCK_PREFIX = "__tr_block_"
GENERATED_BLOCK_PATTERN = re.compile(
    r"\{# (?P<marker_name>__tr_block_\d{4}):start #\}"
    r"(?P<marker_body>.*?)"
    r"\{# (?P=marker_name):end #\}"
    r"|"
    r"\{% set (?P<set_name>__tr_block_\d{4}) %\}"
    r"(?P<set_body>.*?)"
    r"\{% endset %\}\{\{ (?P=set_name) \}\}",
    re.DOTALL,
)


def generated_block_name(match: re.Match[str]) -> str:
    """Return the generated wrapper name from one marker regex match."""

    name = match.group("marker_name") or match.group("set_name")
    if name is None:
        raise ValueError("Generated block marker did not include a block name")
    return name


def generated_block_body(match: re.Match[str]) -> str:
    """Return the generated wrapper body from one marker regex match."""

    body = match.group("marker_body")
    if body is not None:
        return body
    set_body = match.group("set_body")
    if set_body is None:
        raise ValueError("Generated block marker did not include a block body")
    return set_body


def encode_marker_payload(source_text: str) -> str:
    """Encode original source text for reversible marker comments."""

    return base64.urlsafe_b64encode(source_text.encode("utf-8")).decode("ascii")


def decode_marker_payload(payload: str) -> str:
    """Decode original source text from one reversible marker comment."""

    return base64.urlsafe_b64decode(payload).decode("utf-8")
