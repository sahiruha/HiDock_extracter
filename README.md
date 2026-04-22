# HiDock P1 Extractor

[English](#english) | [日本語](#日本語)

---

## English

A Python CLI tool that connects to a [HiDock P1](https://www.hidock.com/products/hidock-p1-ai-voice-recorder) voice recorder via USB and copies new recordings to a local folder — without using the official HiNotes app.

### Features

- Connects directly to the HiDock P1 over USB (no HiNotes required)
- Detects which recordings have already been copied and skips them
- Saves `.hda` recordings as `.mp3` (the files are MP3 internally — just renamed)
- Dry-run mode to preview what would be copied
- Shows file size and estimated duration for each recording

### Requirements

- Python 3.8+
- [pyusb](https://github.com/pyusb/pyusb) (`pip install pyusb`)
- [libusb](https://libusb.info/) (required by pyusb)
  - macOS: `brew install libusb`
  - Linux: `apt install libusb-1.0-0`
- **macOS / Linux**: must run with `sudo` to access USB devices

### Installation

```bash
git clone https://github.com/sahiruha/HiDock_extracter.git
cd HiDock_extracter
pip install pyusb
```

### Usage

Connect your HiDock P1 via USB, then:

```bash
# Dry-run: preview what would be copied
sudo python3 -m hidock_reader --dry-run --dest ~/Recordings

# Copy new recordings
sudo python3 -m hidock_reader --dest ~/Recordings

# Copy only recordings from the last 7 days
sudo python3 -m hidock_reader --dest ~/Recordings --days 7
```

#### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--dest`, `-d` | `~/HidockRecordings` | Destination folder |
| `--dry-run`, `-n` | off | Preview only, no files are copied |
| `--days N` | all | Only process recordings from the last N days |

### How It Works

The HiDock P1 uses a vendor-specific USB protocol (internally called "Jensen") rather than standard USB Mass Storage. This tool implements the protocol directly using `pyusb`.

#### Jensen Protocol

Packet format (12-byte header + body):
```
[0x12][0x34][CMD_HI][CMD_LO][SEQ x4][LEN x4][BODY...]
```

Commands used:

| CMD | Name | Description |
|-----|------|-------------|
| `0x0004` | `QUERY_FILE_LIST` | Get list of all recordings (name, size, MD5) |
| `0x0005` | `TRANSFER_FILE` | Download a file by name |

#### Device Info

| Field | Value |
|-------|-------|
| Vendor ID | `0x10D6` |
| Product ID | `0xB00E` |
| Interface | Class `0xFF` (Vendor-specific) |
| Endpoints | OUT=`0x01`, IN=`0x82` (Bulk) |

#### File Format

HiDock P1 saves recordings as `.hda` files. Despite the extension, these are standard MP3 files (MPEG1 Layer3, 96 kbps, 48 kHz). This tool saves them with a `.mp3` extension.

### Project Structure

```
hidock_reader/
├── __main__.py     # CLI entry point (argparse)
├── device.py       # USB communication & Jensen protocol
└── transfer.py     # Orchestration: diff, download, save
```

### License

MIT

---

## 日本語

[HiDock P1](https://www.hidock.com/products/hidock-p1-ai-voice-recorder) をUSBで接続し、未コピーの録音ファイルを指定フォルダに取り出すPython CLIツールです。公式アプリ「HiNotes」不要で動作します。

### 背景

HiDock P1は優秀な録音機器ですが、公式アプリのUIが使いにくく、ファイルを取り出すたびに手動操作が必要でした。USBプロトコルを解析した結果、独自プロトコル「Jensen」を実装することで直接アクセスできることがわかり、このツールを作りました。

### 機能

- USB経由でHiDock P1に直接接続（HiNotes不要）
- コピー済みファイルを自動スキップ（拡張子なしのファイル名で照合）
- `.hda` ファイルを `.mp3` として保存（中身はMP3そのもの）
- ドライランモードで事前確認が可能
- ファイルサイズ・推定録音時間を一覧表示

### 必要環境

- Python 3.8+
- [pyusb](https://github.com/pyusb/pyusb)（`pip install pyusb`）
- [libusb](https://libusb.info/)
  - macOS: `brew install libusb`
  - Linux: `apt install libusb-1.0-0`
- USBデバイスへのアクセスに `sudo` が必要（macOS / Linux）

### インストール

```bash
git clone https://github.com/sahiruha/HiDock_extracter.git
cd HiDock_extracter
pip install pyusb
```

### 使い方

HiDock P1をUSBで繋いで実行します。

```bash
# ドライラン（実際のコピーなし、確認のみ）
sudo python3 -m hidock_reader --dry-run --dest ~/Recordings

# 未コピーファイルをすべてコピー
sudo python3 -m hidock_reader --dest ~/Recordings

# 直近7日分だけコピー
sudo python3 -m hidock_reader --dest ~/Recordings --days 7
```

#### オプション

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--dest`, `-d` | `~/HidockRecordings` | コピー先フォルダ |
| `--dry-run`, `-n` | オフ | コピーせずに対象ファイルを表示するだけ |
| `--days N` | 全件 | 直近N日以内の録音のみを対象にする |

### 仕組み

HiDock P1は標準のUSBマスストレージではなく、独自プロトコル（内部名: **Jensen**）を使用しています。本ツールは `pyusb` でこのプロトコルを直接実装しています。

#### Jensenプロトコル

パケットフォーマット（12バイトヘッダ＋ボディ）:
```
[0x12][0x34][CMD_HI][CMD_LO][SEQ x4][LEN x4][BODY...]
```

使用コマンド:

| CMD | 名前 | 用途 |
|-----|------|------|
| `0x0004` | `QUERY_FILE_LIST` | ファイル一覧取得（名前・サイズ・MD5） |
| `0x0005` | `TRANSFER_FILE` | ファイルのダウンロード |

#### デバイス情報

| 項目 | 値 |
|------|-----|
| Vendor ID | `0x10D6` |
| Product ID | `0xB00E` |
| Interface | Class `0xFF`（ベンダー独自） |
| Endpoints | OUT=`0x01`、IN=`0x82`（Bulk） |

#### ファイル形式

HiDock P1は録音を `.hda` 拡張子で保存しますが、実体はMP3ファイル（MPEG1 Layer3、96kbps、48kHz）です。本ツールは `.mp3` として保存します。

### プロジェクト構成

```
hidock_reader/
├── __main__.py     # CLIエントリポイント（argparse）
├── device.py       # USB通信・Jensenプロトコル実装
└── transfer.py     # 差分検出・ダウンロード・保存
```

### ライセンス

MIT
