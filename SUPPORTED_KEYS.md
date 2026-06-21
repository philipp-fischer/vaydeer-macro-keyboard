# Supported Native Keys

This file lists the native single-key names accepted by the YAML flasher. These
are byte-sized key codes written as normal key assignments (`keyType = 0`) or as
members of key combinations (`keyType = 1`).

This list intentionally excludes mouse actions, macros, text output, app/file/URL
triggers, firmware update commands, and Vaydeer-specific action types.

Use any listed canonical name or alias in YAML. Raw integer key codes are still
accepted for experiments, but only the named keys below are treated as supported.

## Letters

| Key | Decimal | Hex |
| --- | ---: | ---: |
| `A` | 65 | `0x41` |
| `B` | 66 | `0x42` |
| `C` | 67 | `0x43` |
| `D` | 68 | `0x44` |
| `E` | 69 | `0x45` |
| `F` | 70 | `0x46` |
| `G` | 71 | `0x47` |
| `H` | 72 | `0x48` |
| `I` | 73 | `0x49` |
| `J` | 74 | `0x4A` |
| `K` | 75 | `0x4B` |
| `L` | 76 | `0x4C` |
| `M` | 77 | `0x4D` |
| `N` | 78 | `0x4E` |
| `O` | 79 | `0x4F` |
| `P` | 80 | `0x50` |
| `Q` | 81 | `0x51` |
| `R` | 82 | `0x52` |
| `S` | 83 | `0x53` |
| `T` | 84 | `0x54` |
| `U` | 85 | `0x55` |
| `V` | 86 | `0x56` |
| `W` | 87 | `0x57` |
| `X` | 88 | `0x58` |
| `Y` | 89 | `0x59` |
| `Z` | 90 | `0x5A` |

## Number Row

| Key | Decimal | Hex |
| --- | ---: | ---: |
| `0` | 48 | `0x30` |
| `1` | 49 | `0x31` |
| `2` | 50 | `0x32` |
| `3` | 51 | `0x33` |
| `4` | 52 | `0x34` |
| `5` | 53 | `0x35` |
| `6` | 54 | `0x36` |
| `7` | 55 | `0x37` |
| `8` | 56 | `0x38` |
| `9` | 57 | `0x39` |

## Function Keys

Stock firmware exposes `F1` through `F12`. The additive patched firmware documented
in `FIRMWARE.md` extends the table and HID descriptor so `F13` through `F24` work
as native hardware-emitted keys too.

| Key | Decimal | Hex |
| --- | ---: | ---: |
| `F1` | 112 | `0x70` |
| `F2` | 113 | `0x71` |
| `F3` | 114 | `0x72` |
| `F4` | 115 | `0x73` |
| `F5` | 116 | `0x74` |
| `F6` | 117 | `0x75` |
| `F7` | 118 | `0x76` |
| `F8` | 119 | `0x77` |
| `F9` | 120 | `0x78` |
| `F10` | 121 | `0x79` |
| `F11` | 122 | `0x7A` |
| `F12` | 123 | `0x7B` |
| `F13` | 124 | `0x7C` |
| `F14` | 125 | `0x7D` |
| `F15` | 126 | `0x7E` |
| `F16` | 127 | `0x7F` |
| `F17` | 128 | `0x80` |
| `F18` | 129 | `0x81` |
| `F19` | 130 | `0x82` |
| `F20` | 131 | `0x83` |
| `F21` | 132 | `0x84` |
| `F22` | 133 | `0x85` |
| `F23` | 134 | `0x86` |
| `F24` | 135 | `0x87` |

## Modifiers And System Keys

| Canonical name | Decimal | Hex | Aliases |
| --- | ---: | ---: | --- |
| `SHIFT` | 16 | `0x10` |  |
| `CTRL` | 17 | `0x11` | `CONTROL` |
| `ALT` | 18 | `0x12` |  |
| `RIGHT_SHIFT` | 21 | `0x15` | `RSHIFT` |
| `RIGHT_CTRL` | 22 | `0x16` | `RCTRL` |
| `RIGHT_ALT` | 23 | `0x17` | `RALT` |
| `LEFT_WINDOWS` | 91 | `0x5B` | `LWIN`, `WIN`, `WINDOWS`, `META` |
| `RIGHT_WINDOWS` | 92 | `0x5C` | `RWIN` |
| `CONTEXT_MENU` | 93 | `0x5D` | `CONTEXTMENU`, `APP_MENU`, `MENU` |
| `PAUSE_BREAK` | 19 | `0x13` | `PAUSE` |
| `CAPS_LOCK` | 20 | `0x14` |  |
| `NUM_LOCK` | 144 | `0x90` |  |
| `SCROLL_LOCK` | 145 | `0x91` |  |

## Editing And Navigation

