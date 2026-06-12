# StegoSuite v2.0
### A Steganography Toolkit for Text, Image, Audio, PDF, Office Files, HTML, Binary, Archive
<img width="2558" height="1142" alt="image" src="https://github.com/user-attachments/assets/c0801944-8d7c-4697-9cdf-a4f96e68255a" />
</br>


## Project Background

This project is a reattempt of a previous academic assignment, done professionally.

The original version was incomplete. It could only handle images well along with audio and video but not reliably. 

I wanted to build something I would actually be proud to show. This software, StegoSuite v2.0 is that!

A clean, professional desktop application that actually handles the full picture of what is mostly possible. It supports nine different file type categories for both encoding and decoding, something I genuinely could not do the first time around.

The architecture is properly separated (GUI, logic, and styling are all independent modules), the UI is polished, and every carrier format has a real, technically sound steganography method behind it rather than a hack that sort of works. </br>

---

## What Is Steganography?

<img width="1960" height="706" alt="image" src="https://github.com/user-attachments/assets/626a861d-ece2-410d-8765-0017154403c5" />
Diagram reference: https://www.scaler.com/topics/difference-between-cryptography-and-steganography/


Steganography is the practice of **hiding secret information inside an ordinary, innocent-looking file** so that no one even suspects a message is there. Unlike encryption, which scrambles data so it cannot be read, steganography hides the fact that any secret exists at all.

The file used to carry the hidden message is called the **cover file** or **carrier**. After encoding, it becomes the **stego file**. It looks and behaves completely normally to anyone who opens it, while secretly containing the hidden payload embedded within. </br>

<img width="991" height="595" alt="image" src="https://github.com/user-attachments/assets/b4661e8d-6d44-45d0-8d39-680d60c3f105" />
Diagram reference: https://null-byte.wonderhowto.com/how-to/steganography-hide-secret-data-inside-image-audio-file-seconds-0180936/
</br>

Classic examples: hiding a message in the pixels of a photo, tucking data into the silence of an audio recording, or injecting invisible characters into a text document. To the human eye and ear, nothing has changed. But the data is there.

---

## How StegoSuite Works

StegoSuite has three main components:

- **`main.py`** is the PyQt5 GUI application. It provides the Encode, Decode, Log, and Methods tabs, handles file browsing and drag-and-drop, runs encoding/decoding on a background worker thread, and writes to the operation log.
- **`steganography_functions.py`** contains all the core stego logic, completely separate from the GUI. Each file type has its own class with `encode()` and `decode()` methods.
- **`styling.py`** holds the QSS stylesheet, palette setup, and reusable GUI widgets like the drag-and-drop file label.

### Payload Header Format

Every hidden payload, regardless of file type, is wrapped in a standard binary header before being embedded:

```
[4 bytes]  Magic marker    0xDE 0xAD 0xBE 0xEF
[1 byte ]  Version         0x01
[4 bytes]  Payload size    big-endian uint32
[2 bytes]  Filename len    big-endian uint16
[N bytes]  Original filename  (UTF-8)
[M bytes]  File content  (raw bytes)
```

This means when you decode a stego file, StegoSuite can reconstruct the original file with its correct filename automatically. The magic marker also lets the decoder immediately verify whether a file contains hidden data.

---

## Supported File Types

### 1. Text Files (.txt)
**Technique: Zero-width Unicode character injection**

Hidden bytes are encoded as invisible Unicode characters and inserted after the first word of the cover text. `U+200B` represents a `0` bit, `U+200C` represents a `1` bit, and `U+200D` acts as a byte separator. The document reads completely normally in any text editor because these characters are invisible and non-printing.

**Capacity:** Virtually unlimited, bounded only by storage space.

**Limitation:** Copy-pasting into plain ASCII systems (e.g. some web forms) will strip zero-width characters. The file must be preserved byte-for-byte.

---

### 2. Image Files (.png, .bmp)
**Technique: 1-bit LSB (Least-Significant Bit) substitution**

The least-significant bit of every RGB channel byte in each pixel is replaced with one bit of the payload. A change of ±1 in a 0 to 255 colour channel is completely imperceptible to the human eye. The visual difference is less than 0.4%.

**Capacity:** Width × Height × 3 bits. A 1920×1080 image can hold roughly 777 KB.

**Output:** Always saved as lossless PNG. JPEG re-encoding would destroy the hidden bits via DCT compression.

**Limitation:** Do not re-save the output as JPEG. Lossy compression is fatal to LSB-encoded data.

---

### 3. Audio Files (.wav)
**Technique: 1-bit LSB substitution on 16-bit PCM samples**

The least-significant bit of each 16-bit audio sample is replaced with one payload bit. A change of ±1 in a ±32,768 amplitude range is a ~0.003% variation, well below the threshold of human hearing.

**Capacity:** Total samples × channels bits. A 3-minute 44.1 kHz stereo WAV file has roughly 3.7 MB of capacity.

**Limitation:** Only uncompressed WAV is supported. MP3, AAC, and OGG use lossy encoding that destroys LSBs.

