from __future__ import annotations

import pytest

from vaydeer_keypad.config import parse_config
from vaydeer_keypad.errors import ConfigError
from vaydeer_keypad.keycodes import resolve_key_token


def test_parse_single_layer_keyboard_config() -> None:
    config = parse_config(
        {
            "key_count": 9,
            "layer": {
                "name": "Shortcuts",
                "keys": {
                    1: "A",
                    2: "CTRL+C",
                    3: {"name": "Play", "key": "MEDIA_PLAY_PAUSE"},
                    4: ["ALT", "TAB"],
                    5: 0,
                },
            },
        }
    )

    assert config.name == "Shortcuts"
    assert config.key_count == 9
    assert config.assignment_for_position(1).key_codes == (65,)
    assert config.assignment_for_position(2).key_codes == (17, 67)
    assert config.assignment_for_position(3).name == "Play"
    assert config.assignment_for_position(3).key_codes == (179,)
    assert config.assignment_for_position(4).key_codes == (18, 9)
    assert config.assignment_for_position(5).is_empty
    assert config.assignment_for_position(9).is_empty


def test_rejects_out_of_range_key_position() -> None:
    with pytest.raises(ConfigError, match="outside supported range"):
        parse_config({"layer": {"name": "Bad", "keys": {10: "A"}}})


def test_supports_4_key_config() -> None:
    config = parse_config({"key_count": 4, "layer": {"name": "Four", "keys": {1: "A", 4: "D"}}})

    assert config.key_count == 4
    assert config.assignment_for_position(4).key_codes == (68,)


def test_rejects_unsupported_key_count() -> None:
    with pytest.raises(ConfigError, match="supported counts"):
        parse_config({"key_count": 5, "layer": {"name": "Bad", "keys": {1: "A"}}})


def test_rejects_key_count_that_does_not_match_expected() -> None:
    with pytest.raises(ConfigError, match="but expected 9"):
        parse_config({"key_count": 4, "layer": {"name": "Bad", "keys": {1: "A"}}}, expected_keys=9)


def test_rejects_unknown_key_name() -> None:
    with pytest.raises(ConfigError, match="Unknown key token"):
        parse_config({"layer": {"name": "Bad", "keys": {1: "NOT_A_REAL_KEY"}}})


def test_supports_vendor_function_key_range() -> None:
    assert resolve_key_token("F1") == 112
    assert resolve_key_token("F12") == 123
    assert resolve_key_token("F13") == 124
    assert resolve_key_token("F24") == 135
