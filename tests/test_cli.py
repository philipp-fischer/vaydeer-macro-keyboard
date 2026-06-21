from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from vaydeer_keypad.cli import main
from vaydeer_keypad.firmware_codec import crc16_ccitt_false, xor_key_from_crc


def test_flash_dry_run_uses_default_vid_pid_options(tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
layer:
  name: CLI
  keys:
    1: A
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(main, ["flash", "--dry-run", str(config_path)])

    assert result.exit_code == 0, result.output
    assert "Dry run built 9-key layer 'CLI'." in result.output
    assert "001:" in result.output


def test_flash_command_does_not_accept_expected_keys(tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "key_count: 4\nlayer:\n  name: Four\n  keys:\n    1: A\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        main,
        ["flash", "--dry-run", "--expected-keys", "4", str(config_path)],
    )

    assert result.exit_code != 0
    assert "No such option" in result.output
    assert "--expected-keys" in result.output


def test_firmware_flash_requires_yes_without_dry_run(tmp_path) -> None:
    firmware_path = tmp_path / "firmware.bin"
    firmware_path.write_bytes(b"firmware")

    result = CliRunner().invoke(main, ["flash-firmware", str(firmware_path)])

    assert result.exit_code != 0
    assert "Re-run with --yes" in result.output


def test_firmware_flash_dry_run(tmp_path) -> None:
    firmware_path = tmp_path / "firmware.bin"
    firmware_path.write_bytes(bytes(range(20)))

    result = CliRunner().invoke(main, ["flash-firmware", "--dry-run", str(firmware_path)])

    assert result.exit_code == 0, result.output
    assert "Dry run built firmware" in result.output
    assert "frames=4" in result.output


def test_decode_and_encode_firmware_commands(tmp_path) -> None:
    decoded_payload = bytes([0x00, 0x50, 0x00, 0x20, 0x15, 0x96, 0x00, 0x08, *range(8)])
    decoded_path = tmp_path / "input.decoded"
    decoded_path.write_bytes(decoded_payload)
    base_path = tmp_path / "base.bin"
    base_path.write_bytes(bytes.fromhex("ff fe 00 00 20 00 ff ff 00 08 01") + bytes(21))
    encoded_path = tmp_path / "encoded.bin"

    encode_result = CliRunner().invoke(
        main,
        [
            "encode-firmware",
            str(decoded_path),
            str(encoded_path),
            "--base-header",
            str(base_path),
        ],
    )

    assert encode_result.exit_code == 0, encode_result.output
    crc = crc16_ccitt_false(decoded_payload)
    assert f"crc=0x{crc:04X}" in encode_result.output
    assert f"xor_key=0x{xor_key_from_crc(crc):02X}" in encode_result.output

    roundtrip_path = tmp_path / "roundtrip.decoded"
    decode_result = CliRunner().invoke(
        main,
        ["decode-firmware", str(encoded_path), str(roundtrip_path)],
    )

    assert decode_result.exit_code == 0, decode_result.output
    assert "crc_ok=True" in decode_result.output
    assert roundtrip_path.read_bytes() == decoded_payload


def test_patch_firmware_f13_cli_when_fixture_available(tmp_path) -> None:
    source = Path("firmware/drBoard-custom-UG-v1_1_2.bin")
    known = Path("firmware/drBoard-custom-UG-v1_1_2-f13-f24-additive.derived-key.patched.bin")
    if not source.exists() or not known.exists():
        return

    target = tmp_path / "patched.bin"
    result = CliRunner().invoke(main, ["patch-firmware-f13", str(source), str(target)])

    assert result.exit_code == 0, result.output
    assert "crc=0xA462" in result.output
    assert "xor_key=0xC6" in result.output
    assert target.read_bytes() == known.read_bytes()
