#!/usr/bin/env python3
"""
main.py — StegoSuite GUI application entry point.
Pages: Encode, Decode, Log, Methods
"""

import sys
import os
import struct
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QTextEdit, QComboBox,
    QTabWidget, QProgressBar, QFrame, QGroupBox, QLineEdit,
    QMessageBox, QStatusBar, QScrollArea
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor

# Local modules
from steganography_functions import (
    TextStego, ImageStego, AudioStego, VideoStego,
    PdfStego, OfficeDocStego, HtmlStego, BinaryStego, ArchiveStego,
    detect_type, auto_out_path, pack_secret, unpack_secret
)

from styling import (
    MAIN_QSS, apply_palette, FileDropLabel, mk_separator, mk_label
)


# ─────────────────────────────────────────────
#  TEST FILES FOLDER  (same dir as script)
# ─────────────────────────────────────────────

def get_test_files_dir() -> str:
    """Return path to TestFiles folder next to the script (create if missing)."""
    base = Path(os.path.dirname(os.path.abspath(__file__))) / "TestFiles"
    base.mkdir(exist_ok=True)
    return str(base)

def get_encoded_decoded_dir() -> str:
    """Return path to EncodedDecodedFiles folder next to the script (create if missing)."""
    base = Path(os.path.dirname(os.path.abspath(__file__))) / "EncodedDecodedFiles"
    base.mkdir(exist_ok=True)
    return str(base)


def display_folder_path(full_path: str) -> str:
    """Return a friendly short display like  …/Downloads/StegoSuite/TestFiles"""
    p   = Path(full_path)
    try:
        parts = p.parts
        # Show last 3 path components
        if len(parts) >= 3:
            return "…/" + "/".join(parts[-3:])
        return str(p)
    except Exception:
        return str(p)


# ─────────────────────────────────────────────
#  WORKER THREAD
# ─────────────────────────────────────────────

class Worker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)
    error    = pyqtSignal(str)

    def __init__(self, task, **kwargs):
        super().__init__()
        self.task   = task
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.task(**self.kwargs, progress_cb=self.progress.emit)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# ─────────────────────────────────────────────
#  LOG PAGE
# ─────────────────────────────────────────────

class LogPage(QWidget):
    """Scrollable log — newest entry always on top."""
    def _save_log(self):
        import os
        log_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "LogFiles"
        log_dir.mkdir(exist_ok=True)
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = log_dir / f"stegosuite_log_{ts}.txt"
        # Extract plain text from the HTML
        plain = self.log_area.toPlainText()
        with open(str(out_path), "w", encoding="utf-8") as f:
            f.write(plain)
        sized_msgbox(self, QMessageBox.Information, "Log Saved",
                     f"Log saved to:\n{out_path.name}\n\nFolder: .../{log_dir.parent.name}/{log_dir.name}")
    
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        header_row = QHBoxLayout()
        header_row.addWidget(mk_label("OPERATION LOG", "label_section"))
        header_row.addStretch()
        btn_save_log = QPushButton("Save Log")
        btn_save_log.clicked.connect(self._save_log)
        header_row.addWidget(btn_save_log)
        btn_clear = QPushButton("Clear Log")
        btn_clear.setObjectName("btn_danger")
        btn_clear.clicked.connect(self._clear)
        header_row.addWidget(btn_clear)
        root.addLayout(header_row)

        self.log_area = QTextEdit()
        self.log_area.setObjectName("log_area")
        self.log_area.setReadOnly(True)
        root.addWidget(self.log_area)

    def add_entry(self, message: str, success: bool = True):
        ts      = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        icon    = "✓" if success else "✗"
        colour  = "#115511" if success else "#881111"
        bg      = "#e6f4e6" if success else "#f4e6e6"
        border  = "#88bb88" if success else "#bb8888"

        html = (
            f'<div style="'
            f'background:{bg};'
            f'border-left:4px solid {border};'
            f'padding:8px 12px;'
            f'font-family:Consolas,monospace;'
            f'font-size:11pt;'
            f'">'
            f'<span style="color:#666666;font-size:10pt;">{ts}</span>&nbsp;&nbsp;'
            f'<span style="color:{colour};font-weight:bold;">{icon}&nbsp;{message}</span>'
            f'</div>'
            f'<div style="background:#d8d8d8;height:10px;font-size:1px;">&nbsp;</div>'
        )
        cursor = self.log_area.textCursor()
        cursor.movePosition(QTextCursor.Start)
        self.log_area.setTextCursor(cursor)
        self.log_area.insertHtml(html)

    def _clear(self):
        self.log_area.clear()


