# Vaydeer Vendor App Notes

These notes summarize the Vaydeer keyboard Electron app behavior relevant to the
Python flasher implementation.

## Device Identity

A 9-key keypad presents as:

- Vendor ID: `0x0483`
- Product ID: `0x5752`
- USB product string: `9-key Smart Keypad`
- Manufacturer string: `Vaydeer`
Windows reports it as a composite USB HID device. The important HID collections are:

| Interface | Usage page / usage | Role | Report sizes observed |
| --- | --- | --- | --- |
| `MI_00` | `0xFF00 / 0x0001` | Vendor command/config channel | input 65, output 65 |
| `MI_01` | Generic Desktop / Keyboard | Standard keyboard output | input 13, output 2 |
| `MI_02` | `0xFF00 / 0x0002` | Vendor event/status channel | input 17 |
| `MI_03` | Mouse, Consumer, System Control | Standard mouse/media/system output | input 5/3/3 |

The Python tool currently requires the two vendor-defined HID channels and writes
through `0xFF00 / 0x0001`.

## Vendor App Architecture

The vendor app is an Electron/Vue application:

- Package name: `vaydeer-keyboard`
- Version seen in `package.json`: `1.2.3`
- Main process entry: `background.js`
- Important dependencies:
  - `node-hid@2.1.1`
  - `usb-detection@4.14.2`
  - `robotjs`
  - `@nut-tree/nut-js`

The main Electron window enables Node integration:

```js
webPreferences: {
  nodeIntegration: true,
  webSecurity: false
}
```

This matters because the renderer bundle directly requires `node-hid` and performs
hardware I/O itself. The main process does not implement the keypad protocol.

The main process uses `usb-detection` only for hotplug notifications:

- Starts monitoring with `usb-detection.startMonitoring()`.
- Listens for `add:1155:22354` and `remove:1155:22354`.
- Forwards those events to the renderer as `usbDetect-add` and `usbDetect-remove`.

`1155` and `22354` are decimal for `0x0483` and `0x5752`.

## HID Opening Logic

The renderer calls `node-hid.devices()` and selects two HID paths:

```js
devices().find(d =>
  d.vendorId === 1155 &&
  d.productId === 22354 &&
  d.usagePage === 65280 &&
  d.usage === 1
)

devices().find(d =>
  d.vendorId === 1155 &&
  d.productId === 22354 &&
  d.usagePage === 65280 &&
  d.usage === 2
)
```

It opens:

- usage `1` as the command handle
- usage `2` as the event handle

The event handle listens for `data` events. Reports whose first byte is `251`
(`0xFB`) are treated as keypad events containing the active layer and key event
details.

## Frame Format

The vendor protocol frame body is:

```text
[command, payloadLength, ...payload, xorChecksum]
```

When writing with `node-hid`, the app prepends report ID `0`, so the actual HID
output report is:

```text
[0, command, payloadLength, ...payload, xorChecksum]
```

The XOR checksum covers:

```text
[command, payloadLength, ...payload]
```

For normal command/response operations, the app writes to the command channel and
then calls `readTimeout(2000)`.

Responses use the same checksum idea. The first payload byte is a device status:

- `0`: success
- nonzero: device-level error, mapped by the app to protocol error `1102`

If the response checksum is invalid, the app maps that to protocol error `1101`.
General exceptions are mapped to `9000`.

## Known Command IDs

The app's protocol module exports these command wrappers:

| Command | Hex | Purpose |
| --- | --- | --- |
| `96` | `0x60` | Read device info |
| `97` | `0x61` | Write key assignment |
| `98` | `0x62` | Read key assignment |
| `99` | `0x63` | Read layer info |
| `100` | `0x64` | Change active layer |
| `101` | `0x65` | Write layer name |
| `102` | `0x66` | Commit/finalize layer |
| `103` | `0x67` | Read layer name |
| `252` | `0xFC` | Firmware update data/control |
| `253` | `0xFD` | Initialization/handshake |

## Device Info Response

Command `96` returns a payload parsed by the app as:

```text
data[1]      type
data[2]      subType
data[3:6]    firmware version
data[6:9]    bootloader version
data[9]      active layer id
data[10]     layer count
data[11]     max layer count
```

After stripping the status byte in the Python implementation, this becomes:

