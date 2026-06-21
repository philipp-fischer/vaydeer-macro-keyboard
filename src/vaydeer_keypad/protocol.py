"""Vaydeer keypad HID command protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .errors import ProtocolError
from .hid_device import REPORT_LENGTH, SUPPORTED_KEY_COUNTS

CMD_READ_DEVICE_INFO = 0x60
CMD_WRITE_KEY = 0x61
CMD_READ_KEY = 0x62
CMD_READ_LAYER_INFO = 0x63
CMD_CHANGE_LAYER = 0x64
CMD_WRITE_LAYER_NAME = 0x65
CMD_COMMIT_LAYER = 0x66
CMD_FIRMWARE_UPDATE = 0xFC
CMD_INIT = 0xFD

START_MARKER = 0xFF
END_MARKER = 0xFE
MAX_KEY_DATA_CHUNK = 60


class Transport(Protocol):
    def write(self, data: list[int]) -> None: ...

    def read(self, timeout_ms: int) -> list[int]: ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class DeviceInfo:
    type: int
    subtype: int
    version: tuple[int, int, int]
    bootloader_version: tuple[int, int, int]
    layer_id: int
    layer_count: int
    max_layer_count: int

    @property
    def key_count(self) -> int:
        # The app treats the subtype as the physical key count for type 1 devices.
        return self.subtype

    @property
    def version_string(self) -> str:
        return ".".join(str(part) for part in self.version)


@dataclass(frozen=True)
class CommandResult:
    status: int
    data: list[int]


class SequenceCounter:
    """Mirrors the Electron app's N(reset) sequence helper."""

    def __init__(self) -> None:
        self._value = 0

    def next(self, *, reset: bool = False) -> int:
        if reset:
            self._value = -1
            return self._value
        if self._value >= 15:
            self._value = 0
        else:
            self._value += 1
        return self._value


class VaydeerProtocol:
    def __init__(self, transport: Transport, *, timeout_ms: int = 2_000) -> None:
        self._transport = transport
        self._timeout_ms = timeout_ms
        self._sequence = SequenceCounter()

    def close(self) -> None:
        self._transport.close()

    def initialize(self) -> list[int]:
        return self.send_command(CMD_INIT, [])

    def next_sequence(self, *, reset: bool = False) -> int:
        return self._sequence.next(reset=reset)

    def read_device_info(self) -> DeviceInfo:
        data = self.send_command(CMD_READ_DEVICE_INFO, [])
        if len(data) < 11:
            raise ProtocolError(f"Device info response is too short: {data!r}")
        return DeviceInfo(
            type=data[0],
            subtype=data[1],
            version=(data[2], data[3], data[4]),
            bootloader_version=(data[5], data[6], data[7]),
            layer_id=data[8],
            layer_count=data[9],
            max_layer_count=data[10],
        )

    def write_layer_name(self, layer_index: int, max_layer_index: int, name: str) -> None:
        self.send_command(
            CMD_WRITE_LAYER_NAME,
            [layer_index, max_layer_index, *utf16be_bytes(name)],
        )

    def write_single_key(self, layer_index: int, key_index: int, name: str, key_code: int) -> None:
        self._write_key(
            layer_index=layer_index,
            key_index=key_index,
            key_type=0,
            subtype=0xFF,
            trigger_type=0,
            name=name,
            data=[key_code],
        )

    def write_key_combo(
        self,
        layer_index: int,
        key_index: int,
        name: str,
        key_codes: list[int],
    ) -> None:
        self._write_key(
            layer_index=layer_index,
            key_index=key_index,
            key_type=1,
            subtype=0xFF,
            trigger_type=0,
            name=name,
            data=key_codes,
        )

    def clear_key(self, layer_index: int, key_index: int) -> None:
        self.write_single_key(layer_index, key_index, "", 0)

    def commit_layer(self, layer_index: int, max_layer_index: int) -> None:
        self.send_command(CMD_COMMIT_LAYER, [layer_index, max_layer_index])

    def firmware_prepare_update(self) -> CommandResult:
        return self.send_command_with_status(CMD_FIRMWARE_UPDATE, [START_MARKER])

    def firmware_write_chunk(self, sequence: int, chunk: list[int]) -> None:
        self.send_command(CMD_FIRMWARE_UPDATE, [sequence, *chunk])

    def firmware_finish_update(self) -> CommandResult:
        return self.send_command_with_status(CMD_FIRMWARE_UPDATE, [END_MARKER])

    def send_command(self, command: int, payload: list[int]) -> list[int]:
        result = self.send_command_with_status(command, payload)
        if result.status != 0:
            raise ProtocolError(
                f"Command 0x{command:02X} failed with device status {result.status}: "
                f"{[result.status, *result.data]!r}"
            )
        return result.data

    def send_command_with_status(self, command: int, payload: list[int]) -> CommandResult:
        frame = build_frame(command, payload)
        self._transport.write(frame)
        response = self._transport.read(self._timeout_ms)
        payload_with_status = parse_response(response)
        if not payload_with_status:
            raise ProtocolError(f"Command 0x{command:02X} returned an empty payload")
        status = payload_with_status[0]
        return CommandResult(status=status, data=payload_with_status[1:])

    def _write_key(
        self,
        *,
        layer_index: int,
        key_index: int,
        key_type: int,
        subtype: int,
        trigger_type: int,
        name: str,
        data: list[int],
    ) -> None:
        self.send_command(
            CMD_WRITE_KEY,
            [
                START_MARKER,
                layer_index,
                key_index,
                key_type,
                subtype,
                trigger_type,
                *utf16be_bytes(name),
            ],
        )
        self._sequence.next(reset=True)
        position = 0
        while position < len(data):
            chunk = data[position : position + MAX_KEY_DATA_CHUNK]
            self.send_command(CMD_WRITE_KEY, [self._sequence.next(), *chunk])
            position += MAX_KEY_DATA_CHUNK
        self.send_command(CMD_WRITE_KEY, [END_MARKER])