# ─────────────────────────────────────────────
#  ENCODE PAGE
# ─────────────────────────────────────────────

def sized_msgbox(parent, icon, title, text, min_width=480):
    msg = QMessageBox(parent)
    msg.setIcon(icon)
    msg.setWindowTitle(title)
    msg.setText(text)
    # Find the internal label and set its minimum width directly
    for child in msg.findChildren(QLabel):
        if child.text() == text:
            child.setMinimumWidth(min_width)
            break
    msg.exec_()

class EncodePage(QWidget):
    status_msg = pyqtSignal(str)
    log_entry  = pyqtSignal(str, bool)   # (message, success)

    def __init__(self):
        super().__init__()
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # ── Cover file ──
        grp_cover = QGroupBox("Cover File  (carrier)")
        lv = QVBoxLayout(grp_cover)
        lv.setSpacing(8)

        self.cover_drop = FileDropLabel("Drop cover file here  (image / audio / video / text)")
        self.cover_drop.fileDropped.connect(self._on_cover_dropped)
        lv.addWidget(self.cover_drop)

        row = QHBoxLayout()
        self.cover_type = QComboBox()
        self.cover_type.addItems([
            "Auto-detect",
            "Image (PNG/BMP)", "Audio (WAV)", "Video (MP4/AVI)", "Text (TXT)",
            "PDF (.pdf)", "Office Doc (.docx/.xlsx/.pptx)",
            "HTML/CSS (.html/.css)", "Binary (.exe/.dll/.elf)",
            "Archive (.zip/.rar/.7z)"
        ])
        row.addWidget(mk_label("Type:", "label_section"))
        row.addWidget(self.cover_type)
        row.addStretch()
        btn_browse_cover = QPushButton("Browse")
        btn_browse_cover.clicked.connect(self._browse_cover)
        row.addWidget(btn_browse_cover)
        btn_clear_cover = QPushButton("Clear")
        btn_clear_cover.setObjectName("btn_danger")
        btn_clear_cover.clicked.connect(self.cover_drop.clear_path)
        row.addWidget(btn_clear_cover)
        lv.addLayout(row)
        root.addWidget(grp_cover)

        # ── Secret payload ──
        grp_secret = QGroupBox("Secret Payload  (data to hide)")
        sv = QVBoxLayout(grp_secret)
        sv.setSpacing(8)

        self.secret_drop = FileDropLabel("Drop any file to hide  —  image, audio, video, text, zip, etc.")
        sv.addWidget(self.secret_drop)

        row2 = QHBoxLayout()
        self.secret_is_text = QComboBox()
        self.secret_is_text.addItems(["Any file (browse below)", "Plain text (type below)"])
        self.secret_is_text.currentIndexChanged.connect(self._toggle_text_input)
        row2.addWidget(mk_label("Input:", "label_section"))
        row2.addWidget(self.secret_is_text)
        row2.addStretch()
        btn_browse_secret = QPushButton("Browse")
        btn_browse_secret.clicked.connect(self._browse_secret)
        row2.addWidget(btn_browse_secret)
        btn_clear_secret = QPushButton("Clear")
        btn_clear_secret.setObjectName("btn_danger")
        btn_clear_secret.clicked.connect(self.secret_drop.clear_path)
        row2.addWidget(btn_clear_secret)
        sv.addLayout(row2)

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Type secret message here…")
        self.text_input.setFixedHeight(90)
        self.text_input.hide()
        sv.addWidget(self.text_input)
        root.addWidget(grp_secret)

        # ── Output ──
        grp_out = QGroupBox("Output")
        ov = QVBoxLayout(grp_out)

        row3 = QHBoxLayout()
        self.out_path_edit = QLineEdit()
        self.out_path_edit.setPlaceholderText("Output file path (auto-generated if empty)")
        row3.addWidget(self.out_path_edit)
        btn_browse_out = QPushButton("…")
        btn_browse_out.setFixedWidth(44)
        btn_browse_out.clicked.connect(self._browse_output)
        row3.addWidget(btn_browse_out)
        ov.addLayout(row3)

        # Dynamic folder display
        self._out_folder_label = QLabel()
        self._out_folder_label.setObjectName("label_section")
        self._refresh_folder_label()
        ov.addWidget(self._out_folder_label)

        self._video_warn = QLabel(
            "⚠  Video stego output is always saved as lossless AVI.\n"
            "   Lossy compression (MP4/H.264) destroys hidden data."
        )
        self._video_warn.setObjectName("label_warn")
        self._video_warn.setWordWrap(True)
        self._video_warn.hide()
        ov.addWidget(self._video_warn)
        root.addWidget(grp_out)

        # ── Run ──
        root.addWidget(mk_separator())
        self.progress = QProgressBar()
        self.progress.setValue(0)
        root.addWidget(self.progress)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_encode = QPushButton("▶  Encode")
        self.btn_encode.setObjectName("btn_primary")
        self.btn_encode.clicked.connect(self._run_encode)
        btn_row.addWidget(self.btn_encode)
        btn_row.addStretch()
        root.addLayout(btn_row)
        root.addStretch()
        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ── helpers ──

    def _refresh_folder_label(self):
        folder = get_encoded_decoded_dir()
        self._out_folder_label.setText(
            f"Output folder:  {display_folder_path(folder)}"
        )

    def _toggle_text_input(self, idx):
        if idx == 1:
            self.secret_drop.hide()
            self.text_input.show()
        else:
            self.secret_drop.show()
            self.text_input.hide()

    def _browse_cover(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Cover File", get_test_files_dir(),
            "All Files (*);;Images (*.png *.bmp *.jpg);;Audio (*.wav);;"
            "Video (*.mp4 *.avi);;Text (*.txt);;PDF (*.pdf);;"
            "Office Docs (*.docx *.xlsx *.pptx);;HTML/CSS (*.html *.htm *.css);;"
            "Binaries (*.exe *.dll *.so *.elf);;Archives (*.zip *.rar *.7z *.tar *.gz)"
        )
        if path:
            self.cover_drop.set_path(path)
            self._video_warn.setVisible(detect_type(path) == "video")

    def _on_cover_dropped(self, path: str):
        self._video_warn.setVisible(detect_type(path) == "video")

    def _browse_secret(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Secret File", get_test_files_dir(), "All Files (*)"
        )
        if path:
            self.secret_drop.set_path(path)

    def _browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Output File", get_encoded_decoded_dir(), "All Files (*)"
        )
        if path:
            self.out_path_edit.setText(path)

    def _run_encode(self):
        cover = self.cover_drop.path
        if not cover:
            QMessageBox.warning(self, "Missing Input", "Please select a cover file.")
            return

        # Build secret bytes
        if self.secret_is_text.currentIndex() == 1:
            msg = self.text_input.toPlainText()
            if not msg.strip():
                QMessageBox.warning(self, "Missing Input", "Please type a secret message.")
                return
            secret_bytes = msg.encode("utf-8")
            secret_name  = "message.txt"
        else:
            if not self.secret_drop.path:
                QMessageBox.warning(self, "Missing Input", "Please select a secret file.")
                return
            with open(self.secret_drop.path, "rb") as f:
                secret_bytes = f.read()
            secret_name = Path(self.secret_drop.path).name

        payload = pack_secret(secret_bytes, secret_name)

        out_path = self.out_path_edit.text().strip()
        if not out_path:
            # Default output to TestFiles folder with _encoded suffix
            cover_p  = Path(cover)
            tf       = get_encoded_decoded_dir()
            out_path = auto_out_path(str(Path(tf) / cover_p.name), "_encoded")

        ctype_idx = self.cover_type.currentIndex()
        if ctype_idx == 0:
            ctype = detect_type(cover)
        else:
            ctype = [
                "image", "image", "audio", "video", "text",
                "pdf", "officedoc", "html", "binary", "archive"
            ][ctype_idx]
        cover_name  = Path(cover).name
        secret_size = f"{len(secret_bytes):,} bytes"

        self.btn_encode.setEnabled(False)
        self.progress.setValue(0)
        self.status_msg.emit(f"Encoding into {ctype} → {Path(out_path).name} …")

        _out_path_ref = [out_path]   # mutable box so task closure can update it

        def task(progress_cb=None):
            op = _out_path_ref[0]
            if ctype == "image":
                ImageStego.encode(cover, payload, op)
            elif ctype == "audio":
                AudioStego.encode(cover, payload, op)
            elif ctype == "video":
                result = VideoStego.encode(cover, payload, op, progress_cb)
                return result
            elif ctype == "pdf":
                PdfStego.encode(cover, payload, op)
            elif ctype == "officedoc":
                OfficeDocStego.encode(cover, payload, op)
            elif ctype == "html":
                HtmlStego.encode(cover, payload, op)
            elif ctype == "binary":
                BinaryStego.encode(cover, payload, op)
            elif ctype == "archive":
                ArchiveStego.encode(cover, payload, op)
            else:  # text
                with open(cover, "r", encoding="utf-8", errors="replace") as f:
                    cover_text = f.read()
                stego_text = TextStego.encode(cover_text, payload)
                with open(op, "w", encoding="utf-8") as f:
                    f.write(stego_text)
            if progress_cb:
                progress_cb(100)
            return op

        self._cover_name   = cover_name
        self._secret_name  = secret_name
        self._secret_size  = secret_size
        self._ctype        = ctype

        self._worker = Worker(task)
        self._worker.progress.connect(self.progress.setValue)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()


    
    def _on_done(self, result):
        self.btn_encode.setEnabled(True)
        self.progress.setValue(100)
        out_name = Path(result).name
        self.status_msg.emit(f"✓ Encoded  →  {result}")
        msg = (
            f"Encoded  |  {self._ctype.upper()}  |  "
            f"cover: {self._cover_name}  →  payload: {self._secret_name} "
            f"({self._secret_size})  →  output: {out_name}"
        )
        self.log_entry.emit(msg, True)
        sized_msgbox(self, QMessageBox.Information, "Encoding Complete", f"Steganography complete!\n\nOutput: {Path(result).name}")


    def _on_error(self, msg):
        self.btn_encode.setEnabled(True)
        self.progress.setValue(0)
        self.status_msg.emit(f"✗ Error: {msg}")
        cover_name = Path(self.cover_drop.path).name if self.cover_drop.path else "unknown"
        self.log_entry.emit(
            f"ENCODE FAILED  |  cover: {cover_name}  |  {msg}", False
        )
        sized_msgbox(self, QMessageBox.Critical, "Encoding Error", msg)


