from __future__ import annotations

import ipaddress
import socket
import struct
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterable

from PySide6.QtCore import Qt, QObject, QSettings, QThread, Signal, QRectF, QPointF
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QAbstractSpinBox,
    QButtonGroup,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "3Dropia"
VERSION = "0.4.4"
AUTHOR = "enderlit"
REPO_URL = "https://github.com/endercodezz/3Dropia"

SUPPORTED_EXTENSIONS = (".cia", ".tik", ".cetk", ".3dsx")
DEFAULT_FBI_PORT = 5000
DEFAULT_HTTP_PORT = 8080

THEMES = {
    "white": {
        "name": "White",
        "window": "#F4F5F7",
        "surface": "#FFFFFF",
        "surface_alt": "#F7F8FA",
        "border": "#DADDE2",
        "border_hover": "#B7BDC6",
        "text": "#17191C",
        "muted": "#69717C",
        "accent": "#2F6FEB",
        "accent_hover": "#255DCA",
        "accent_text": "#FFFFFF",
        "link": "#1559B7",
        "danger": "#C83E46",
        "progress_bg": "#E6E9EE",
        "menu_bg": "#FFFFFF",
        "menu_selected": "#EAF1FF",
    },
    "black": {
        "name": "Black",
        "window": "#151515",
        "surface": "#1E1E1E",
        "surface_alt": "#252525",
        "border": "#363636",
        "border_hover": "#505050",
        "text": "#F3F3F3",
        "muted": "#A4A4A7",
        "accent": "#5B8CFF",
        "accent_hover": "#709BFF",
        "accent_text": "#FFFFFF",
        "link": "#5B8CFF",
        "danger": "#FF727A",
        "progress_bg": "#2C2C2C",
        "menu_bg": "#222222",
        "menu_selected": "#343A46",
    },
}


def theme(theme_id: str) -> dict:
    return THEMES.get(theme_id, THEMES["white"])


def human_size(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{value} B"


def valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value.strip())
        return True
    except ValueError:
        return False


def detect_host_ip(target_ip: str) -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect((target_ip, 9))
        detected = sock.getsockname()[0]
        if detected and detected != "0.0.0.0":
            return detected
    finally:
        sock.close()

    detected = socket.gethostbyname(socket.gethostname())
    if not detected or detected == "127.0.0.1":
        raise RuntimeError("Could not detect this PC's LAN IP.")
    return detected



def apply_link_palette(theme_id: str) -> None:
    """Set rich-text QLabel link color explicitly.

    Qt rich-text anchors use QPalette.Link, which is more reliable than
    trying to style <a> tags through QSS on Windows.
    """
    app = QApplication.instance()
    if app is None:
        return

    t = theme(theme_id)
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Link, QColor(t["link"]))
    palette.setColor(QPalette.ColorRole.LinkVisited, QColor(t["link"]))
    app.setPalette(palette)


