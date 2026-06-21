# Vaydeer Firmware Reference

This document describes the Vaydeer firmware format, update transport, codec, and
the supported F13-F24 patch workflow implemented by this project.

## Firmware Metadata

The vendor firmware metadata endpoint is:

```text
https://downloads.vaydeer.com/keyboard/firmware.json?d=<date>
```

Firmware paths are relative to:

```text
https://downloads.vaydeer.com/keyboard/
```

Known firmware metadata entries:

| Device family | Version | Path |
| --- | --- | --- |
| 1-key | `0.9.5` | `/drBoard-custom-1-UG-v0_9_5.bin` |
| 4-key | `0.9.7` | `/drBoard-custom-4-UG-v0_9_7.bin` |
| 6-key | `0.9.2` | `/drBoard-custom-6-UG-v0_9_2.bin` |
| 9-key | `1.1.2` | `/drBoard-custom-UG-v1_1_2.bin` |

The 9-key firmware URL is:

```text
https://downloads.vaydeer.com/keyboard/drBoard-custom-UG-v1_1_2.bin
```

## Firmware Update Transport

Firmware update uses vendor command `0xFC` over the `0xFF00 / 0x0001` HID command
interface. The command frame format is the same as the normal keypad protocol:

```text
[0, command, payloadLength, ...payload, xorChecksum]
```

The update sequence is:

1. Prepare update:
   ```text
   0xFC [0xFF]
   ```
2. If the device returns status `2`, wait and retry the prepare command.
3. When prepare returns status `0`, stream the whole vendor `.bin` file.
4. Send chunks of up to 16 firmware bytes:
   ```text
   0xFC [sequence, ...upTo16FirmwareBytes]
   ```
5. The sequence byte cycles from `0` through `15`.
6. Finish update:
   ```text
   0xFC [0xFE]
   ```
7. Final status `0` or `2` is treated as success.

The streamed data is the vendor-format `.bin` file exactly as downloaded or
generated, including the 32-byte wrapper header.

## Firmware File Layout

Each vendor `.bin` file has:

```text
0x0000..0x001F  Vaydeer wrapper header
0x0020..end     XOR-encoded raw ARM Cortex-M payload
```

Decoded payloads are raw Cortex-M images and begin with the vector table:

```text
decoded+0x00: initial stack pointer
decoded+0x04: reset vector
```

## Header Structure

Known header fields:

| Offset | Meaning |
| --- | --- |
| `0x00` | magic byte `0xFF` |
| `0x01` | magic byte `0xFE` |
| `0x02..0x03` | CRC16-CCITT-FALSE of decoded payload, little-endian |
| `0x04..0x05` | header size `0x0020`, little-endian |
| `0x06..0x07` | constant `0xFFFF` |
| `0x08..0x0A` | constant bytes `00 08 01` |
| `0x0B..0x1F` | variable metadata; no common checksum/size encoding identified |

No consistent file-size or payload-size field has been identified in the header.

## CRC And XOR Key

The payload XOR key is derived from the header CRC bytes:

```python
crc = crc16_ccitt_false(decoded_payload)
crc_low = crc & 0xFF
crc_high = crc >> 8
xor_key = crc_low ^ crc_high
```

Observed firmware keys:

| Device family | Header CRC bytes | CRC value | XOR key |
| --- | --- | --- | --- |
| 1-key | `4A 8C` | `0x8C4A` | `0xC6` |
| 4-key | `D8 78` | `0x78D8` | `0xA0` |
| 6-key | `CD 45` | `0x45CD` | `0x88` |
| 9-key | `BD 7F` | `0x7FBD` | `0xC2` |

The header bytes are not XOR-encoded. Only bytes from offset `0x20` onward are
XOR-encoded.

## Firmware Codec CLI

The Python CLI can decode, encode, and patch firmware files:

```powershell
uv run vaydeer-flash decode-firmware firmware/drBoard-custom-UG-v1_1_2.bin
uv run vaydeer-flash encode-firmware patched.decoded patched.bin --base-header firmware/drBoard-custom-UG-v1_1_2.bin
uv run vaydeer-flash patch-firmware-f13 firmware/drBoard-custom-UG-v1_1_2.bin firmware/drBoard-custom-UG-v1_1_2-f13-f24.bin
```

`decode-firmware`:

- reads the wrapper header
- derives the XOR key from `header[0x02:0x04]`
- decodes the payload
- verifies CRC16-CCITT-FALSE against the header

