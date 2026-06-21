"""Key name resolution for the Vaydeer keypad protocol.

The Electron app stores keyboard assignments as Windows-style virtual key codes.  The
names below intentionally include several aliases so YAML can stay readable.
"""

from __future__ import annotations

import re

from .errors import ConfigError

KEYCODES: dict[str, int] = {
    "BACKSPACE": 8,
    "TAB": 9,
    "CLEAR": 12,
    "ENTER": 13,
    "RETURN": 13,
    "SHIFT": 16,
    "CTRL": 17,
    "CONTROL": 17,
    "ALT": 18,
    "PAUSE": 19,
    "PAUSE_BREAK": 19,
    "CAPS_LOCK": 20,
    "RIGHT_SHIFT": 21,
    "RSHIFT": 21,
    "RIGHT_CTRL": 22,
    "RCTRL": 22,
    "RIGHT_ALT": 23,
    "RALT": 23,
    "NUM_ENTER": 24,
    "ESC": 27,
    "ESCAPE": 27,
    "SPACE": 32,
    "PAGE_UP": 33,
    "PGUP": 33,
    "PAGE_DOWN": 34,
    "PGDN": 34,
    "END": 35,
    "HOME": 36,
    "LEFT": 37,
    "ARROW_LEFT": 37,
    "UP": 38,
    "ARROW_UP": 38,
    "RIGHT": 39,
    "ARROW_RIGHT": 39,
    "DOWN": 40,
    "ARROW_DOWN": 40,
    "PRINT_SCREEN": 44,
    "PRTSC": 44,
    "INSERT": 45,
    "INS": 45,
    "DELETE": 46,
    "DEL": 46,
    "LEFT_WINDOWS": 91,
    "LWIN": 91,
    "WIN": 91,
    "WINDOWS": 91,
    "META": 91,
    "RIGHT_WINDOWS": 92,
    "RWIN": 92,
    "CONTEXT_MENU": 93,
    "CONTEXTMENU": 93,
    "APP_MENU": 93,
    "MENU": 93,
    "NUM_LOCK": 144,
    "SCROLL_LOCK": 145,
    ";": 186,
    "SEMICOLON": 186,
    "=": 187,
    "EQUALS": 187,
    ",": 188,
    "COMMA": 188,
    "-": 189,
    "MINUS": 189,
    ".": 190,
    "PERIOD": 190,
    "/": 191,
    "SLASH": 191,
    "`": 192,
    "BACKTICK": 192,
    "[": 219,
    "LEFT_BRACKET": 219,
    "\\": 220,
    "BACKSLASH": 220,
    "]": 221,
    "RIGHT_BRACKET": 221,
    "'": 222,
    "QUOTE": 222,
    # Multimedia and browser VK codes. These are accepted as raw key assignments by
    # the same protocol path as ordinary keys.
    "BROWSER_BACK": 166,
    "BROWSER_FORWARD": 167,
    "BROWSER_REFRESH": 168,
    "BROWSER_STOP": 169,
    "BROWSER_SEARCH": 170,
    "BROWSER_FAVORITES": 171,
    "BROWSER_HOME": 172,
    "MEDIA_MUTE": 173,
    "VOLUME_MUTE": 173,
    "MEDIA_VOLUME_DOWN": 174,
    "VOLUME_DOWN": 174,
    "VOL_DOWN": 174,
    "MEDIA_VOLUME_UP": 175,
    "VOLUME_UP": 175,
    "VOL_UP": 175,
    "MEDIA_NEXT_TRACK": 176,
    "MEDIA_NEXT": 176,
    "MEDIA_PREVIOUS_TRACK": 177,
    "MEDIA_PREV": 177,
    "MEDIA_STOP": 178,
    "MEDIA_PLAY_PAUSE": 179,
    "PLAY_PAUSE": 179,
    "LAUNCH_MAIL": 180,
    "LAUNCH_MEDIA": 181,
    "LAUNCH_APP1": 182,
    "LAUNCH_APP2": 183,
}

KEYCODES.update({chr(code): code for code in range(ord("A"), ord("Z") + 1)})
KEYCODES.update({str(number): 48 + number for number in range(10)})
KEYCODES.update({f"F{number}": 111 + number for number in range(1, 25)})
KEYCODES.update({f"NUM_{number}": 96 + number for number in range(10)})
KEYCODES.update({f"NUM{number}": 96 + number for number in range(10)})
KEYCODES.update(
    {
        "NUM_MULTIPLY": 106,
        "NUM_STAR": 106,
        "NUM_PLUS": 107,
        "NUM_MINUS": 109,
        "NUM_DECIMAL": 110,
        "NUM_DEL": 110,
        "NUM_DIVIDE": 111,
        "NUM_SLASH": 111,
    }
)


def resolve_key_token(token: str | int) -> int:
    if isinstance(token, int):
        return validate_key_code(token)

    text = str(token).strip()
    if not text:
        raise ConfigError("Empty key token")

    if re.fullmatch(r"0x[0-9a-fA-F]+", text):
        return validate_key_code(int(text, 16))
    if re.fullmatch(r"\d+", text):
        return validate_key_code(int(text, 10))

    normalized = normalize_key_name(text)
    try:
        return KEYCODES[normalized]
    except KeyError as exc:
        raise ConfigError(f"Unknown key token {token!r}") from exc


def resolve_key_sequence(value: str | int | list[str | int]) -> list[int]:
    if isinstance(value, list):
        if not value:
            raise ConfigError("Key sequence lists must not be empty")
        return [resolve_key_token(item) for item in value]

    if isinstance(value, int):
        return [resolve_key_token(value)]

    text = str(value).strip()
    if not text:
        return []
    if "+" in text:
        return [resolve_key_token(part) for part in text.split("+")]
    return [resolve_key_token(text)]


def normalize_key_name(value: str) -> str:
    text = value.strip().upper()
    text = text.replace(" ", "_").replace("-", "_")
    text = text.replace("ARROWLEFT", "ARROW_LEFT")
    return text


def validate_key_code(value: int) -> int:
    if not 0 <= value <= 255:
        raise ConfigError(f"Key code must fit in one byte, got {value}")
    return value