def stylesheet(theme_id: str) -> str:
    t = theme(theme_id)
    return f"""
    QWidget {{
        font-family: "Segoe UI", sans-serif;
        font-size: 10pt;
        color: {t["text"]};
    }}

    QMainWindow, QDialog, QWidget#Root {{
        background: {t["window"]};
    }}

    QFrame#Card {{
        background: {t["surface"]};
        border: 1px solid {t["border"]};
        border-radius: 10px;
    }}

    QLabel#Title {{
        font-size: 22pt;
        font-weight: 650;
    }}

    QLabel#SectionTitle {{
        font-size: 11pt;
        font-weight: 600;
    }}

    QLabel#Muted, QLabel#Footer {{
        color: {t["muted"]};
    }}

    QLabel#Legal {{
        color: {t["muted"]};
        font-size: 8.5pt;
    }}

    QPushButton {{
        min-height: 34px;
        padding: 0 13px;
        border-radius: 7px;
        background: {t["surface"]};
        border: 1px solid {t["border"]};
        font-weight: 500;
    }}

    QPushButton:hover {{
        border-color: {t["border_hover"]};
        background: {t["surface_alt"]};
    }}

    QPushButton:pressed {{
        padding-top: 1px;
    }}

    QPushButton#Primary {{
        min-height: 38px;
        min-width: 135px;
        background: {t["accent"]};
        color: {t["accent_text"]};
        border: 1px solid {t["accent"]};
        font-weight: 600;
    }}

    QPushButton#Primary:hover {{
        background: {t["accent_hover"]};
        border-color: {t["accent_hover"]};
    }}

    QPushButton#Primary:disabled {{
        background: {t["surface_alt"]};
        border-color: {t["border"]};
        color: {t["muted"]};
    }}

    QPushButton#Danger {{
        color: {t["danger"]};
    }}

    QLineEdit, QSpinBox {{
        min-height: 34px;
        padding: 0 9px;
        border-radius: 7px;
        background: {t["surface"]};
        border: 1px solid {t["border"]};
        selection-background-color: {t["accent"]};
        selection-color: {t["accent_text"]};
    }}

    QLineEdit:focus, QSpinBox:focus {{
        border-color: {t["accent"]};
    }}

    QPushButton#ThemeButton {{
        min-height: 38px;
        background: {t["surface"]};
        color: {t["text"]};
        border: 1px solid {t["border"]};
        font-weight: 500;
    }}

    QPushButton#ThemeButton:hover {{
        background: {t["surface_alt"]};
        border-color: {t["border_hover"]};
    }}

    QPushButton#ThemeButton:checked {{
        background: {t["surface_alt"]};
        color: {t["text"]};
        border: 2px solid {t["accent"]};
        font-weight: 600;
    }}

    QProgressBar {{
        min-height: 5px;
        max-height: 5px;
        background: {t["progress_bg"]};
        border: none;
        border-radius: 2px;
    }}

    QProgressBar::chunk {{
        background: {t["accent"]};
        border-radius: 2px;
    }}

    QLabel a {{
        color: {t["link"]};
        text-decoration: none;
    }}
    """


