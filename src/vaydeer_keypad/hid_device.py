"""HID discovery and transport for Vaydeer keypads."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol

from .errors import DeviceError

DEFAULT_VENDOR_ID = 0x0483
DEFAULT_PRODUCT_ID = 0x5752
VENDOR_USAGE_PAGE = 0xFF00
COMMAND_USAGE = 0x0001
EVENT_USAGE = 0x0002
SUPPORTED_KEY_COUNT = 9
SUPPORTED_KEY_COUNTS = frozenset({1, 4, 6, 9})
REPORT_LENGTH = 65


class HidApiModule(Protocol):
    """Subset of hidapi used by the application."""

    def enumerate(self, vendor_id: int = 0, product_id: int = 0) -> list[dict[str, Any]]: ...

    def device(self) -> Any: ...


@dataclass(frozen=True)
class HidInterfaceInfo:
    path: bytes | str
    vendor_id: int
    product_id: int
    serial_number: str
    manufacturer_string: str
    product_string: str
    usage_page: int | None
    usage: int | None
    interface_number: int | None

    @classmethod
    def from_hidapi(cls, raw: dict[str, Any]) -> HidInterfaceInfo:
        return cls(
            path=raw["path"],
            vendor_id=int(raw.get("vendor_id") or 0),
            product_id=int(raw.get("product_id") or 0),
            serial_number=str(raw.get("serial_number") or ""),
            manufacturer_string=str(raw.get("manufacturer_string") or ""),
            product_string=str(raw.get("product_string") or ""),
            usage_page=_optional_int(raw.get("usage_page")),
            usage=_optional_int(raw.get("usage")),
            interface_number=_optional_int(raw.get("interface_number")),
        )


@dataclass(frozen=True)
class KeypadCandidate:
    key: str
    interfaces: tuple[HidInterfaceInfo, ...]
    command_interface: HidInterfaceInfo
    event_interface: HidInterfaceInfo


class HidTransport:
    """Thin wrapper around a hidapi device handle."""

    def __init__(self, handle: Any, *, read_length: int = REPORT_LENGTH) -> None:
        self._handle = handle
        self._read_length = read_length

    def write(self, data: list[int]) -> None:
        self._handle.write(data)

    def read(self, timeout_ms: int) -> list[int]:
        return list(self._handle.read(self._read_length, timeout_ms))

    def close(self) -> None:
        close = getattr(self._handle, "close", None)
        if close is not None:
            close()


def find_keypad(
    *,
    vendor_id: int = DEFAULT_VENDOR_ID,
    product_id: int = DEFAULT_PRODUCT_ID,
    hid_module: HidApiModule | None = None,
) -> KeypadCandidate:
    """Find exactly one physical Vaydeer keypad with the required vendor HID interfaces."""

    hid = _load_hid(hid_module)
    raw_devices = hid.enumerate(vendor_id, product_id)
    interfaces = [HidInterfaceInfo.from_hidapi(item) for item in raw_devices]
    candidates = _group_interfaces(interfaces)

    complete = []
    incomplete = []
    for key, grouped in candidates.items():
        command = _find_vendor_interface(grouped, COMMAND_USAGE)
        event = _find_vendor_interface(grouped, EVENT_USAGE)
        if command and event:
            complete.append(
                KeypadCandidate(
                    key=key,
                    interfaces=tuple(grouped),
                    command_interface=command,
                    event_interface=event,
                )
            )
        else:
            incomplete.append((key, grouped))

    if len(complete) == 1:
        return complete[0]

    if not complete:
        details = _format_groups(incomplete or candidates.items())
        raise DeviceError(
            "No complete Vaydeer keypad found. Expected one physical device with "
            "vendor HID usages 0xFF00/0x0001 and 0xFF00/0x0002.\n" + details
        )

    details = _format_groups((candidate.key, candidate.interfaces) for candidate in complete)
    raise DeviceError(
        "Multiple Vaydeer keypads found. Unplug extras and retry; refusing to choose one.\n"
        + details
    )


def open_command_transport(
    candidate: KeypadCandidate,
    *,
    hid_module: HidApiModule | None = None,
) -> HidTransport:
    hid = _load_hid(hid_module)
    handle = hid.device()
    handle.open_path(candidate.command_interface.path)
    return HidTransport(handle)


def _load_hid(hid_module: HidApiModule | None) -> HidApiModule:
    if hid_module is not None:
        return hid_module
    try:
        import hid  # type: ignore[import-not-found]
    except ImportError as exc:
        raise DeviceError(
            "The 'hid' module is unavailable. Install dependencies with 'uv sync'."
        ) from exc
    return hid


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _group_interfaces(
    interfaces: Iterable[HidInterfaceInfo],
) -> dict[str, list[HidInterfaceInfo]]:
    groups: dict[str, list[HidInterfaceInfo]] = defaultdict(list)
    for interface in interfaces:
        # Serial is stable for the Vaydeer keypad; interface paths remain as fallback for tests
        # and for HIDAPI backends that do not expose serial strings.
        key = interface.serial_number or _path_group_key(interface.path)
        groups[key].append(interface)
    return dict(groups)


def _path_group_key(path: bytes | str) -> str:
    text = path.decode(errors="ignore") if isinstance(path, bytes) else path
    lower = text.lower()
    for token in ("&mi_", "#mi_"):
        index = lower.find(token)
        if index >= 0:
            return lower[:index]
    return lower


def _find_vendor_interface(
    interfaces: Iterable[HidInterfaceInfo],
    usage: int,
) -> HidInterfaceInfo | None:
    for interface in interfaces:
        if interface.usage_page == VENDOR_USAGE_PAGE and interface.usage == usage:
            return interface
    return None


def _format_groups(groups: Iterable[tuple[str, Iterable[HidInterfaceInfo]]]) -> str:
    lines = ["Detected matching HID groups:"]
    count = 0
    for key, interfaces in groups:
        count += 1
        lines.append(f"- {key}:")
        for interface in interfaces:
            lines.append(
                "  "
                f"usage_page={_hex_or_none(interface.usage_page)} "
                f"usage={_hex_or_none(interface.usage)} "
                f"serial={interface.serial_number!r} "
                f"product={interface.product_string!r}"
            )
    if count == 0:
        lines.append("- none")
    return "\n".join(lines)


def _hex_or_none(value: int | None) -> str:
    return "None" if value is None else f"0x{value:04X}"
