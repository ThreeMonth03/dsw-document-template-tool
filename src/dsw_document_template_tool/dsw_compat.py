"""Official DSW compatibility source helpers.

This module intentionally only discovers *candidate* runtime information.
Checked-in CI runtimes still live in ``config/dsw-compat.yml`` and should only
be updated after an import/render smoke test.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from dataclasses import dataclass

OFFICIAL_TEMPLATE_METAMODEL_SPEC_URL = (
    "https://guide.ds-wizard.org/en/latest/more/development/document-templates/specification.html"
)
HTTP_USER_AGENT = "DSW-document-template-tool/compat-discovery"


class DswCompatSourceError(RuntimeError):
    """Raised when an official DSW compatibility source cannot be used."""


@dataclass(frozen=True)
class DswTemplateMetamodelSupport:
    """Official minimum DSW version for a document-template metamodel."""

    metamodel_version: str
    minimum_dsw_version: str
    source_url: str


def fetch_official_template_metamodel_support(
    source_url: str = OFFICIAL_TEMPLATE_METAMODEL_SPEC_URL,
    *,
    timeout_seconds: int = 20,
) -> dict[str, DswTemplateMetamodelSupport]:
    """Fetch and parse the official DSW document-template metamodel table."""

    try:
        request = urllib.request.Request(
            source_url,
            headers={"User-Agent": HTTP_USER_AGENT},
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            text = response.read().decode("utf-8")
    except (OSError, urllib.error.URLError) as exc:
        raise DswCompatSourceError(
            f"Could not load official DSW metamodel source {source_url!r}: {exc}"
        ) from exc

    return parse_template_metamodel_support(text, source_url=source_url)


def parse_template_metamodel_support(
    text: str,
    *,
    source_url: str,
) -> dict[str, DswTemplateMetamodelSupport]:
    """Parse DSW metamodel support rows from the official specification page."""

    rows: dict[str, DswTemplateMetamodelSupport] = {}
    for match in re.finditer(
        r"Version\s+"
        r"(?P<metamodel>[0-9]+(?:\.[0-9]+)*)"
        r"\s+\(since\s+"
        r"(?P<dsw>[0-9]+(?:\.[0-9]+){1,2})"
        r"\)",
        text,
    ):
        metamodel_version = _normalize_version(match.group("metamodel"))
        rows[metamodel_version] = DswTemplateMetamodelSupport(
            metamodel_version=metamodel_version,
            minimum_dsw_version=_normalize_version(match.group("dsw")),
            source_url=source_url,
        )

    if not rows:
        raise DswCompatSourceError(
            f"Could not parse any metamodel support rows from {source_url!r}"
        )
    return rows


def runtime_candidate_message(
    metamodel_version: str,
    support_by_metamodel: dict[str, DswTemplateMetamodelSupport] | None,
) -> str:
    """Return a maintainer-facing runtime suggestion for one metamodel."""

    if support_by_metamodel is None:
        return "No official runtime suggestion is available."

    support = support_by_metamodel.get(_normalize_version(metamodel_version))
    if support is None:
        return "No official DSW metamodel mapping was found for this metamodelVersion."

    return (
        f"Official DSW docs say document-template metamodel "
        f"{support.metamodel_version} is supported since DSW "
        f"{support.minimum_dsw_version}. Start by smoke-testing a "
        f"wizard-server/document-worker runtime at or above that version with "
        f"a matching dsw-tdk release, then add the proven runtime to "
        f"`config/dsw-compat.yml`."
    )


def _normalize_version(version: str) -> str:
    return version.strip()
