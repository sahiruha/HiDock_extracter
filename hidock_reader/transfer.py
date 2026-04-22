"""転送オーケストレーション: デバイスとターゲットディレクトリの差分コピー"""
import os
import datetime
from . import device as dev_mod

# ファイル名フォーマット: 2026Jan01-163234-Wip00.hda
_MONTH_MAP = {m: i+1 for i, m in enumerate(
    ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
)}

def _parse_file_date(name):
    """ファイル名から日付を返す。パース失敗時は None。"""
    try:
        date_part = name[:9]           # e.g. "2026Jan01"
        year  = int(date_part[:4])
        month = _MONTH_MAP[date_part[4:7]]
        day   = int(date_part[7:9])
        return datetime.date(year, month, day)
    except Exception:
        return None

MP3_BITRATE_KBPS = 96


def _fmt_size(n):
    for unit in ("KiB", "MiB", "GiB", "TiB"):
        n /= 1024
        if n < 1024:
            return f"{n:.2f} {unit}"
    return f"{n:.2f} TiB"


def _fmt_duration(size_bytes):
    secs = size_bytes * 8 / (MP3_BITRATE_KBPS * 1000)
    m, s = divmod(int(secs), 60)
    return f"{m}:{s:02d}"


def run(dest_dir, dry_run=False, days=None):
    """
    ターゲットディレクトリにないファイルをデバイスからコピーする。
    dry_run=True の場合はコピーせず対象ファイルを表示するだけ。
    """
    if not dry_run:
        os.makedirs(dest_dir, exist_ok=True)
    elif not os.path.isdir(dest_dir):
        print(f"エラー: コピー先ディレクトリが存在しません: {dest_dir}")
        return

    print("HiDock P1 に接続中...")
    dev = dev_mod.open_device()
    print("接続完了\n")

    print("ファイル一覧を取得中...")
    device_files = dev_mod.query_file_list(dev)
    print(f"デバイス上のファイル数: {len(device_files)}\n")

    # ターゲットディレクトリの既存ファイル名セット（拡張子なしで比較）
    existing_stems = {os.path.splitext(f)[0] for f in os.listdir(dest_dir)}

    def _is_done(f):
        stem = os.path.splitext(f['name'])[0]
        return stem in existing_stems

    # --days フィルタ
    if days is not None:
        cutoff = datetime.date.today() - datetime.timedelta(days=days)
        device_files_filtered = [
            f for f in device_files
            if (_parse_file_date(f['name']) or datetime.date.min) >= cutoff
        ]
    else:
        device_files_filtered = device_files

    to_copy = [f for f in device_files_filtered if not _is_done(f)]
    skip    = len(device_files_filtered) - len(to_copy)

    scope = f"直近{days}日" if days is not None else "全件"
    print(f"対象範囲: {scope}  ({len(device_files_filtered)} ファイル中)")
    print(f"コピー対象: {len(to_copy)} ファイル  /  スキップ(既存): {skip} ファイル")
    if dry_run:
        print("【ドライランモード - 実際のコピーは行いません】\n")

    if not to_copy and not dry_run:
        print("コピーするファイルはありません。")
        return

    print()
    total_bytes = sum(f['size'] for f in to_copy)
    print(f"{'No':>4}  {'ファイル名':<38} {'サイズ':>10}  {'時間':>6}  {'状態'}")
    print("-" * 80)

    if dry_run:
        for i, f in enumerate(device_files_filtered):
            size_str = _fmt_size(f['size'])
            dur_str  = _fmt_duration(f['size'])
            status = "済" if _is_done(f) else "コピー予定"
            print(f"{i+1:>4}  {f['name']:<38} {size_str:>10}  {dur_str:>6}  {status}")
        print(f"\n[ドライラン] {len(to_copy)} ファイル ({_fmt_size(total_bytes)}) がコピー対象です")
        return

    for i, f in enumerate(to_copy):
        size_str = _fmt_size(f['size'])
        dur_str  = _fmt_duration(f['size'])
        mp3_name  = os.path.splitext(f['name'])[0] + '.mp3'
        dest_path = os.path.join(dest_dir, mp3_name)

        print(f"{i+1:>4}  {mp3_name:<38} {size_str:>10}  {dur_str:>6}", end='  ', flush=True)

        def on_progress(received, expected):
            pct = received * 100 // max(expected, 1)
            print(f"\r{i+1:>4}  {mp3_name:<38} {size_str:>10}  {dur_str:>6}  {pct:>3}%", end='', flush=True)

        data = dev_mod.download_file(dev, f['name'], f['size'], seq=100 + i, on_progress=on_progress)

        # 部分受信の場合は削除
        if len(data) != f['size']:
            print(f"\r{i+1:>4}  {mp3_name:<38} {size_str:>10}  {dur_str:>6}  NG (期待={f['size']} 受信={len(data)})")
            continue

        with open(dest_path, 'wb') as fp:
            fp.write(data)
        print(f"\r{i+1:>4}  {f['name']:<38} {size_str:>10}  {dur_str:>6}  OK")

    if not dry_run:
        print(f"\n完了: {len(to_copy)} ファイル ({_fmt_size(total_bytes)})")
    else:
        print(f"\n[ドライラン] {len(to_copy)} ファイル ({_fmt_size(total_bytes)}) がコピー対象です")
