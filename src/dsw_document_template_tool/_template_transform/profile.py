"""Template profile identity and rewrite trace models."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .models import TemplateTransformError


@dataclass(frozen=True)
class TemplateIdentity:
    """Coordinates that select template-specific transform behavior."""

    organization_id: str
    template_id: str
    version: str

    @property
    def full_id(self) -> str:
        """Return DSW-style template coordinates."""

        return f"{self.organization_id}:{self.template_id}:{self.version}"


@dataclass(frozen=True)
class TransformContext:
    """Identity and source location available to one transform rule."""

    identity: TemplateIdentity
    relative_path: str
    apply_local_patches: bool


@dataclass(frozen=True)
class RewriteApplication:
    """One named rewrite group applied to one source file."""

    group_id: str
    rationale: str
    source_file: str
    match_count: int


@dataclass
class TransformTrace:
    """Collect deterministic diagnostics without changing rendered output."""

    profile_id: str
    applications: list[RewriteApplication] = field(default_factory=list)

    def record(
        self,
        *,
        group_id: str,
        rationale: str,
        source_file: str,
        match_count: int,
    ) -> None:
        """Record a group only when it changed source text."""

        if match_count <= 0:
            return
        self.applications.append(
            RewriteApplication(
                group_id=group_id,
                rationale=rationale,
                source_file=source_file,
                match_count=match_count,
            )
        )

    def to_manifest(self) -> dict[str, object]:
        """Return stable JSON-compatible trace data."""

        grouped: dict[tuple[str, str, str], int] = {}
        for application in self.applications:
            key = (application.group_id, application.rationale, application.source_file)
            grouped[key] = grouped.get(key, 0) + application.match_count
        return {
            "profile": self.profile_id,
            "applications": [
                {
                    "group_id": group_id,
                    "rationale": rationale,
                    "source_file": source_file,
                    "match_count": match_count,
                }
                for (group_id, rationale, source_file), match_count in sorted(grouped.items())
            ],
        }


def read_template_identity(template_dir: Path) -> TemplateIdentity:
    """Read required transform coordinates from ``template.json``."""

    template_json = template_dir / "template.json"
    try:
        payload = json.loads(template_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TemplateTransformError(
            f"Cannot read template identity from {template_json}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise TemplateTransformError(f"Expected a JSON object in {template_json}")

    values: dict[str, str] = {}
    for key in ("organizationId", "templateId", "version"):
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise TemplateTransformError(f"Missing non-empty {key!r} in {template_json}")
        values[key] = value
    return TemplateIdentity(
        organization_id=values["organizationId"],
        template_id=values["templateId"],
        version=values["version"],
    )
