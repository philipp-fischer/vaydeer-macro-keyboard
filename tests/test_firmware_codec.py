from __future__ import annotations

from pathlib import Path

import pytest

from vaydeer_keypad.errors import ConfigError
from vaydeer_keypad.firmware_codec import (
    crc16_ccitt_false,
    decode_firmware_file,
    encode_firmware_file,
    patch_firmware_f13_file,
    xor_key_from_crc,
)


def test_encode_decode_round_trip_with_base_header(tmp_path) -> None:
    decoded = bytes([0x00, 0x50, 0x00, 0x20, 0x15, 0x96, 0x00, 0x08, *range(32)])
    source_decoded = tmp_path / "firmware.decoded"
    source_decoded.write_bytes(decoded)
    base_header = tmp_path / "base.bin"
    base_header.write_bytes(bytes.fromhex("ff fe 00 00 20 00 ff ff 00 08 01") + bytes(21))

    encoded_path = tmp_path / "firmware.bin"
    encode_result = encode_firmware_file(
        source_decoded,
        encoded_path,
        base_header=base_header,
    )

    expected_crc = crc16_ccitt_false(decoded)
    expected_key = xor_key_from_crc(expected_crc)
    assert encode_result.crc == expected_crc
    assert encode_result.xor_key == expected_key
    encoded = encoded_path.read_bytes()
    assert encoded[2:4] == expected_crc.to_bytes(2, "little")
    assert encoded[0x20:] == bytes(byte ^ expected_key for byte in decoded)

    decoded_path = tmp_path / "roundtrip.decoded"
    decode_result = decode_firmware_file(encoded_path, decoded_path)

    assert decode_result.crc_ok
    assert decode_result.xor_key == expected_key
    assert decoded_path.read_bytes() == decoded


def test_patch_firmware_f13_rejects_non_stock_fixture(tmp_path) -> None:
    source = tmp_path / "not-stock.bin"
    source.write_bytes(bytes.fromhex("ff fe 00 00 20 00 ff ff 00 08 01") + bytes(64))

    target = tmp_path / "patched.bin"

    with pytest.raises(ConfigError, match="Refusing to patch"):
        patch_firmware_f13_file(source, target)


def test_patch_firmware_f13_matches_known_artifact_when_available(tmp_path) -> None:
    source = Path("firmware/drBoard-custom-UG-v1_1_2.bin")
    known = Path("firmware/drBoard-custom-UG-v1_1_2-f13-f24-additive.derived-key.patched.bin")
    if not source.exists() or not known.exists():
        pytest.skip("firmware fixtures not present")

    target = tmp_path / "patched.bin"
    result = patch_firmware_f13_file(source, target)

    assert result.crc == 0xA462
    assert result.xor_key == 0xC6
    assert target.read_bytes() == known.read_bytes()
