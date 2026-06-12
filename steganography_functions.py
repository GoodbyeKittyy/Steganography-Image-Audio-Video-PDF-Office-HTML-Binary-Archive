#!/usr/bin/env python3
"""
steganography_functions.py — Core stego engines (text, image, audio, video)
No GUI code here — pure logic only.
"""

import os
import struct
import wave
import shutil
import numpy as np
from pathlib import Path

# ─────────────────────────────────────────────
#  PAYLOAD HEADER
# ─────────────────────────────────────────────

MAGIC_HEADER = b"\xDE\xAD\xBE\xEF"   # 4-byte sentinel
VERSION      = b"\x01"                # 1-byte version


def _pack_payload(data: bytes) -> bytes:
    """Prepend magic + version + 4-byte length to raw payload."""
    return MAGIC_HEADER + VERSION + struct.pack(">I", len(data)) + data


def _unpack_payload(raw: bytes) -> bytes:
    """Validate magic header and extract payload."""
    if raw[:4] != MAGIC_HEADER:
        raise ValueError("No hidden data found (magic header missing).")
    if raw[4:5] != VERSION:
        raise ValueError("Unsupported stego version.")
    length = struct.unpack(">I", raw[5:9])[0]
    payload = raw[9: 9 + length]
    if len(payload) < length:
        raise ValueError("Data appears truncated or corrupt.")
    return payload


# ─────────────────────────────────────────────
#  TEXT STEGO
# ─────────────────────────────────────────────

class TextStego:
    """Hide data in a text file using zero-width Unicode characters."""

    ZWS  = "\u200B"   # bit 0
    ZWNJ = "\u200C"   # bit 1
    SEP  = "\u200D"   # byte separator

    @classmethod
    def encode(cls, cover_text: str, secret: bytes) -> str:
        payload  = _pack_payload(secret)
        hidden   = []
        for byte in payload:
            bits = format(byte, "08b")
            for b in bits:
                hidden.append(cls.ZWS if b == "0" else cls.ZWNJ)
            hidden.append(cls.SEP)
        words = cover_text.split(" ", 1)
        if len(words) == 1:
            return words[0] + "".join(hidden)
        return words[0] + "".join(hidden) + " " + words[1]

    @classmethod
    def decode(cls, stego_text: str) -> bytes:
        bits      = []
        byte_bits = []
        for ch in stego_text:
            if ch == cls.ZWS:
                byte_bits.append("0")
            elif ch == cls.ZWNJ:
                byte_bits.append("1")
            elif ch == cls.SEP:
                if len(byte_bits) == 8:
                    bits.append(int("".join(byte_bits), 2))
                byte_bits = []
        if not bits:
            raise ValueError("No hidden data found in text file.")
        return _unpack_payload(bytes(bits))


# ─────────────────────────────────────────────
#  IMAGE STEGO
# ─────────────────────────────────────────────

class ImageStego:
    """LSB steganography for PNG/BMP images."""

    @classmethod
    def encode(cls, cover_path: str, secret: bytes, out_path: str):
        from PIL import Image
        img  = Image.open(cover_path).convert("RGB")
        arr  = np.array(img, dtype=np.uint8)
        flat = arr.flatten()

        payload  = _pack_payload(secret)
        bits     = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))
        capacity = len(flat)

        if len(bits) > capacity:
            raise ValueError(
                f"Image too small — insufficient LSBs. "
                f"Available: {capacity:,}, Required: {len(bits):,}."
            )

        flat[: len(bits)] = (flat[: len(bits)] & 0xFE) | bits
        result = flat.reshape(arr.shape)
        Image.fromarray(result.astype(np.uint8)).save(out_path, format="PNG")

    @classmethod
    def decode(cls, stego_path: str) -> bytes:
        from PIL import Image
        img  = Image.open(stego_path).convert("RGB")
        flat = np.array(img).flatten()
        lsbs = (flat & 1).astype(np.uint8)

        header_bits = lsbs[:72]
        header = np.packbits(header_bits).tobytes()
        if header[:4] != MAGIC_HEADER:
            raise ValueError("No hidden data found in image.")
        length     = struct.unpack(">I", header[5:9])[0]
        total_bits = (9 + length) * 8
        all_bits   = lsbs[:total_bits]
        return _unpack_payload(np.packbits(all_bits).tobytes())