def build_icon(size: int = 256) -> QIcon:
    """
    Simple 3Dropia mark:
      - rounded blue square
      - a clean '3'
      - drop arrow landing into a tray
    """
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)

    pad = size * 0.045
    rect = QRectF(pad, pad, size - pad * 2, size - pad * 2)

    p.setBrush(QColor("#2F6FEB"))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(rect, size * 0.22, size * 0.22)

    # subtle inner highlight
    p.setPen(QPen(QColor(255, 255, 255, 35), max(1.0, size * 0.008)))
    p.setBrush(Qt.NoBrush)
    inner = rect.adjusted(size * 0.025, size * 0.025, -size * 0.025, -size * 0.025)
    p.drawRoundedRect(inner, size * 0.19, size * 0.19)

    white = QColor("#FFFFFF")

    # "3"
    p.setPen(white)
    p.setFont(QFont("Segoe UI", int(size * 0.25), QFont.Bold))
    three_rect = QRectF(size * 0.13, size * 0.19, size * 0.36, size * 0.52)
    p.drawText(three_rect, Qt.AlignCenter, "3")

    # Drop arrow
    pen = QPen(white, size * 0.055, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    x = size * 0.66
    p.drawLine(QPointF(x, size * 0.27), QPointF(x, size * 0.59))
    p.drawLine(QPointF(x, size * 0.59), QPointF(size * 0.56, size * 0.49))
    p.drawLine(QPointF(x, size * 0.59), QPointF(size * 0.76, size * 0.49))

    # Tray
    tray = QPainterPath()
    tray.moveTo(size * 0.53, size * 0.68)
    tray.lineTo(size * 0.53, size * 0.73)
    tray.quadTo(size * 0.53, size * 0.78, size * 0.58, size * 0.78)
    tray.lineTo(size * 0.75, size * 0.78)
    tray.quadTo(size * 0.80, size * 0.78, size * 0.80, size * 0.73)
    tray.lineTo(size * 0.80, size * 0.68)
    p.drawPath(tray)

    p.end()
    return QIcon(pm)


class DropArea(QFrame):
    pathsDropped = Signal(list)
    browseRequested = Signal()
    clearRequested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Card")
        self.setAcceptDrops(True)
        self.setMinimumHeight(190)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(12)

        text_box = QVBoxLayout()
        text_box.setSpacing(4)

        self.title = QLabel("Choose files to send")
        self.title.setObjectName("SectionTitle")

        self.subtitle = QLabel("Drop files here, or select them from your computer.")
        self.subtitle.setObjectName("Muted")
        self.subtitle.setWordWrap(True)

        self.formats = QLabel("Supported: .cia, .tik, .cetk, .3dsx")
        self.formats.setObjectName("Muted")

        text_box.addWidget(self.title)
        text_box.addWidget(self.subtitle)
        text_box.addWidget(self.formats)

        self.browse_button = QPushButton("Browse…")
        self.browse_button.setMinimumWidth(100)
        self.browse_button.clicked.connect(self.browseRequested.emit)

        top.addLayout(text_box, 1)
        top.addWidget(self.browse_button, 0, Qt.AlignTop)

        layout.addLayout(top)

        self.selection_frame = QFrame()
        self.selection_frame.setObjectName("Card")
        selection_layout = QHBoxLayout(self.selection_frame)
        selection_layout.setContentsMargins(13, 10, 13, 10)
        selection_layout.setSpacing(10)

        selection_text = QVBoxLayout()
        selection_text.setSpacing(2)

        self.selection_title = QLabel("No files selected")
        self.selection_title.setObjectName("SectionTitle")

        self.selection_detail = QLabel("Your selected files will appear here.")
        self.selection_detail.setObjectName("Muted")
        self.selection_detail.setWordWrap(True)

        selection_text.addWidget(self.selection_title)
        selection_text.addWidget(self.selection_detail)

        self.clear_button = QPushButton("Clear")
        self.clear_button.setObjectName("Danger")
        self.clear_button.clicked.connect(self.clearRequested.emit)
        self.clear_button.hide()

        selection_layout.addLayout(selection_text, 1)
        selection_layout.addWidget(self.clear_button, 0, Qt.AlignVCenter)

        layout.addWidget(self.selection_frame)

    def set_files(self, files: list[Path]) -> None:
        if not files:
            self.selection_title.setText("No files selected")
            self.selection_detail.setText("Your selected files will appear here.")
            self.clear_button.hide()
            return

        total = sum(p.stat().st_size if p.exists() else 0 for p in files)
        self.selection_title.setText(
            f"{len(files)} file{'s' if len(files) != 1 else ''} selected · {human_size(total)}"
        )

        names = [p.name for p in files]
        if len(names) <= 2:
            detail = " · ".join(names)
        else:
            detail = f"{names[0]} · {names[1]} · +{len(names) - 2} more"

        self.selection_detail.setText(detail)
        self.clear_button.show()

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.pathsDropped.emit(paths)
            event.acceptProposedAction()


class ReusableHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def make_handler(route_map: dict[str, Path], on_bytes):
    class FileHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, _format: str, *args) -> None:
            return

        def _resolve(self) -> Path | None:
            route = urllib.parse.urlsplit(self.path).path
            return route_map.get(route)

        def do_HEAD(self) -> None:
            path = self._resolve()
            if path is None or not path.is_file():
                self.send_error(404)
                return

            size = path.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.send_header("Connection", "close")
            self.end_headers()

        def do_GET(self) -> None:
            path = self._resolve()
            if path is None or not path.is_file():
                self.send_error(404)
                return

            size = path.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.send_header("Connection", "close")
            self.end_headers()

            with path.open("rb") as handle:
                while True:
                    chunk = handle.read(1024 * 1024)
                    if not chunk:
                        break

                    try:
                        self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionResetError):
                        break

                    on_bytes(len(chunk), path.name)

    return FileHandler


