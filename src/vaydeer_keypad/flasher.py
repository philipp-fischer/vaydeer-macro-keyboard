"""High-level configuration flashing flow."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from time import sleep

from tqdm import tqdm

from .config import LayerConfig, load_config
from .errors import ConfigError
from .hid_device import (
    DEFAULT_PRODUCT_ID,
    DEFAULT_VENDOR_ID,
    SUPPORTED_KEY_COUNT,
    find_keypad,
    open_command_transport,
)
from .protocol import (
    DeviceInfo,
    VaydeerProtocol,
    validate_supported_device,
    xor_checksum,
)

FIRMWARE_CHUNK_SIZE = 16
FIRMWARE_RETRY_COUNT = 10
FIRMWARE_RESTART_WAIT_SECONDS = 11.0
FIRMWARE_CHUNK_PAUSE_SECONDS = 0.01


@dataclass(frozen=True)
class FlashResult:
    device_info: DeviceInfo
    config: LayerConfig
    dry_run: bool
    frames: tuple[list[int], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FirmwareFlashResult:
    firmware_path: Path
    firmware_size: int
    dry_run: bool
    device_info: DeviceInfo | None = None
    frames: tuple[list[int], ...] = field(default_factory=tuple)


class DryRunTransport:
    def __init__(self) -> None:
        self.frames: list[list[int]] = []
        self._last_command = 0

    def write(self, data: list[int]) -> None:
        self.frames.append(list(data))
        self._last_command = data[1]

    def read(self, timeout_ms: int) -> list[int]:
        _ = timeout_ms
        body = [self._last_command, 1, 0]
        return [*body, xor_checksum(body)]

    def close(self) -> None:
        return None


def flash_config_file(
    config_path: Path,
    *,
    dry_run: bool = False,
    vendor_id: int = DEFAULT_VENDOR_ID,
    product_id: int = DEFAULT_PRODUCT_ID,
    timeout_ms: int = 2_000,
) -> FlashResult:
    config = load_config(config_path)
    return flash_config(
        config,
        dry_run=dry_run,
        vendor_id=vendor_id,
        product_id=product_id,
        timeout_ms=timeout_ms,
    )


def flash_config(
    config: LayerConfig,
    *,
    dry_run: bool = False,
    expected_keys: int | None = None,
    vendor_id: int = DEFAULT_VENDOR_ID,
    product_id: int = DEFAULT_PRODUCT_ID,
    timeout_ms: int = 2_000,
) -> FlashResult:
    if expected_keys is not None and config.key_count != expected_keys:
        raise ConfigError(f"Config has {config.key_count} keys, expected {expected_keys}")

    if dry_run:
        transport = DryRunTransport()
        protocol = VaydeerProtocol(transport, timeout_ms=timeout_ms)
        device_info = DeviceInfo(
            type=1,
            subtype=config.key_count,
            version=(0, 0, 0),
            bootloader_version=(0, 0, 0),
            layer_id=0,
            layer_count=1,
            max_layer_count=1,
        )
        _flash_layer(protocol, config, show_progress=False)
        return FlashResult(
            device_info=device_info,
            config=config,
            dry_run=True,
            frames=tuple(transport.frames),
        )

    candidate = find_keypad(vendor_id=vendor_id, product_id=product_id)
    transport = open_command_transport(candidate)
    protocol = VaydeerProtocol(transport, timeout_ms=timeout_ms)
    try:
        protocol.initialize()
        device_info = protocol.read_device_info()
        validate_supported_device(device_info, expected_keys=expected_keys or config.key_count)
        if config.key_count != device_info.key_count:
            raise ConfigError(
                "Config targets "
                f"{config.key_count} keys, but device reports {device_info.key_count}"
            )
        _flash_layer(protocol, config, show_progress=True)
        return FlashResult(device_info=device_info, config=config, dry_run=False)
    finally:
        protocol.close()


def flash_firmware_file(
    firmware_path: Path,
    *,
    dry_run: bool = False,
    expected_keys: int | None = SUPPORTED_KEY_COUNT,
    vendor_id: int = DEFAULT_VENDOR_ID,
    product_id: int = DEFAULT_PRODUCT_ID,
    timeout_ms: int = 2_000,
) -> FirmwareFlashResult:
    try:
        firmware = firmware_path.read_bytes()
    except OSError as exc:
        raise ConfigError(f"Unable to read firmware file {firmware_path}: {exc}") from exc
    if not firmware:
        raise ConfigError(f"Firmware file is empty: {firmware_path}")

    if dry_run:
        transport = DryRunTransport()
        protocol = VaydeerProtocol(transport, timeout_ms=timeout_ms)
        _flash_firmware(protocol, firmware, show_progress=False)
        return FirmwareFlashResult(
            firmware_path=firmware_path,
            firmware_size=len(firmware),
            dry_run=True,
            frames=tuple(transport.frames),
        )

    candidate = find_keypad(vendor_id=vendor_id, product_id=product_id)
    transport = open_command_transport(candidate)
    protocol = VaydeerProtocol(transport, timeout_ms=timeout_ms)
    try:
        protocol.initialize()
        device_info = protocol.read_device_info()
        validate_supported_device(device_info, expected_keys=expected_keys)
        _flash_firmware(protocol, firmware, show_progress=True)
        return FirmwareFlashResult(
            firmware_path=firmware_path,
            firmware_size=len(firmware),
            dry_run=False,
            device_info=device_info,
        )
    finally:
        protocol.close()


def _flash_layer(protocol: VaydeerProtocol, config: LayerConfig, *, show_progress: bool) -> None:
    max_layer_index = 0
    iterator = range(1, config.key_count + 1)
    progress = tqdm(total=config.key_count + 2, disable=not show_progress, unit="step")
    try:
        protocol.write_layer_name(0, max_layer_index, config.name)
        progress.update(1)

        for position in iterator:
            assignment = config.assignment_for_position(position)
            if assignment.is_empty:
                protocol.clear_key(0, assignment.key_index)
            elif len(assignment.key_codes) == 1:
                protocol.write_single_key(
                    0,
                    assignment.key_index,
                    assignment.name,
                    assignment.key_codes[0],
                )
            else:
                protocol.write_key_combo(
                    0,
                    assignment.key_index,
                    assignment.name,
                    list(assignment.key_codes),
                )
            progress.update(1)

        protocol.commit_layer(0, max_layer_index)
        progress.update(1)
    finally:
        progress.close()


def _flash_firmware(protocol: VaydeerProtocol, firmware: bytes, *, show_progress: bool) -> None:
    _prepare_firmware_update(protocol)
    protocol.next_sequence(reset=True)

    progress = tqdm(total=len(firmware) + 1, disable=not show_progress, unit="B")
    try:
        position = 0
        while position < len(firmware):
            chunk = list(firmware[position : position + FIRMWARE_CHUNK_SIZE])
            protocol.firmware_write_chunk(protocol.next_sequence(), chunk)
            position += FIRMWARE_CHUNK_SIZE
            progress.update(len(chunk))
            if show_progress and position % 160 == 0:
                sleep(FIRMWARE_CHUNK_PAUSE_SECONDS)

        result = protocol.firmware_finish_update()
        if result.status not in {0, 2}:
            raise ConfigError(f"Firmware finalize failed with device status {result.status}")
        progress.update(1)
    finally:
        progress.close()


def _prepare_firmware_update(protocol: VaydeerProtocol) -> None:
    for _ in range(FIRMWARE_RETRY_COUNT):
        result = protocol.firmware_prepare_update()
        if result.status == 0:
            return
        if result.status == 2:
            sleep(FIRMWARE_RESTART_WAIT_SECONDS)
            continue
        raise ConfigError(f"Firmware prepare failed with device status {result.status}")
    raise ConfigError("Firmware prepare did not complete after retries")


def dry_run_frame_summary(frames: tuple[list[int], ...]) -> str:
    lines = []
    for index, frame in enumerate(frames, start=1):
        unpadded = _strip_padding(frame)
        lines.append(f"{index:03d}: " + " ".join(f"{byte:02X}" for byte in unpadded))
    return "\n".join(lines)


def _strip_padding(frame: list[int]) -> list[int]:
    if len(frame) <= 4:
        return frame
    payload_length = frame[2]
    end = 4 + payload_length
    return frame[:end]


def dry_run_frame_brief(frames: tuple[list[int], ...], *, edge_count: int = 4) -> str:
    if len(frames) <= edge_count * 2:
        return dry_run_frame_summary(frames)

    head = dry_run_frame_summary(frames[:edge_count])
    tail_start = len(frames) - edge_count + 1
    tail_lines = []
    for index, frame in enumerate(frames[-edge_count:], start=tail_start):
        unpadded = _strip_padding(frame)
        tail_lines.append(f"{index:03d}: " + " ".join(f"{byte:02X}" for byte in unpadded))
    omitted = len(frames) - edge_count * 2
    return head + f"\n... {omitted} frames omitted ...\n" + "\n".join(tail_lines)
