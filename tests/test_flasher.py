from __future__ import annotations

import pytest

from vaydeer_keypad.config import parse_config
from vaydeer_keypad.flasher import flash_config, flash_firmware_file
from vaydeer_keypad.protocol import DeviceInfo, ProtocolError, validate_supported_device


def test_dry_run_builds_expected_single_layer_frames() -> None:
    config = parse_config(
        {
            "layer": {
                "name": "Dry Run",
                "keys": {
                    1: "A",
                    2: "CTRL+C",
                    3: "MEDIA_PLAY_PAUSE",
                },
            }
        }
    )

    result = flash_config(config, dry_run=True)

    assert result.dry_run
    assert len(result.frames) == 29
    assert result.frames[0][1] == 0x65
    assert result.frames[-1][1] == 0x66
    assert all(len(frame) == 65 for frame in result.frames)


def test_dry_run_supports_4_key_config() -> None:
    config = parse_config({"key_count": 4, "layer": {"name": "Four", "keys": {1: "A", 4: "D"}}})

    result = flash_config(config, dry_run=True)

    assert result.config.key_count == 4
    assert result.device_info.key_count == 4


def test_validate_supported_device_rejects_unsupported_subtype() -> None:
    device_info = DeviceInfo(
        type=1,
        subtype=5,
        version=(1, 2, 3),
        bootloader_version=(1, 0, 0),
        layer_id=0,
        layer_count=1,
        max_layer_count=1,
    )

    with pytest.raises(ProtocolError, match="supported counts"):
        validate_supported_device(device_info)


def test_validate_supported_device_rejects_expected_mismatch() -> None:
    device_info = DeviceInfo(
        type=1,
        subtype=4,
        version=(1, 2, 3),
        bootloader_version=(1, 0, 0),
        layer_id=0,
        layer_count=1,
        max_layer_count=1,
    )

    with pytest.raises(ProtocolError, match="expected 9"):
        validate_supported_device(device_info, expected_keys=9)


def test_dry_run_firmware_flash_streams_vendor_bin_frames(tmp_path) -> None:
    firmware = tmp_path / "firmware.bin"
    firmware.write_bytes(bytes(range(34)))

    result = flash_firmware_file(firmware, dry_run=True)

    assert result.dry_run
    assert result.firmware_size == 34
    assert len(result.frames) == 5
    assert [frame[1] for frame in result.frames] == [0xFC, 0xFC, 0xFC, 0xFC, 0xFC]
    assert result.frames[0][2:4] == [1, 0xFF]
    assert result.frames[1][2:5] == [17, 0, 0]
    assert result.frames[2][2:5] == [17, 1, 16]
    assert result.frames[3][2:5] == [3, 2, 32]
    assert result.frames[4][2:4] == [1, 0xFE]