class SenderWorker(QObject):
    status = Signal(str)
    progress = Signal(int, int, str)
    finished = Signal(bool, str)

    def __init__(
        self,
        files: list[Path],
        target_ip: str,
        fbi_port: int,
        http_port: int,
        host_ip: str,
    ) -> None:
        super().__init__()

        self.files = files
        self.target_ip = target_ip
        self.fbi_port = fbi_port
        self.http_port = http_port
        self.host_ip = host_ip

        self._cancel = threading.Event()
        self._bytes_sent = 0
        self._bytes_lock = threading.Lock()
        self._total = sum(p.stat().st_size for p in files)

    def cancel(self) -> None:
        self._cancel.set()

    def _on_bytes(self, count: int, name: str) -> None:
        with self._bytes_lock:
            self._bytes_sent += count
            current = self._bytes_sent

        self.progress.emit(min(current, self._total), self._total, name)

    def run(self) -> None:
        server = None
        server_thread = None
        sock = None

        try:
            self.status.emit("Preparing local server…")

            host_ip = self.host_ip.strip()
            if not host_ip or host_ip.lower() == "auto":
                host_ip = detect_host_ip(self.target_ip)

            routes: dict[str, Path] = {}
            urls: list[str] = []

            for index, path in enumerate(self.files, start=1):
                safe_name = urllib.parse.quote(path.name, safe="")
                route = f"/{index}-{safe_name}"
                routes[route] = path
                urls.append(f"{host_ip}:{self.http_port}{route}")

            handler = make_handler(routes, self._on_bytes)
            server = ReusableHTTPServer(("", self.http_port), handler)

            server_thread = threading.Thread(
                target=server.serve_forever,
                daemon=True,
            )
            server_thread.start()

            if self._cancel.is_set():
                raise RuntimeError("Cancelled.")

            payload_text = "\n".join(urls)
            if len(urls) > 1:
                payload_text += "\n"

            payload = payload_text.encode("ascii")

            self.status.emit("Waiting for FBI — Remote Install → Receive URLs")

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(8.0)
            sock.connect((self.target_ip, self.fbi_port))

            if self._cancel.is_set():
                raise RuntimeError("Cancelled.")

            sock.sendall(struct.pack("!L", len(payload)) + payload)
            sock.settimeout(0.5)

            self.status.emit("URL list sent. Confirm the install on your 3DS.")
            self.progress.emit(0, self._total, "")

            while not self._cancel.is_set():
                try:
                    reply = sock.recv(1)

                    if reply:
                        break

                    if reply == b"":
                        raise ConnectionError("The 3DS closed the connection.")

                except socket.timeout:
                    continue

            if self._cancel.is_set():
                raise RuntimeError("Cancelled.")

            self.progress.emit(self._total, self._total, "")
            self.finished.emit(True, "Done.")

        except OSError as exc:
            if self._cancel.is_set():
                self.finished.emit(False, "Cancelled.")
            elif getattr(exc, "winerror", None) == 10048 or getattr(exc, "errno", None) in (48, 98):
                self.finished.emit(
                    False,
                    f"HTTP port {self.http_port} is already in use. Change it in Settings.",
                )
            else:
                self.finished.emit(False, f"Network error: {exc}")

        except Exception as exc:
            self.finished.emit(False, str(exc) or exc.__class__.__name__)

        finally:
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass

            if server is not None:
                try:
                    server.shutdown()
                except Exception:
                    pass

                try:
                    server.server_close()
                except Exception:
                    pass

            if server_thread is not None and server_thread.is_alive():
                server_thread.join(timeout=1.0)