def build_frame(command: int, payload: list[int]) -> list[int]:
    assert_byte(command, "command")
    if len(payload) > 0xFF:
        raise ProtocolError(f"Payload too long for one frame: {len(payload)} bytes")
    body = [command, len(payload), *payload]
    checksum = xor_checksum(body)
    frame = [0, *body, checksum]
    if len(frame) > REPORT_LENGTH:
        raise ProtocolError(f"Frame exceeds {REPORT_LENGTH} bytes: {len(frame)}")
    return frame + [0] * (REPORT_LENGTH - len(frame))


def parse_response(response: list[int]) -> list[int]:
    candidates = [response]
    if response and response[0] == 0:
        candidates.append(response[1:])

    for candidate in candidates:
        try:
            return _parse_response_candidate(candidate)
        except ProtocolError:
            continue
    raise ProtocolError(f"Invalid response frame: {response!r}")

def _parse_response_candidate(response: list[int]) -> list[int]:
    if len(response) < 3:
        raise ProtocolError("Response is too short")
    payload_length = response[1]
    expected_length = payload_length + 3
    if len(response) < expected_length:
        raise ProtocolError(
            f"Response length mismatch: expected {expected_length}, got {len(response)}"
        )
    body = response[: expected_length - 1]
    expected_checksum = response[expected_length - 1]
    actual_checksum = xor_checksum(body)
    if actual_checksum != expected_checksum:
        raise ProtocolError(
            f"Checksum mismatch: expected 0x{expected_checksum:02X}, got 0x{actual_checksum:02X}"
        )
    return response[2 : 2 + payload_length]


def xor_checksum(data: list[int]) -> int:
    result = 0
    for value in data:
        assert_byte(value, "checksum input")
        result ^= value
    return result


def utf16be_bytes(text: str) -> list[int]:
    output: list[int] = []
    for char in text:
        value = ord(char)
        output.extend([(value >> 8) & 0xFF, value & 0xFF])
    return output


def assert_byte(value: int, label: str) -> None:
    if not 0 <= value <= 0xFF:
        raise ProtocolError(f"{label} value is outside byte range: {value!r}")


def validate_supported_device(
    device_info: DeviceInfo,
    *,
    expected_keys: int | None = None,
) -> None:
    if device_info.key_count not in SUPPORTED_KEY_COUNTS:
        supported = ", ".join(str(count) for count in sorted(SUPPORTED_KEY_COUNTS))
        raise ProtocolError(
            f"Detected keypad has {device_info.key_count} keys; supported counts are: {supported}"
        )
    if expected_keys is not None and device_info.key_count != expected_keys:
        raise ProtocolError(
            f"Detected keypad has {device_info.key_count} keys; expected {expected_keys}"
        )
