"""DSW preview runtime loading and template-version selection."""

from __future__ import annotations

from pathlib import Path

from ..yaml_config import YamlConfigError, load_yaml_file
from .errors import TranslationRepositoryError
from .models import DswPreviewRuntime
from .validation import optional_bool, reject_unknown_keys, required_str
from .versions import version_sort_key

DEFAULT_DSW_COMPAT_PATH = Path("config/dsw-compat.yml")
DSW_COMPAT_SCHEMA_VERSION = 1


def load_preview_runtimes(
    path: Path = DEFAULT_DSW_COMPAT_PATH,
) -> tuple[DswPreviewRuntime, ...]:
    """Load DSW preview runtimes from an explicit repository compatibility table."""

    try:
        payload = load_yaml_file(path)
    except (OSError, YamlConfigError) as exc:
        raise TranslationRepositoryError(str(exc)) from exc
    if not isinstance(payload, dict):
        raise TranslationRepositoryError(f"DSW compatibility config {path} must contain a mapping")
    reject_unknown_keys(payload, {"runtimes", "schema_version"}, "DSW compatibility config")
    if payload.get("schema_version") != DSW_COMPAT_SCHEMA_VERSION:
        raise TranslationRepositoryError(
            f"DSW compatibility config schema_version must be {DSW_COMPAT_SCHEMA_VERSION}"
        )

    runtime_payloads = payload.get("runtimes")
    if not isinstance(runtime_payloads, list) or not runtime_payloads:
        raise TranslationRepositoryError(
            f"DSW compatibility config {path} must define non-empty runtimes"
        )
    runtimes = tuple(_load_preview_runtime(item) for item in runtime_payloads)
    _validate_preview_runtimes(runtimes)
    return runtimes


def preview_runtime_for_version(
    version: str,
    *,
    runtimes: tuple[DswPreviewRuntime, ...] | None = None,
) -> DswPreviewRuntime:
    """Return the DSW runtime that can preview a template version tag."""

    for runtime in runtimes or load_preview_runtimes():
        if _version_in_runtime(version, runtime):
            return runtime
    raise TranslationRepositoryError(
        f"No DSW preview runtime configured for template version {version!r}"
    )


def preview_runtime_for_template(
    version: str,
    metamodel_version: str,
    *,
    runtimes: tuple[DswPreviewRuntime, ...] | None = None,
) -> DswPreviewRuntime:
    """Return the configured runtime for a concrete version/metamodel pair."""

    runtime = preview_runtime_for_version(version, runtimes=runtimes)
    if runtime.metamodel_version != metamodel_version:
        raise TranslationRepositoryError(
            f"Template {version} uses metamodelVersion {metamodel_version!r}, but "
            f"configured runtime {runtime.metamodel_key!r} expects "
            f"{runtime.metamodel_version!r}"
        )
    return runtime


def preview_runtime_matrix(
    path: Path = DEFAULT_DSW_COMPAT_PATH,
) -> list[dict[str, str]]:
    """Return GitHub Actions matrix rows for configured preview runtimes."""

    return [
        {
            "metamodel_key": runtime.metamodel_key,
            "metamodel_version": runtime.metamodel_version,
            "dsw_version": runtime.dsw_version,
            "tdk_version": runtime.tdk_version,
            "upstream_template_artifact_refs": runtime.upstream_template_artifact_refs,
            "run_preview_regression": str(runtime.run_preview_regression).lower(),
            "strict_project_preview": str(runtime.strict_project_preview).lower(),
        }
        for runtime in load_preview_runtimes(path)
    ]


def _load_preview_runtime(payload: object) -> DswPreviewRuntime:
    if not isinstance(payload, dict):
        raise TranslationRepositoryError("Each DSW preview runtime must be a mapping")
    reject_unknown_keys(
        payload,
        {
            "dsw_version",
            "max_version",
            "metamodel_key",
            "metamodel_version",
            "min_version",
            "run_preview_regression",
            "strict_project_preview",
            "tdk_version",
            "upstream_template_artifact_refs",
        },
        "DSW preview runtime",
    )
    max_version = payload.get("max_version")
    if max_version is not None and not isinstance(max_version, str):
        raise TranslationRepositoryError("Expected string or null at max_version")
    return DswPreviewRuntime(
        metamodel_key=required_str(payload, "metamodel_key"),
        metamodel_version=required_str(payload, "metamodel_version"),
        dsw_version=required_str(payload, "dsw_version"),
        tdk_version=required_str(payload, "tdk_version"),
        min_version=required_str(payload, "min_version"),
        max_version=max_version,
        upstream_template_artifact_refs=required_str(
            payload,
            "upstream_template_artifact_refs",
        ),
        run_preview_regression=optional_bool(
            payload,
            "run_preview_regression",
            default=False,
        ),
        strict_project_preview=optional_bool(
            payload,
            "strict_project_preview",
            default=False,
        ),
    )


def _validate_preview_runtimes(runtimes: tuple[DswPreviewRuntime, ...]) -> None:
    seen_keys: set[str] = set()
    seen_metamodels: set[str] = set()
    for runtime in runtimes:
        if runtime.metamodel_key in seen_keys:
            raise TranslationRepositoryError(
                f"Duplicate DSW preview runtime key {runtime.metamodel_key!r}"
            )
        seen_keys.add(runtime.metamodel_key)
        if runtime.metamodel_version in seen_metamodels:
            raise TranslationRepositoryError(
                "Each metamodelVersion should map to one CI runtime; "
                f"duplicate {runtime.metamodel_version!r}"
            )
        seen_metamodels.add(runtime.metamodel_version)
        version_sort_key(runtime.min_version)
        if runtime.max_version is not None and (
            version_sort_key(runtime.max_version) < version_sort_key(runtime.min_version)
        ):
            raise TranslationRepositoryError(
                f"Runtime {runtime.metamodel_key} has max_version before min_version"
            )


def _version_in_runtime(version: str, runtime: DswPreviewRuntime) -> bool:
    version_key = version_sort_key(version)
    if version_key < version_sort_key(runtime.min_version):
        return False
    return runtime.max_version is None or version_key <= version_sort_key(runtime.max_version)
