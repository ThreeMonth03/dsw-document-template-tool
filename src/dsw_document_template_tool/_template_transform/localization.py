"""Local reversible patches applied to expanded Science Europe templates."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

CJK_FONT_PATCH_NAME = "cjk_font_face"
ZH_HANT_ALLOWED_PACKAGE_PATCH_NAME = "zh_hant_allowed_package"
CJK_FONT_SOURCE_PATH = Path("assets/fonts/NotoSansTC-Variable.ttf")
CJK_FONT_TEMPLATE_PATH = Path("src/fonts/NotoSansTC-Variable.ttf")
CJK_FONT_PDF_FORMAT_UUID = "68c26e34-5e77-4e15-9bf7-06ff92582257"
CJK_FONT_FAMILY_ORIGINAL = '"Open Sans", sans-serif'
CJK_FONT_FAMILY_PATCHED = (
    f'{{% if dsw_document_format_uuid == "{CJK_FONT_PDF_FORMAT_UUID}" %}}'
    '"DSW Noto Sans TC", '
    "{% endif %}"
    f"{CJK_FONT_FAMILY_ORIGINAL}"
)
CJK_FONT_CSS_START = "/* DSW Document Template Tool CJK font fallback:start */"
CJK_FONT_CSS_END = "/* DSW Document Template Tool CJK font fallback:end */"
CJK_FONT_CSS = f"""{{% set dsw_document_format_uuid = ctx.document.formatUuid|default("") -%}}
{{% if dsw_document_format_uuid == "{CJK_FONT_PDF_FORMAT_UUID}" -%}}
{{% set dsw_noto_sans_tc_font = assets("{CJK_FONT_TEMPLATE_PATH.as_posix()}") -%}}
{{% if dsw_noto_sans_tc_font -%}}
{CJK_FONT_CSS_START}
@font-face {{
  font-family: "DSW Noto Sans TC";
  src: url("data:font/ttf;base64,{{{{ dsw_noto_sans_tc_font.data_base64 }}}}") format("truetype");
  font-weight: 400;
  font-style: normal;
  unicode-range: U+2E80-2EFF, U+2F00-2FDF, U+3000-303F, U+3100-312F,
    U+31C0-31EF, U+3200-32FF, U+3400-4DBF, U+4E00-9FFF,
    U+F900-FAFF, U+FE10-FE1F, U+FE30-FE4F, U+FF00-FFEF;
}}

