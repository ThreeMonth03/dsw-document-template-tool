"""Traceable Knowledge Model evidence for DSW render regression."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .translation_repository import DswPreviewRuntime
from .yaml_config import YamlConfigError, load_yaml_file

EVIDENCE_SCHEMA_VERSION = 1


class RegressionEvidenceError(ValueError):
    """Raised when regression evidence configuration is invalid or stale."""


@dataclass(frozen=True)
class KnowledgeModelEvidence:
    """Pinned provenance for one immutable Knowledge Model bundle."""

    key: str
    path: Path
    package_id: str
    version: str
    metamodel_version: str
    source_url: str
    sha256: str


@dataclass(frozen=True)
class RegressionEvidenceConfig:
    """Knowledge Model fixtures assigned to supported DSW runtimes."""

    knowledge_models: dict[str, KnowledgeModelEvidence]
    runtime_knowledge_models: dict[str, str]

    def knowledge_model_for_runtime(self, runtime: DswPreviewRuntime) -> KnowledgeModelEvidence:
        """Return the pinned Knowledge Model assigned to ``runtime``."""

        fixture_key = self.runtime_knowledge_models.get(runtime.metamodel_key)
        if fixture_key is None:
            raise RegressionEvidenceError(
                f"Runtime {runtime.metamodel_key!r} has no regression Knowledge Model assignment"
            )
        try:
            return self.knowledge_models[fixture_key]
        except KeyError as exc:
            raise RegressionEvidenceError(
                f"Runtime {runtime.metamodel_key!r} references unknown Knowledge Model "
                f"fixture {fixture_key!r}"
            ) from exc


def load_regression_evidence_config(path: Path) -> RegressionEvidenceConfig:
    """Load and validate pinned regression evidence from YAML."""

    path = Path(path)
    try:
        payload = load_yaml_file(path)
    except (OSError, YamlConfigError) as exc:
        raise RegressionEvidenceError(str(exc)) from exc
    if not isinstance(payload, dict):
        raise RegressionEvidenceError(f"Regression evidence config {path} must be a mapping")
    _reject_unknown_keys(
        payload,
        {"knowledge_models", "runtime_knowledge_models", "schema_version"},
        "regression evidence config",
    )
    if payload.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        raise RegressionEvidenceError(
            f"Regression evidence schema_version must be {EVIDENCE_SCHEMA_VERSION}"
        )

    raw_models = payload.get("knowledge_models")
    if not isinstance(raw_models, dict) or not raw_models:
        raise RegressionEvidenceError("Regression evidence must define knowledge_models")
    knowledge_models = {
        _mapping_key(key, context="knowledge_models"): _load_knowledge_model(
            key=_mapping_key(key, context="knowledge_models"),
            payload=value,
            base_dir=path.parent,
        )
        for key, value in raw_models.items()
    }

    raw_assignments = payload.get("runtime_knowledge_models")
    if not isinstance(raw_assignments, dict) or not raw_assignments:
        raise RegressionEvidenceError("Regression evidence must define runtime_knowledge_models")
    assignments = {
        _mapping_key(key, context="runtime_knowledge_models"): _required_string_value(
            value,
            context=f"runtime_knowledge_models.{key}",
        )
        for key, value in raw_assignments.items()
    }
    config = RegressionEvidenceConfig(
        knowledge_models=knowledge_models,
        runtime_knowledge_models=assignments,
    )
    _validate_assignment_references(config)
    return config


def validate_regression_evidence_config(
    config: RegressionEvidenceConfig,
    runtimes: tuple[DswPreviewRuntime, ...],
) -> None:
    """Validate runtime assignments and every pinned Knowledge Model bundle."""

    runtime_keys = {runtime.metamodel_key for runtime in runtimes}
    assignment_keys = set(config.runtime_knowledge_models)
    missing = sorted(runtime_keys - assignment_keys)
    stale = sorted(assignment_keys - runtime_keys)
    if missing:
        raise RegressionEvidenceError(
            f"Missing regression Knowledge Model assignment for runtime(s): {', '.join(missing)}"
        )
    if stale:
        raise RegressionEvidenceError(
            f"Regression evidence references unknown runtime(s): {', '.join(stale)}"
        )
    for runtime in runtimes:
        verify_knowledge_model_evidence(config.knowledge_model_for_runtime(runtime))


def verify_knowledge_model_evidence(evidence: KnowledgeModelEvidence) -> None:
    """Verify one pinned bundle's checksum and declared package metadata."""

    if not evidence.path.is_file():
        raise RegressionEvidenceError(
            f"Knowledge Model fixture {evidence.key!r} does not exist: {evidence.path}"
        )
    actual_sha256 = _sha256(evidence.path)
    if actual_sha256 != evidence.sha256:
        raise RegressionEvidenceError(
            f"Knowledge Model fixture {evidence.key!r} checksum mismatch: "
            f"expected {evidence.sha256}, got {actual_sha256}"
        )
    try:
        payload = json.loads(evidence.path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RegressionEvidenceError(
            f"Knowledge Model fixture {evidence.key!r} is not valid JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise RegressionEvidenceError(
            f"Knowledge Model fixture {evidence.key!r} must contain a JSON object"
        )
    expected_fields = {
        "id": evidence.package_id,
        "metamodelVersion": evidence.metamodel_version,
        "version": evidence.version,
    }
    for field, expected in expected_fields.items():
        actual = str(payload.get(field, ""))
        if actual != expected:
            raise RegressionEvidenceError(
                f"Knowledge Model fixture {evidence.key!r} declares {field}={actual!r}; "
                f"expected {expected!r}"
            )


def _load_knowledge_model(
    *,
    key: str,
    payload: object,
    base_dir: Path,
) -> KnowledgeModelEvidence:
    if not isinstance(payload, dict):
        raise RegressionEvidenceError(f"Knowledge Model fixture {key!r} must be a mapping")
    _reject_unknown_keys(
        payload,
        {"metamodel_version", "package_id", "path", "sha256", "source_url", "version"},
        f"knowledge_models.{key}",
    )
    raw_path = _required_string(payload, "path", context=f"knowledge_models.{key}")
    path = Path(raw_path)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    sha256 = _required_string(payload, "sha256", context=f"knowledge_models.{key}")
    if len(sha256) != 64 or any(character not in "0123456789abcdef" for character in sha256):
        raise RegressionEvidenceError(
            f"knowledge_models.{key}.sha256 must be a lowercase SHA-256 digest"
        )
    return KnowledgeModelEvidence(
        key=key,
        path=path,
        package_id=_required_string(payload, "package_id", context=f"knowledge_models.{key}"),
        version=_required_string(payload, "version", context=f"knowledge_models.{key}"),
        metamodel_version=_required_string(
            payload,
            "metamodel_version",
            context=f"knowledge_models.{key}",
        ),
        source_url=_required_string(payload, "source_url", context=f"knowledge_models.{key}"),
        sha256=sha256,
    )


def _validate_assignment_references(config: RegressionEvidenceConfig) -> None:
    unknown = sorted(set(config.runtime_knowledge_models.values()) - set(config.knowledge_models))
    if unknown:
        raise RegressionEvidenceError(
            f"Unknown Knowledge Model fixture assignment(s): {', '.join(unknown)}"
        )


def _reject_unknown_keys(
    payload: dict[object, object],
    allowed: set[str],
    context: str,
) -> None:
    unknown = sorted(str(key) for key in payload if not isinstance(key, str) or key not in allowed)
    if unknown:
        raise RegressionEvidenceError(f"Unknown field(s) in {context}: {', '.join(unknown)}")


def _mapping_key(value: object, *, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise RegressionEvidenceError(f"Expected non-empty string key in {context}")
    return value


def _required_string(payload: dict[object, object], key: str, *, context: str) -> str:
    return _required_string_value(payload.get(key), context=f"{context}.{key}")


def _required_string_value(value: object, *, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RegressionEvidenceError(f"Expected non-empty string at {context}")
    return value.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
