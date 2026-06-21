from __future__ import annotations

from vaydeer_keypad.key_tester import KeyEventInfo, format_key_event


def test_format_key_event_includes_keysym_keycode_and_modifiers() -> None:
    info = KeyEventInfo(
        event_type="press",
        keysym="F13",
        keycode=124,
        char="",
        state=0x0005,
    )

    assert format_key_event(info) == (
        "press | keysym=F13 | keycode=124 | modifiers=Shift+Ctrl | state=0x0005"
    )


def test_format_key_event_includes_printable_char() -> None:
    info = KeyEventInfo(
        event_type="press",
        keysym="a",
        keycode=65,
        char="a",
        state=0,
    )

    assert format_key_event(info) == "press | keysym=a | keycode=65 | char='a' | state=0x0000"
