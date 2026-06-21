from __future__ import annotations

import pytest

from vaydeer_keypad.protocol import (
    CMD_FIRMWARE_UPDATE,
    CMD_READ_DEVICE_INFO,
    ProtocolError,
    VaydeerProtocol,
    build_frame,
    parse_response,
    utf16be_bytes,
    xor_checksum,
)


def test_build_frame_pads_to_hid_report_length() -> None:
    frame = build_frame(0x61, [0xFF, 0, 0])

    assert len(frame) == 65
    assert frame[:6] == [0, 0x61, 3, 0xFF, 0, 0]
    assert frame[6] == xor_checksum([0x61, 3, 0xFF, 0, 0])


def test_parse_response_accepts_padded_report() -> None:
    body = [CMD_READ_DEVICE_INFO, 4, 0, 1, 9, 48]
    response = [*body, xor_checksum(body)] + [0] * 20

    assert parse_response(response) == [0, 1, 9, 48]


def test_parse_response_accepts_leading_report_id() -> None:
    body = [CMD_READ_DEVICE_INFO, 2, 0, 9]
    response = [0, *body, xor_checksum(body)] + [0] * 20

    assert parse_response(response) == [0, 9]


def test_parse_response_rejects_bad_checksum() -> None:
    with pytest.raises(ProtocolError):
        parse_response([0x61, 1, 0, 0xFF])


def test_utf16be_bytes_matches_electron_helper() -> None:
    assert utf16be_bytes("A") == [0, 65]
    assert utf16be_bytes("Copy") == [0, 67, 0, 111, 0, 112, 0, 121]


class FakeStatusTransport:
    def __init__(self, status: int) -> None:
        self.status = status
        self.writes: list[list[int]] = []

    def write(self, data: list[int]) -> None:
        self.writes.append(data)

    def read(self, timeout_ms: int) -> list[int]:
        _ = timeout_ms
        command = self.writes[-1][1]
        body = [command, 1, self.status]
        return [*body, xor_checksum(body)]

    def close(self) -> None:
        return None


def test_status_preserving_firmware_command_result() -> None:
    protocol = VaydeerProtocol(FakeStatusTransport(status=2))

    result = protocol.firmware_finish_update()

    assert result.status == 2
    assert result.data == []
    assert result.status != 0


def test_firmware_prepare_frame_uses_command_fc() -> None:
    transport = FakeStatusTransport(status=0)
    protocol = VaydeerProtocol(transport)

    protocol.firmware_prepare_update()

    assert transport.writes[0][1] == CMD_FIRMWARE_UPDATE
    assert transport.writes[0][2:4] == [1, 0xFF]
