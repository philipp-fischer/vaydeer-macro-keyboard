"""Project-specific exceptions."""


class VaydeerError(Exception):
    """Base error for expected CLI failures."""


class DeviceError(VaydeerError):
    """Raised when the target keypad cannot be uniquely or safely opened."""


class ProtocolError(VaydeerError):
    """Raised when HID command framing or responses are invalid."""


class ConfigError(VaydeerError):
    """Raised when the YAML configuration is invalid."""
