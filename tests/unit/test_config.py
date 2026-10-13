"""Tests for workflow config loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from dsw_document_template_tool.config import WorkflowConfigError, load_workflow_config


def _document_language_config(tmp_path: Path, *, mode="document", kind="released_id") -> Path:
    config_path = tmp_path / "language.yml"
    config_path.write_text(
        f"""api:
  url: http://localhost/wizard-api
  token: synthetic-test-token
subjects:
  candidate:
    kind: {kind}
    value: example:template:1.0.0
regression:
  assertion: render_success
  mode: {mode}
  format_uuid: html-format-uuid
  output_dir: outputs
  language: zh-Hant
fixtures:
  - name: sample
    project_uuid: project-uuid
    project_event_uuid: snapshot-uuid
""",
        encoding="utf-8",
    )
    return config_path


@pytest.mark.parametrize("language", [None, "en", "zh-Hant"])
def test_document_language_config_is_optional(tmp_path: Path, language: str | None) -> None:
    """Locale selection is explicit and never inferred from the project or KM."""

    path = _document_language_config(tmp_path)
    text = path.read_text(encoding="utf-8")
    replacement = "" if language is None else f"  language: {language}\n"
    path.write_text(text.replace("  language: zh-Hant\n", replacement), encoding="utf-8")
    assert load_workflow_config(path).regression.language == language


@pytest.mark.parametrize(
    ("mode", "kind", "message"),
    [
        ("preview", "draft_id", "requires document mode"),
        ("document", "local_dir", "requires released_id subjects"),
        ("document", "local_package", "requires released_id subjects"),
    ],
)
def test_document_language_rejects_untranslated_paths(
    tmp_path: Path, mode: str, kind: str, message: str
) -> None:
    """Unsupported language paths fail during config loading, before authentication."""

    path = _document_language_config(tmp_path, mode=mode, kind=kind)
    with pytest.raises(WorkflowConfigError, match=message):
        load_workflow_config(path)


def test_document_language_checks_baseline_too(tmp_path: Path) -> None:
    """Equality must not mix a released PO candidate with a staged untranslated baseline."""

    path = _document_language_config(tmp_path)
    text = (
        path.read_text(encoding="utf-8")
        .replace(
            "subjects:\n",
            "subjects:\n  baseline:\n    kind: local_package\n    value: baseline.zip\n",
        )
        .replace("assertion: render_success", "assertion: equal")
    )
    path.write_text(text, encoding="utf-8")
    with pytest.raises(WorkflowConfigError, match="requires released_id subjects"):
        load_workflow_config(path)


@pytest.mark.parametrize("value", ['""', '" "', '"zh Hant"', "123", "false", "[en]"])
def test_document_language_config_rejects_invalid_values(tmp_path: Path, value: str) -> None:
    """A malformed configured language must not silently become the base language."""

    path = _document_language_config(tmp_path)
    path.write_text(
        path.read_text(encoding="utf-8").replace("language: zh-Hant", f"language: {value}"),
        encoding="utf-8",
    )
    with pytest.raises(WorkflowConfigError, match="language"):
        load_workflow_config(path)


def test_load_workflow_config_rejects_duplicate_keys(tmp_path: Path) -> None:
    """Ambiguous workflow settings should fail before any DSW request runs."""

    config_path = tmp_path / "workflow.yml"
    config_path.write_text(
        "api:\n  url: http://first.example\n  url: http://second.example\n",
        encoding="utf-8",
    )

    with pytest.raises(WorkflowConfigError, match="duplicate key 'url'"):
        load_workflow_config(config_path)


def test_load_workflow_config_rejects_unknown_keys(tmp_path: Path) -> None:
    """A misspelled setting should fail instead of falling back to a default."""

    config_path = tmp_path / "workflow.yml"
    config_path.write_text(
        """
api:
  url: http://localhost
  token: secret
subjects:
  baseline:
    kind: draft_id
    value: example:baseline:1.0.0
  candidate:
    kind: draft_id
    value: example:candidate:1.0.0
regression:
  mode: preview
  format_uuid: format-id
  output_dir: outputs
  poll_second: 1
fixtures:
  - name: sample
    project_uuid: 11111111-1111-4111-8111-111111111111
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(WorkflowConfigError, match="poll_second"):
        load_workflow_config(config_path)


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


