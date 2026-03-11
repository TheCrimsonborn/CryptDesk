from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QSize, Qt
from PySide6.QtGui import QGuiApplication, QPixmap


@dataclass(slots=True)
class CapturedFrame:
    image_bytes: bytes
    image_size: QSize
    preview: QPixmap


def capture_primary_screen(max_width: int = 1280, quality: int = 70) -> CapturedFrame | None:
    app = QGuiApplication.instance()
    if app is None:
        return None
    screen = app.primaryScreen()
    if screen is None:
        return None
    pixmap = screen.grabWindow(0)
    if pixmap.isNull():
        return None
    if max_width > 0 and pixmap.width() > max_width:
        pixmap = pixmap.scaledToWidth(max_width, Qt.TransformationMode.SmoothTransformation)
    buffer_array = QByteArray()
    buffer = QBuffer(buffer_array)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buffer, "JPEG", quality)
    return CapturedFrame(image_bytes=bytes(buffer_array), image_size=pixmap.size(), preview=pixmap)


def pixmap_from_jpeg(data: bytes) -> QPixmap:
    pixmap = QPixmap()
    pixmap.loadFromData(data, "JPEG")
    return pixmap
