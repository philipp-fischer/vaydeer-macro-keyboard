"""Command line interface for the Vaydeer keypad flasher."""

from __future__ import annotations

from pathlib import Path

import click

from .errors import VaydeerError
from .firmware_codec import decode_firmware_file, encode_firmware_file, patch_firmware_f13_file
from .flasher import (
    dry_run_frame_brief,
    dry_run_frame_summary,
    flash_config_file,
    flash_firmware_file,
)
from .hid_device import DEFAULT_PRODUCT_ID, DEFAULT_VENDOR_ID, find_keypad, open_command_transport
from .protocol import VaydeerProtocol, validate_supported_device


def _hex_int(value: str | int) -> int:
    if isinstance(value, int):
        return value
    try:
        return int(value, 0)
    except ValueError as exc:
        raise click.BadParameter(f"Expected an integer, got {value!r}") from exc


@click.group()
def main() -> None:
    """Flash Vaydeer macro keypad configurations from YAML."""


@main.command()
@click.argument("config_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--dry-run", is_flag=True, help="Build frames without opening the USB device.")
@click.option("--vid", default=DEFAULT_VENDOR_ID, type=_hex_int, show_default="0x0483")
@click.option("--pid", default=DEFAULT_PRODUCT_ID, type=_hex_int, show_default="0x5752")
@click.option("--timeout-ms", default=2_000, type=int, show_default=True)
def flash(
    config_path: Path,
    *,
    dry_run: bool,
    vid: int,
    pid: int,
    timeout_ms: int,
) -> None:
    """Flash CONFIG_PATH to the connected keypad."""

    try:
        result = flash_config_file(
            config_path,
            dry_run=dry_run,
            vendor_id=vid,
            product_id=pid,
            timeout_ms=timeout_ms,
        )
    except VaydeerError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(
        f"{'Dry run built' if result.dry_run else 'Flashed'} "
        f"{result.config.key_count}-key layer {result.config.name!r}."
    )
    if result.dry_run:
        click.echo(dry_run_frame_summary(result.frames))
    else:
        click.echo(
            "Device firmware "
            f"{result.device_info.version_string}; active layer {result.device_info.layer_id}."
        )


@main.command()
@click.option("--vid", default=DEFAULT_VENDOR_ID, type=_hex_int, show_default="0x0483")
@click.option("--pid", default=DEFAULT_PRODUCT_ID, type=_hex_int, show_default="0x5752")
@click.option("--timeout-ms", default=2_000, type=int, show_default=True)
@click.option("--expected-keys", type=int, help="Override expected key count.")
def inspect(*, vid: int, pid: int, timeout_ms: int, expected_keys: int | None) -> None:
    """Find the connected keypad and print the device info used for validation."""

    try:
        candidate = find_keypad(vendor_id=vid, product_id=pid)
        transport = open_command_transport(candidate)
        protocol = VaydeerProtocol(transport, timeout_ms=timeout_ms)
        try:
            protocol.initialize()
            device_info = protocol.read_device_info()
            validate_supported_device(device_info, expected_keys=expected_keys)
        finally:
            protocol.close()
    except VaydeerError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Found Vaydeer keypad: {candidate.key}")
    click.echo(f"type={device_info.type} subtype={device_info.subtype}")
    click.echo(f"firmware={device_info.version_string}")
    click.echo(
        "layers="
        f"{device_info.layer_count}/{device_info.max_layer_count}, active={device_info.layer_id}"
    )


@main.command("decode-firmware")
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("target", type=click.Path(dir_okay=False, path_type=Path), required=False)
@click.option("--force", is_flag=True, help="Overwrite TARGET if it already exists.")
def decode_firmware(source: Path, target: Path | None, *, force: bool) -> None:
    """Decode a vendor .bin firmware file into a raw Cortex-M payload."""

    if target is None:
        target = source.with_suffix(source.suffix + ".decoded")
    try:
        result = decode_firmware_file(source, target, force=force)
    except VaydeerError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Decoded {result.source} -> {result.target}")
    click.echo(f"encoded_size={result.encoded_size} decoded_size={result.decoded_size}")
    click.echo(f"header_crc=0x{result.header_crc:04X}")
    click.echo(f"computed_crc=0x{result.computed_crc:04X}")
    click.echo(f"xor_key=0x{result.xor_key:02X}")
    click.echo(f"crc_ok={result.crc_ok}")


@main.command("encode-firmware")
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("target", type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--base-header",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Vendor .bin file whose 32-byte header should be reused.",
)
@click.option("--force", is_flag=True, help="Overwrite TARGET if it already exists.")
def encode_firmware(
    source: Path,
    target: Path,
    *,
    base_header: Path | None,
    force: bool,
) -> None:
    """Encode a raw Cortex-M payload into Vaydeer's vendor .bin format."""

    try:
        result = encode_firmware_file(source, target, base_header=base_header, force=force)
    except VaydeerError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Encoded {result.source} -> {result.target}")
    click.echo(f"decoded_size={result.decoded_size} encoded_size={result.encoded_size}")
    click.echo(f"crc=0x{result.crc:04X}")
    click.echo(f"xor_key=0x{result.xor_key:02X}")


@main.command("flash-firmware")
@click.argument("firmware_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--dry-run", is_flag=True, help="Build frames without opening the USB device.")
@click.option("--yes", is_flag=True, help="Confirm real firmware flashing.")
@click.option("--vid", default=DEFAULT_VENDOR_ID, type=_hex_int, show_default="0x0483")
@click.option("--pid", default=DEFAULT_PRODUCT_ID, type=_hex_int, show_default="0x5752")
@click.option("--timeout-ms", default=2_000, type=int, show_default=True)
@click.option("--expected-keys", default=9, type=int, show_default=True)
def flash_firmware(
    firmware_path: Path,
    *,
    dry_run: bool,
    yes: bool,
    vid: int,
    pid: int,
    timeout_ms: int,
    expected_keys: int,
) -> None:
    """Flash a local vendor-format firmware .bin file."""

    if not dry_run and not yes:
        raise click.ClickException(
            "Firmware flashing is risky. Re-run with --yes to confirm, or use --dry-run."
        )

    try:
        result = flash_firmware_file(
            firmware_path,
            dry_run=dry_run,
            vendor_id=vid,
            product_id=pid,
            timeout_ms=timeout_ms,
            expected_keys=expected_keys,
        )
    except VaydeerError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(
        f"{'Dry run built' if result.dry_run else 'Flashed'} firmware "
        f"{result.firmware_path} ({result.firmware_size} bytes)."
    )
    if result.dry_run:
        click.echo(f"frames={len(result.frames)}")
        click.echo(dry_run_frame_brief(result.frames))
    elif result.device_info is not None:
        click.echo(
            "Previous device firmware "
            f"{result.device_info.version_string}; device may restart now."
        )


@main.command("patch-firmware-f13")
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("target", type=click.Path(dir_okay=False, path_type=Path))
@click.option("--force", is_flag=True, help="Overwrite TARGET if it already exists.")
def patch_firmware_f13(source: Path, target: Path, *, force: bool) -> None:
    """Patch the known 9-key stock firmware to add native F13-F24 support."""

    try:
        result = patch_firmware_f13_file(source, target, force=force)
    except VaydeerError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Patched {result.source} -> {result.target}")
    click.echo(f"encoded_size={result.encoded_size}")
    click.echo(f"crc=0x{result.crc:04X}")
    click.echo(f"xor_key=0x{result.xor_key:02X}")


if __name__ == "__main__":
    main()