# ─────────────────────────────────────────────
#  AUDIO STEGO
# ─────────────────────────────────────────────

class AudioStego:
    """LSB steganography for WAV audio."""

    @classmethod
    def encode(cls, cover_path: str, secret: bytes, out_path: str):
        with wave.open(cover_path, "rb") as wf:
            params = wf.getparams()
            frames = wf.readframes(wf.getnframes())

        audio   = np.frombuffer(frames, dtype=np.int16).copy().view(np.uint16)
        payload = _pack_payload(secret)
        bits    = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))

        if len(bits) > len(audio):
            raise ValueError(
                f"Audio too short — insufficient LSBs. "
                f"Available: {len(audio):,}, Required: {len(bits):,}."
            )

        audio[: len(bits)] = (audio[: len(bits)] & np.uint16(0xFFFE)) | bits.astype(np.uint16)

        with wave.open(out_path, "wb") as wf:
            wf.setparams(params)
            wf.writeframes(audio.view(np.int16).tobytes())

    @classmethod
    def decode(cls, stego_path: str) -> bytes:
        with wave.open(stego_path, "rb") as wf:
            frames = wf.readframes(wf.getnframes())

        audio = np.frombuffer(frames, dtype=np.int16).view(np.uint16)
        lsbs  = (audio & np.uint16(1)).astype(np.uint8)

        header_bits = lsbs[:72]
        header = np.packbits(header_bits).tobytes()
        if header[:4] != MAGIC_HEADER:
            raise ValueError("No hidden data found in audio.")
        length     = struct.unpack(">I", header[5:9])[0]
        total_bits = (9 + length) * 8
        all_bits   = lsbs[:total_bits]
        return _unpack_payload(np.packbits(all_bits).tobytes())


# ─────────────────────────────────────────────
#  VIDEO STEGO
# ─────────────────────────────────────────────

