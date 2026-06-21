from __future__ import annotations

import pytest

from vaydeer_keypad.errors import DeviceError
from vaydeer_keypad.hid_device import find_keypad


class FakeHid:
    def __init__(self, devices: list[dict[str, object]]) -> None:
        self._devices = devices

    def enumerate(self, vendor_id: int = 0, product_id: int = 0) -> list[dict[str, object]]:
        return [
            device
            for device in self._devices
            if device["vendor_id"] == vendor_id and device["product_id"] == product_id
        ]

    def device(self) -> object:
        raise AssertionError("not used")


def iface(serial: str, usage: int, path: bytes | None = None) -> dict[str, object]:
    return {
        "path": path or f"hid#vid_0483&pid_5752&mi_{usage:02x}#{serial}".encode(),
        "vendor_id": 0x0483,
        "product_id": 0x5752,
        "serial_number": serial,
        "manufacturer_string": "Vaydeer",
        "product_string": "9-key Smart Keypad",
        "usage_page": 0xFF00,
        "usage": usage,
        "interface_number": usage - 1,
    }


def test_find_keypad_requires_command_and_event_interfaces() -> None:
    candidate = find_keypad(hid_module=FakeHid([iface("JP101", 1), iface("JP101", 2)]))

    assert candidate.key == "JP101"
    assert candidate.command_interface.usage == 1
    assert candidate.event_interface.usage == 2


def test_find_keypad_rejects_missing_event_interface() -> None:
    with pytest.raises(DeviceError, match="No complete"):
        find_keypad(hid_module=FakeHid([iface("JP101", 1)]))


def test_find_keypad_rejects_multiple_complete_keypads() -> None:
    with pytest.raises(DeviceError, match="Multiple"):
        find_keypad(
            hid_module=FakeHid(
                [
                    iface("JP101", 1),
                    iface("JP101", 2),
                    iface("JP102", 1),
                    iface("JP102", 2),
                ]
            )
        )