```text
payload[0]      type
payload[1]      subtype
payload[2:5]    firmware version
payload[5:8]    bootloader version
payload[8]      active layer id
payload[9]      layer count
payload[10]     max layer count
```

For `type == 1`, the app effectively treats `subType` as the number of physical
keys. The 9-key keypad uses `subType == 9`.

## Key Assignment Flashing

The string `Flash Keypad successfully` belongs to keymap/config flashing, not
firmware update.

The UI flow for flashing a keypad config:

1. Iterate layers.
2. Write each layer name with command `101`.
3. Iterate every key in the layer.
4. Write each key assignment with command `97`.
5. Commit/finalize each layer with command `102`.
6. Read layer/device state again.
7. Show `FlashSuccess` or `FlashFail`.

The write-key helper sends a three-stage sequence:

```text
Start:
  command 97
  [0xFF, layerIndex, keyIndex, keyType, subType, triggerType, ...keyNameUtf16Bytes]

Data chunks:
  command 97
  [sequence, ...data]

End:
  command 97
  [0xFE]
```

The sequence counter cycles `0..15`. Before chunks start, the app resets it by
setting the internal counter to `-1`; the first actual chunk gets sequence `0`.

The key name encoding helper stores each JavaScript character as two bytes:

```text
charCode >> 8, charCode & 0xFF
```

For ASCII strings this is equivalent to UTF-16BE without surrogate handling.

## Key Assignment Types

The app writes all these assignment categories through command `97` with different
`keyType` / `subType` / `triggerType` values:

| App type | `keyType` | Notes |
| --- | --- | --- |
| Single key | `0` | Data is one key code byte |
| Key combo | `1` | Data is multiple key code bytes |
| Text | `2` | `subType`: `0` Unicode, `1` GBK, `2` software mode |
| Trigger/app/file/url | `3` | First data byte selects file/directory/url/app |
| Mouse | `4` | Data stores mouse action, click count, interval |
| Macro | `5` | `subType` is macro mode; data contains key/action/interval triplets |
| Vaydeer-specific | `6` | Data is Vaydeer action bytes |
| Unknown/special | `7` | Seen in protocol wrapper, exact UI usage not yet mapped |

The Python v1 tool currently supports only `keyType` `0` and `1`.

## Keyboard and Media Codes

The app stores keyboard assignments as Windows-style virtual key code bytes. Examples:

- `A`: `65`
- `F1`..`F12`: `112`..`123`
- `Ctrl`: `17`
- `Alt`: `18`
- `Contextmenu`: `93`
- `Volume up`: `175`
- `Play/Pause`: `179`

Media/system/app keys are still stored as ordinary key assignment bytes. The device
can then emit the appropriate standard HID collection reports through its keyboard,
consumer-control, or system-control interfaces.

The vendor app's built-in key tables list only `F1` through `F12`. Raw Windows
virtual-key values for `F13` and above exist, but testing showed that a flashed
`F13`-style config did not emit usable keypresses on the 9-key keypad firmware.
Treat `F13+` as unsupported unless future firmware testing proves otherwise.

## Mouse Actions

Mouse assignments are stored on the keypad, not synthesized by the app during
normal use.

The mouse write wrapper is:

```js
const data = [mouseAction, ...uint16LE(clickCount), ...uint16LE(interval)]
writeKey(layer, key, keyType=4, subType=255, triggerType=0, name, data)
```

Because the USB device exposes a standard mouse HID collection, the firmware can
emit mouse reports directly after the config is flashed.

Known UI strings include:

- Mouse
- Mouse clicks
- Custom Left Button
- Anti-sleep / MouseJiggler

The exact mouse action code table still needs mapping from UI data structures if
we want to add this to Python.

## Macros

Macros are also stored on-device via `keyType == 5`.

The app maps macro modes:

| Macro mode | `subType` |
| --- | --- |
| `NoRepeat` | `0` |
| `PressRepeat` | `1` |
| `Trigger` | `2` |
| `Sequence` | `3` |

Macro data is a sequence of:

```text
[keyCode, action, ...uint16LE(intervalMs)]
```

For `Sequence` macros, the app writes three separate key assignment records with
`triggerType` values `0`, `1`, and `2`, corresponding to down/press/up phases.

## Text Assignments

Text assignments use `keyType == 2`.

Encoding modes:

