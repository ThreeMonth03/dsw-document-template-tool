"""Offline compatibility fingerprints for upstream template versions."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dsw_document_template_tool._template_transform.markers import GENERATED_BLOCK_PATTERN
from dsw_document_template_tool._translation_tree.document import (
    parse_sentence_text,
    parse_translation_document,
)
from dsw_document_template_tool._translation_tree.manifest import load_tree_manifest
from dsw_document_template_tool._translation_tree.placeholders import (
    extract_translator_placeholder_names,
)
from dsw_document_template_tool.translation_migration import version_sort_key

DEFAULT_SOURCE_LANG = "en"
DEFAULT_TARGET_LANG = "zh_Hant"
LEDGER_SCHEMA_VERSION = 1
REGRESSION_PLAN_SCHEMA_VERSION = 1


class CompatLedgerError(RuntimeError):
    """Raised when a compatibility ledger cannot be generated."""


@dataclass(frozen=True)
class VersionWorkspace:
    """Conventional generated workspace paths for one source template version."""

    version: str
    version_number: str
    version_root: Path
    workspace_name: str
    compact_dir: Path
    expanded_dir: Path
    regression_expanded_dir: Path
    translation_tree_dir: Path


def write_compat_ledger(
    *,
    workspace_root: Path,
    output_dir: Path,
    source_template_id: str,
    scaffold_root: Path | None = None,
    source_lang: str = DEFAULT_SOURCE_LANG,
    target_lang: str = DEFAULT_TARGET_LANG,
) -> list[dict[str, Any]]:
    """Write per-version JSON ledgers and a Markdown summary."""

    workspace_root = Path(workspace_root)
    output_dir = Path(output_dir)
    scaffold_root = Path(scaffold_root) if scaffold_root is not None else None
    entries = [
        build_version_entry(
            workspace=workspace,
            source_template_id=source_template_id,
            scaffold_root=scaffold_root,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        for workspace in iter_version_workspaces(
            workspace_root=workspace_root,
            source_template_id=source_template_id,
        )
    ]
    if not entries:
        raise CompatLedgerError(f"No version workspaces found under {workspace_root}")

    output_dir.mkdir(parents=True, exist_ok=True)
    stale_ledger_paths = [
        *output_dir.glob("v*.json"),
        output_dir / "index.json",
        output_dir / "regression-plan.json",
        output_dir / "regression-plan.md",
        output_dir / "summary.md",
    ]
    for stale_path in stale_ledger_paths:
        if stale_path.is_file():
            stale_path.unlink()
    for entry in entries:
        version = str(entry["version"])
        (output_dir / f"{version}.json").write_text(
            json.dumps(entry, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    (output_dir / "index.json").write_text(
        json.dumps(
            {
                "schema_version": LEDGER_SCHEMA_VERSION,
                "source_template_id": source_template_id,
                "versions": [entry["version"] for entry in entries],
                "entries": entries,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "summary.md").write_text(
        render_compat_ledger_summary(entries),
        encoding="utf-8",
    )
    regression_plan = build_regression_plan(entries)
    (output_dir / "regression-plan.json").write_text(
        json.dumps(regression_plan, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "regression-plan.md").write_text(
        render_regression_plan_summary(regression_plan),
        encoding="utf-8",
    )
    return entries


def build_version_entry(
    *,
    workspace: VersionWorkspace,
    source_template_id: str,
    scaffold_root: Path | None,
    source_lang: str,
    target_lang: str,
) -> dict[str, Any]:
    """Build one machine-readable compatibility fingerprint."""

    template_payload = _read_json(workspace.compact_dir / "template.json")
    upstream_payload = _read_optional_json(workspace.version_root / "upstream.json")
    return {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "source_template_id": source_template_id,
        "version": workspace.version,
        "version_number": workspace.version_number,
        "upstream": upstream_payload,
        "template": {
            "organization_id": template_payload.get("organizationId"),
            "template_id": template_payload.get("templateId"),
            "version": template_payload.get("version"),
            "metamodel_version": str(template_payload.get("metamodelVersion", "")),
        },
        "compact": collect_file_tree_stats(workspace.compact_dir),
        "expanded": collect_expanded_tree_stats(workspace.expanded_dir),
        "regression_expanded": collect_expanded_tree_stats(workspace.regression_expanded_dir),
        "translation_tree": collect_translation_tree_stats(
            workspace.translation_tree_dir,
            source_lang=source_lang,
            target_lang=target_lang,
        ),
        "scaffold_packages": collect_scaffold_packages(
            scaffold_root=scaffold_root,
            version=workspace.version,
        ),
    }


def iter_version_workspaces(
    *,
    workspace_root: Path,
    source_template_id: str,
) -> list[VersionWorkspace]:
    """Return generated version workspace paths sorted by semantic version."""

    workspaces: list[VersionWorkspace] = []
    if not workspace_root.is_dir():
        return workspaces
    version_roots = [
        path for path in workspace_root.iterdir() if path.is_dir() and path.name.startswith("v")
    ]
    for version_root in sorted(version_roots, key=lambda path: version_sort_key(path.name)):
        version = version_root.name
        version_number = version.removeprefix("v")
        workspace_name = f"{source_template_id}-{version_number}"
        workspaces.append(
            VersionWorkspace(
                version=version,
                version_number=version_number,
                version_root=version_root,
                workspace_name=workspace_name,
                compact_dir=version_root / "compact" / workspace_name,
                expanded_dir=version_root / "expanded" / workspace_name,
                regression_expanded_dir=version_root / "expanded-regression" / workspace_name,
                translation_tree_dir=version_root / "translation" / workspace_name,
            )
        )
    return workspaces


def collect_file_tree_stats(root: Path) -> dict[str, Any]:
    """Collect stable file-level stats for a generated workspace."""

    _require_dir(root)
    files = sorted(path for path in root.rglob("*") if path.is_file())
    relative_files = [path.relative_to(root).as_posix() for path in files]
    return {
        "exists": True,
        "file_count": len(files),
        "jinja_file_count": sum(1 for path in relative_files if path.endswith(".j2")),
        "static_file_count": sum(1 for path in relative_files if not path.endswith(".j2")),
        "total_bytes": sum(path.stat().st_size for path in files),
        "tree_digest": digest_file_tree(root),
        "files": relative_files,
    }


def collect_expanded_tree_stats(root: Path) -> dict[str, Any]:
    """Collect expanded-template stats, including generated translation wrappers."""

    stats = collect_file_tree_stats(root)
    block_counts_by_file: dict[str, int] = {}
    for path in sorted(root.rglob("*.j2")):
        relative_path = path.relative_to(root).as_posix()
        block_count = len(GENERATED_BLOCK_PATTERN.findall(path.read_text(encoding="utf-8")))
        if block_count:
            block_counts_by_file[relative_path] = block_count
    stats["generated_block_count"] = sum(block_counts_by_file.values())
    stats["generated_block_files"] = block_counts_by_file
    return stats


def collect_translation_tree_stats(
    tree_dir: Path,
    *,
    source_lang: str,
    target_lang: str,
) -> dict[str, Any]:
    """Collect unit and placeholder stats from a translator-facing tree."""

    _require_dir(tree_dir)
    manifest = load_tree_manifest(tree_dir)
    units = manifest.get("units")
    if not isinstance(units, list):
        raise CompatLedgerError(f"Invalid translation-tree manifest at {tree_dir}")

    source_files: Counter[str] = Counter()
    wrappers: set[tuple[str, str]] = set()
    placeholder_counts: Counter[str] = Counter()
    translated_units = 0
    units_with_placeholders = 0
    for unit in units:
        if not isinstance(unit, dict):
            raise CompatLedgerError(f"Invalid manifest unit in {tree_dir}")
        source_file = _required_str(unit, "source_file", tree_dir)
        wrapper_key = _required_str(unit, "wrapper_key", tree_dir)
        document_path = tree_dir / _required_str(unit, "document_path", tree_dir)
        source_files[source_file] += 1
        wrappers.add((source_file, wrapper_key))
        sentence = parse_sentence_text(document_path=document_path, source_lang=source_lang)
        translation = parse_translation_document(
            document_path=document_path,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        if translation.strip():
            translated_units += 1
        names = extract_translator_placeholder_names(sentence)
        if names:
            units_with_placeholders += 1
            placeholder_counts.update(names)

    return {
        "exists": True,
        "tree_digest": digest_file_tree(tree_dir),
        "manifest_version": manifest.get("version"),
        "unit_count": len(units),
        "translated_unit_count": translated_units,
        "untranslated_unit_count": len(units) - translated_units,
        "source_file_count": len(source_files),
        "wrapper_count": len(wrappers),
        "units_with_placeholders": units_with_placeholders,
        "placeholder_count": sum(placeholder_counts.values()),
        "placeholder_inventory": dict(sorted(placeholder_counts.items())),
        "units_by_source_file": dict(sorted(source_files.items())),
    }


def collect_scaffold_packages(
    *,
    scaffold_root: Path | None,
    version: str,
) -> list[dict[str, Any]]:
    """Collect package metadata for generated clean scaffold zip files."""

    if scaffold_root is None:
        return []
    version_root = scaffold_root / version
    if not version_root.is_dir():
        return []
    packages = sorted(version_root.glob("*/scaffold/*.zip"))
    return [
        {
            "path": path.as_posix(),
            "bytes": path.stat().st_size,
            "sha256": digest_file(path),
        }
        for path in packages
    ]


def render_compat_ledger_summary(entries: list[dict[str, Any]]) -> str:
    """Render a maintainer-facing compatibility summary."""

    lines = [
        "# Upstream Compatibility Ledger",
        "",
        "This report is generated from offline compact/expanded/translation-tree",
        "artifacts. It does not prove DSW runtime rendering; use it to spot",
        "cross-version structure drift before spending time on full render",
        "regression.",
        "",
        "| Version | Metamodel | Expanded files | Blocks | Units | Placeholders | Package |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for entry in entries:
        expanded = entry["expanded"]
        tree = entry["translation_tree"]
        packages = entry["scaffold_packages"]
        package_label = f"{len(packages)} zip" if packages else "missing"
        lines.append(
            "| {version} | {metamodel} | {files} | {blocks} | {units} | "
            "{placeholders} | {package} |".format(
                version=entry["version"],
                metamodel=entry["template"]["metamodel_version"],
                files=expanded["file_count"],
                blocks=expanded["generated_block_count"],
                units=tree["unit_count"],
                placeholders=tree["placeholder_count"],
                package=package_label,
            )
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- `Blocks` counts generated translation wrapper blocks in expanded Jinja files.")
    lines.append("- `Units` counts translator-facing `translation.md` files.")
    lines.append("- `Placeholders` counts translator-visible placeholders in source sentences.")
    lines.append("- Full DSW preview/PDF behavior is still covered by render regression jobs.")
    return "\n".join(lines) + "\n"


def build_regression_plan(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Recommend high-value DSW regression candidates from ledger entries."""

    sorted_entries = sorted(entries, key=lambda entry: version_sort_key(str(entry["version"])))
    latest_by_metamodel = {
        _metamodel_version(entry): str(entry["version"]) for entry in sorted_entries
    }
    previous_signature_by_metamodel: dict[str, dict[str, Any]] = {}
    candidates: list[dict[str, Any]] = []
    for entry in sorted_entries:
        metamodel_version = _metamodel_version(entry)
        version = str(entry["version"])
        signature = structure_signature(entry)
        reasons: list[str] = []

        previous_signature = previous_signature_by_metamodel.get(metamodel_version)
        if previous_signature is None:
            reasons.append("first_for_metamodel")
        elif signature != previous_signature:
            reasons.append("structure_signature_changed")

        if version == latest_by_metamodel[metamodel_version]:
            reasons.append("latest_for_metamodel")

        if not entry.get("scaffold_packages"):
            reasons.append("missing_scaffold_package")

        candidates.append(
            {
                "version": version,
                "metamodel_version": metamodel_version,
                "recommended": bool(reasons),
                "reasons": reasons,
                "structure_signature_digest": digest_json(signature),
            }
        )
        previous_signature_by_metamodel[metamodel_version] = signature

    return {
        "schema_version": REGRESSION_PLAN_SCHEMA_VERSION,
        "recommended_versions": [
            candidate["version"] for candidate in candidates if candidate["recommended"]
        ],
        "candidates": candidates,
    }


