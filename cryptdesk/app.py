from __future__ import annotations

import socket
from typing import Any

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRect, QTimer, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QCloseEvent,
    QGuiApplication,
    QKeyEvent,
    QMouseEvent,
    QPixmap,
    QResizeEvent,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from cryptdesk.control import ControlError, RemoteController
from cryptdesk.network import ConnectionInfo, PeerConnection
from cryptdesk.screen import capture_primary_screen, pixmap_from_jpeg


def list_local_addresses() -> list[str]:
    addresses = {"127.0.0.1"}
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            addresses.add(info[4][0])
    except OSError:
        pass
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        addresses.add(probe.getsockname()[0])
        probe.close()
    except OSError:
        pass
    return sorted(address for address in addresses if address)


def primary_share_address(addresses: list[str]) -> str:
    for address in addresses:
        if address != "127.0.0.1":
            return address
    return addresses[0] if addresses else "127.0.0.1"


def copy_text(text: str) -> None:
    clipboard = QGuiApplication.clipboard()
    if clipboard is not None:
        clipboard.setText(text)


def add_shadow(widget: QWidget, blur: int = 32, y_offset: int = 10, alpha: int = 32) -> None:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, y_offset)
    shadow.setColor(QColor(15, 23, 42, alpha))
    widget.setGraphicsEffect(shadow)


def qt_button_name(button: Qt.MouseButton) -> str | None:
    mapping = {
        Qt.MouseButton.LeftButton: "left",
        Qt.MouseButton.RightButton: "right",
        Qt.MouseButton.MiddleButton: "middle",
    }
    return mapping.get(button)


def qt_key_payload(event: QKeyEvent) -> tuple[str | None, str]:
    special = {
        Qt.Key.Key_Alt: "alt",
        Qt.Key.Key_Backspace: "backspace",
        Qt.Key.Key_CapsLock: "caps_lock",
        Qt.Key.Key_Control: "ctrl",
        Qt.Key.Key_Delete: "delete",
        Qt.Key.Key_Down: "down",
        Qt.Key.Key_End: "end",
        Qt.Key.Key_Enter: "enter",
        Qt.Key.Key_Escape: "esc",
        Qt.Key.Key_Home: "home",
        Qt.Key.Key_Insert: "insert",
        Qt.Key.Key_Left: "left",
        Qt.Key.Key_Meta: "cmd",
        Qt.Key.Key_PageDown: "page_down",
        Qt.Key.Key_PageUp: "page_up",
        Qt.Key.Key_Return: "enter",
        Qt.Key.Key_Right: "right",
        Qt.Key.Key_Shift: "shift",
        Qt.Key.Key_Space: "space",
        Qt.Key.Key_Tab: "tab",
        Qt.Key.Key_Up: "up",
        Qt.Key.Key_F1: "f1",
        Qt.Key.Key_F2: "f2",
        Qt.Key.Key_F3: "f3",
        Qt.Key.Key_F4: "f4",
        Qt.Key.Key_F5: "f5",
        Qt.Key.Key_F6: "f6",
        Qt.Key.Key_F7: "f7",
        Qt.Key.Key_F8: "f8",
        Qt.Key.Key_F9: "f9",
        Qt.Key.Key_F10: "f10",
        Qt.Key.Key_F11: "f11",
        Qt.Key.Key_F12: "f12",
    }
    token = special.get(event.key())
    if token is not None:
        return token, ""
    text = event.text()
    if text and text.isprintable():
        return text, text
    return None, ""


def detail_value_label(text: str = "-") -> QLabel:
    label = QLabel(text)
    label.setObjectName("detailValue")
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    label.setWordWrap(True)
    return label


