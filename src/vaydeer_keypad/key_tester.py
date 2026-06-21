"""Small focused-window key tester for the Vaydeer keypad."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MODIFIERS: tuple[tuple[int, str], ...] = (
    (0x0001, "Shift"),
    (0x0004, "Ctrl"),
    (0x0008, "Alt"),
    (0x0080, "NumLock"),
    (0x0100, "CapsLock"),
)


@dataclass(frozen=True)
class KeyEventInfo:
    event_type: str
    keysym: str
    keycode: int
    char: str
    state: int

    @classmethod
    def from_tk_event(cls, event_type: str, event: Any) -> KeyEventInfo:
        return cls(
            event_type=event_type,
            keysym=str(getattr(event, "keysym", "")),
            keycode=int(getattr(event, "keycode", 0)),
            char=str(getattr(event, "char", "")),
            state=int(getattr(event, "state", 0)),
        )


def format_key_event(info: KeyEventInfo) -> str:
    modifiers = [name for bit, name in MODIFIERS if info.state & bit]
    parts = [
        info.event_type,
        f"keysym={info.keysym or '<none>'}",
        f"keycode={info.keycode}",
    ]
    if info.char:
        parts.append(f"char={info.char!r}")
    if modifiers:
        parts.append("modifiers=" + "+".join(modifiers))
    parts.append(f"state=0x{info.state:04X}")
    return " | ".join(parts)


def run_app() -> None:
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("Vaydeer Key Tester")
    root.geometry("680x420")
    root.minsize(520, 320)

    title = ttk.Label(
        root,
        text="Press keys on the Vaydeer keypad while this window is focused.",
        font=("Segoe UI", 12),
    )
    title.pack(padx=16, pady=(16, 8), anchor="w")

    latest_var = tk.StringVar(value="Waiting for key press...")
    latest = ttk.Label(root, textvariable=latest_var, font=("Consolas", 18))
    latest.pack(padx=16, pady=(8, 12), fill="x")

    help_text = (
        "Tip: after flashing F13-F21, press each keypad key here. "
        "Run with pythonw.exe if you want no console window."
    )
    help_label = ttk.Label(root, text=help_text, wraplength=640)
    help_label.pack(padx=16, pady=(0, 12), anchor="w")

    history = tk.Listbox(root, font=("Consolas", 10), activestyle="none")
    history.pack(padx=16, pady=(0, 16), fill="both", expand=True)

    def record(event_type: str, event: Any) -> None:
        info = KeyEventInfo.from_tk_event(event_type, event)
        line = format_key_event(info)
        latest_var.set(line)
        history.insert(0, line)
        if history.size() > 200:
            history.delete(200, tk.END)

    root.bind("<KeyPress>", lambda event: record("press", event))
    root.bind("<KeyRelease>", lambda event: record("release", event))

    root.after(100, root.focus_force)
    root.mainloop()


def main() -> None:
    run_app()


if __name__ == "__main__":
    main()