---

### 4. Video Files (.mp4, .avi, .mov, .mkv)
**Technique: Per-frame 1-bit LSB substitution on BGR pixel data**

Payload bits are spread sequentially across video frames using OpenCV, one bit per channel byte per pixel. The decoder reads only as many frames as needed to recover the full payload.

**Capacity:** Width × Height × 3 × Frame count bits. A 1280×720 video at 30 fps for 10 seconds has roughly 103 MB of capacity.

**Output:** Always saved as a lossless AVI container (codec priority: FFV1 > HFYU > RGBA > DIB). Lossy codecs like H.264 completely destroy hidden data via block-DCT compression.

**Limitation:** Output files are larger than the original due to the lossless container. Audio tracks are not preserved in the output.

---

### 5. PDF Files (.pdf)
**Technique: Metadata field injection**

The encoded payload (hex-encoded) is injected into a hidden `/StegoData` field inside the PDF's Info dictionary object. PDF readers render the document completely normally and ignore unknown metadata fields.

**Limitation:** Some aggressive PDF optimisers or "clean metadata" tools may strip unknown dictionary entries.

---

### 6. Office Documents (.docx, .xlsx, .pptx)
**Technique: Hidden ZIP part injection**

Office Open XML files are internally ZIP archives. StegoSuite injects a hidden file (`docProps/stego.bin`, stored as base64) into the archive. Microsoft Office and LibreOffice ignore unknown parts entirely, so the document opens and functions normally.

**Limitation:** Tools that repack or optimise the ZIP structure may strip the hidden part.

---

### 7. HTML and CSS Files (.html, .htm, .css)
**Technique: Zero-width Unicode character injection**

Identical to the text file method. Invisible Unicode characters are injected after the first tag or word in the file. The HTML renders perfectly in any browser and the hidden characters are non-printing with no visual effect.

**Limitation:** HTML minifiers, formatters, or copy-paste into plain ASCII environments will strip zero-width characters.

---

### 8. Binary Executables (.exe, .dll, .so, .elf)
**Technique: EOF (end-of-file) append with sentinel marker**

The payload is appended after the binary's logical end, preceded by a sentinel byte sequence (`\x00STEGO\x00`). The OS loader stops reading at the last valid section and ignores trailing bytes, so the executable continues to run normally. For PE files (.exe, .dll), the append is placed after the last section boundary.

**Limitation:** Some antivirus heuristics flag binaries with unusual trailing data. Code signing will be invalidated.

---

### 9. Archive Files (.zip, .rar, .7z, .tar, .gz)
**Technique: EOF append after end-of-central-directory**

For ZIP files, data is appended after the well-defined `PK\x05\x06` end-of-central-directory marker. Every compliant ZIP tool stops reading there and ignores anything after it. For RAR, 7z, tar, and gz archives, the same EOF-append approach is used; each format's own end marker causes the tool to stop before reaching the hidden data.

**Limitation:** Archive re-packing tools or re-compression will discard appended data.

---

## Project Structure

```
StegoSuite/
├── main.py                      # GUI application entry point
├── steganography_functions.py   # Core stego logic (all file types)
├── styling.py                   # QSS stylesheet, palette, shared widgets
├── TestFiles/                   # Place cover files and secret files here
├── EncodedDecodedFiles/         # Output files saved here automatically
└── LogFiles/                    # Saved operation logs
```

---

## Requirements

- Python 3.8+
- PyQt5
- Pillow
- NumPy
- OpenCV (cv2) for video support

Install dependencies:
```bash
pip install PyQt5 Pillow numpy opencv-python
```

Run the application:
```bash
python main.py
```

---

## Usage

1. **Encode tab:** Select a cover file (the carrier), select a secret file to hide, choose the file type (or leave on Auto-detect), and click Encode. The output is saved to `EncodedDecodedFiles/`.
<img width="2539" height="1039" alt="image" src="https://github.com/user-attachments/assets/5b7ffa10-55a0-493b-9707-822e3498bc1e" />


3. **Decode tab:** Select a stego file previously encoded by StegoSuite, click Decode, and the hidden file will be extracted and saved.
<img width="2551" height="1132" alt="image" src="https://github.com/user-attachments/assets/b2c5eb34-4b80-46f8-8b08-f5cada3ba8bd" />

   
5. **Log tab:** View a timestamped record of all encode/decode operations. Logs can be saved to `LogFiles/`.
<img width="2551" height="484" alt="image" src="https://github.com/user-attachments/assets/452c3e0b-e841-40b4-abbe-a9e0f7d8ce82" />

   
7. **Methods tab:** In-app reference for all steganography techniques and their capacities and limitations.
<img width="2516" height="1009" alt="image" src="https://github.com/user-attachments/assets/f11ac491-5a45-4d19-aa73-ac6f67bde20b" />
<img width="2504" height="1107" alt="image" src="https://github.com/user-attachments/assets/81c7d606-ec6b-4df1-b3db-0fbb520c80da" />