class CardFrame(QFrame):
    def __init__(self, object_name: str = "card", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        add_shadow(self)


class BadgeLabel(QLabel):
    _tones = {
        "idle": ("#e8edf4", "#516273", "#d4dde7"),
        "info": ("#d8f0ef", "#0f5d58", "#b4dfdc"),
        "online": ("#d6f5e7", "#0b6b45", "#b0e7ce"),
        "warn": ("#fff1d7", "#a35c00", "#f5d59c"),
        "danger": ("#fee2e2", "#b42318", "#f7b6b6"),
    }

    def __init__(self, text: str = "", tone: str = "idle", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(28)
        self.set_badge(text, tone)

    def set_badge(self, text: str, tone: str = "idle") -> None:
        background, foreground, border = self._tones.get(tone, self._tones["idle"])
        self.setText(text)
        self.setStyleSheet(
            "QLabel {"
            f"background-color: {background};"
            f"color: {foreground};"
            f"border: 1px solid {border};"
            "border-radius: 14px;"
            "padding: 4px 12px;"
            "font-size: 12px;"
            "font-weight: 700;"
            "letter-spacing: 0.25px;"
            "}"
        )


class MetricCard(CardFrame):
    def __init__(self, title: str, value: str, caption: str, parent: QWidget | None = None) -> None:
        super().__init__("metricCard", parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("metricTitle")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("metricValue")
        self.value_label.setWordWrap(True)
        self.caption_label = QLabel(caption)
        self.caption_label.setObjectName("metricCaption")
        self.caption_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.caption_label)

    def set_value(self, value: str, caption: str | None = None) -> None:
        self.value_label.setText(value)
        if caption is not None:
            self.caption_label.setText(caption)


class AnimatedStackedWidget(QStackedWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._animation: QPropertyAnimation | None = None

    def setCurrentIndexAnimated(self, index: int) -> None:
        if index == self.currentIndex():
            return
        super().setCurrentIndex(index)
        widget = self.currentWidget()
        if widget is None:
            return
        effect = QGraphicsDropShadowEffect(widget)
        effect.setBlurRadius(0)
        effect.setOffset(0, 0)
        effect.setColor(QColor(0, 0, 0, 0))
        widget.setGraphicsEffect(effect)
        self._animation = QPropertyAnimation(effect, b"color", self)
        self._animation.setDuration(180)
        self._animation.setStartValue(QColor(255, 255, 255, 0))
        self._animation.setEndValue(QColor(255, 255, 255, 0))
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.finished.connect(lambda: widget.setGraphicsEffect(None))
        self._animation.start()


class PageIntro(CardFrame):
    def __init__(self, eyebrow: str, title: str, subtitle: str, parent: QWidget | None = None) -> None:
        super().__init__("heroCard", parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(10)

        eyebrow_label = QLabel(eyebrow)
        eyebrow_label.setObjectName("eyebrow")
        title_label = QLabel(title)
        title_label.setObjectName("pageTitle")
        title_label.setWordWrap(True)
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("pageSubtitle")
        subtitle_label.setWordWrap(True)

        layout.addWidget(eyebrow_label)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        self.body_layout = QVBoxLayout()
        self.body_layout.setContentsMargins(0, 6, 0, 0)
        self.body_layout.setSpacing(16)
        layout.addLayout(self.body_layout)


class RemoteDisplayWidget(QLabel):
    control_event = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Connect to a device and wait for the first frame.", parent)
        self.setObjectName("remoteCanvas")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(480, 280)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self._control_enabled = False
        self._source_pixmap = QPixmap()
        self._display_rect = QRect()

    def clear_frame(self, message: str) -> None:
        self._source_pixmap = QPixmap()
        self._display_rect = QRect()
        self.setPixmap(QPixmap())
        self.setText(message)

    def set_remote_frame(self, pixmap: QPixmap) -> None:
        self._source_pixmap = pixmap
        self.setText("")
        self._render_pixmap()

    def set_control_enabled(self, enabled: bool) -> None:
        self._control_enabled = enabled
        self.setCursor(Qt.CursorShape.CrossCursor if enabled else Qt.CursorShape.ArrowCursor)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._render_pixmap()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        if not self._control_enabled:
            return
        normalized = self._normalized_position(event.position().toPoint())
        if normalized is None:
            return
        x_pos, y_pos = normalized
        self.control_event.emit({"kind": "mouse_move", "x": x_pos, "y": y_pos})

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)
        if not self._control_enabled:
            return
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        normalized = self._normalized_position(event.position().toPoint())
        button_name = qt_button_name(event.button())
        if normalized is None or button_name is None:
            return
        x_pos, y_pos = normalized
        self.control_event.emit({"kind": "mouse_press", "x": x_pos, "y": y_pos, "button": button_name})

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        if not self._control_enabled:
            return
        normalized = self._normalized_position(event.position().toPoint())
        button_name = qt_button_name(event.button())
        if normalized is None or button_name is None:
            return
        x_pos, y_pos = normalized
        self.control_event.emit({"kind": "mouse_release", "x": x_pos, "y": y_pos, "button": button_name})

    def wheelEvent(self, event: QWheelEvent) -> None:
        super().wheelEvent(event)
        if not self._control_enabled:
            return
        delta = event.angleDelta()
        self.control_event.emit({"kind": "wheel", "dx": delta.x() // 120, "dy": delta.y() // 120})

    def keyPressEvent(self, event: QKeyEvent) -> None:
        super().keyPressEvent(event)
        if not self._control_enabled or event.isAutoRepeat():
            return
        token, text = qt_key_payload(event)
        if token is None:
            return
        self.control_event.emit({"kind": "key_press", "token": token, "text": text})

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        super().keyReleaseEvent(event)
        if not self._control_enabled or event.isAutoRepeat():
            return
        token, text = qt_key_payload(event)
        if token is None:
            return
        self.control_event.emit({"kind": "key_release", "token": token, "text": text})

    def _render_pixmap(self) -> None:
        if self._source_pixmap.isNull():
            return
        scaled = self._source_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x_offset = max((self.width() - scaled.width()) // 2, 0)
        y_offset = max((self.height() - scaled.height()) // 2, 0)
        self._display_rect = QRect(x_offset, y_offset, scaled.width(), scaled.height())
        self.setPixmap(scaled)

    def _normalized_position(self, point: QPoint) -> tuple[float, float] | None:
        if self._display_rect.isNull() or not self._display_rect.contains(point):
            return None
        x_pos = (point.x() - self._display_rect.left()) / max(self._display_rect.width(), 1)
        y_pos = (point.y() - self._display_rect.top()) / max(self._display_rect.height(), 1)
        return min(max(x_pos, 0.0), 1.0), min(max(y_pos, 0.0), 1.0)


class ViewerSessionWindow(QMainWindow):
    input_toggled = Signal(bool)
    disconnect_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CryptDesk Session")
        self.resize(1600, 960)
        self._build_ui()

    def _build_ui(self) -> None:
        shell = QWidget()
        shell.setObjectName("sessionShell")
        self.setCentralWidget(shell)

        root = QVBoxLayout(shell)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(16)

        top_bar = QFrame()
        top_bar.setObjectName("sessionBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(18, 16, 18, 16)
        top_layout.setSpacing(14)

        heading_block = QVBoxLayout()
        heading_block.setSpacing(4)
        self.session_title = QLabel("Remote target")
        self.session_title.setObjectName("sessionTitle")
        self.session_subtitle = QLabel("Waiting for connection")
        self.session_subtitle.setObjectName("sessionSubtitle")
        self.session_subtitle.setWordWrap(True)
        self.session_meta = QLabel("Safety code: -")
        self.session_meta.setObjectName("sessionMeta")
        self.session_meta.setWordWrap(True)
        heading_block.addWidget(self.session_title)
        heading_block.addWidget(self.session_subtitle)
        heading_block.addWidget(self.session_meta)

        control_block = QHBoxLayout()
        control_block.setSpacing(10)
        self.session_badge = BadgeLabel("Standby", "idle")
        self.permission_badge = BadgeLabel("Input blocked", "warn")
        self.enable_input = QCheckBox("Enable remote input")
        self.enable_input.setObjectName("sessionCheckbox")
        self.enable_input.setEnabled(False)
        self.window_mode_button = QPushButton("Windowed")
        self.window_mode_button.setObjectName("secondaryButton")
        self.dashboard_button = QPushButton("Dashboard")
        self.dashboard_button.setObjectName("secondaryButton")
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setObjectName("secondaryButton")

        control_block.addWidget(self.session_badge)
        control_block.addWidget(self.permission_badge)
        control_block.addWidget(self.enable_input)
        control_block.addWidget(self.window_mode_button)
        control_block.addWidget(self.dashboard_button)
        control_block.addWidget(self.disconnect_button)

        top_layout.addLayout(heading_block, 1)
        top_layout.addLayout(control_block)
        root.addWidget(top_bar)

        self.display = RemoteDisplayWidget()
        self.display.setMinimumSize(0, 0)
        self.display.clear_frame("Connect to a device and wait for the first frame.")
        root.addWidget(self.display, 1)

        self.enable_input.toggled.connect(self.input_toggled.emit)
        self.dashboard_button.clicked.connect(self.hide)
        self.disconnect_button.clicked.connect(self.disconnect_requested.emit)
        self.window_mode_button.clicked.connect(self._toggle_window_mode)

    def show_session(self) -> None:
        self.show()
        self.showFullScreen()
        self.window_mode_button.setText("Windowed")
        self.raise_()
        self.activateWindow()

    def set_session_identity(self, peer_name: str, peer_address: str, safety_code: str) -> None:
        self.session_title.setText(peer_name)
        self.session_subtitle.setText(f"Connected to {peer_address}")
        self.session_meta.setText(f"Safety code: {safety_code}")
        self.session_badge.set_badge("Live", "online")

    def set_status_message(self, message: str, tone: str = "info") -> None:
        self.session_subtitle.setText(message)
        self.session_badge.set_badge(message.split()[0] if message else "Status", tone)

    def set_control_allowed(self, allowed: bool) -> None:
        self.permission_badge.set_badge("Input allowed" if allowed else "Input blocked", "online" if allowed else "warn")
        self.enable_input.setEnabled(allowed)
        if not allowed:
            self.set_input_checked(False)

    def set_input_checked(self, enabled: bool) -> None:
        previous = self.enable_input.blockSignals(True)
        self.enable_input.setChecked(enabled)
        self.enable_input.blockSignals(previous)
        self.display.set_control_enabled(enabled)

    def set_remote_frame(self, pixmap: QPixmap) -> None:
        self.display.set_remote_frame(pixmap)

    def reset_session(self, message: str) -> None:
        self.session_title.setText("Remote target")
        self.session_subtitle.setText(message)
        self.session_meta.setText("Safety code: -")
        self.session_badge.set_badge("Standby", "idle")
        self.set_control_allowed(False)
        self.display.clear_frame("Connect to a device and wait for the first frame.")
        self.hide()

    def _toggle_window_mode(self) -> None:
        if self.isFullScreen():
            self.showMaximized()
            self.window_mode_button.setText("Full screen")
            return
        self.showFullScreen()
        self.window_mode_button.setText("Windowed")


class HostPanel(QWidget):
    activity_changed = Signal(str, str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.connection = PeerConnection("host")
        self._controller: RemoteController | None = None
        self._addresses = list_local_addresses()
        self._build_ui()
        self._wire_signals()
        self.frame_timer = QTimer(self)
        self.frame_timer.setInterval(150)
        self.frame_timer.timeout.connect(self._send_frame)
        self._apply_idle_state("Ready to share this device.")

    def _build_ui(self) -> None:
        shell_layout = QVBoxLayout(self)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        page_scroll = QScrollArea()
        page_scroll.setWidgetResizable(True)
        page_scroll.setFrameShape(QFrame.Shape.NoFrame)
        page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        shell_layout.addWidget(page_scroll)

        page = QWidget()
        page_scroll.setWidget(page)
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 4, 0)
        root.setSpacing(22)

        intro = PageIntro(
            "RECEIVE SUPPORT",
            "Share this device with clear trust cues.",
            "Expose a direct route, verify the safety code, then decide if the viewer may take control.",
        )
        control_row = QHBoxLayout()
        control_row.setSpacing(12)

        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(48555)
        self.port_input.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.port_input.setMinimumWidth(120)

        self.secret_input = QLineEdit()
        self.secret_input.setPlaceholderText("Optional shared secret")
        self.secret_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.start_button = QPushButton("Start sharing")
        self.start_button.setObjectName("primaryButton")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("secondaryButton")
        self.stop_button.setEnabled(False)

        control_row.addWidget(self._field_stack("Port", self.port_input), 0)
        control_row.addWidget(self._field_stack("Shared secret", self.secret_input), 1)
        control_row.addWidget(self.start_button, 0, Qt.AlignmentFlag.AlignBottom)
        control_row.addWidget(self.stop_button, 0, Qt.AlignmentFlag.AlignBottom)
        intro.body_layout.addLayout(control_row)
        root.addWidget(intro)

        metrics = QHBoxLayout()
        metrics.setSpacing(16)
        self.route_metric = MetricCard("Share route", "-", "Auto-detected local endpoints")
        self.session_metric = MetricCard("Session", "Standby", "Nobody is connected yet")
        self.permission_metric = MetricCard("Remote control", "Blocked", "Host approval is required")
        metrics.addWidget(self.route_metric)
        metrics.addWidget(self.session_metric)
        metrics.addWidget(self.permission_metric)
        root.addLayout(metrics)

        content = QHBoxLayout()
        content.setSpacing(18)

        left_column = QVBoxLayout()
        left_column.setSpacing(18)

        device_card = CardFrame()
        device_layout = QVBoxLayout(device_card)
        device_layout.setContentsMargins(22, 22, 22, 22)
        device_layout.setSpacing(14)
        device_layout.addWidget(self._card_title("This device", "Share one of these routes with the viewer."))
        self.routes_value = detail_value_label()
        self.routes_value.setObjectName("routeValue")
        self.copy_share_button = QPushButton("Copy share details")
        self.copy_share_button.setObjectName("secondaryButton")
        device_layout.addWidget(self.routes_value)
        device_layout.addWidget(self.copy_share_button, 0, Qt.AlignmentFlag.AlignLeft)
        left_column.addWidget(device_card)

        trust_card = CardFrame()
        trust_layout = QVBoxLayout(trust_card)
        trust_layout.setContentsMargins(22, 22, 22, 22)
        trust_layout.setSpacing(14)
        trust_layout.addWidget(self._card_title("Consent and trust", "Make control explicit and easy to verify."))

        control_row_widget = QHBoxLayout()
        control_row_widget.setSpacing(10)
        self.allow_control = QCheckBox("Allow remote control")
        self.control_badge = BadgeLabel("Blocked", "warn")
        control_row_widget.addWidget(self.allow_control)
        control_row_widget.addStretch(1)
        control_row_widget.addWidget(self.control_badge)
        trust_layout.addLayout(control_row_widget)

        details = QGridLayout()
        details.setHorizontalSpacing(12)
        details.setVerticalSpacing(10)

        details.addWidget(self._detail_label("Session state"), 0, 0)
        self.status_value = detail_value_label()
        details.addWidget(self.status_value, 0, 1)

        details.addWidget(self._detail_label("Connected viewer"), 1, 0)
        self.peer_value = detail_value_label()
        details.addWidget(self.peer_value, 1, 1)

        details.addWidget(self._detail_label("Safety code"), 2, 0)
        self.safety_value = detail_value_label()
        details.addWidget(self.safety_value, 2, 1)
        trust_layout.addLayout(details)

        self.copy_safety_button = QPushButton("Copy safety code")
        self.copy_safety_button.setObjectName("secondaryButton")
        trust_layout.addWidget(self.copy_safety_button, 0, Qt.AlignmentFlag.AlignLeft)

        trust_note = QLabel(
            "Compare the safety code on both ends before enabling control. Keep remote control disabled until the other person is verified."
        )
        trust_note.setObjectName("supportText")
        trust_note.setWordWrap(True)
        trust_layout.addWidget(trust_note)
        left_column.addWidget(trust_card)
        left_column.addStretch(1)

        preview_card = CardFrame("displayShell")
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(20, 20, 20, 20)
        preview_layout.setSpacing(12)

        preview_toolbar = QHBoxLayout()
        preview_toolbar.setSpacing(12)
        self.preview_badge = BadgeLabel("Standby", "idle")
        self.preview_peer_value = QLabel("Waiting for a viewer")
        self.preview_peer_value.setObjectName("toolbarValue")
        preview_toolbar.addWidget(self.preview_badge)
        preview_toolbar.addWidget(self.preview_peer_value, 1)
        preview_layout.addLayout(preview_toolbar)

        self.preview = QLabel("Your primary display preview will appear here when a viewer connects.")
        self.preview.setObjectName("hostPreview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(480, 300)
        preview_layout.addWidget(self.preview, 1)

        content.addLayout(left_column, 1)
        content.addWidget(preview_card, 2)
        root.addLayout(content, 1)

    def _field_stack(self, label_text: str, widget: QWidget) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        layout.addWidget(label)
        layout.addWidget(widget)
        return container

    def _card_title(self, title: str, subtitle: str) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("cardSubtitle")
        subtitle_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        return wrapper

    def _detail_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("detailLabel")
        return label

    def _wire_signals(self) -> None:
        self.start_button.clicked.connect(self._start_hosting)
        self.stop_button.clicked.connect(self._stop_hosting)
        self.secret_input.returnPressed.connect(self._start_hosting)
        self.port_input.valueChanged.connect(self._refresh_share_details)
        self.copy_share_button.clicked.connect(self._copy_share_details)
        self.copy_safety_button.clicked.connect(self._copy_safety_code)
        self.allow_control.toggled.connect(self._push_control_state)
        self.allow_control.toggled.connect(self._update_control_status)

        self.connection.status_changed.connect(self._on_status_changed)
        self.connection.connected.connect(self._on_connected)
        self.connection.disconnected.connect(self._on_disconnected)
        self.connection.packet_received.connect(self._on_packet)
        self.connection.error_occurred.connect(self._on_error)

    def _start_hosting(self) -> None:
        self.connection.passphrase = self.secret_input.text().strip()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.session_metric.set_value("Listening", f"Port {self.port_input.value()} is open for one viewer")
        self.preview_badge.set_badge("Listening", "info")
        self.preview_peer_value.setText("Waiting for incoming connection")
        self.activity_changed.emit("Receive ready", "Waiting for a viewer to connect", "info")
        self.connection.start_host(port=self.port_input.value())
        self._refresh_share_details()

    def _stop_hosting(self) -> None:
        self.frame_timer.stop()
        self.connection.close("Sharing stopped")
        self._apply_idle_state("Sharing stopped.")

    def _on_status_changed(self, message: str) -> None:
        self.status_value.setText(message)

    def _on_connected(self, info: ConnectionInfo) -> None:
        self.peer_value.setText(f"{info.peer_name} ({info.peer_address})")
        self.safety_value.setText(info.safety_code)
        self.session_metric.set_value("Live session", f"Connected to {info.peer_name}")
        self.preview_badge.set_badge("Live", "online")
        self.preview_peer_value.setText(f"Viewer: {info.peer_name}")
        self.frame_timer.start()
        self._push_control_state()
        self.activity_changed.emit("Receive live", f"Sharing with {info.peer_name}", "online")

    def _on_disconnected(self, reason: str) -> None:
        self.frame_timer.stop()
        self._apply_idle_state(reason)

    def _on_error(self, message: str) -> None:
        self.status_value.setText(message)
        if not self.connection.is_connected:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.session_metric.set_value("Issue", "Check the port, firewall, or local permissions")
            self.preview_badge.set_badge("Issue", "danger")
            self.activity_changed.emit("Receive issue", message, "danger")

    def _on_packet(self, header: dict[str, Any], payload: bytes) -> None:
        if header.get("type") != "input":
            return
        if not self.allow_control.isChecked():
            return
        controller = self._ensure_controller()
        if controller is None:
            return
        try:
            controller.apply_event(header)
        except ControlError as exc:
            self.status_value.setText(str(exc))

    def _send_frame(self) -> None:
        if not self.connection.is_connected:
            return
        frame = capture_primary_screen()
        if frame is None:
            self.status_value.setText("Unable to capture the primary screen")
            return
        preview = frame.preview.scaled(
            self.preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview.setPixmap(preview)
        self.connection.send_message(
            {
                "type": "frame",
                "encoding": "jpeg",
                "width": frame.image_size.width(),
                "height": frame.image_size.height(),
            },
            frame.image_bytes,
        )

    def _push_control_state(self) -> None:
        self._update_control_status()
        if self.connection.is_connected:
            self.connection.send_message({"type": "control_state", "enabled": self.allow_control.isChecked()})

    def _update_control_status(self) -> None:
        if self.allow_control.isChecked():
            self.permission_metric.set_value("Armed", "Viewer may request mouse and keyboard control")
            self.control_badge.set_badge("Allowed", "online")
        else:
            self.permission_metric.set_value("Blocked", "Host approval is required before any input is accepted")
            self.control_badge.set_badge("Blocked", "warn")

    def _ensure_controller(self) -> RemoteController | None:
        if self._controller is not None:
            return self._controller
        try:
            self._controller = RemoteController()
        except ControlError as exc:
            self.status_value.setText(str(exc))
            self.allow_control.setChecked(False)
            return None
        return self._controller

    def _refresh_share_details(self) -> None:
        share_lines = [f"{address}:{self.port_input.value()}" for address in self._addresses]
        self.routes_value.setText("\n".join(share_lines))
        self.route_metric.set_value(primary_share_address(self._addresses), f"Port {self.port_input.value()} ready")

    def _copy_share_details(self) -> None:
        share_lines = [f"{address}:{self.port_input.value()}" for address in self._addresses]
        payload = "\n".join(share_lines)
        if self.secret_input.text().strip():
            payload += f"\nsecret={self.secret_input.text().strip()}"
        copy_text(payload)
        self.status_value.setText("Share details copied to clipboard.")

    def _copy_safety_code(self) -> None:
        if self.safety_value.text().strip() and self.safety_value.text().strip() != "-":
            copy_text(self.safety_value.text().strip())
            self.status_value.setText("Safety code copied to clipboard.")

    def _apply_idle_state(self, reason: str) -> None:
        self.status_value.setText(reason)
        self.peer_value.setText("-")
        self.safety_value.setText("-")
        self.preview.setPixmap(QPixmap())
        self.preview.setText("Your primary display preview will appear here when a viewer connects.")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.session_metric.set_value("Standby", "Start sharing when you are ready to accept a viewer")
        self.preview_badge.set_badge("Standby", "idle")
        self.preview_peer_value.setText("Waiting for a viewer")
        self.activity_changed.emit("Receive standby", reason, "idle")
        self._refresh_share_details()
        self._update_control_status()

    def shutdown(self) -> None:
        self.frame_timer.stop()
        self.connection.close(silent=True)


class ViewerPanel(QWidget):
    activity_changed = Signal(str, str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.connection = PeerConnection("viewer")
        self.host_control_enabled = False
        self.session_window = ViewerSessionWindow()
        self._build_ui()
        self._wire_signals()
        self._apply_idle_state("Ready to connect.")

    def _build_ui(self) -> None:
        shell_layout = QVBoxLayout(self)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        page_scroll = QScrollArea()
        page_scroll.setWidgetResizable(True)
        page_scroll.setFrameShape(QFrame.Shape.NoFrame)
        page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        shell_layout.addWidget(page_scroll)

        page = QWidget()
        page_scroll.setWidget(page)
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 4, 0)
        root.setSpacing(22)

        intro = PageIntro(
            "CONTROL A DEVICE",
            "Join a remote desktop in one clean pass.",
            "Enter the target route, connect directly, verify the safety code, then request control only if the host allows it.",
        )

        connect_row = QHBoxLayout()
        connect_row.setSpacing(12)

        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("192.168.1.24 or support-peer.local")
        self.host_input.setMinimumWidth(260)

        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(48555)
        self.port_input.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.port_input.setMinimumWidth(120)

        self.connect_button = QPushButton("Connect")
        self.connect_button.setObjectName("primaryButton")
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setObjectName("secondaryButton")
        self.disconnect_button.setEnabled(False)
        self.open_session_button = QPushButton("Open full screen")
        self.open_session_button.setObjectName("secondaryButton")
        self.open_session_button.setEnabled(False)

        connect_row.addWidget(self._field_stack("Remote route", self.host_input), 1)
        connect_row.addWidget(self._field_stack("Port", self.port_input), 0)
        connect_row.addWidget(self.connect_button, 0, Qt.AlignmentFlag.AlignBottom)
        connect_row.addWidget(self.disconnect_button, 0, Qt.AlignmentFlag.AlignBottom)
        connect_row.addWidget(self.open_session_button, 0, Qt.AlignmentFlag.AlignBottom)
        intro.body_layout.addLayout(connect_row)

        self.secret_input = QLineEdit()
        self.secret_input.setPlaceholderText("Optional shared secret")
        self.secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        intro.body_layout.addWidget(self._field_stack("Shared secret", self.secret_input))
        root.addWidget(intro)

        metrics = QHBoxLayout()
        metrics.setSpacing(16)
        self.target_metric = MetricCard("Target route", "-", "Enter an address or hostname")
        self.session_metric = MetricCard("Session", "Standby", "No active remote desktop")
        self.permission_metric = MetricCard("Input", "Pending", "Host must explicitly allow remote control")
        metrics.addWidget(self.target_metric)
        metrics.addWidget(self.session_metric)
        metrics.addWidget(self.permission_metric)
        root.addLayout(metrics)

        content = QHBoxLayout()
        content.setSpacing(18)

        display_card = CardFrame("displayShell")
        display_layout = QVBoxLayout(display_card)
        display_layout.setContentsMargins(20, 20, 20, 20)
        display_layout.setSpacing(12)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        self.session_badge = BadgeLabel("Standby", "idle")
        self.toolbar_peer_value = QLabel("No active session")
        self.toolbar_peer_value.setObjectName("toolbarValue")
        self.enable_input = QCheckBox("Enable remote input")
        self.enable_input.setEnabled(False)
        toolbar.addWidget(self.session_badge)
        toolbar.addWidget(self.toolbar_peer_value, 1)
        toolbar.addWidget(self.enable_input)
        display_layout.addLayout(toolbar)

        hint = QLabel("Click inside the session canvas before typing so keyboard focus stays on the remote desktop.")
        hint.setObjectName("supportText")
        hint.setWordWrap(True)
        display_layout.addWidget(hint)

        self.display = RemoteDisplayWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.display)
        display_layout.addWidget(scroll, 1)

        right_column = QVBoxLayout()
        right_column.setSpacing(18)

        session_card = CardFrame()
        session_layout = QVBoxLayout(session_card)
        session_layout.setContentsMargins(22, 22, 22, 22)
        session_layout.setSpacing(14)
        session_layout.addWidget(self._card_title("Session overview", "Track who you are connected to and what has been verified."))

        details = QGridLayout()
        details.setHorizontalSpacing(12)
        details.setVerticalSpacing(10)

        details.addWidget(self._detail_label("Status"), 0, 0)
        self.status_value = detail_value_label()
        details.addWidget(self.status_value, 0, 1)

        details.addWidget(self._detail_label("Remote device"), 1, 0)
        self.peer_value = detail_value_label()
        details.addWidget(self.peer_value, 1, 1)

        details.addWidget(self._detail_label("Safety code"), 2, 0)
        self.safety_value = detail_value_label()
        details.addWidget(self.safety_value, 2, 1)
        session_layout.addLayout(details)

        self.copy_safety_button = QPushButton("Copy safety code")
        self.copy_safety_button.setObjectName("secondaryButton")
        session_layout.addWidget(self.copy_safety_button, 0, Qt.AlignmentFlag.AlignLeft)
        right_column.addWidget(session_card)

        trust_card = CardFrame()
        trust_layout = QVBoxLayout(trust_card)
        trust_layout.setContentsMargins(22, 22, 22, 22)
        trust_layout.setSpacing(14)
        trust_layout.addWidget(self._card_title("Trust checks", "Do not send input until the host is confirmed."))

        self.permission_badge = BadgeLabel("Waiting", "warn")
        trust_layout.addWidget(self.permission_badge, 0, Qt.AlignmentFlag.AlignLeft)

        self.permission_value = QLabel("Remote control is unavailable until the host grants it.")
        self.permission_value.setObjectName("supportText")
        self.permission_value.setWordWrap(True)
        trust_layout.addWidget(self.permission_value)

        trust_note = QLabel(
            "Match the safety code on both ends. A matching code means the encrypted session fingerprint lines up for this connection."
        )
        trust_note.setObjectName("supportText")
        trust_note.setWordWrap(True)
        trust_layout.addWidget(trust_note)
        right_column.addWidget(trust_card)

        route_card = CardFrame()
        route_layout = QVBoxLayout(route_card)
        route_layout.setContentsMargins(22, 22, 22, 22)
        route_layout.setSpacing(12)
        route_layout.addWidget(self._card_title("Connection target", "Keep the route visible while you are troubleshooting."))
        self.target_value = detail_value_label()
        route_layout.addWidget(self.target_value)
        self.copy_target_button = QPushButton("Copy target route")
        self.copy_target_button.setObjectName("secondaryButton")
        route_layout.addWidget(self.copy_target_button, 0, Qt.AlignmentFlag.AlignLeft)
        right_column.addWidget(route_card)
        right_column.addStretch(1)

        content.addWidget(display_card, 2)
        content.addLayout(right_column, 1)
        root.addLayout(content, 1)

    def _field_stack(self, label_text: str, widget: QWidget) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        layout.addWidget(label)
        layout.addWidget(widget)
        return container

    def _card_title(self, title: str, subtitle: str) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("cardSubtitle")
        subtitle_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        return wrapper

    def _detail_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("detailLabel")
        return label

    def _wire_signals(self) -> None:
        self.connect_button.clicked.connect(self._connect)
        self.disconnect_button.clicked.connect(self._disconnect)
        self.open_session_button.clicked.connect(self._open_session_window)
        self.host_input.returnPressed.connect(self._connect)
        self.secret_input.returnPressed.connect(self._connect)
        self.enable_input.toggled.connect(self._toggle_input)
        self.host_input.textChanged.connect(self._refresh_target_summary)
        self.port_input.valueChanged.connect(self._refresh_target_summary)
        self.display.control_event.connect(self._send_control_event)
        self.copy_safety_button.clicked.connect(self._copy_safety_code)
        self.copy_target_button.clicked.connect(self._copy_target_route)
        self.session_window.input_toggled.connect(self._toggle_input)
        self.session_window.disconnect_requested.connect(self._disconnect)
        self.session_window.display.control_event.connect(self._send_control_event)

        self.connection.status_changed.connect(self._on_status_changed)
        self.connection.connected.connect(self._on_connected)
        self.connection.disconnected.connect(self._on_disconnected)
        self.connection.packet_received.connect(self._on_packet)
        self.connection.error_occurred.connect(self._on_error)

    def _connect(self) -> None:
        host = self.host_input.text().strip()
        if not host:
            self.status_value.setText("Enter a host address before connecting.")
            return
        self.connection.passphrase = self.secret_input.text().strip()
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        self.display.clear_frame("Connecting to the remote device...")
        self.session_metric.set_value("Connecting", f"Attempting {host}:{self.port_input.value()}")
        self.session_badge.set_badge("Connecting", "info")
        self.toolbar_peer_value.setText(f"Target: {host}:{self.port_input.value()}")
        self.activity_changed.emit("Control dialing", f"Connecting to {host}:{self.port_input.value()}", "info")
        self.connection.connect_to(host, self.port_input.value())
        self._refresh_target_summary()

    def _disconnect(self) -> None:
        self.connection.close("Viewer disconnected")
        self._apply_idle_state("Viewer disconnected.")

    def _on_status_changed(self, message: str) -> None:
        self.status_value.setText(message)
        if self.connection.is_connected:
            self.session_window.set_status_message(message, "online")

    def _on_connected(self, info: ConnectionInfo) -> None:
        self.peer_value.setText(f"{info.peer_name} ({info.peer_address})")
        self.safety_value.setText(info.safety_code)
        self.session_metric.set_value("Live session", f"Connected to {info.peer_name}")
        self.session_badge.set_badge("Live", "online")
        self.toolbar_peer_value.setText(f"Remote device: {info.peer_name}")
        self.open_session_button.setEnabled(True)
        self.session_window.set_session_identity(info.peer_name, info.peer_address, info.safety_code)
        self.session_window.set_control_allowed(self.host_control_enabled)
        self._set_input_toggle_state(False)
        self._open_session_window()
        self.activity_changed.emit("Control live", f"Connected to {info.peer_name}", "online")

    def _on_disconnected(self, reason: str) -> None:
        self._apply_idle_state(reason)

    def _on_error(self, message: str) -> None:
        self.status_value.setText(message)
        if not self.connection.is_connected:
            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)
            self.open_session_button.setEnabled(False)
            self.display.clear_frame("Connect to a device and wait for the first frame.")
            self.session_window.reset_session("Connection lost")
            self.session_metric.set_value("Issue", "Connection could not be established")
            self.session_badge.set_badge("Issue", "danger")
            self.activity_changed.emit("Control issue", message, "danger")

    def _on_packet(self, header: dict[str, Any], payload: bytes) -> None:
        message_type = header.get("type")
        if message_type == "frame":
            pixmap = pixmap_from_jpeg(payload)
            if pixmap.isNull():
                return
            self.display.set_remote_frame(pixmap)
            self.session_window.set_remote_frame(pixmap)
            return
        if message_type == "control_state":
            self.host_control_enabled = bool(header.get("enabled"))
            if self.host_control_enabled:
                self.permission_value.setText("The host allows remote control for this session.")
                self.permission_badge.set_badge("Allowed", "online")
                self.permission_metric.set_value("Armed", "You may enable remote input from the session toolbar")
            else:
                self.permission_value.setText("The host has disabled remote control for this session.")
                self.permission_badge.set_badge("Blocked", "warn")
                self.permission_metric.set_value("Pending", "Host must explicitly allow remote control")
            self.enable_input.setEnabled(self.host_control_enabled)
            self.session_window.set_control_allowed(self.host_control_enabled)
            if not self.host_control_enabled:
                self._set_input_toggle_state(False)

    def _toggle_input(self, enabled: bool) -> None:
        if enabled and not self.host_control_enabled:
            self._set_input_toggle_state(False)
            return
        self._set_input_toggle_state(enabled)
        self.permission_metric.set_value(
            "Live input" if enabled else ("Armed" if self.host_control_enabled else "Pending"),
            "Mouse and keyboard events are being sent" if enabled else (
                "You may enable remote input from the session toolbar" if self.host_control_enabled else
                "Host must explicitly allow remote control"
            ),
        )

    def _send_control_event(self, event: dict[str, Any]) -> None:
        if not self.connection.is_connected or not self.enable_input.isChecked() or not self.host_control_enabled:
            return
        packet = {"type": "input"}
        packet.update(event)
        self.connection.send_message(packet)

    def _refresh_target_summary(self) -> None:
        host = self.host_input.text().strip() or "-"
        route = f"{host}:{self.port_input.value()}" if host != "-" else "-"
        self.target_metric.set_value(route, "Direct route entered by the operator")
        self.target_value.setText(route)

    def _copy_safety_code(self) -> None:
        if self.safety_value.text().strip() and self.safety_value.text().strip() != "-":
            copy_text(self.safety_value.text().strip())
            self.status_value.setText("Safety code copied to clipboard.")

    def _copy_target_route(self) -> None:
        route = self.target_value.text().strip()
        if route and route != "-":
            copy_text(route)
            self.status_value.setText("Target route copied to clipboard.")

    def _open_session_window(self) -> None:
        if not self.connection.is_connected:
            return
        self.session_window.show_session()

    def _set_input_toggle_state(self, enabled: bool) -> None:
        previous = self.enable_input.blockSignals(True)
        self.enable_input.setChecked(enabled)
        self.enable_input.blockSignals(previous)
        self.display.set_control_enabled(enabled)
        self.session_window.set_input_checked(enabled)

    def _apply_idle_state(self, reason: str) -> None:
        self.status_value.setText(reason)
        self.peer_value.setText("-")
        self.safety_value.setText("-")
        self.permission_value.setText("Remote control is unavailable until the host grants it.")
        self.permission_badge.set_badge("Waiting", "warn")
        self.host_control_enabled = False
        self._set_input_toggle_state(False)
        self.enable_input.setEnabled(False)
        self.display.set_control_enabled(False)
        self.display.clear_frame("Connect to a device and wait for the first frame.")
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.open_session_button.setEnabled(False)
        self.session_metric.set_value("Standby", "No active remote desktop")
        self.permission_metric.set_value("Pending", "Host must explicitly allow remote control")
        self.session_badge.set_badge("Standby", "idle")
        self.toolbar_peer_value.setText("No active session")
        self.session_window.reset_session(reason)
        self.activity_changed.emit("Control standby", reason, "idle")
        self._refresh_target_summary()

    def shutdown(self) -> None:
        self.connection.close(silent=True)
        self.session_window.close()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CryptDesk")
        self.resize(1480, 940)
        self.setMinimumSize(1024, 720)
        self._build_ui()
        self._wire_signals()
        self._update_summary("Control standby", "Direct, encrypted desktop support", "idle")

    def _build_ui(self) -> None:
        shell = QWidget()
        shell.setObjectName("shell")
        self.setCentralWidget(shell)

        layout = QHBoxLayout(shell)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(18)

        sidebar_scroll = QScrollArea()
        sidebar_scroll.setObjectName("sidebarScroll")
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sidebar_scroll.setFixedWidth(252)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        sidebar_scroll.setWidget(self.sidebar)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(22, 22, 22, 22)
        sidebar_layout.setSpacing(18)

        brand_panel = CardFrame("brandPanel")
        brand_layout = QVBoxLayout(brand_panel)
        brand_layout.setContentsMargins(18, 18, 18, 18)
        brand_layout.setSpacing(8)
        brand_eyebrow = QLabel("CRYPTDESK")
        brand_eyebrow.setObjectName("brandEyebrow")
        brand_title = QLabel("Remote support without relay clutter.")
        brand_title.setObjectName("brandTitle")
        brand_title.setWordWrap(True)
        brand_body = QLabel("Peer to peer transport, end to end encryption, explicit host consent.")
        brand_body.setObjectName("brandBody")
        brand_body.setWordWrap(True)
        brand_layout.addWidget(brand_eyebrow)
        brand_layout.addWidget(brand_title)
        brand_layout.addWidget(brand_body)
        sidebar_layout.addWidget(brand_panel)

        nav_panel = CardFrame("sidebarCard")
        nav_layout = QVBoxLayout(nav_panel)
        nav_layout.setContentsMargins(14, 14, 14, 14)
        nav_layout.setSpacing(10)

        self.control_button = QPushButton("Control a device")
        self.control_button.setObjectName("navButton")
        self.control_button.setCheckable(True)
        self.receive_button = QPushButton("Share this device")
        self.receive_button.setObjectName("navButton")
        self.receive_button.setCheckable(True)

        button_group = QButtonGroup(self)
        button_group.setExclusive(True)
        button_group.addButton(self.control_button, 0)
        button_group.addButton(self.receive_button, 1)
        self.control_button.setChecked(True)

        nav_layout.addWidget(self.control_button)
        nav_layout.addWidget(self.receive_button)
        sidebar_layout.addWidget(nav_panel)

        summary_panel = CardFrame("sidebarCard")
        summary_layout = QVBoxLayout(summary_panel)
        summary_layout.setContentsMargins(18, 18, 18, 18)
        summary_layout.setSpacing(10)
        summary_title = QLabel("Session radar")
        summary_title.setObjectName("sidebarTitle")
        self.summary_badge = BadgeLabel("Standby", "idle")
        self.summary_heading = QLabel("No active session")
        self.summary_heading.setObjectName("summaryHeading")
        self.summary_heading.setWordWrap(True)
        self.summary_detail = QLabel("Direct, encrypted desktop support")
        self.summary_detail.setObjectName("summaryDetail")
        self.summary_detail.setWordWrap(True)
        summary_layout.addWidget(summary_title)
        summary_layout.addWidget(self.summary_badge, 0, Qt.AlignmentFlag.AlignLeft)
        summary_layout.addWidget(self.summary_heading)
        summary_layout.addWidget(self.summary_detail)
        sidebar_layout.addWidget(summary_panel)

        trust_panel = CardFrame("sidebarCard")
        trust_layout = QVBoxLayout(trust_panel)
        trust_layout.setContentsMargins(18, 18, 18, 18)
        trust_layout.setSpacing(8)
        trust_title = QLabel("Trust baseline")
        trust_title.setObjectName("sidebarTitle")
        trust_lines = QLabel(
            "Compare the safety code on both ends.\nOnly enable remote control after identity is clear.\nKeep the shared secret out of chat logs when possible."
        )
        trust_lines.setObjectName("brandBody")
        trust_lines.setWordWrap(True)
        trust_layout.addWidget(trust_title)
        trust_layout.addWidget(trust_lines)
        sidebar_layout.addWidget(trust_panel)
        sidebar_layout.addStretch(1)

        self.stack = AnimatedStackedWidget()
        self.viewer_panel = ViewerPanel()
        self.host_panel = HostPanel()
        self.stack.addWidget(self.viewer_panel)
        self.stack.addWidget(self.host_panel)

        content_shell = QWidget()
        content_shell.setObjectName("contentArea")
        content_layout = QVBoxLayout(content_shell)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self.stack)

        layout.addWidget(sidebar_scroll)
        layout.addWidget(content_shell, 1)

    def _wire_signals(self) -> None:
        self.control_button.clicked.connect(lambda: self.stack.setCurrentIndexAnimated(0))
        self.receive_button.clicked.connect(lambda: self.stack.setCurrentIndexAnimated(1))
        self.viewer_panel.activity_changed.connect(self._update_summary)
        self.host_panel.activity_changed.connect(self._update_summary)

    def _update_summary(self, heading: str, detail: str, tone: str) -> None:
        self.summary_badge.set_badge(heading.split()[-1], tone)
        self.summary_heading.setText(heading)
        self.summary_detail.setText(detail)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.host_panel.shutdown()
        self.viewer_panel.shutdown()
        super().closeEvent(event)


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("CryptDesk")
    app.setStyleSheet(
        """
        QWidget {
            color: #122033;
            font-family: "Segoe UI Variable Text", "Segoe UI";
            font-size: 14px;
        }
        QWidget#shell {
            background-color: #edf2f7;
        }
        QWidget#contentArea {
            background: transparent;
        }
        QScrollArea#sidebarScroll {
            border: 0;
            background: transparent;
        }
        QFrame#sidebar {
            background-color: #0f172a;
            border-radius: 30px;
        }
        QFrame#brandPanel {
            background: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 1,
                stop: 0 #113247,
                stop: 1 #0f766e
            );
            border-radius: 24px;
        }
        QWidget#sessionShell {
            background-color: #08111f;
        }
        QFrame#sessionBar {
            background-color: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 24px;
        }
        QFrame#sidebarCard {
            background-color: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 22px;
        }
        QLabel#brandEyebrow {
            color: rgba(255, 255, 255, 0.72);
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1.6px;
        }
        QLabel#brandTitle {
            color: white;
            font-size: 24px;
            font-weight: 700;
        }
        QLabel#brandBody, QLabel#sidebarTitle, QLabel#summaryHeading, QLabel#summaryDetail {
            color: rgba(255, 255, 255, 0.88);
        }
        QLabel#sidebarTitle {
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.6px;
        }
        QLabel#summaryHeading {
            font-size: 18px;
            font-weight: 700;
        }
        QLabel#summaryDetail {
            color: rgba(255, 255, 255, 0.74);
            line-height: 1.35;
        }
        QLabel#sessionTitle {
            color: white;
            font-size: 24px;
            font-weight: 700;
        }
        QLabel#sessionSubtitle {
            color: rgba(255, 255, 255, 0.82);
            font-size: 15px;
        }
        QLabel#sessionMeta {
            color: rgba(148, 163, 184, 0.96);
            font-size: 13px;
            font-weight: 600;
        }
        QPushButton#navButton {
            background-color: transparent;
            color: rgba(255, 255, 255, 0.86);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 18px;
            text-align: left;
            padding: 14px 16px;
            font-size: 15px;
            font-weight: 600;
        }
        QPushButton#navButton:hover {
            background-color: rgba(255, 255, 255, 0.07);
        }
        QPushButton#navButton:checked {
            background-color: rgba(36, 212, 191, 0.18);
            border-color: rgba(94, 234, 212, 0.5);
            color: white;
        }
        QFrame#heroCard {
            background: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 1,
                stop: 0 #ffffff,
                stop: 0.72 #f5fbfa,
                stop: 1 #e3f6f3
            );
            border: 1px solid #d8e7e5;
            border-radius: 28px;
        }
        QFrame#card, QFrame#metricCard, QFrame#displayShell {
            background-color: #ffffff;
            border: 1px solid #d9e3ee;
            border-radius: 24px;
        }
        QLabel#eyebrow {
            color: #0f766e;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1.6px;
        }
        QLabel#pageTitle {
            color: #112033;
            font-size: 32px;
            font-weight: 700;
        }
        QLabel#pageSubtitle {
            color: #55657b;
            font-size: 15px;
            line-height: 1.4;
        }
        QLabel#fieldLabel {
            color: #425469;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        QLabel#cardTitle {
            color: #122033;
            font-size: 18px;
            font-weight: 700;
        }
        QLabel#cardSubtitle, QLabel#supportText, QLabel#toolbarValue {
            color: #5f7084;
            line-height: 1.35;
        }
        QLabel#detailLabel {
            color: #5f7084;
            font-size: 13px;
            font-weight: 600;
        }
        QLabel#detailValue {
            color: #122033;
            font-size: 14px;
            font-weight: 600;
        }
        QLabel#routeValue {
            color: #122033;
            font-size: 16px;
            font-weight: 600;
            background-color: #f8fafc;
            border: 1px dashed #c8d4e0;
            border-radius: 18px;
            padding: 16px;
        }
        QLabel#metricTitle {
            color: #607086;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.65px;
            text-transform: uppercase;
        }
        QLabel#metricValue {
            color: #122033;
            font-size: 24px;
            font-weight: 700;
        }
        QLabel#metricCaption {
            color: #66788e;
            line-height: 1.35;
        }
        QLabel#remoteCanvas, QLabel#hostPreview {
            background: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 1,
                stop: 0 #0f172a,
                stop: 1 #162841
            );
            color: rgba(255, 255, 255, 0.82);
            border: 1px solid #1d3654;
            border-radius: 22px;
            padding: 24px;
            font-size: 15px;
        }
        QScrollArea {
            border: 0;
            background: transparent;
        }
        QLineEdit, QSpinBox {
            background-color: white;
            color: #122033;
            border: 1px solid #cfd9e4;
            border-radius: 16px;
            padding: 12px 14px;
            min-height: 24px;
            selection-background-color: #bfdbfe;
        }
        QLineEdit:focus, QSpinBox:focus {
            border: 1px solid #0f766e;
        }
        QPushButton {
            min-height: 46px;
            border-radius: 16px;
            padding: 0 18px;
            font-size: 14px;
            font-weight: 700;
            border: 0;
        }
        QPushButton#primaryButton {
            background-color: #0f766e;
            color: white;
        }
        QPushButton#primaryButton:hover {
            background-color: #0b615b;
        }
        QPushButton#secondaryButton {
            background-color: #eef3f8;
            color: #1f2d3d;
            border: 1px solid #d5e0eb;
        }
        QPushButton#secondaryButton:hover {
            background-color: #e5edf5;
        }
        QWidget#sessionShell QPushButton#secondaryButton {
            background-color: rgba(255, 255, 255, 0.1);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.14);
        }
        QWidget#sessionShell QPushButton#secondaryButton:hover {
            background-color: rgba(255, 255, 255, 0.16);
        }
        QPushButton:disabled {
            background-color: #d8e1ea;
            color: #7d8c9d;
        }
        QCheckBox {
            color: #122033;
            font-weight: 600;
            spacing: 10px;
        }
        QWidget#sessionShell QCheckBox {
            color: rgba(255, 255, 255, 0.94);
        }
        QCheckBox::indicator {
            width: 20px;
            height: 20px;
            border-radius: 6px;
            border: 1px solid #b9c6d3;
            background: white;
        }
        QCheckBox::indicator:checked {
            background: #0f766e;
            border-color: #0f766e;
        }
        """
    )
    window = MainWindow()
    window.showFullScreen()
    return app.exec()
