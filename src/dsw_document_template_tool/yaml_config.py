"""Strict YAML loading for repository configuration files."""

from __future__ import annotations

from pathlib import Path

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode


class YamlConfigError(ValueError):
    """Raised when a YAML config is malformed or contains duplicate keys."""


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects ambiguous duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader,
    node: MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    loader.flatten_mapping(node)
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def load_yaml_file(path: str | Path) -> object:
    """Load a YAML file while rejecting duplicate mapping keys."""

    config_path = Path(path)
    return load_yaml_text(
        config_path.read_text(encoding="utf-8"),
        source=str(config_path),
    )


def load_yaml_text(text: str, *, source: str = "YAML input") -> object:
    """Load YAML text while reporting its source in validation errors."""

    try:
        return yaml.load(text, Loader=_UniqueKeySafeLoader)
    except yaml.YAMLError as exc:
        raise YamlConfigError(f"Invalid YAML in {source}: {exc}") from exc
