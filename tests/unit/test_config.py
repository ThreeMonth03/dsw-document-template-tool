"""Tests for workflow config loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from dsw_document_template_tool.config import WorkflowConfigError, load_workflow_config


def test_load_workflow_config_resolves_relative_event_path(tmp_path: Path, monkeypatch) -> None:
    """Relative paths and environment-variable placeholders should resolve safely."""

    monkeypatch.setenv("DSW_API_URL", "http://localhost:3000/wizard-api")
    monkeypatch.setenv("DSW_API_KEY", "secret-token")

    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    events_path = fixtures_dir / "happy.json"
    events_path.write_text("[]\n", encoding="utf-8")

    config_path = tmp_path / "workflow.yml"
    config_path.write_text(
        """
api:
  url: ${DSW_API_URL}
  token: ${DSW_API_KEY}
tdk:
  executable: tools/dsw-tdk
subjects:
  baseline:
    kind: draft_id
    value: myorg:baseline:1.0.0
  candidate:
    kind: draft_id
    value: myorg:candidate:1.0.0
regression:
  mode: preview
  format_uuid: html-format-uuid
  output_dir: outputs
fixtures:
  - name: happy-path
    project:
      name: happy path
      knowledge_model_package_id: myorg:km:1.0.0
    events_file: fixtures/happy.json
""".strip()
        + "\n",
        encoding="utf-8",
    )

    config = load_workflow_config(config_path)

    assert config.api.url == "http://localhost:3000/wizard-api"
    assert config.api.token == "secret-token"
    assert config.tdk.executable == str((tmp_path / "tools" / "dsw-tdk").resolve())
    assert config.regression.output_dir == (tmp_path / "outputs").resolve()
    assert config.fixtures[0].events_file == events_path.resolve()


def test_load_workflow_config_rejects_unexpanded_env_var(tmp_path: Path, monkeypatch) -> None:
    """Missing CI secrets should fail fast during config loading."""

    monkeypatch.delenv("DSW_API_URL", raising=False)
    monkeypatch.setenv("DSW_API_KEY", "secret-token")

    config_path = tmp_path / "workflow.yml"
    config_path.write_text(
        """
api:
  url: ${DSW_API_URL}
  token: ${DSW_API_KEY}
subjects:
  baseline:
    kind: draft_id
    value: myorg:baseline:1.0.0
  candidate:
    kind: draft_id
    value: myorg:candidate:1.0.0
regression:
  mode: preview
  format_uuid: html-format-uuid
  output_dir: outputs
fixtures:
  - name: happy-path
    project:
      name: happy path
      knowledge_model_package_id: myorg:km:1.0.0
    events_file: fixtures/happy.json
""".strip()
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(WorkflowConfigError, match="DSW_API_URL"):
        load_workflow_config(config_path)


def test_load_document_config_allows_events_file_without_project_event_uuid(
    tmp_path: Path, monkeypatch
) -> None:
    """Document mode can derive the snapshot from the applied fixture events."""

    monkeypatch.setenv("DSW_API_URL", "http://localhost:3000/wizard-api")
    monkeypatch.setenv("DSW_API_KEY", "secret-token")
    monkeypatch.setenv("DSW_KM_PACKAGE_ID", "myorg:km:1.0.0")
    monkeypatch.setenv("DSW_BASELINE_TEMPLATE_ID", "myorg:baseline:1.0.0")
    monkeypatch.setenv("DSW_CANDIDATE_TEMPLATE_ID", "myorg:candidate:1.0.0")

    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    events_path = fixtures_dir / "happy.json"
    events_path.write_text("[]\n", encoding="utf-8")

    config_path = tmp_path / "workflow.yml"
    config_path.write_text(
        """
api:
  url: ${DSW_API_URL}
  token: ${DSW_API_KEY}
subjects:
  baseline:
    kind: released_id
    value: ${DSW_BASELINE_TEMPLATE_ID}
  candidate:
    kind: released_id
    value: ${DSW_CANDIDATE_TEMPLATE_ID}
regression:
  mode: document
  format_uuid: html-format-uuid
  output_dir: outputs
fixtures:
  - name: happy-path
    project:
      name: happy path
      knowledge_model_package_id: ${DSW_KM_PACKAGE_ID}
    events_file: fixtures/happy.json
""".strip()
        + "\n",
        encoding="utf-8",
    )

    config = load_workflow_config(config_path)

    assert config.regression.mode == "document"
    assert config.fixtures[0].project_event_uuid is None
    assert config.fixtures[0].events_file == events_path.resolve()


def test_load_document_config_requires_snapshot_source(tmp_path: Path, monkeypatch) -> None:
    """Document mode should reject fixtures that cannot resolve a stable snapshot."""

    monkeypatch.setenv("DSW_API_URL", "http://localhost:3000/wizard-api")
    monkeypatch.setenv("DSW_API_KEY", "secret-token")
    monkeypatch.setenv("DSW_BASELINE_TEMPLATE_ID", "myorg:baseline:1.0.0")
    monkeypatch.setenv("DSW_CANDIDATE_TEMPLATE_ID", "myorg:candidate:1.0.0")

    config_path = tmp_path / "workflow.yml"
    config_path.write_text(
        """
api:
  url: ${DSW_API_URL}
  token: ${DSW_API_KEY}
subjects:
  baseline:
    kind: released_id
    value: ${DSW_BASELINE_TEMPLATE_ID}
  candidate:
    kind: released_id
    value: ${DSW_CANDIDATE_TEMPLATE_ID}
regression:
  mode: document
  format_uuid: html-format-uuid
  output_dir: outputs
fixtures:
  - name: released-snapshot
    project_uuid: 11111111-1111-4111-8111-111111111111
""".strip()
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(WorkflowConfigError, match="project_event_uuid"):
        load_workflow_config(config_path)