| Mode | `subType` | Payload |
| --- | --- | --- |
| `Unicode` | `0` | JavaScript char code as two bytes |
| `GBK` | `1` | GBK-encoded bytes |
| `Software` | `2` | No text bytes stored for output; app assists at runtime |

The app has special handling for `Text` entries with `Software` encoding when
loading local layers, so software-mode text may rely on the app being running.

## Trigger / App / File / URL Assignments

Trigger assignments use `keyType == 3`.

The first payload byte selects the trigger type:

| Trigger type | Byte |
| --- | --- |
| File | `0` |
| Directory | `1` |
| Url | `2` |
| App | `3` |

The rest of the data is the path or URL encoded with the same two-byte string
helper used for names.

Runtime behavior may require the app for some trigger modes. The main process has
IPC handlers that call `shell.openPath()` or `shell.openExternal()` for trigger
events.

## Layer Handling

Layer names are written with command `101`:

```text
[layerIndex, maxLayerIndex, ...layerNameUtf16Bytes]
```

Layer commit/finalize uses command `102`:

```text
[layerIndex, maxLayerIndex]
```

The app changes the active layer by sending command `100`:

```text
[layerIndex]
```

Layer switching is mixed:

- The hardware stores multiple layers and reports the active layer in vendor event
  reports.
- The firmware appears to handle the physical `1 + 9` layer-switch key combination.
- The app can change layers in software by sending command `100`.
- Tray menu, floating window, mouse-wheel layer switching, and foreground-app
  layer switching are app-driven helpers that eventually call command `100`.

Settings such as these are stored in the app database, not flashed as key assignments:

- `changeLayerByTray`
- `changeLayerKeyCombination`
- `changeLayerBySoftware`

Foreground-app switching is implemented by launching helper executable
`Vaydeer.Keyboard.Win.exe` / `Vaydeer.Keyboard.Win1.exe`, reading foreground window
paths from stdout, matching configured app paths, and sending command `100`.

## Event Reports

The event/status interface (`0xFF00 / 0x0002`) is opened separately and listened to
with `m.on("data", ...)`.

Reports beginning with `0xFB` (`251`) are decoded with the same checksum helper.
The decoded payload is interpreted as:

```text
payload[0] active layer id
payload[1] key id or key event field
payload[2] key state or key event field
```

The app forwards `payload[1]` and `payload[2]` over IPC as `keydownHandle`, and if
`payload[0]` differs from the Vue store's current layer id, it updates UI state.

## Firmware

Firmware download, update transport, file encoding, checksums, decoded-image
layout, and patch experiments are documented in [`FIRMWARE.md`](FIRMWARE.md).


## Software Updates and Telemetry

The vendor app also includes:

- Electron auto-update support for the app itself.
- Autostart-on-boot configuration.
- Sentry/Glitchtip-style telemetry/error reporting toggle.
- Tray menu, floating window, and exit confirmation UI.

These are unrelated to flashing the keypad configuration.

## Current Python Tool Coverage

Implemented:

- `VID_0483/PID_5752` discovery.
- Required vendor HID interface validation.
- Hardware/key-count validation for known 1-, 4-, 6-, and 9-key layouts.
- Command framing and checksum.
- Device info read.
- Layer name write.
- Single key and key combo assignment writes.
- Empty/clear key writes.
- Layer commit.
- Local vendor-format firmware flashing via command `252`.
- YAML parsing and examples.
- Dry-run frame generation.

Not yet implemented:

- Mouse assignments (`keyType == 4`).
- Text assignments (`keyType == 2`).
- Trigger/app/file/url assignments (`keyType == 3`).
- Macros (`keyType == 5`).
- Vaydeer-specific actions (`keyType == 6`).
- Multi-layer YAML.
- Read-back/diff support.
- Firmware download/metadata integration.
- Robust bootloader reconnect handling if update status `2` drops the HID handle.
- Runtime helper features such as foreground-app layer switching.

## Open Questions / Mapping Work

Before adding full feature parity, map these tables from the vendor UI/state:

- Mouse action code values.
- Vaydeer-specific action byte values.
- Macro key action values for down/up/press.
- Whether trigger/file/url assignments work fully standalone or need the app
  listening for `keydownHandle`.
- Exact event payload semantics for `0xFB` reports.
- Whether all media/system virtual key codes are interpreted by firmware on every
  model/firmware version.
