#!/usr/bin/env python3
"""Stage generated files as GitHub Release assets.

The script is deliberately GitHub-agnostic: it copies or archives selected
files into one output directory, writes SHA256SUMS, and creates release notes.
Workflow YAML can then use `gh release upload --clobber` for the actual upload.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AssetSpec:
    """One source path and its staged file name."""

    source: Path
    name: str
    optional: bool = False


def parse_asset_spec(value: str, *, optional: bool = False) -> AssetSpec:
    """Parse SRC or SRC=NAME into an asset spec."""

    source_text, separator, name = value.partition("=")
    source = Path(source_text)
    if not source_text:
        raise argparse.ArgumentTypeError("asset source must not be empty")
    if separator and not name:
        raise argparse.ArgumentTypeError("asset destination name must not be empty")
    return AssetSpec(source=source, name=name or source.name, optional=optional)


def parse_args() -> argparse.Namespace:
    """Return command-line options."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--notes-title", required=True)
    parser.add_argument(
        "--notes-body",
        action="append",
        default=[],
        help="Additional markdown paragraph for release notes. May be repeated.",
    )
    parser.add_argument(
        "--asset",
        action="append",
        default=[],
        type=lambda value: parse_asset_spec(value, optional=False),
        help="Required file to copy, as SRC or SRC=NAME. May be repeated.",
    )
    parser.add_argument(
        "--optional-asset",
        action="append",
        default=[],
        type=lambda value: parse_asset_spec(value, optional=True),
        help="Optional file to copy when present, as SRC or SRC=NAME. May be repeated.",
    )
    parser.add_argument(
        "--archive-dir",
        action="append",
        default=[],
        type=lambda value: parse_asset_spec(value, optional=False),
        help="Required directory to zip, as SRC=NAME.zip. May be repeated.",
    )
    parser.add_argument(
        "--optional-archive-dir",
        action="append",
        default=[],
        type=lambda value: parse_asset_spec(value, optional=True),
        help="Optional directory to zip when present, as SRC=NAME.zip. May be repeated.",
    )
    parser.add_argument("--notes-file", default="release-notes.md")
    parser.add_argument("--checksums-file", default="SHA256SUMS")
    return parser.parse_args()


def main() -> int:
    """Stage release assets."""

    args = parse_args()
    output_dir: Path = args.output_dir
    reset_output_dir(output_dir)

    staged_files: list[Path] = []
    for spec in [*args.asset, *args.optional_asset]:
        staged = stage_file(spec, output_dir)
        if staged is not None:
            staged_files.append(staged)

    for spec in [*args.archive_dir, *args.optional_archive_dir]:
        staged = stage_directory_archive(spec, output_dir)
        if staged is not None:
            staged_files.append(staged)

    if not staged_files:
        raise SystemExit("No release assets were staged")

    checksums_path = output_dir / args.checksums_file
    write_checksums(checksums_path, staged_files)
    notes_path = output_dir / args.notes_file
    write_release_notes(
        notes_path,
        title=args.notes_title,
        body=args.notes_body,
        staged_files=[*staged_files, checksums_path],
        checksums_file=checksums_path.name,
    )

    print(f"Staged {len(staged_files)} release assets in {output_dir}")
    return 0


def reset_output_dir(output_dir: Path) -> None:
    """Create a fresh output directory."""

    if output_dir.exists():
        if not output_dir.is_dir():
            raise SystemExit(f"Output path exists and is not a directory: {output_dir}")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)


def stage_file(spec: AssetSpec, output_dir: Path) -> Path | None:
    """Copy one file into the release asset directory."""

    if not spec.source.is_file():
        if spec.optional:
            return None
        raise SystemExit(f"Required release asset file is missing: {spec.source}")

    destination = safe_destination(output_dir, spec.name)
    shutil.copy2(spec.source, destination)
    return destination


def stage_directory_archive(spec: AssetSpec, output_dir: Path) -> Path | None:
    """Zip one directory into the release asset directory."""

    if not spec.source.is_dir():
        if spec.optional:
            return None
        raise SystemExit(f"Required release asset directory is missing: {spec.source}")
    if not spec.name.endswith(".zip"):
        raise SystemExit(f"Directory archive asset name must end with .zip: {spec.name}")

    destination = safe_destination(output_dir, spec.name)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        base = spec.source.parent
        for path in sorted(spec.source.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(base))
    return destination


def safe_destination(output_dir: Path, name: str) -> Path:
    """Return a destination path that cannot escape output_dir."""

    if Path(name).name != name:
        raise SystemExit(f"Release asset name must be a plain file name: {name}")
    destination = output_dir / name
    if destination.exists():
        raise SystemExit(f"Duplicate staged release asset name: {name}")
    return destination


def write_checksums(path: Path, staged_files: list[Path]) -> None:
    """Write SHA256SUMS for staged files."""

    lines = [
        f"{sha256_file(staged)}  {staged.name}"
        for staged in sorted(staged_files, key=lambda item: item.name)
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of one file."""

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_release_notes(
    path: Path,
    *,
    title: str,
    body: list[str],
    staged_files: list[Path],
    checksums_file: str,
) -> None:
    """Write concise markdown release notes."""

    lines = [f"# {title}", ""]
    for paragraph in body:
        stripped = paragraph.strip()
        if stripped:
            lines.extend([stripped, ""])
    lines.extend(["## Assets", ""])
    for staged in sorted(staged_files, key=lambda item: item.name):
        lines.append(f"- `{staged.name}`")
    lines.extend(["", "## Integrity", "", f"SHA-256 checksums are in `{checksums_file}`.", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
