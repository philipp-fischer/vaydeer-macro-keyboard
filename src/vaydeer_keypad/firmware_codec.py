"""Encode and decode Vaydeer vendor firmware files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import ConfigError

HEADER_SIZE = 0x20
STOCK_9KEY_SHA256 = "946ba10137e4e621e78353a9579691d57d9b609262fe51a4c152c006cb20f68b"
STOCK_9KEY_SIZE = 0x7A7C
STOCK_9KEY_CRC = 0x7FBD
STOCK_9KEY_XOR_KEY = 0xC2
F1_TABLE_OFFSET = 0x76A8
F13_TABLE_OFFSET = 0x76B4
KEYBOARD_USAGE_MAX_OFFSET = 0x789F
F1_F12_HID_USAGES = bytes(range(0x3A, 0x46))
F13_F24_HID_USAGES = bytes(range(0x68, 0x74))


@dataclass(frozen=True)
class FirmwareDecodeResult:
    source: Path
    target: Path
    encoded_size: int
    decoded_size: int
    header_crc: int
    computed_crc: int
    xor_key: int

    @property
    def crc_ok(self) -> bool:
        return self.header_crc == self.computed_crc


@dataclass(frozen=True)
class FirmwareEncodeResult:
    source: Path
    target: Path
    decoded_size: int
    encoded_size: int
    crc: int
    xor_key: int


@dataclass(frozen=True)
class FirmwarePatchResult:
    source: Path
    target: Path
    crc: int
    xor_key: int
    encoded_size: int


def crc16_ccitt_false(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def decode_firmware_bytes(data: bytes) -> tuple[bytes, int, int, int]:
    if len(data) <= HEADER_SIZE:
        raise ConfigError("Firmware data is too small")
    header_crc = int.from_bytes(data[2:4], "little")
    xor_key = xor_key_from_crc(header_crc)
    decoded = bytes(byte ^ xor_key for byte in data[HEADER_SIZE:])
    computed_crc = crc16_ccitt_false(decoded)
    return decoded, header_crc, computed_crc, xor_key


def xor_key_from_crc(crc: int) -> int:
    return (crc & 0xFF) ^ (crc >> 8)


def decode_firmware_file(
    source: Path,
    target: Path,
    *,
    force: bool = False,
) -> FirmwareDecodeResult:
    data = source.read_bytes()
    if len(data) <= HEADER_SIZE:
        raise ConfigError(f"Firmware file is too small: {source}")
    if target.exists() and not force:
        raise ConfigError(f"Refusing to overwrite existing file: {target}")

    header_crc = int.from_bytes(data[2:4], "little")
    decoded, _, computed_crc, xor_key = decode_firmware_bytes(data)
    target.write_bytes(decoded)

    return FirmwareDecodeResult(
        source=source,
        target=target,
        encoded_size=len(data),
        decoded_size=len(decoded),
        header_crc=header_crc,
        computed_crc=computed_crc,
        xor_key=xor_key,
    )


def encode_firmware_bytes(decoded: bytes, header: bytes) -> tuple[bytes, int, int]:
    if len(header) < HEADER_SIZE:
        raise ConfigError("Firmware header is too small")
    if not decoded:
        raise ConfigError("Decoded firmware payload is empty")
    crc = crc16_ccitt_false(decoded)
    xor_key = xor_key_from_crc(crc)
    patched_header = bytearray(header[:HEADER_SIZE])
    patched_header[2:4] = crc.to_bytes(2, "little")
    encoded = bytes(patched_header) + bytes(byte ^ xor_key for byte in decoded)
    return encoded, crc, xor_key


def encode_firmware_file(
    source: Path,
    target: Path,
    *,
    base_header: Path | None = None,
    force: bool = False,
) -> FirmwareEncodeResult:
    decoded = source.read_bytes()
    if not decoded:
        raise ConfigError(f"Decoded firmware payload is empty: {source}")
    if target.exists() and not force:
        raise ConfigError(f"Refusing to overwrite existing file: {target}")

    if base_header is None:
        header = bytearray(default_header())
    else:
        header_source = base_header.read_bytes()
        if len(header_source) < HEADER_SIZE:
            raise ConfigError(f"Base header file is too small: {base_header}")
        header = bytearray(header_source[:HEADER_SIZE])

    encoded, crc, xor_key = encode_firmware_bytes(decoded, bytes(header))
    target.write_bytes(encoded)

    return FirmwareEncodeResult(
        source=source,
        target=target,
        decoded_size=len(decoded),
        encoded_size=len(encoded),
        crc=crc,
        xor_key=xor_key,
    )


def patch_firmware_f13_file(
    source: Path,
    target: Path,
    *,
    force: bool = False,
) -> FirmwarePatchResult:
    data = source.read_bytes()
    if target.exists() and not force:
        raise ConfigError(f"Refusing to overwrite existing file: {target}")
    validate_stock_9key_firmware(data, source)

    decoded, _, _, _ = decode_firmware_bytes(data)
    patched_decoded = bytearray(decoded)
    if patched_decoded[F1_TABLE_OFFSET : F1_TABLE_OFFSET + 12] != F1_F12_HID_USAGES:
        raise ConfigError("Stock F1-F12 table bytes do not match expected values")
    if patched_decoded[F13_TABLE_OFFSET : F13_TABLE_OFFSET + 12] != bytes(12):
        raise ConfigError("Stock F13-F24 table bytes do not match expected zero values")
    if patched_decoded[KEYBOARD_USAGE_MAX_OFFSET] != 0x65:
        raise ConfigError("Stock keyboard descriptor usage max does not match 0x65")

    patched_decoded[F13_TABLE_OFFSET : F13_TABLE_OFFSET + 12] = F13_F24_HID_USAGES
    patched_decoded[KEYBOARD_USAGE_MAX_OFFSET] = 0x73
    encoded, crc, xor_key = encode_firmware_bytes(bytes(patched_decoded), data[:HEADER_SIZE])
    target.write_bytes(encoded)
    return FirmwarePatchResult(
        source=source,
        target=target,
        crc=crc,
        xor_key=xor_key,
        encoded_size=len(encoded),
    )


def validate_stock_9key_firmware(data: bytes, source: Path | None = None) -> None:
    import hashlib

    label = f" {source}" if source is not None else ""
    if len(data) != STOCK_9KEY_SIZE:
        raise ConfigError(f"Refusing to patch{label}: expected size 0x{STOCK_9KEY_SIZE:X}")
    decoded, header_crc, computed_crc, xor_key = decode_firmware_bytes(data)
    if header_crc != STOCK_9KEY_CRC or computed_crc != STOCK_9KEY_CRC:
        raise ConfigError(f"Refusing to patch{label}: CRC does not match stock 9-key firmware")
    if xor_key != STOCK_9KEY_XOR_KEY:
        raise ConfigError(f"Refusing to patch{label}: XOR key does not match stock 9-key firmware")
    sha256 = hashlib.sha256(data).hexdigest()
    if sha256 != STOCK_9KEY_SHA256:
        raise ConfigError(f"Refusing to patch{label}: SHA256 does not match stock 9-key firmware")
    if decoded[:8] != bytes.fromhex("00 50 00 20 15 96 00 08"):
        raise ConfigError(
            f"Refusing to patch{label}: vector table does not match stock 9-key firmware"
        )


def default_header() -> bytes:
    # Keep the known Vaydeer wrapper constants. The opaque metadata bytes are best
    # preserved by passing --base-header when encoding production firmware.
    return bytes.fromhex(
        "ff fe 00 00 20 00 ff ff 00 08 01 "
        "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00"
    )
