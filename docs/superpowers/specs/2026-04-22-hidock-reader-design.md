# HIDOCK P1 Reader - Design Spec

## Overview

HIDOCK P1からPCへ未コピー音声ファイルを自動抽出するPython CLIツール。
USB接続時にコマンド一発で実行し、コピー済みMD5ハッシュを記録することで重複コピーを防ぐ。

## デバイス仕様

| 項目 | 値 |
|------|-----|
| Vendor ID | 0x10D6 |
| Product ID | 0xB00E |
| Interface | Class 0xFF (Vendor-specific), SubClass 0xF0 |
| Endpoints | OUT=EP1, IN=EP2 (Bulk) |
| Protocol | Jensen（内部名） |

## Jensenプロトコル

パケットフォーマット（12バイトヘッダ + ボディ）:
```
[0x12][0x34][CMD_HI][CMD_LO][SEQ x4][LEN x4][BODY...]
```

使用コマンド:
- `0x0004` QUERY_FILE_LIST: ファイル名・サイズ・フォーマット・MD5ハッシュの一覧取得
- `0x0005` TRANSFER_FILE: ファイル名を指定してストリーミングダウンロード
- `0x0006` QUERY_FILE_COUNT: ファイル数取得

## アーキテクチャ

```
hidock_reader/
  __main__.py   # CLIエントリポイント（argparse）
  device.py     # USB通信・Jensenプロトコル実装
  transfer.py   # 転送オーケストレーション
  state.py      # copied.json 読み書き
  config.py     # 設定管理
```

## データフロー

1. `config.py` で設定解決（CLI引数 → デフォルト値）
2. `device.py` でUSBデバイスを検出・接続（VID/PIDで特定）
3. `device.query_file_list()` でファイル一覧取得（CMD 0x0004）
4. `state.load_state()` でコピー済みMD5セットを読み込み
5. 未コピーファイル（MD5が記録にないもの）を抽出
6. 各ファイルを `device.download_file()` → 宛先フォルダに書き込み
7. `state.save_state()` でMD5を追記保存

## 状態管理ファイル（copied.json）

```json
{
  "copied_md5s": ["abc123...", "def456..."],
  "last_run": "2026-04-22T15:00:00"
}
```

デフォルト保存場所: `~/.hidock_state.json`

## CLI仕様

```
python -m hidock_reader [--dest PATH] [--state-file PATH]

Options:
  --dest PATH        コピー先フォルダ（デフォルト: ~/HidockRecordings）
  --state-file PATH  状態ファイルのパス（デフォルト: ~/.hidock_state.json）
```

## 依存ライブラリ

- `pyusb` (>=1.0.0): USB通信
- Python標準ライブラリのみそれ以外

## エラーハンドリング

- デバイスが見つからない場合: わかりやすいエラーメッセージを表示して終了
- 転送中断: 部分ファイルを削除し、その旨を表示（状態には記録しない）
- 宛先フォルダが存在しない場合: 自動作成