# ─────────────────────────────────────────────
#  DECODE PAGE
# ─────────────────────────────────────────────

class DecodePage(QWidget):
    status_msg = pyqtSignal(str)
    log_entry  = pyqtSignal(str, bool)

    def __init__(self):
        super().__init__()
        self._worker          = None
        self._extracted_bytes = None
        self._extracted_name  = None
        self._saved_path      = None
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # ── Input ──
        grp = QGroupBox("Stego File  (contains hidden data)")
        lv = QVBoxLayout(grp)
        self.stego_drop = FileDropLabel("Drop stego file here  (image / audio / video / text)")
        lv.addWidget(self.stego_drop)

        row = QHBoxLayout()
        self.stego_type = QComboBox()
        self.stego_type.addItems([
            "Auto-detect",
            "Image (PNG/BMP)", "Audio (WAV)", "Video (MP4/AVI)", "Text (TXT)",
            "PDF (.pdf)", "Office Doc (.docx/.xlsx/.pptx)",
            "HTML/CSS (.html/.css)", "Binary (.exe/.dll/.elf)",
            "Archive (.zip/.rar/.7z)"
        ])
        row.addWidget(mk_label("Type:", "label_section"))
        row.addWidget(self.stego_type)
        row.addStretch()
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self._browse_stego)
        row.addWidget(btn_browse)
        lv.addLayout(row)
        root.addWidget(grp)

        # ── Output dir ──
        grp_out = QGroupBox("Output Directory  (extracted file saved here)")
        ov = QVBoxLayout(grp_out)
        row_dir = QHBoxLayout()
        self.out_dir_edit = QLineEdit()
        self.out_dir_edit.setPlaceholderText("TestFiles folder (default)")
        row_dir.addWidget(self.out_dir_edit)
        btn_dir = QPushButton("…")
        btn_dir.setFixedWidth(44)
        btn_dir.clicked.connect(self._browse_out_dir)
        row_dir.addWidget(btn_dir)
        ov.addLayout(row_dir)

        self._out_folder_label = QLabel()
        self._out_folder_label.setObjectName("label_section")
        self._refresh_folder_label()
        ov.addWidget(self._out_folder_label)
        root.addWidget(grp_out)

        # ── Preview ──
        grp_prev = QGroupBox("Extracted Content Preview")
        pv = QVBoxLayout(grp_prev)

        self.preview_label = mk_label("No data extracted yet.", "label_value")
        self.preview_label.setWordWrap(True)
        pv.addWidget(self.preview_label)

        self.preview_saved = mk_label("", "label_section")
        self.preview_saved.setWordWrap(True)
        self.preview_saved.hide()
        pv.addWidget(self.preview_saved)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFixedHeight(130)
        self.preview_text.setPlaceholderText("Text content will appear here…")
        pv.addWidget(self.preview_text)

        btn_save_row = QHBoxLayout()
        self.btn_save = QPushButton("Save Extracted File")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._save_extracted)
        btn_save_row.addWidget(self.btn_save)
        btn_save_row.addStretch()
        pv.addLayout(btn_save_row)
        root.addWidget(grp_prev)

        # ── Run ──
        root.addWidget(mk_separator())
        self.progress = QProgressBar()
        root.addWidget(self.progress)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_decode = QPushButton("▶  Decode")
        self.btn_decode.setObjectName("btn_primary")
        self.btn_decode.clicked.connect(self._run_decode)
        btn_row.addWidget(self.btn_decode)
        btn_row.addStretch()
        root.addLayout(btn_row)
        root.addStretch()
        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ── helpers ──

    def _refresh_folder_label(self):
        folder = get_encoded_decoded_dir()
        self._out_folder_label.setText(
            f"Output folder:  {display_folder_path(folder)}"
        )

    def _browse_stego(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Stego File", get_encoded_decoded_dir(), "All Files (*)"
        )
        if path:
            self.stego_drop.set_path(path)

    def _browse_out_dir(self):
        d = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", get_test_files_dir()
        )
        if d:
            self.out_dir_edit.setText(d)
            self._out_folder_label.setText(
                f"Output folder:  {display_folder_path(d)}"
            )

    def _run_decode(self):
        stego = self.stego_drop.path
        if not stego:
            QMessageBox.warning(self, "Missing Input", "Please select a stego file.")
            return

        ctype_idx = self.stego_type.currentIndex()
        if ctype_idx == 0:
            ctype = detect_type(stego)
        else:
            ctype = [
                "image", "image", "audio", "video", "text",
                "pdf", "officedoc", "html", "binary", "archive"
            ][ctype_idx]
        self.btn_decode.setEnabled(False)
        self.progress.setValue(0)
        self.preview_text.clear()
        self.preview_saved.hide()
        self.preview_label.setText("Decoding…")
        self.status_msg.emit(f"Decoding {ctype} file…")

        def task(progress_cb=None):
            if ctype == "image":
                raw = ImageStego.decode(stego)
            elif ctype == "audio":
                raw = AudioStego.decode(stego)
            elif ctype == "video":
                raw = VideoStego.decode(stego, progress_cb)
            elif ctype == "pdf":
                raw = PdfStego.decode(stego)
            elif ctype == "officedoc":
                raw = OfficeDocStego.decode(stego)
            elif ctype == "html":
                raw = HtmlStego.decode(stego)
            elif ctype == "binary":
                raw = BinaryStego.decode(stego)
            elif ctype == "archive":
                raw = ArchiveStego.decode(stego)
            else:  # text
                with open(stego, "r", encoding="utf-8", errors="replace") as f:
                    txt = f.read()
                raw = TextStego.decode(txt)
            if progress_cb:
                progress_cb(100)
            return raw

        self._stego_name = Path(stego).name
        self._ctype      = ctype

        self._worker = Worker(task)
        self._worker.progress.connect(self.progress.setValue)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, raw: bytes):
        self.btn_decode.setEnabled(True)
        self.progress.setValue(100)

        fname, data = unpack_secret(raw)

        # Build _decoded output name
        p          = Path(fname)
        fname_out  = p.stem + "_decoded" + p.suffix

        self._extracted_bytes = data
        self._extracted_name  = fname_out

        size_str = f"{len(data):,} bytes"
        self.preview_label.setText(
            f"✓  Extracted:  <b>{fname}</b>  →  saved as  <b>{fname_out}</b>  ({size_str})"
        )
        self.preview_label.setTextFormat(Qt.RichText)

        try:
            text = data.decode("utf-8")
            self.preview_text.setPlainText(
                text[:4000] + ("…" if len(text) > 4000 else "")
            )
        except Exception:
            self.preview_text.setPlainText("[Binary file — use Save button to extract]")

        self.btn_save.setEnabled(True)
        self.status_msg.emit(f"✓ Decoded  →  {fname_out}  ({size_str})")

        # Auto-save
        out_dir = self.out_dir_edit.text().strip() or get_encoded_decoded_dir()
        saved   = self._do_save(out_dir)

        if saved:
            self.preview_saved.setText(f"📁  Saved to:  {saved}")
            self.preview_saved.show()
            self.log_entry.emit(
                f"Decoded  |  {self._ctype.upper()}  |  "
                f"source: {self._stego_name}  →  extracted: {fname_out} ({size_str})  →  {saved}",
                True
            )

    def _save_extracted(self):
        if not self._extracted_bytes:
            return
        out_dir = self.out_dir_edit.text().strip()
        if not out_dir:
            out_dir = QFileDialog.getExistingDirectory(
                self, "Choose Save Directory", get_encoded_decoded_dir()
            )
            if not out_dir:
                return
        self._do_save(out_dir)

    def _do_save(self, out_dir: str) -> str:
        """Save extracted file, return saved path or empty string."""
        try:
            out_path = Path(out_dir) / self._extracted_name
            counter  = 1
            base     = out_path
            while out_path.exists():
                out_path = base.parent / f"{base.stem}_{counter}{base.suffix}"
                counter += 1
            with open(str(out_path), "wb") as f:
                f.write(self._extracted_bytes)
            self._saved_path = str(out_path)
            return str(out_path)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))
            return ""

    def _on_error(self, msg):
        self.btn_decode.setEnabled(True)
        self.progress.setValue(0)
        self.preview_label.setText("✗ Error during decoding.")
        self.status_msg.emit(f"✗ Error: {msg}")
        self.log_entry.emit(
            f"DECODE FAILED  |  source: {self._stego_name}  |  {msg}", False
        )
        QMessageBox.critical(self, "Decoding Error", msg)


