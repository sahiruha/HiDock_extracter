# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

HiDock P1 ボイスレコーダーからUSB経由で録音ファイル(.hda = 実質MP3)をコピーするPython CLIツール。公式HiNotesアプリ不要。

## Running

```bash
# venv の Python を使う（system Python は externally-managed で pip 不可）
.venv/bin/python3 -m hidock_reader --dest ~/Recordings --days 7

# USB デバイスアクセスに sudo が必要
sudo .venv/bin/python3 -m hidock_reader --dest ~/Recordings
```

CLIオプション: `--dest`(コピー先), `--dry-run`(プレビュー), `--days N`(直近N日), `--no-cache`(キャッシュ無視)

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install pyusb
# macOS: brew install libusb
```

## Architecture

`hidock_reader/` パッケージは3層構成:

- **device.py** — USB通信層。Jensenプロトコル(独自バイナリプロトコル)でHiDock P1と通信。パケットヘッダは `0x1234` マジック + コマンドID + シーケンス番号 + ボディ長。コマンドは `0x0004`(ファイル一覧) と `0x0005`(ファイル転送)の2種。レスポンスは複数パケットに分割されるためループで受信。
- **transfer.py** — 転送オーケストレーション。デバイスとローカルの差分を取り、未コピーファイルだけを転送。ファイル一覧は `~/.cache/hidock_reader/file_list.json` にキャッシュ(TTL 1時間)。ファイル名から日付をパース(`2026Jan01-163234-Wip00.hda` 形式)して `--days` フィルタに使用。
- **__main__.py** — argparse エントリポイント。

ルート直下の `test_connect.py`, `test_download.py`, `debug_list.py` は開発時の手動デバッグスクリプト(自動テストではない)。

## Key details

- USB VID=`0x10D6`, PID=`0xB00E`
- .hda ファイルの中身はMP3(96kbps)。コピー時に拡張子を .mp3 に変換
- ファイルの重複判定は拡張子なしのファイル名で比較(MD5ではない)
