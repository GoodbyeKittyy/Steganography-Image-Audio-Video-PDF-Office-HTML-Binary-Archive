#!/usr/bin/env python3
"""
styling.py — QSS stylesheet, palette setup, and shared GUI widgets for StegoSuite.
Grey background, black fonts, minimum 24 pt font sizes.
"""

from PyQt5.QtWidgets import QLabel, QFrame, QApplication
from PyQt5.QtGui import QColor, QPalette, QFont
from PyQt5.QtCore import Qt, pyqtSignal

# ─────────────────────────────────────────────
#  STYLESHEET  (grey BG, black text, 24 pt min)
# ─────────────────────────────────────────────

MAIN_QSS = """
/* ── Global ── */
QMainWindow, QDialog, QWidget {
    background-color: #d8d8d8;
    color: #111111;
    font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;
    font-size: 15pt;
}

/* ── Menu bar — removed per requirements ── */

/* ── Tab widget ── */
QTabWidget::pane {
    border: 2px solid #aaaaaa;
    background: #d8d8d8;
}
QTabBar::tab {
    background: #c0c0c0;
    color: #444444;
    padding: 14px 38px;
    border: 1px solid #aaaaaa;
    border-bottom: none;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13pt;
    font-weight: bold;
    letter-spacing: 1px;
    min-width: 120px;
}
QTabBar::tab:selected {
    background: #d8d8d8;
    color: #000000;
    border-top: 3px solid #333333;
}
QTabBar::tab:hover {
    background: #cccccc;
    color: #111111;
}

/* ── GroupBox ── */
QGroupBox {
    border: 2px solid #aaaaaa;
    border-radius: 4px;
    margin-top: 22px;
    padding-top: 14px;
    color: #222222;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13pt;
    font-weight: bold;
    letter-spacing: 1px;
    background: #cfcfcf;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    top: -2px;
    padding: 0 8px;
    background: #cfcfcf;
    color: #111111;
}

/* ── Buttons ── */
QPushButton {
    background: #b8b8b8;
    border: 2px solid #888888;
    color: #111111;
    padding: 10px 24px;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13pt;
    font-weight: bold;
    border-radius: 3px;
    min-height: 38px;
}
QPushButton:hover {
    background: #a0a0a0;
    border-color: #555555;
    color: #000000;
}
QPushButton:pressed {
    background: #909090;
    color: #000000;
}
QPushButton:disabled {
    color: #888888;
    border-color: #aaaaaa;
    background: #cccccc;
}

QPushButton#btn_primary {
    background: #444444;
    border: 2px solid #222222;
    color: #ffffff;
    padding: 12px 40px;
    font-size: 14pt;
    font-weight: bold;
    min-height: 46px;
    border-radius: 4px;
}
QPushButton#btn_primary:hover {
    background: #222222;
    color: #ffffff;
}
QPushButton#btn_danger {
    border-color: #994444;
    color: #882222;
    background: #ccbbbb;
}
QPushButton#btn_danger:hover {
    background: #cc9999;
    border-color: #772222;
    color: #550000;
}

/* ── Inputs ── */
QLineEdit, QTextEdit {
    background: #f0f0f0;
    border: 2px solid #aaaaaa;
    color: #111111;
    padding: 8px 12px;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13pt;
    selection-background-color: #888888;
    selection-color: #ffffff;
    border-radius: 3px;
}
QLineEdit:focus, QTextEdit:focus {
    border-color: #333333;
    background: #ffffff;
}

/* ── ComboBox ── */
QComboBox {
    background: #f0f0f0;
    border: 2px solid #aaaaaa;
    color: #111111;
    padding: 8px 12px;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13pt;
    border-radius: 3px;
    min-height: 38px;
}
QComboBox:hover { border-color: #555555; }
QComboBox QAbstractItemView {
    background: #f0f0f0;
    color: #111111;
    selection-background-color: #888888;
    selection-color: #ffffff;
    border: 2px solid #aaaaaa;
    font-size: 13pt;
}
QComboBox::drop-down { border: none; }
QComboBox::down-arrow {
    image: none;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 8px solid #555555;
    margin-right: 10px;
}

/* ── Progress bar ── */
QProgressBar {
    background: #bbbbbb;
    border: 2px solid #aaaaaa;
    height: 18px;
    text-align: center;
    color: #111111;
    border-radius: 3px;
    font-size: 11pt;
    font-weight: bold;
}
QProgressBar::chunk {
    background: #555555;
    border-radius: 2px;
}

/* ── Named Labels ── */
QLabel#label_title {
    font-size: 23pt;
    color: #111111;
    letter-spacing: 4px;
    font-family: 'Segoe UI', sans-serif;
    font-weight: bold;
}
QLabel#label_subtitle {
    font-size: 13pt;
    color: #555555;
    letter-spacing: 3px;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#label_section {
    font-size: 13pt;
    color: #222222;
    font-family: 'Segoe UI', sans-serif;
    font-weight: bold;
    letter-spacing: 1px;
}
QLabel#label_value {
    color: #111111;
    font-size: 13pt;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#label_warn {
    color: #774400;
    font-size: 13pt;
    font-family: 'Segoe UI', sans-serif;
    background: #ffe0b0;
    border: 1px solid #ccaa66;
    padding: 6px 10px;
    border-radius: 3px;
}

/* ── Log tab text area ── */
QTextEdit#log_area {
    background: #f5f5f5;
    border: 2px solid #aaaaaa;
    color: #111111;
    font-family: 'Courier New', 'Consolas', monospace;
    font-size: 12pt;
    padding: 10px;
}

/* ── Status bar ── */
QStatusBar {
    background: #bbbbbb;
    color: #222222;
    border-top: 2px solid #999999;
    font-family: 'Segoe UI', sans-serif;
    font-size: 12pt;
}

/* ── Frames ── */
QFrame#divider {
    background: #aaaaaa;
    max-height: 2px;
}
QFrame#panel {
    background: #cccccc;
    border: 1px solid #bbbbbb;
}

/* ── Scrollbar ── */
QScrollBar:vertical {
    background: #cccccc;
    width: 14px;
    border-radius: 7px;
}
QScrollBar::handle:vertical {
    background: #888888;
    min-height: 28px;
    border-radius: 7px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

/* ── MessageBox ── */
QMessageBox {
    background-color: #d8d8d8;
    color: #111111;
    font-size: 13pt;
}
QMessageBox QLabel {
    color: #111111;
    font-size: 13pt;
}
QMessageBox QPushButton {
    min-width: 100px;
    min-height: 38px;
    font-size: 13pt;
}
"""


