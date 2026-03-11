from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6.QtGui import QGuiApplication


class ControlError(RuntimeError):
    """Raised when the local machine cannot inject remote input."""


@dataclass(slots=True)
class ScreenGeometry:
    left: int
    top: int
    width: int
    height: int


class RemoteController:
    def __init__(self) -> None:
        try:
            from pynput.keyboard import Controller as KeyboardController
            from pynput.keyboard import Key
            from pynput.mouse import Button
            from pynput.mouse import Controller as MouseController
        except Exception as exc:  # pragma: no cover - import environment specific
            raise ControlError(f"Unable to load input control backend: {exc}") from exc
        self._keyboard = KeyboardController()
        self._mouse = MouseController()
        self._buttons = {
            "left": Button.left,
            "right": Button.right,
            "middle": Button.middle,
        }
        self._special_keys = {
            "alt": Key.alt,
            "backspace": Key.backspace,
            "caps_lock": Key.caps_lock,
            "cmd": Key.cmd,
            "ctrl": Key.ctrl,
            "delete": Key.delete,
            "down": Key.down,
            "end": Key.end,
            "enter": Key.enter,
            "esc": Key.esc,
            "f1": Key.f1,
            "f2": Key.f2,
            "f3": Key.f3,
            "f4": Key.f4,
            "f5": Key.f5,
            "f6": Key.f6,
            "f7": Key.f7,
            "f8": Key.f8,
            "f9": Key.f9,
            "f10": Key.f10,
            "f11": Key.f11,
            "f12": Key.f12,
            "home": Key.home,
            "insert": Key.insert,
            "left": Key.left,
            "page_down": Key.page_down,
            "page_up": Key.page_up,
            "right": Key.right,
            "shift": Key.shift,
            "space": Key.space,
            "tab": Key.tab,
            "up": Key.up,
        }

    def apply_event(self, event: dict[str, Any]) -> None:
        kind = event.get("kind")
        if kind == "mouse_move":
            self.move_mouse(float(event["x"]), float(event["y"]))
            return
        if kind == "mouse_press":
            self.move_mouse(float(event["x"]), float(event["y"]))
            self._mouse.press(self._resolve_button(str(event.get("button", "left"))))
            return
        if kind == "mouse_release":
            self.move_mouse(float(event["x"]), float(event["y"]))
            self._mouse.release(self._resolve_button(str(event.get("button", "left"))))
            return
        if kind == "wheel":
            self._mouse.scroll(int(event.get("dx", 0)), int(event.get("dy", 0)))
            return
        if kind == "key_press":
            self._keyboard.press(self._resolve_key(str(event.get("token", "")), str(event.get("text", ""))))
            return
        if kind == "key_release":
            self._keyboard.release(self._resolve_key(str(event.get("token", "")), str(event.get("text", ""))))
            return
        raise ControlError(f"Unsupported input event: {kind}")

    def move_mouse(self, normalized_x: float, normalized_y: float) -> None:
        geometry = self._primary_screen_geometry()
        bounded_x = min(max(normalized_x, 0.0), 1.0)
        bounded_y = min(max(normalized_y, 0.0), 1.0)
        x_pos = geometry.left + round(bounded_x * max(geometry.width - 1, 1))
        y_pos = geometry.top + round(bounded_y * max(geometry.height - 1, 1))
        self._mouse.position = (x_pos, y_pos)

    def _primary_screen_geometry(self) -> ScreenGeometry:
        app = QGuiApplication.instance()
        if app is None or app.primaryScreen() is None:
            raise ControlError("No primary screen is available for remote control")
        geometry = app.primaryScreen().geometry()
        return ScreenGeometry(
            left=geometry.left(),
            top=geometry.top(),
            width=geometry.width(),
            height=geometry.height(),
        )

    def _resolve_button(self, name: str) -> Any:
        button = self._buttons.get(name)
        if button is None:
            raise ControlError(f"Unsupported mouse button: {name}")
        return button

    def _resolve_key(self, token: str, text: str) -> Any:
        if text:
            return text
        key = self._special_keys.get(token)
        if key is None:
            raise ControlError(f"Unsupported keyboard key: {token}")
        return key
