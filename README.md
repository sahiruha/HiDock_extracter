# HiDock P1 Extractor

A Python CLI tool that connects to a [HiDock P1](https://www.hidock.com/products/hidock-p1-ai-voice-recorder) voice recorder via USB and copies new recordings to a local folder — without using the official HiNotes app.

## Features

- Connects directly to the HiDock P1 over USB (no HiNotes required)
- Detects which recordings have already been copied and skips them
- Saves `.hda` recordings as `.mp3` (the files are MP3 internally — just renamed)
- Dry-run mode to preview what would be copied
- Shows file size and estimated duration for each recording

## Requirements

- Python 3.8+
- [pyusb](https://github.com/pyusb/pyusb) (`pip install pyusb`)
- [libusb](https://libusb.info/) (required by pyusb)
  - macOS: `brew install libusb`
  - Linux: `apt install libusb-1.0-0`
- **macOS / Linux**: must run with `sudo` to access USB devices

## Installation

```bash
git clone https://github.com/sahiruha/HiDock_extracter.git
cd HiDock_extracter
pip install pyusb
```

## Usage

Connect your HiDock P1 via USB, then:

```bash
# Dry-run: preview what would be copied
sudo python3 -m hidock_reader --dry-run --dest ~/Recordings

# Copy new recordings
sudo python3 -m hidock_reader --dest ~/Recordings
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--dest`, `-d` | `~/HidockRecordings` | Destination folder |
| `--dry-run`, `-n` | off | Preview only, no files are copied |

## How It Works

The HiDock P1 uses a vendor-specific USB protocol (internally called "Jensen") rather than standard USB Mass Storage. This tool implements the protocol directly using `pyusb`.

### Jensen Protocol

**Packet format** (12-byte header + body):
```
[0x12][0x34][CMD_HI][CMD_LO][SEQ x4][LEN x4][BODY...]
```

**Commands used:**

| CMD | Name | Description |
|-----|------|-------------|
| `0x0004` | `QUERY_FILE_LIST` | Get list of all recordings (name, size, MD5) |
| `0x0005` | `TRANSFER_FILE` | Download a file by name |

### Device Info

| Field | Value |
|-------|-------|
| Vendor ID | `0x10D6` |
| Product ID | `0xB00E` |
| Interface | Class `0xFF` (Vendor-specific) |
| Endpoints | OUT=`0x01`, IN=`0x82` (Bulk) |

### File Format

HiDock P1 saves recordings as `.hda` files. Despite the extension, these are standard MP3 files (MPEG1 Layer3, 96 kbps, 48 kHz). This tool saves them with a `.mp3` extension.

## Project Structure

```
hidock_reader/
├── __main__.py     # CLI entry point (argparse)
├── device.py       # USB communication & Jensen protocol
└── transfer.py     # Orchestration: diff, download, save
```

## License

MIT