# ─────────────────────────────────────────────
#  PALETTE SETUP
# ─────────────────────────────────────────────

def apply_palette(app: QApplication):
    """Apply a light grey palette to complement the QSS."""
    pal = QPalette()
    grey     = QColor("#d8d8d8")
    darkgrey = QColor("#aaaaaa")
    black    = QColor("#111111")
    white    = QColor("#ffffff")
    mid      = QColor("#555555")

    pal.setColor(QPalette.Window,          grey)
    pal.setColor(QPalette.WindowText,      black)
    pal.setColor(QPalette.Base,            QColor("#f0f0f0"))
    pal.setColor(QPalette.AlternateBase,   QColor("#e0e0e0"))
    pal.setColor(QPalette.ToolTipBase,     grey)
    pal.setColor(QPalette.ToolTipText,     black)
    pal.setColor(QPalette.Text,            black)
    pal.setColor(QPalette.Button,          QColor("#b8b8b8"))
    pal.setColor(QPalette.ButtonText,      black)
    pal.setColor(QPalette.BrightText,      white)
    pal.setColor(QPalette.Link,            mid)
    pal.setColor(QPalette.Highlight,       darkgrey)
    pal.setColor(QPalette.HighlightedText, white)
    app.setPalette(pal)


# ─────────────────────────────────────────────
#  SHARED WIDGETS
# ─────────────────────────────────────────────

class FileDropLabel(QLabel):
    """Drag-and-drop file picker label."""
    fileDropped = pyqtSignal(str)

    def __init__(self, hint="Drop file here or click Browse", parent=None):
        super().__init__(hint, parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(80)
        self.path = None
        self._hint = hint
        self._update_style(False)

    def _update_style(self, active):
        self.setStyleSheet(
            f"""
            QLabel {{
                border: 2px dashed {'#333333' if active else '#888888'};
                background: {'#c8c8c8' if active else '#cccccc'};
                color: {'#000000' if active else '#444444'};
                font-family: 'Segoe UI', sans-serif;
                font-size: 12pt;
                letter-spacing: 1px;
                padding: 14px;
                border-radius: 4px;
            }}
            """
        )

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._update_style(True)

    def dragLeaveEvent(self, e):
        self._update_style(False)

    def dropEvent(self, e):
        self._update_style(False)
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.set_path(path)
            self.fileDropped.emit(path)

    def set_path(self, path):
        from pathlib import Path as P
        self.path = path
        name = P(path).name
        if len(name) > 52:
            name = "…" + name[-49:]
        self.setText(f"✓  {name}")
        self._update_style(False)

    def clear_path(self):
        self.path = None
        self.setText(self._hint)
        self._update_style(False)


def mk_separator():
    f = QFrame()
    f.setObjectName("divider")
    f.setFrameShape(QFrame.HLine)
    return f


def mk_label(text, obj_name="label_value"):
    lbl = QLabel(text)
    lbl.setObjectName(obj_name)
    return lbl