| Canonical name | Decimal | Hex | Aliases |
| --- | ---: | ---: | --- |
| `BACKSPACE` | 8 | `0x08` |  |
| `TAB` | 9 | `0x09` |  |
| `CLEAR` | 12 | `0x0C` |  |
| `ENTER` | 13 | `0x0D` | `RETURN` |
| `ESC` | 27 | `0x1B` | `ESCAPE` |
| `SPACE` | 32 | `0x20` |  |
| `PAGE_UP` | 33 | `0x21` | `PGUP` |
| `PAGE_DOWN` | 34 | `0x22` | `PGDN` |
| `END` | 35 | `0x23` |  |
| `HOME` | 36 | `0x24` |  |
| `LEFT` | 37 | `0x25` | `ARROW_LEFT` |
| `UP` | 38 | `0x26` | `ARROW_UP` |
| `RIGHT` | 39 | `0x27` | `ARROW_RIGHT` |
| `DOWN` | 40 | `0x28` | `ARROW_DOWN` |
| `PRINT_SCREEN` | 44 | `0x2C` | `PRTSC` |
| `INSERT` | 45 | `0x2D` | `INS` |
| `DELETE` | 46 | `0x2E` | `DEL` |

## Punctuation

| Key | Decimal | Hex | Aliases |
| --- | ---: | ---: | --- |
| `;` | 186 | `0xBA` | `SEMICOLON` |
| `=` | 187 | `0xBB` | `EQUALS` |
| `,` | 188 | `0xBC` | `COMMA` |
| `-` | 189 | `0xBD` | `MINUS` |
| `.` | 190 | `0xBE` | `PERIOD` |
| `/` | 191 | `0xBF` | `SLASH` |
| `BACKTICK` | 192 | `0xC0` | literal backtick |
| `[` | 219 | `0xDB` | `LEFT_BRACKET` |
| `\` | 220 | `0xDC` | `BACKSLASH` |
| `]` | 221 | `0xDD` | `RIGHT_BRACKET` |
| `'` | 222 | `0xDE` | `QUOTE` |

## Numpad

| Canonical name | Decimal | Hex | Aliases |
| --- | ---: | ---: | --- |
| `NUM_0` | 96 | `0x60` | `NUM0` |
| `NUM_1` | 97 | `0x61` | `NUM1` |
| `NUM_2` | 98 | `0x62` | `NUM2` |
| `NUM_3` | 99 | `0x63` | `NUM3` |
| `NUM_4` | 100 | `0x64` | `NUM4` |
| `NUM_5` | 101 | `0x65` | `NUM5` |
| `NUM_6` | 102 | `0x66` | `NUM6` |
| `NUM_7` | 103 | `0x67` | `NUM7` |
| `NUM_8` | 104 | `0x68` | `NUM8` |
| `NUM_9` | 105 | `0x69` | `NUM9` |
| `NUM_MULTIPLY` | 106 | `0x6A` | `NUM_STAR` |
| `NUM_PLUS` | 107 | `0x6B` |  |
| `NUM_MINUS` | 109 | `0x6D` |  |
| `NUM_DECIMAL` | 110 | `0x6E` | `NUM_DEL` |
| `NUM_DIVIDE` | 111 | `0x6F` | `NUM_SLASH` |
| `NUM_ENTER` | 24 | `0x18` |  |

## Browser, Media, And Launch Keys

These are native virtual-key codes written through the same key assignment protocol
as ordinary keys.

| Canonical name | Decimal | Hex | Aliases |
| --- | ---: | ---: | --- |
| `BROWSER_BACK` | 166 | `0xA6` |  |
| `BROWSER_FORWARD` | 167 | `0xA7` |  |
| `BROWSER_REFRESH` | 168 | `0xA8` |  |
| `BROWSER_STOP` | 169 | `0xA9` |  |
| `BROWSER_SEARCH` | 170 | `0xAA` |  |
| `BROWSER_FAVORITES` | 171 | `0xAB` |  |
| `BROWSER_HOME` | 172 | `0xAC` |  |
| `MEDIA_MUTE` | 173 | `0xAD` | `VOLUME_MUTE` |
| `MEDIA_VOLUME_DOWN` | 174 | `0xAE` | `VOLUME_DOWN`, `VOL_DOWN` |
| `MEDIA_VOLUME_UP` | 175 | `0xAF` | `VOLUME_UP`, `VOL_UP` |
| `MEDIA_NEXT_TRACK` | 176 | `0xB0` | `MEDIA_NEXT` |
| `MEDIA_PREVIOUS_TRACK` | 177 | `0xB1` | `MEDIA_PREV` |
| `MEDIA_STOP` | 178 | `0xB2` |  |
| `MEDIA_PLAY_PAUSE` | 179 | `0xB3` | `PLAY_PAUSE` |
| `LAUNCH_MAIL` | 180 | `0xB4` |  |
| `LAUNCH_MEDIA` | 181 | `0xB5` |  |
| `LAUNCH_APP1` | 182 | `0xB6` |  |
| `LAUNCH_APP2` | 183 | `0xB7` |  |