class SettingsDialog(QDialog):
    saved = Signal()

    def __init__(self, settings: QSettings, parent=None) -> None:
        super().__init__(parent)

        self.settings = settings
        self.setWindowTitle("3Dropia Settings")
        self.setModal(True)
        self.setMinimumWidth(470)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(18)

        title = QLabel("Settings")
        title.setObjectName("Title")

        subtitle = QLabel("Connection and appearance")
        subtitle.setObjectName("Muted")

        root.addWidget(title)
        root.addWidget(subtitle)

        form = QGridLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)

        self.ip_edit = QLineEdit(str(settings.value("target_ip", "")))
        self.ip_edit.setPlaceholderText("192.168.1.123")

        self.fbi_port = QSpinBox()
        self.fbi_port.setRange(1, 65535)
        self.fbi_port.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.fbi_port.setValue(int(settings.value("fbi_port", DEFAULT_FBI_PORT)))

        self.http_port = QSpinBox()
        self.http_port.setRange(1, 65535)
        self.http_port.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.http_port.setValue(int(settings.value("http_port", DEFAULT_HTTP_PORT)))

        self.host_ip_edit = QLineEdit(str(settings.value("host_ip", "auto")))
        self.host_ip_edit.setPlaceholderText("auto")

        rows = [
            ("Nintendo 3DS IP", self.ip_edit),
            ("FBI port", self.fbi_port),
            ("HTTP server port", self.http_port),
            ("PC host IP", self.host_ip_edit),
        ]

        for row, (label_text, widget) in enumerate(rows):
            label = QLabel(label_text)
            label.setObjectName("Muted")
            form.addWidget(label, row, 0)
            form.addWidget(widget, row, 1)

        form.setColumnStretch(1, 1)
        root.addLayout(form)

        appearance_label = QLabel("Appearance")
        appearance_label.setObjectName("SectionTitle")
        root.addWidget(appearance_label)

        theme_row = QHBoxLayout()
        theme_row.setSpacing(10)

        self.theme_group = QButtonGroup(self)
        self.theme_group.setExclusive(True)
        self.theme_buttons = {}

        for theme_id in ("white", "black"):
            button = QPushButton(THEMES[theme_id]["name"])
            button.setObjectName("ThemeButton")
            button.setCheckable(True)
            button.setProperty("themeId", theme_id)
            self.theme_group.addButton(button)
            self.theme_buttons[theme_id] = button
            theme_row.addWidget(button)

        current_theme = str(settings.value("theme", "white"))
        if current_theme not in self.theme_buttons:
            current_theme = "white"
        self.theme_buttons[current_theme].setChecked(True)

        root.addLayout(theme_row)

        hint = QLabel(
            "Leave PC host IP on “auto” unless a VPN or second network adapter causes problems."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        root.addWidget(hint)

        buttons = QHBoxLayout()
        buttons.addStretch(1)

        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)

        save = QPushButton("Save")
        save.setObjectName("Primary")
        save.clicked.connect(self.save_settings)

        buttons.addWidget(cancel)
        buttons.addWidget(save)

        root.addLayout(buttons)

    def save_settings(self) -> None:
        target_ip = self.ip_edit.text().strip()
        host_ip = self.host_ip_edit.text().strip() or "auto"

        if target_ip and not valid_ip(target_ip):
            QMessageBox.warning(self, APP_NAME, "Nintendo 3DS IP is not valid.")
            return

        if host_ip.lower() != "auto" and not valid_ip(host_ip):
            QMessageBox.warning(self, APP_NAME, "PC host IP must be a valid IP or 'auto'.")
            return

        self.settings.setValue("target_ip", target_ip)
        self.settings.setValue("fbi_port", self.fbi_port.value())
        self.settings.setValue("http_port", self.http_port.value())
        self.settings.setValue("host_ip", host_ip)

        checked_theme = self.theme_group.checkedButton()
        theme_id = (
            str(checked_theme.property("themeId"))
            if checked_theme is not None
            else "white"
        )
        if theme_id not in THEMES:
            theme_id = "white"

        self.settings.setValue("theme", theme_id)
        self.settings.sync()

        self.saved.emit()
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.settings = QSettings(AUTHOR, APP_NAME)
        self.files: list[Path] = []

        self.worker: SenderWorker | None = None
        self.worker_thread: QThread | None = None
        self._closing = False

        if self.settings.value("theme") not in THEMES:
            self.settings.setValue("theme", "white")

        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        self.setWindowIcon(build_icon())
        self.resize(735, 565)
        self.setMinimumSize(650, 520)

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 26, 28, 18)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        header.setSpacing(14)

        icon = QLabel()
        icon.setPixmap(build_icon().pixmap(44, 44))
        icon.setFixedSize(44, 44)

        title_box = QVBoxLayout()
        title_box.setSpacing(0)

        title = QLabel(APP_NAME)
        title.setObjectName("Title")

        subtitle = QLabel("Send files to FBI over your local network.")
        subtitle.setObjectName("Muted")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        settings_button = QPushButton("Settings")
        settings_button.clicked.connect(self.open_settings)

        header.addWidget(icon)
        header.addLayout(title_box)
        header.addStretch(1)
        header.addWidget(settings_button)

        layout.addLayout(header)

        # Connection
        connection = QFrame()
        connection.setObjectName("Card")

        connection_layout = QHBoxLayout(connection)
        connection_layout.setContentsMargins(18, 14, 18, 14)
        connection_layout.setSpacing(12)

        conn_text = QVBoxLayout()
        conn_text.setSpacing(2)

        conn_title = QLabel("Nintendo 3DS")
        conn_title.setObjectName("SectionTitle")

        self.connection_status = QLabel()
        self.connection_status.setObjectName("Muted")

        conn_text.addWidget(conn_title)
        conn_text.addWidget(self.connection_status)

        change = QPushButton("Change")
        change.clicked.connect(self.open_settings)

        connection_layout.addLayout(conn_text)
        connection_layout.addStretch(1)
        connection_layout.addWidget(change)

        layout.addWidget(connection)

        # The only file-selection box.
        self.drop_area = DropArea()
        self.drop_area.browseRequested.connect(self.choose_files)
        self.drop_area.pathsDropped.connect(self.add_paths)
        self.drop_area.clearRequested.connect(self.clear_files)

        layout.addWidget(self.drop_area)

        # Bottom action area
        bottom = QHBoxLayout()
        bottom.setSpacing(14)

        status_box = QVBoxLayout()
        status_box.setSpacing(7)

        self.status_label = QLabel("Ready.")
        self.status_label.setObjectName("Muted")
        self.status_label.setWordWrap(True)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)

        status_box.addWidget(self.status_label)
        status_box.addWidget(self.progress)

        self.send_button = QPushButton("Send to 3DS")
        self.send_button.setObjectName("Primary")
        self.send_button.clicked.connect(self.send_or_cancel)

        bottom.addLayout(status_box, 1)
        bottom.addWidget(self.send_button, 0, Qt.AlignBottom)

        layout.addLayout(bottom)
        layout.addStretch(1)

        # Footer
        footer = QHBoxLayout()

        footer_label = QLabel(
            f'3Dropia {VERSION}  ·  '
            f'<a href="{REPO_URL}">by {AUTHOR}</a>'
        )
        footer_label.setObjectName("Footer")
        footer_label.setOpenExternalLinks(True)

        compat = QLabel(
            '<a href="https://github.com/Steveice10/FBI">FBI</a> Remote Install compatible'
        )
        compat.setObjectName("Footer")
        compat.setOpenExternalLinks(True)

        footer.addWidget(footer_label)
        footer.addStretch(1)
        footer.addWidget(compat)

        layout.addLayout(footer)

        legal = QLabel(
            "Nintendo and Nintendo 3DS are trademarks of Nintendo. "
            "3Dropia is an independent, unofficial project and is not affiliated with or endorsed by Nintendo."
        )
        legal.setObjectName("Legal")
        legal.setWordWrap(True)
        layout.addWidget(legal)

        self.apply_theme()
        self.refresh_connection()
        self.refresh_files()

    def theme_id(self) -> str:
        current = str(self.settings.value("theme", "white"))
        return current if current in THEMES else "white"

    def apply_theme(self) -> None:
        theme_id = self.theme_id()
        QApplication.instance().setStyleSheet(stylesheet(theme_id))
        apply_link_palette(theme_id)

    def refresh_connection(self) -> None:
        ip = str(self.settings.value("target_ip", "")).strip()

        if ip:
            self.connection_status.setText(
                f"{ip}  ·  FBI port {int(self.settings.value('fbi_port', DEFAULT_FBI_PORT))}"
            )
        else:
            self.connection_status.setText("Not configured")

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self)

        def on_saved() -> None:
            self.apply_theme()
            self.refresh_connection()

        dialog.saved.connect(on_saved)
        dialog.exec()

    def choose_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Choose files",
            "",
            "Nintendo 3DS files (*.cia *.tik *.cetk *.3dsx);;All files (*.*)",
        )

        if paths:
            self.add_paths(paths)

    def iter_supported(self, paths: Iterable[str]) -> Iterable[Path]:
        for raw in paths:
            path = Path(raw).expanduser()

            if path.is_file():
                if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    yield path.resolve()
                continue

            if path.is_dir():
                for child in sorted(path.iterdir()):
                    if child.is_file() and child.suffix.lower() in SUPPORTED_EXTENSIONS:
                        yield child.resolve()

    def add_paths(self, paths: list[str]) -> None:
        existing = {str(p).lower() for p in self.files}
        added = 0

        for path in self.iter_supported(paths):
            key = str(path).lower()

            if key not in existing:
                self.files.append(path)
                existing.add(key)
                added += 1

        if added:
            self.status_label.setText(
                f"Added {added} file{'s' if added != 1 else ''}."
            )
        else:
            self.status_label.setText("No supported files found.")

        self.refresh_files()

    def refresh_files(self) -> None:
        self.drop_area.set_files(self.files)
        self.send_button.setEnabled(bool(self.files) or self.worker is not None)

    def clear_files(self) -> None:
        self.files.clear()
        self.refresh_files()
        self.progress.setValue(0)
        self.status_label.setText("Ready.")

    def send_or_cancel(self) -> None:
        if self.worker is not None:
            self.worker.cancel()
            self.status_label.setText("Cancelling…")
            self.send_button.setEnabled(False)
            return

        self.start_send()

    def start_send(self) -> None:
        if not self.files:
            return

        target_ip = str(self.settings.value("target_ip", "")).strip()

        if not valid_ip(target_ip):
            QMessageBox.information(
                self,
                APP_NAME,
                "Set your Nintendo 3DS IP first.\n\n"
                "On the console open FBI → Remote Install → Receive URLs.",
            )
            self.open_settings()
            return

        missing = [p for p in self.files if not p.exists()]

        if missing:
            QMessageBox.warning(
                self,
                APP_NAME,
                f"File no longer exists:\n{missing[0]}",
            )
            return

        fbi_port = int(self.settings.value("fbi_port", DEFAULT_FBI_PORT))
        http_port = int(self.settings.value("http_port", DEFAULT_HTTP_PORT))
        host_ip = str(self.settings.value("host_ip", "auto"))

        self.worker_thread = QThread(self)

        self.worker = SenderWorker(
            self.files.copy(),
            target_ip,
            fbi_port,
            http_port,
            host_ip,
        )
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.status.connect(self.on_status)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.drop_area.setEnabled(False)
        self.send_button.setText("Cancel")
        self.progress.setValue(0)
        self.status_label.setText("Starting…")

        self.worker_thread.start()

    def on_status(self, text: str) -> None:
        self.status_label.setText(text)

    def on_progress(self, current: int, total: int, filename: str) -> None:
        if total <= 0:
            self.progress.setValue(0)
            return

        percent = max(0, min(100, int((current / total) * 100)))
        self.progress.setValue(percent)

        if filename and current > 0:
            self.status_label.setText(
                f"Serving {filename} · {human_size(current)} / {human_size(total)}"
            )

    def on_finished(self, success: bool, message: str) -> None:
        self.status_label.setText(message)

        if success:
            self.progress.setValue(100)

        elif message != "Cancelled.":
            QMessageBox.warning(
                self,
                APP_NAME,
                message
                + "\n\nMake sure your PC and 3DS are on the same network and "
                  "FBI is open at Remote Install → Receive URLs.",
            )

        self.drop_area.setEnabled(True)
        self.send_button.setEnabled(True)
        self.send_button.setText("Send to 3DS")

        self.worker = None
        self.worker_thread = None

    def closeEvent(self, event) -> None:
        if (
            self.worker is not None
            and self.worker_thread is not None
            and self.worker_thread.isRunning()
        ):
            if not self._closing:
                self._closing = True
                self.worker.cancel()
                self.status_label.setText("Closing…")
                self.worker_thread.finished.connect(self.close)

            event.ignore()
            return

        event.accept()


def export_icon() -> int:
    app = QApplication.instance() or QApplication(sys.argv)

    out = Path(__file__).with_name("3dropia.ico")
    pm = build_icon(256).pixmap(256, 256)

    return 0 if pm.save(str(out), "ICO") else 1


def main() -> int:
    if "--export-icon" in sys.argv:
        return export_icon()

    QApplication.setOrganizationName(AUTHOR)
    QApplication.setApplicationName(APP_NAME)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setWindowIcon(build_icon())

    settings = QSettings(AUTHOR, APP_NAME)

    if str(settings.value("theme", "white")) not in THEMES:
        settings.setValue("theme", "white")

    initial_theme = str(settings.value("theme", "white"))
    app.setStyleSheet(stylesheet(initial_theme))
    apply_link_palette(initial_theme)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
