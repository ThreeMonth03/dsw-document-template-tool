"""Tests for pinned Knowledge Model regression evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from dsw_document_template_tool.regression_evidence import (
    RegressionEvidenceError,
    load_regression_evidence_config,
    validate_regression_evidence_config,
)
from dsw_document_template_tool.translation_repository import DswPreviewRuntime


def test_load_and_validate_regression_evidence_config(tmp_path: Path) -> None:
    """A runtime assignment should verify the pinned bundle and its metadata."""

    bundle = _write_bundle(tmp_path / "root.km")
    config_path = _write_config(tmp_path, bundle=bundle)
    runtime = _runtime()

    config = load_regression_evidence_config(config_path)
    validate_regression_evidence_config(config, (runtime,))

    evidence = config.knowledge_model_for_runtime(runtime)
    assert evidence.package_id == "dsw:root:2.7.0"
    assert evidence.metamodel_version == "19"
    assert evidence.path == bundle.resolve()


def test_runtime_evidence_rejects_checksum_drift(tmp_path: Path) -> None:
    """Fixture replacement must require an intentional checksum update."""

    bundle = _write_bundle(tmp_path / "root.km")
    config_path = _write_config(tmp_path, bundle=bundle)
    bundle.write_text("{}\n", encoding="utf-8")

    with pytest.raises(RegressionEvidenceError, match="checksum mismatch"):
        validate_regression_evidence_config(
            load_regression_evidence_config(config_path),
            (_runtime(),),
        )


def test_runtime_evidence_requires_every_runtime_assignment(tmp_path: Path) -> None:
    """Adding a runtime must also select an explicit regression KM fixture."""

    bundle = _write_bundle(tmp_path / "root.km")
    config_path = _write_config(tmp_path, bundle=bundle)
    unknown_runtime = DswPreviewRuntime(
        metamodel_key="19-0",
        metamodel_version="19.0",
        dsw_version="4.35",
        tdk_version="4.35.0",
        min_version="v1.31.0",
        max_version=None,
        upstream_template_artifact_refs="v1.31.0+",
    )

    with pytest.raises(RegressionEvidenceError, match="Missing.*19-0"):
        validate_regression_evidence_config(
            load_regression_evidence_config(config_path),
            (_runtime(), unknown_runtime),
        )


def _write_bundle(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "id": "dsw:root:2.7.0",
                "metamodelVersion": 19,
                "version": "2.7.0",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_config(tmp_path: Path, *, bundle: Path) -> Path:
    checksum = hashlib.sha256(bundle.read_bytes()).hexdigest()
    path = tmp_path / "regression-evidence.yml"
    path.write_text(
        f"""
schema_version: 1
knowledge_models:
  official-root:
    path: {bundle.name}
    package_id: dsw:root:2.7.0
    version: "2.7.0"
    metamodel_version: "19"
    source_url: https://example.test/root
    sha256: {checksum}
runtime_knowledge_models:
  "18-0": official-root
""".lstrip(),
        encoding="utf-8",
    )
    return path


def _runtime() -> DswPreviewRuntime:
    return DswPreviewRuntime(
        metamodel_key="18-0",
        metamodel_version="18.0",
        dsw_version="4.30",
        tdk_version="4.30.2",
        min_version="v1.30.0",
        max_version=None,
        upstream_template_artifact_refs="v1.30.0+",
    )