def structure_signature(entry: dict[str, Any]) -> dict[str, Any]:
    """Return the low-noise expanded/tree structure signature for one version."""

    expanded = entry["expanded"]
    regression_expanded = entry["regression_expanded"]
    tree = entry["translation_tree"]
    return {
        "expanded": {
            "file_count": expanded["file_count"],
            "generated_block_count": expanded["generated_block_count"],
            "generated_block_files": expanded["generated_block_files"],
            "jinja_file_count": expanded["jinja_file_count"],
        },
        "regression_expanded": {
            "file_count": regression_expanded["file_count"],
            "generated_block_count": regression_expanded["generated_block_count"],
            "generated_block_files": regression_expanded["generated_block_files"],
            "jinja_file_count": regression_expanded["jinja_file_count"],
        },
        "translation_tree": {
            "manifest_version": tree["manifest_version"],
            "placeholder_inventory": tree["placeholder_inventory"],
            "source_file_count": tree["source_file_count"],
            "unit_count": tree["unit_count"],
            "units_by_source_file": tree["units_by_source_file"],
            "units_with_placeholders": tree["units_with_placeholders"],
            "wrapper_count": tree["wrapper_count"],
        },
    }


def render_regression_plan_summary(plan: dict[str, Any]) -> str:
    """Render a maintainer-facing regression candidate plan."""

    lines = [
        "# Recommended Regression Plan",
        "",
        "This plan is generated from the offline compatibility ledger. It selects",
        "versions that give good coverage without blindly running full DSW",
        "regression for every upstream tag.",
        "",
        "| Version | Metamodel | Recommended | Reasons | Signature |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for candidate in plan["candidates"]:
        reasons = ", ".join(candidate["reasons"]) if candidate["reasons"] else "-"
        lines.append(
            "| {version} | {metamodel} | {recommended} | {reasons} | `{digest}` |".format(
                version=candidate["version"],
                metamodel=candidate["metamodel_version"],
                recommended="yes" if candidate["recommended"] else "no",
                reasons=reasons,
                digest=candidate["structure_signature_digest"][:12],
            )
        )
    lines.append("")
    lines.append("## Policy")
    lines.append("")
    lines.append("- Always include the first and latest version for each metamodel runtime.")
    lines.append(
        "- Include any version whose expanded/tree structure signature changed "
        "within the same metamodel."
    )
    lines.append("- Treat missing scaffold packages as a packaging issue to investigate.")
    lines.append(
        "- This is a planning layer; full DSW render regression remains the final behavior check."
    )
    return "\n".join(lines) + "\n"


def digest_file_tree(root: Path) -> str:
    """Return a deterministic digest for paths and contents below ``root``."""

    digest = hashlib.sha256()
    for path in sorted(path for path in root.rglob("*") if path.is_file()):
        relative_path = path.relative_to(root).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(digest_file(path).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def digest_json(payload: Any) -> str:
    """Return a deterministic SHA-256 digest for JSON-compatible data."""

    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def digest_file(path: Path) -> str:
    """Return a SHA-256 digest for one file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CompatLedgerError(f"Missing required JSON file at {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise CompatLedgerError(f"Expected JSON object at {path}")
    return payload


def _read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return _read_json(path)


def _require_dir(path: Path) -> None:
    if not path.is_dir():
        raise CompatLedgerError(f"Missing required directory at {path}")


def _required_str(payload: dict[str, Any], key: str, tree_dir: Path) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise CompatLedgerError(f"Invalid manifest field {key!r} in {tree_dir}")
    return value


def _metamodel_version(entry: dict[str, Any]) -> str:
    metamodel_version = entry.get("template", {}).get("metamodel_version")
    if not isinstance(metamodel_version, str) or not metamodel_version:
        raise CompatLedgerError(f"Ledger entry has no metamodel version: {entry!r}")
    return metamodel_version
