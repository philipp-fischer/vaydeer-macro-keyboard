"""YAML configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigError
from .hid_device import SUPPORTED_KEY_COUNT, SUPPORTED_KEY_COUNTS
from .keycodes import resolve_key_sequence


@dataclass(frozen=True)
class KeyAssignment:
    position: int
    name: str
    key_codes: tuple[int, ...]

    @property
    def key_index(self) -> int:
        return self.position - 1

    @property
    def is_empty(self) -> bool:
        return len(self.key_codes) == 0


@dataclass(frozen=True)
class LayerConfig:
    name: str
    key_count: int
    assignments: tuple[KeyAssignment, ...]

    def assignment_for_position(self, position: int) -> KeyAssignment:
        for assignment in self.assignments:
            if assignment.position == position:
                return assignment
        return KeyAssignment(position=position, name="", key_codes=())


def load_config(path: Path, *, expected_keys: int | None = None) -> LayerConfig:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"Unable to read config {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    return parse_config(raw, expected_keys=expected_keys)


def parse_config(raw: Any, *, expected_keys: int | None = None) -> LayerConfig:
    if not isinstance(raw, dict):
        raise ConfigError("Top-level YAML value must be a mapping")

    configured_key_count = int(raw.get("key_count", expected_keys or SUPPORTED_KEY_COUNT))
    if configured_key_count not in SUPPORTED_KEY_COUNTS:
        supported = ", ".join(str(count) for count in sorted(SUPPORTED_KEY_COUNTS))
        raise ConfigError(
            f"Config declares key_count={configured_key_count}, supported counts are: {supported}"
        )
    if expected_keys is not None and configured_key_count != expected_keys:
        raise ConfigError(
            f"Config declares key_count={configured_key_count}, but expected {expected_keys}"
        )

    raw_layer = raw.get("layer")
    if not isinstance(raw_layer, dict):
        raise ConfigError("Config must contain a 'layer' mapping")

    layer_name = str(raw_layer.get("name", "Default"))
    raw_keys = raw_layer.get("keys")
    if not isinstance(raw_keys, dict):
        raise ConfigError("Config layer must contain a 'keys' mapping")

    assignments: list[KeyAssignment] = []
    seen_positions: set[int] = set()
    for raw_position, raw_assignment in raw_keys.items():
        position = parse_position(raw_position)
        if not 1 <= position <= configured_key_count:
            raise ConfigError(
                f"Key position {position} is outside supported range 1..{configured_key_count}"
            )
        if position in seen_positions:
            raise ConfigError(f"Duplicate key position {position}")
        seen_positions.add(position)
        assignments.append(parse_assignment(position, raw_assignment))

    assignments.sort(key=lambda item: item.position)
    return LayerConfig(
        name=layer_name,
        key_count=configured_key_count,
        assignments=tuple(assignments),
    )


def parse_position(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Key position must be an integer, got {value!r}") from exc


def parse_assignment(position: int, value: Any) -> KeyAssignment:
    if is_empty_assignment(value):
        return KeyAssignment(position=position, name="", key_codes=())

    if isinstance(value, dict):
        if value.get("empty") is True:
            return KeyAssignment(position=position, name="", key_codes=())
        key_value = value.get("keys", value.get("key", value.get("raw")))
        if key_value is None:
            raise ConfigError(f"Key {position} mapping must contain 'key', 'keys', or 'raw'")
        key_codes = tuple(resolve_key_sequence(key_value))
        name = str(value.get("name") or default_assignment_name(key_value))
        return KeyAssignment(position=position, name=name, key_codes=key_codes)

    key_codes = tuple(resolve_key_sequence(value))
    if len(key_codes) == 1 and key_codes[0] == 0:
        return KeyAssignment(position=position, name="", key_codes=())
    return KeyAssignment(
        position=position,
        name=default_assignment_name(value),
        key_codes=key_codes,
    )


def is_empty_assignment(value: Any) -> bool:
    if value is None:
        return True
    if value == []:
        return True
    if isinstance(value, str) and value.strip().lower() in {"", "none", "empty", "disabled"}:
        return True
    return False


def default_assignment_name(value: Any) -> str:
    if isinstance(value, list):
        return "+".join(str(item) for item in value)
    return str(value)
