"""hidock_reader エントリポイント: python -m hidock_reader"""
import argparse
import os
from .transfer import run

DEFAULT_DEST = os.path.expanduser("~/HidockRecordings")


def main():
    parser = argparse.ArgumentParser(
        description="HiDock P1 から未コピーの録音ファイルをターゲットフォルダにコピーする"
    )
    parser.add_argument(
        "--dest", "-d",
        default=DEFAULT_DEST,
        help=f"コピー先フォルダ (デフォルト: {DEFAULT_DEST})"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="実際のコピーを行わず、対象ファイルを表示するだけ"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        metavar="N",
        help="直近N日以内の録音のみを対象にする"
    )
    args = parser.parse_args()

    try:
        run(dest_dir=args.dest, dry_run=args.dry_run, days=args.days)
    except RuntimeError as e:
        print(f"エラー: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