@font-face {{
  font-family: "DSW Noto Sans TC";
  src: url("data:font/ttf;base64,{{{{ dsw_noto_sans_tc_font.data_base64 }}}}") format("truetype");
  font-weight: 700;
  font-style: normal;
  unicode-range: U+2E80-2EFF, U+2F00-2FDF, U+3000-303F, U+3100-312F,
    U+31C0-31EF, U+3200-32FF, U+3400-4DBF, U+4E00-9FFF,
    U+F900-FAFF, U+FE10-FE1F, U+FE30-FE4F, U+FF00-FFEF;
}}
{CJK_FONT_CSS_END}
{{% endif -%}}
{{% endif -%}}
"""
ZH_HANT_ALLOWED_PACKAGE_RULE = {
    "orgId": "dsw",
    "kmId": "root-zh-hant",
    "minVersion": "2.7.0",
    "maxVersion": None,
}


class LocalizationPatchError(RuntimeError):
    """Raised when a local template patch cannot be applied."""


def build_post_expand_patch_state(*, output_dir: Path) -> dict[str, object]:
    """Capture source formatting details needed for patch reversal."""

    template_json_path = output_dir / "template.json"
    return {
        "template_json_trailing_newline": (
            template_json_path.read_bytes().endswith(b"\n")
            if template_json_path.is_file()
            else None
        )
    }


def apply_post_expand_patches(*, output_dir: Path) -> list[str]:
    """Apply deterministic local template patches after reversible expansion."""

    patches: list[str] = []
    if _patch_zh_hant_allowed_package(output_dir=output_dir):
        patches.append(ZH_HANT_ALLOWED_PACKAGE_PATCH_NAME)
    if _patch_cjk_font_face(output_dir=output_dir):
        patches.append(CJK_FONT_PATCH_NAME)
    return patches


def revert_post_expand_patches(
    *,
    output_dir: Path,
    patches: object,
    patch_state: object,
) -> None:
    """Remove local-only patches when compacting back to the upstream template."""

    if not isinstance(patches, list):
        return
    state = patch_state if isinstance(patch_state, dict) else {}
    patch_names = {patch for patch in patches if isinstance(patch, str)}
    if ZH_HANT_ALLOWED_PACKAGE_PATCH_NAME in patch_names:
        _remove_zh_hant_allowed_package(
            output_dir=output_dir,
            trailing_newline=state.get("template_json_trailing_newline"),
        )
    if CJK_FONT_PATCH_NAME in patch_names:
        _remove_cjk_font_face(output_dir=output_dir)


def _patch_zh_hant_allowed_package(*, output_dir: Path) -> bool:
    template_json_path = output_dir / "template.json"
    if not template_json_path.is_file():
        return False
    payload = json.loads(template_json_path.read_text(encoding="utf-8"))
    allowed_packages = payload.get("allowedPackages")
    if not isinstance(allowed_packages, list):
        return False
    if not any(
        _is_allowed_package_rule(rule, org_id="dsw", km_id="root") for rule in allowed_packages
    ):
        return False
    if any(
        _is_allowed_package_rule(rule, org_id="dsw", km_id="root-zh-hant")
        for rule in allowed_packages
    ):
        return False

    allowed_packages.append(dict(ZH_HANT_ALLOWED_PACKAGE_RULE))
    template_json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return True


def _remove_zh_hant_allowed_package(*, output_dir: Path, trailing_newline: object) -> None:
    template_json_path = output_dir / "template.json"
    if not template_json_path.is_file():
        return
    payload = json.loads(template_json_path.read_text(encoding="utf-8"))
    allowed_packages = payload.get("allowedPackages")
    if not isinstance(allowed_packages, list):
        return
    filtered_packages = [
        rule
        for rule in allowed_packages
        if not _is_exact_allowed_package_rule(rule, ZH_HANT_ALLOWED_PACKAGE_RULE)
    ]
    if len(filtered_packages) == len(allowed_packages):
        return
    payload["allowedPackages"] = filtered_packages
    suffix = "\n" if trailing_newline is not False else ""
    template_json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + suffix,
        encoding="utf-8",
    )


def _patch_cjk_font_face(*, output_dir: Path) -> bool:
    style_path = output_dir / "src" / "style.css"
    if not style_path.is_file():
        return False
    style_text = style_path.read_text(encoding="utf-8")
    if CJK_FONT_CSS_START in style_text:
        return False

    font_source_path = _repo_root() / CJK_FONT_SOURCE_PATH
    if not font_source_path.is_file():
        raise LocalizationPatchError(
            f"Cannot apply CJK font patch because the font asset is missing: {font_source_path}"
        )

    font_destination_path = output_dir / CJK_FONT_TEMPLATE_PATH
    font_destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(font_source_path, font_destination_path)
    style_text = style_text.replace(CJK_FONT_FAMILY_ORIGINAL, CJK_FONT_FAMILY_PATCHED)
    style_path.write_text(
        _insert_css_after_initial_imports(style_text, CJK_FONT_CSS),
        encoding="utf-8",
    )
    return True


def _remove_cjk_font_face(*, output_dir: Path) -> None:
    style_path = output_dir / "src" / "style.css"
    if style_path.is_file():
        style_text = style_path.read_text(encoding="utf-8")
        style_text = re.sub(
            rf"\{{%\s*set dsw_document_format_uuid\b[\s\S]*?"
            rf"{re.escape(CJK_FONT_CSS_END)}\s*"
            rf"\{{%\s*endif\s*-?%\}}\s*"
            rf"\{{%\s*endif\s*-?%\}}\s*",
            "",
            style_text,
            count=1,
            flags=re.DOTALL,
        )
        style_text = re.sub(
            rf"{re.escape(CJK_FONT_CSS_START)}.*?{re.escape(CJK_FONT_CSS_END)}\n*",
            "",
            style_text,
            count=1,
            flags=re.DOTALL,
        )
        style_text = style_text.replace(CJK_FONT_FAMILY_PATCHED, CJK_FONT_FAMILY_ORIGINAL)
        style_path.write_text(style_text, encoding="utf-8")

    font_destination_path = output_dir / CJK_FONT_TEMPLATE_PATH
    font_destination_path.unlink(missing_ok=True)
    fonts_dir = font_destination_path.parent
    if fonts_dir.is_dir() and not any(fonts_dir.iterdir()):
        fonts_dir.rmdir()


def _is_allowed_package_rule(rule: object, *, org_id: str, km_id: str) -> bool:
    return isinstance(rule, dict) and rule.get("orgId") == org_id and rule.get("kmId") == km_id


def _is_exact_allowed_package_rule(rule: object, expected: dict[str, object]) -> bool:
    return (
        isinstance(rule, dict)
        and rule.get("orgId") == expected["orgId"]
        and rule.get("kmId") == expected["kmId"]
        and rule.get("minVersion") == expected["minVersion"]
        and rule.get("maxVersion") == expected["maxVersion"]
    )


def _insert_css_after_initial_imports(style_text: str, css_block: str) -> str:
    lines = style_text.splitlines(keepends=True)
    insert_at = 0
    while insert_at < len(lines):
        stripped = lines[insert_at].strip()
        if stripped.startswith("@charset") or stripped.startswith("@import"):
            insert_at += 1
            continue
        if not stripped:
            insert_at += 1
            continue
        break

    return "".join([*lines[:insert_at], css_block, "\n", *lines[insert_at:]])


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]