# ─────────────────────────────────────────────
#  METHODS (INFO) PAGE
# ─────────────────────────────────────────────

class InfoPage(QWidget):
    def __init__(self):
        super().__init__()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        inner = QWidget()
        root  = QVBoxLayout(inner)
        root.setContentsMargins(30, 24, 30, 24)
        root.setSpacing(14)

        root.addWidget(mk_label("STEGANOGRAPHY METHODS", "label_section"))
        root.addWidget(mk_separator())

        methods = [
            (
                "Text files  (.txt)",
                "Technique:  Zero-width Unicode character injection.\n\n"
                "Each hidden byte is encoded as 8 invisible characters "
                "(U+200B = bit 0, U+200C = bit 1) followed by a byte-separator "
                "(U+200D). The hidden stream is inserted after the first word of "
                "the cover text so the document reads completely normally in any "
                "text editor or word processor.\n\n"
                "Capacity:  Virtually unlimited — one hidden byte per word is "
                "extremely conservative; the actual limit is storage space.\n\n"
                "Limitation:  Copy-paste into plain-ASCII systems strips zero-width "
                "characters. Only use .txt files preserved byte-for-byte."
            ),
            (
                "Image files  (.png / .bmp)",
                "Technique:  1-bit LSB (Least-Significant Bit) substitution on "
                "RGB pixel channels.\n\n"
                "The LSB of every channel byte (R, G, B) is replaced with one "
                "payload bit. A visual change of ±1 in a 0–255 channel is "
                "completely imperceptible to the human eye.\n\n"
                "Capacity:  Width × Height × 3 bits total "
                "(e.g. a 1920×1080 image can hold ~777 KB).\n\n"
                "Output:  Always saved as lossless PNG — JPEG re-encoding "
                "would destroy the hidden bits via DCT compression.\n\n"
                "Limitation:  Only uncompressed/lossless images are safe "
                "carriers. Do not re-save the output as JPEG."
            ),
            (
                "Audio files  (.wav)",
                "Technique:  1-bit LSB substitution on 16-bit PCM audio samples.\n\n"
                "The least-significant bit of each 16-bit sample is replaced "
                "with one payload bit. A change of ±1 in a ±32768 amplitude "
                "range represents a ~0.003% variation — well below the threshold "
                "of human hearing.\n\n"
                "Capacity:  Total samples × channels bits "
                "(e.g. a 3-minute 44.1 kHz stereo WAV ≈ ~3.7 MB capacity).\n\n"
                "Limitation:  Only uncompressed WAV is supported. MP3/AAC/OGG "
                "lossy encoding destroys LSBs."
            ),
            (
                "Video files  (.avi — lossless output)",
                "Technique:  Per-frame 1-bit LSB substitution on BGR pixel data "
                "using OpenCV.\n\n"
                "Payload bits are spread sequentially across frames, one bit per "
                "channel byte per pixel. The decoder reads only as many frames as "
                "needed to recover the full payload.\n\n"
                "Capacity:  Width × Height × 3 × Frame-count bits "
                "(e.g. 1280×720 @ 30 fps for 10 s ≈ ~103 MB capacity).\n\n"
                "Output:  Always saved as lossless AVI (codec priority: "
                "FFV1 → HFYU → RGBA → DIB). Lossy codecs such as H.264 "
                "(MP4) completely destroy hidden data via block-DCT compression.\n\n"
                "Limitation:  Output files are larger than the original MP4 "
                "due to the lossless container. Audio tracks are not preserved."
            ),
        ]

        for title, desc in methods:
            grp = QGroupBox(title)
            v   = QVBoxLayout(grp)
            lbl = QLabel(desc)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(
                "color: #222222; font-size: 12pt; "
                "line-height: 1.6; padding: 4px;"
            )
            v.addWidget(lbl)
            root.addWidget(grp)

        root.addWidget(mk_separator())

        grp_hdr = QGroupBox("Payload Header Format  (all methods)")
        v2      = QVBoxLayout(grp_hdr)
        hdr_info = QLabel(
            "  [4 bytes]  Magic marker  —  0xDE 0xAD 0xBE 0xEF\n"
            "  [1 byte ]  Version       —  0x01\n"
            "  [4 bytes]  Payload size  —  big-endian uint32\n"
            "  [2 bytes]  Filename len  —  big-endian uint16\n"
            "  [N bytes]  Original filename  (UTF-8)\n"
            "  [M bytes]  File content  (raw bytes)"
        )
        hdr_info.setStyleSheet(
            "color: #111111; font-family: 'Consolas','Courier New',monospace; "
            "font-size: 11pt; background: #e8e8e8; padding: 12px; border-radius: 4px;"
        )
        v2.addWidget(hdr_info)
        root.addWidget(grp_hdr)
        root.addStretch()

        scroll.setWidget(inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)