`encode-firmware`:

- computes CRC16-CCITT-FALSE over a decoded payload
- writes the raw little-endian CRC into `header[0x02:0x04]`
- derives the new XOR key from the CRC bytes
- XOR-encodes the payload with the derived key

`patch-firmware-f13`:

- accepts the stock 9-key `drBoard-custom-UG-v1_1_2.bin` image
- applies the F13-F24 patch
- recomputes the CRC and derived XOR key
- writes a flashable vendor-format `.bin`

## Cortex-M Image Details

Known decoded image vectors:

| Device family | XOR key | Stack pointer | Reset vector |
| --- | --- | --- | --- |
| 1-key | `0xC6` | `0x20005000` | `0x080092A9` |
| 4-key | `0xA0` | `0x20005000` | `0x080094E9` |
| 6-key | `0x88` | `0x20005000` | `0x0800951D` |
| 9-key | `0xC2` | `0x20005000` | `0x08009615` |

Suggested Ghidra import for decoded 9-key payloads:

```text
Format: Raw Binary
Language: ARM Cortex little endian / Thumb
Base address: 0x08007000
Initial stack pointer: 0x20005000
Reset vector: 0x08009615
```

The USB vendor ID `0x0483` and decoded Cortex-M image indicate an
STMicroelectronics STM32-family microcontroller.

## Device Info

Normal 9-key firmware reports:

```text
type=1
subType=9
firmware=1.1.2
bootloader=0.2.2
```

In the decoded 9-key application firmware, command `0x60` hard-codes the normal
key count / subtype:

```c
pbVar6[3] = 1;      // type
pbVar6[4] = 9;      // subType / key count
pbVar6[5] = 1;
pbVar6[6] = 1;
pbVar6[7] = 2;      // bootloader version component
```

## Key Translation Table

The decoded 9-key image contains a virtual-key-to-HID-usage table:

```text
decoded offset: 0x7638
runtime address with 0x08007000 base: 0x0800E638
```

Stock F-key table entries:

```text
index 0x70..0x7B: 3A 3B 3C 3D 3E 3F 40 41 42 43 44 45
index 0x7C..0x87: 00 00 00 00 00 00 00 00 00 00 00 00
```

This means stock firmware maps `F1` through `F12` to HID usages `0x3A` through
`0x45`, while `F13` through `F24` are unmapped.

Relevant firmware functions:

| Decompiled name | Suggested name |
| --- | --- |
| `FUN_0000127c` | `vk_to_hid_usage_bytes` |
| `FUN_000012a4` | `hid_usage_to_vk_bytes` |

Forward mapping uses:

```c
*dst = table[*src];
```

## HID Descriptor

The stock keyboard report descriptor contains:

```text
05 07 19 00 29 65 81 00
```

This declares keyboard usage maximum `0x65`. Firmware that emits usages
`0x68..0x73` also needs the descriptor maximum raised to `0x73`.

## F13-F24 Firmware Patch

The supported patch keeps stock `F1` through `F12`, fills the previously-zero
`F13` through `F24` table entries, and raises the HID keyboard descriptor usage
maximum.

Patch details:

```text
F1-F12 table remains:
3A 3B 3C 3D 3E 3F 40 41 42 43 44 45

F13-F24 table becomes:
68 69 6A 6B 6C 6D 6E 6F 70 71 72 73

descriptor offset 0x789F:
0x65 -> 0x73
```

For the stock 9-key `1.1.2` image, the patched payload has:

```text
CRC = 0xA462
CRC bytes = 62 A4
derived XOR key = 0xC6
```

Use the CLI to generate this patch from the stock firmware:

```powershell
uv run vaydeer-flash patch-firmware-f13 firmware/drBoard-custom-UG-v1_1_2.bin firmware/drBoard-custom-UG-v1_1_2-f13-f24.bin
```

## Unknown Header Bytes

The header region `0x0B..0x1F` varies between firmware files. It has not been
matched to common raw or XOR-encoded checksum/size hypotheses, including:

- file size
- payload size
- decoded payload size
- size variants and page counts
- CRC32
- Adler32
- CRC16 variants
- Fletcher16
- sum8/sum16/sum32
- xor8
- FNV1a32
- DJB2
- MD5/SHA1/SHA256 prefixes/suffixes

These bytes may be packaging metadata, custom check data, model/version/build
metadata, seed material, or fields unused by the bootloader.