class VideoStego:
    """Frame-based LSB steganography for video files.

    Always writes to a lossless AVI container (FFV1/HFYU/RGBA/DIB).
    Lossy codecs (H.264, mp4v, etc.) destroy LSBs.
    """

    _LOSSLESS_CODECS = ["FFV1", "HFYU", "RGBA", "DIB "]

    @classmethod
    def _pick_codec(cls, width, height, fps, test_path):
        import cv2
        for name in cls._LOSSLESS_CODECS:
            fourcc   = cv2.VideoWriter_fourcc(*name)
            out_path = test_path.replace(".avi", f"_{name}.avi")
            w        = cv2.VideoWriter(out_path, fourcc, fps, (width, height))
            if w.isOpened():
                w.release()
                try:
                    os.remove(out_path)
                except OSError:
                    pass
                return fourcc, name
            w.release()
        raise RuntimeError(
            "No lossless video codec available (tried FFV1, HFYU, RGBA, DIB). "
            "Install ffmpeg/opencv with lossless codec support."
        )

    @classmethod
    def _avi_out_path(cls, out_path: str) -> str:
        p = Path(out_path)
        return str(p.parent / (p.stem + "_encoded.avi")) if p.suffix.lower() != ".avi" \
               else str(p.parent / (p.stem + ".avi"))

    @classmethod
    def encode(cls, cover_path: str, secret: bytes, out_path: str,
               progress_cb=None):
        import cv2
        cap    = cv2.VideoCapture(cover_path)
        fps    = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        avi_path          = cls._avi_out_path(out_path)
        fourcc, codec_name = cls._pick_codec(width, height, fps, avi_path)
        writer            = cv2.VideoWriter(avi_path, fourcc, fps, (width, height))

        if not writer.isOpened():
            cap.release()
            raise RuntimeError(f"Could not open VideoWriter with codec {codec_name}.")

        payload            = _pack_payload(secret)
        bits               = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))
        capacity_per_frame = width * height * 3
        capacity_total     = capacity_per_frame * total

        if len(bits) > capacity_total:
            cap.release()
            writer.release()
            raise ValueError(
                f"Video too short — insufficient LSBs. "
                f"Available: {capacity_total:,}, Required: {len(bits):,}."
            )

        ptr = 0
        idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if ptr < len(bits):
                flat  = frame.flatten().astype(np.uint8)
                end   = min(ptr + len(flat), len(bits))
                chunk = bits[ptr:end].astype(np.uint8)
                flat[:len(chunk)] = (flat[:len(chunk)] & np.uint8(0xFE)) | chunk
                ptr  += len(chunk)
                frame = flat.reshape(frame.shape)
            writer.write(frame)
            idx += 1
            if progress_cb and total > 0:
                progress_cb(int(idx / total * 100))

        cap.release()
        writer.release()

        if avi_path != out_path and out_path.lower().endswith(".avi"):
            shutil.move(avi_path, out_path)
            return out_path
        return avi_path

    @classmethod
    def decode(cls, stego_path: str, progress_cb=None) -> bytes:
        import cv2
        cap = cv2.VideoCapture(stego_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {stego_path}")
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        collected   = []
        header_done = False
        needed_bits = 72
        length      = 0
        idx         = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            lsbs = (frame.flatten().astype(np.uint8) & np.uint8(1))
            collected.extend(lsbs.tolist())

            if not header_done and len(collected) >= 72:
                header = np.packbits(
                    np.array(collected[:72], dtype=np.uint8)
                ).tobytes()
                if header[:4] != MAGIC_HEADER:
                    cap.release()
                    raise ValueError(
                        "No hidden data found in video. "
                        "Ensure the file was encoded with StegoSuite and saved as lossless AVI."
                    )
                length      = struct.unpack(">I", header[5:9])[0]
                needed_bits = (9 + length) * 8
                header_done = True

            if header_done and len(collected) >= needed_bits:
                break

            idx += 1
            if progress_cb and total > 0:
                progress_cb(int(idx / total * 100))

        cap.release()
        if not header_done:
            raise ValueError("No hidden data found in video (file ended before header was read).")

        all_bits = np.array(collected[:needed_bits], dtype=np.uint8)
        return _unpack_payload(np.packbits(all_bits).tobytes())

# ─────────────────────────────────────────────
#  PDF STEGO
# ─────────────────────────────────────────────

class PdfStego:
    """Hide data in a PDF's metadata and comment fields.

    Strategy: encode payload as hex inside a /StegoData key in the PDF's
    Info dictionary. The PDF remains fully valid and openable.
    """

    _KEY = b"/StegoData"

    @classmethod
    def encode(cls, cover_path: str, secret: bytes, out_path: str):
        payload    = _pack_payload(secret)
        hex_payload = payload.hex().encode("ascii")

        with open(cover_path, "rb") as f:
            data = f.read()

        # Strip any previous StegoData entry
        import re
        data = re.sub(rb"/StegoData\s*\([^)]*\)", b"", data)

        # Find the first Info dictionary or append before %%EOF
        stego_entry = b"\n" + cls._KEY + b" (" + hex_payload + b")"
        eof_idx = data.rfind(b"%%EOF")
        if eof_idx == -1:
            raise ValueError("Not a valid PDF (no %%EOF marker).")

        # Try to inject into existing Info dict
        info_match = re.search(rb"<<([^>]*?/Title|[^>]*?/Author|[^>]*?/Creator)[^>]*?>>",
                               data, re.DOTALL)
        if info_match:
            insert_at = info_match.end() - 2   # before closing >>
            data = data[:insert_at] + stego_entry + data[insert_at:]
        else:
            # Append a standalone Info object before %%EOF
            info_obj = b"\n99 0 obj\n<<" + stego_entry + b"\n>>\nendobj\n"
            data = data[:eof_idx] + info_obj + data[eof_idx:]

        with open(out_path, "wb") as f:
            f.write(data)

    @classmethod
    def decode(cls, stego_path: str) -> bytes:
        import re
        with open(stego_path, "rb") as f:
            data = f.read()

        m = re.search(rb"/StegoData\s*\(([^)]+)\)", data)
        if not m:
            raise ValueError("No hidden data found in PDF.")
        try:
            payload = bytes.fromhex(m.group(1).decode("ascii"))
        except Exception:
            raise ValueError("Hidden data in PDF is corrupt.")
        return _unpack_payload(payload)


# ─────────────────────────────────────────────
#  OFFICE OPEN XML STEGO  (.docx / .xlsx / .pptx)
# ─────────────────────────────────────────────

class OfficeDocStego:
    """Hide data inside Office Open XML files (ZIP-based).

    Strategy: inject a hidden XML part `docProps/stego.bin` (stored as
    base64 text) into the ZIP archive. The Office app ignores unknown parts.
    """

    _HIDDEN_PART = "docProps/stego.bin"

    @classmethod
    def encode(cls, cover_path: str, secret: bytes, out_path: str):
        import zipfile, base64, io
        payload = _pack_payload(secret)
        b64     = base64.b64encode(payload)

        with zipfile.ZipFile(cover_path, "r") as zin:
            names = zin.namelist()
            buf   = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
                for name in names:
                    if name == cls._HIDDEN_PART:
                        continue   # remove previous stego entry
                    zout.writestr(name, zin.read(name))
                zout.writestr(cls._HIDDEN_PART, b64)

        with open(out_path, "wb") as f:
            f.write(buf.getvalue())

    @classmethod
    def decode(cls, stego_path: str) -> bytes:
        import zipfile, base64
        with zipfile.ZipFile(stego_path, "r") as z:
            if cls._HIDDEN_PART not in z.namelist():
                raise ValueError("No hidden data found in Office document.")
            b64 = z.read(cls._HIDDEN_PART)
        payload = base64.b64decode(b64)
        return _unpack_payload(payload)


# ─────────────────────────────────────────────
#  HTML / CSS STEGO
# ─────────────────────────────────────────────

class HtmlStego:
    """Hide data in HTML/CSS using zero-width Unicode characters.

    Identical encoding to TextStego but operates on the raw file bytes
    decoded as UTF-8, inserting the hidden stream after the first tag
    or first word so the file still renders correctly in a browser.
    """

    # Reuse TextStego's zero-width character codec
    @classmethod
    def encode(cls, cover_path: str, secret: bytes, out_path: str):
        with open(cover_path, "r", encoding="utf-8", errors="replace") as f:
            cover_text = f.read()
        stego_text = TextStego.encode(cover_text, secret)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(stego_text)

    @classmethod
    def decode(cls, stego_path: str) -> bytes:
        with open(stego_path, "r", encoding="utf-8", errors="replace") as f:
            stego_text = f.read()
        return TextStego.decode(stego_text)


# ─────────────────────────────────────────────
#  PE / ELF BINARY STEGO
# ─────────────────────────────────────────────

class BinaryStego:
    """Hide data by appending after the binary's logical end.

    For PE (.exe/.dll) files the logical end is after the last section.
    For all other binaries we simply append after the existing content.
    This is the classic EOF-append technique — the OS loader ignores
    trailing bytes and the file still executes normally.
    """

    _SENTINEL = b"\x00STEGO\x00"

    @classmethod
    def encode(cls, cover_path: str, secret: bytes, out_path: str):
        payload = _pack_payload(secret)
        with open(cover_path, "rb") as f:
            data = f.read()

        # Strip any previous append
        idx = data.rfind(cls._SENTINEL)
        if idx != -1:
            data = data[:idx]

        with open(out_path, "wb") as f:
            f.write(data)
            f.write(cls._SENTINEL)
            f.write(payload)

    @classmethod
    def decode(cls, stego_path: str) -> bytes:
        with open(stego_path, "rb") as f:
            data = f.read()

        idx = data.rfind(cls._SENTINEL)
        if idx == -1:
            raise ValueError("No hidden data found in binary (sentinel missing).")
        payload = data[idx + len(cls._SENTINEL):]
        return _unpack_payload(payload)


# ─────────────────────────────────────────────
#  ARCHIVE STEGO  (.zip / .rar / .7z etc.)
# ─────────────────────────────────────────────

class ArchiveStego:
    """Hide data by appending after the archive's end-of-central-directory.

    ZIP files have a well-defined end marker (PK\x05\x06).  Data appended
    after it is ignored by every compliant ZIP tool.  For non-ZIP archives
    (RAR, 7z, tar, gz) the same EOF-append approach is used — archive tools
    stop reading at their own end marker and ignore trailing bytes.
    """

    _SENTINEL = b"\x00STEGO_ARCH\x00"

    @classmethod
    def encode(cls, cover_path: str, secret: bytes, out_path: str):
        payload = _pack_payload(secret)
        with open(cover_path, "rb") as f:
            data = f.read()

        # Strip any previous stego append
        idx = data.rfind(cls._SENTINEL)
        if idx != -1:
            data = data[:idx]

        with open(out_path, "wb") as f:
            f.write(data)
            f.write(cls._SENTINEL)
            f.write(payload)

    @classmethod
    def decode(cls, stego_path: str) -> bytes:
        with open(stego_path, "rb") as f:
            data = f.read()

        idx = data.rfind(cls._SENTINEL)
        if idx == -1:
            raise ValueError("No hidden data found in archive (sentinel missing).")
        payload = data[idx + len(cls._SENTINEL):]
        return _unpack_payload(payload)
# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def detect_type(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext in (".png", ".bmp", ".jpg", ".jpeg"):
        return "image"
    if ext == ".wav":
        return "audio"
    if ext in (".mp4", ".avi", ".mov", ".mkv"):
        return "video"
    if ext == ".pdf":
        return "pdf"
    if ext in (".docx", ".xlsx", ".pptx"):
        return "officedoc"
    if ext in (".html", ".htm", ".css"):
        return "html"
    if ext in (".exe", ".dll", ".so", ".elf"):
        return "binary"
    if ext in (".zip", ".rar", ".7z", ".tar", ".gz"):
        return "archive"
    return "text"


def auto_out_path(cover: str, suffix: str = "_encoded") -> str:
    """Generate output path with given suffix.

    - Lossy images (.jpg/.jpeg/.bmp) are forced to .png (LSB requires lossless).
    - All other formats keep their original extension so the file stays
      openable by its native application after encoding.
    """
    p   = Path(cover)
    ext = p.suffix.lower()
    if ext in (".jpg", ".jpeg", ".bmp"):
        return str(p.parent / (p.stem + suffix + ".png"))
    return str(p.parent / (p.stem + suffix + ext))


def pack_secret(secret_bytes: bytes, secret_name: str) -> bytes:
    """Prepend original filename header to secret bytes."""
    fname_bytes  = secret_name.encode("utf-8")
    fname_header = struct.pack(">H", len(fname_bytes)) + fname_bytes
    return fname_header + secret_bytes


def unpack_secret(raw: bytes):
    """Return (filename, data) from raw decoded bytes."""
    try:
        fname_len = struct.unpack(">H", raw[:2])[0]
        fname     = raw[2: 2 + fname_len].decode("utf-8")
        data      = raw[2 + fname_len:]
        return fname, data
    except Exception:
        return "extracted_secret", raw