# ─────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StegoSuite — Steganography Toolkit")
        self.setMinimumSize(900, 760)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header banner ──
        banner = QFrame()
        banner.setFixedHeight(82)
        banner.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #bbbbbb, stop:0.5 #cccccc, stop:1 #bbbbbb);"
            "border-bottom: 2px solid #999999;"
        )
        bh = QHBoxLayout(banner)
        bh.setContentsMargins(30, 0, 30, 0)

        title_col = QVBoxLayout()
        t = QLabel("STEGONOGRAPHY FOR TEXT, IMAGE, AUDIO, VIDEO FILE TYPES")
        t.setObjectName("label_title")
        title_col.addWidget(t)
        bh.addLayout(title_col)
        bh.addStretch()

        ver = QLabel("v2.0")
        ver.setStyleSheet(
            "color: #777777; font-size: 11pt; "
            "letter-spacing: 2px; font-family: 'Segoe UI', sans-serif;"
        )
        bh.addWidget(ver)
        root.addWidget(banner)

        # ── Tabs ──
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.encode_page = EncodePage()
        self.decode_page = DecodePage()
        self.log_page    = LogPage()
        self.info_page   = InfoPage()

        self.tabs.addTab(self.encode_page, "  Encode  ")
        self.tabs.addTab(self.decode_page, "  Decode  ")
        self.tabs.addTab(self.log_page,    "  Log  ")
        self.tabs.addTab(self.info_page,   "  Methods  ")

        root.addWidget(self.tabs)

        # ── Status bar ──
        self.status = QStatusBar()
        self.status.showMessage("Ready  |  Select a tab to begin")
        self.setStatusBar(self.status)

        # Wire signals
        self.encode_page.status_msg.connect(self.status.showMessage)
        self.decode_page.status_msg.connect(self.status.showMessage)
        self.encode_page.log_entry.connect(self.log_page.add_entry)
        self.decode_page.log_entry.connect(self.log_page.add_entry)


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    apply_palette(app)
    app.setStyleSheet(MAIN_QSS)

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