def test_load_workflow_config_supports_generated_fixtures(tmp_path: Path, monkeypatch) -> None:
    """CI can ask the workflow to create deterministic random fixture projects."""

    monkeypatch.setenv("DSW_API_URL", "http://localhost:3000/wizard-api")
    monkeypatch.setenv("DSW_API_KEY", "secret-token")

    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    events_path = fixtures_dir / "empty.json"
    events_path.write_text("[]\n", encoding="utf-8")

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
  - name: empty-project
    project:
      name: empty path
      knowledge_model_package_id: myorg:km:1.0.0
    events_file: fixtures/empty.json
generated_fixtures:
  - name_prefix: random-project
    count: 80
    seed: 20260522
    max_events: 320
    max_items_per_list: 3
    answer_probability: 1.0
    selection_pool_size: 640
    require_complete_coverage: true
    project:
      name: random path
      knowledge_model_package_id: myorg:km:1.0.0
""".strip()
        + "\n",
        encoding="utf-8",
    )

    config = load_workflow_config(config_path)

    generated = config.generated_fixtures[0]
    assert generated.name_prefix == "random-project"
    assert generated.count == 80
    assert generated.seed == 20260522
    assert generated.max_events == 320
    assert generated.max_items_per_list == 3
    assert generated.selection_pool_size == 640
    assert generated.require_complete_coverage
    assert generated.project.name == "random path"


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


def test_load_render_success_config_accepts_one_local_package(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A translated package regression should not require a fake baseline."""

    monkeypatch.setenv("DSW_API_URL", "http://localhost:3000/wizard-api")
    monkeypatch.setenv("DSW_API_KEY", "secret-token")

    package_path = tmp_path / "translated-template.zip"
    package_path.write_bytes(b"package")
    events_path = tmp_path / "events.json"
    events_path.write_text("[]\n", encoding="utf-8")
    config_path = tmp_path / "workflow.yml"
    config_path.write_text(
        """
api:
  url: ${DSW_API_URL}
  token: ${DSW_API_KEY}
subjects:
  candidate:
    kind: local_package
    value: translated-template.zip
regression:
  assertion: render_success
  mode: document
  format_uuid: html-format-uuid
  output_dir: outputs
fixtures:
  - name: translated-package
    project:
      name: translated package
      knowledge_model_package_id: myorg:km:1.0.0
    events_file: events.json
""".strip()
        + "\n",
        encoding="utf-8",
    )

    config = load_workflow_config(config_path)

    assert config.baseline is None
    assert config.candidate.kind == "local_package"
    assert config.candidate.value == str(package_path.resolve())
    assert config.regression.assertion == "render_success"


def test_load_render_success_config_rejects_baseline(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Single-package validation must not disguise self-comparison as regression."""

    monkeypatch.setenv("DSW_API_URL", "http://localhost:3000/wizard-api")
    monkeypatch.setenv("DSW_API_KEY", "secret-token")
    config_path = tmp_path / "workflow.yml"
    config_path.write_text(
        """
api:
  url: ${DSW_API_URL}
  token: ${DSW_API_KEY}
subjects:
  baseline:
    kind: released_id
    value: myorg:template:1.0.0
  candidate:
    kind: released_id
    value: myorg:template:1.0.0
regression:
  assertion: render_success
  mode: document
  format_uuid: html-format-uuid
  output_dir: outputs
fixtures:
  - name: translated-package
    project_uuid: 11111111-1111-4111-8111-111111111111
    project_event_uuid: 22222222-2222-4222-8222-222222222222
""".strip()
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(WorkflowConfigError, match="baseline.*must be omitted"):
        load_workflow_config(config_path)


def test_load_equal_config_requires_baseline(tmp_path: Path, monkeypatch) -> None:
    """The default equality assertion should fail fast without a comparison subject."""

    monkeypatch.setenv("DSW_API_URL", "http://localhost:3000/wizard-api")
    monkeypatch.setenv("DSW_API_KEY", "secret-token")
    config_path = tmp_path / "workflow.yml"
    config_path.write_text(
        """
api:
  url: ${DSW_API_URL}
  token: ${DSW_API_KEY}
subjects:
  candidate:
    kind: draft_id
    value: myorg:candidate:1.0.0
regression:
  mode: preview
  format_uuid: html-format-uuid
  output_dir: outputs
fixtures:
  - name: sample
    project_uuid: 11111111-1111-4111-8111-111111111111
""".strip()
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(WorkflowConfigError, match="baseline.*required"):
        load_workflow_config(config_path)


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
