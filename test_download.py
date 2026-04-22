"""HIDOCK P1 - ファイル一覧取得 + 先頭10ファイルを ~/Downloads にダウンロード"""
import usb.core
import struct
import os
import sys

VID = 0x10D6
PID = 0xB00E
EP_OUT = 0x01
EP_IN  = 0x82

CMD_QUERY_FILE_LIST = 0x0004
CMD_TRANSFER_FILE   = 0x0005

DEST = os.path.expanduser("~/Downloads")
MP3_BITRATE_KBPS = 96  # ヘッダ解析より (FF FB 74 = MPEG1 Layer3 96kbps)

def fmt_size(n):
    if n >= 1024 * 1024:
        return f"{n / (1024*1024):.2f} MiB"
    return f"{n / 1024:.1f} KiB"

def fmt_duration(size_bytes):
    secs = size_bytes * 8 / (MP3_BITRATE_KBPS * 1000)
    m, s = divmod(int(secs), 60)
    return f"{m}:{s:02d}"

# ---- パケット構築 ----
def build_packet(cmd, seq=0, body=b''):
    header = bytes([0x12, 0x34, (cmd >> 8) & 0xFF, cmd & 0xFF]) + \
             struct.pack('>I', seq) + \
             struct.pack('>I', len(body))
    return header + body

# ---- デバイス接続 ----
def open_device():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        print("ERROR: HiDock P1 が見つかりません。USB接続を確認してください。")
        sys.exit(1)
    try:
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
    except Exception:
        pass
    dev.set_configuration()
    usb.util.claim_interface(dev, 0)
    print("HiDock P1 接続完了")
    return dev

# ---- ファイル一覧取得 ----
def query_file_list(dev):
    dev.write(EP_OUT, build_packet(CMD_QUERY_FILE_LIST, seq=1), timeout=3000)
    resp = bytes(dev.read(EP_IN, 131072, timeout=10000))

    body = resp[12:]
    ENTRY_SIZE = 57
    ENTRY_START = 4
    files = []
    offset = ENTRY_START
    while offset + ENTRY_SIZE <= len(body):
        entry = body[offset:offset + ENTRY_SIZE]
        fname_len = entry[5]
        if fname_len == 0:
            break
        fname = entry[6:6 + fname_len - 1].decode('ascii', errors='replace')
        fsize = struct.unpack('>I', entry[33:37])[0]
        fmt   = struct.unpack('>I', entry[37:41])[0]
        md5   = entry[41:57].hex()
        files.append({'name': fname, 'size': fsize, 'format': fmt, 'md5': md5})
        offset += ENTRY_SIZE
    return files

# ---- Jensenパケットバッファ解析 ----
def parse_jensen_packets(buf):
    """
    バッファ内の複数Jensenパケットを解析してペイロードを結合する。
    body_len=0のパケットが来たら転送完了。
    戻り値: (結合済みデータ, 転送完了フラグ)
    """
    result = bytearray()
    done = False
    pos = 0
    while pos + 12 <= len(buf):
        if buf[pos] == 0x12 and buf[pos + 1] == 0x34:
            body_len = struct.unpack('>I', buf[pos + 8: pos + 12])[0]
            if body_len == 0:
                done = True
                break
            data_end = pos + 12 + body_len
            result.extend(buf[pos + 12: data_end])
            pos = data_end
        else:
            # 予期しないデータ: 残りをそのまま追加
            result.extend(buf[pos:])
            break
    return bytes(result), done

# ---- ファイルダウンロード ----
def download_file(dev, filename, dest_path, expected_size, seq):
    body = filename.encode('ascii') + b'\x00'
    dev.write(EP_OUT, build_packet(CMD_TRANSFER_FILE, seq=seq, body=body), timeout=3000)

    data = bytearray()
    while True:
        try:
            chunk = bytes(dev.read(EP_IN, 131072, timeout=10000))
        except usb.core.USBTimeoutError:
            print(f"  タイムアウト (受信済み: {len(data)} バイト)")
            break

        payload, done = parse_jensen_packets(chunk)
        data.extend(payload)

        received = len(data)
        print(f"\r  {received:>10} / {expected_size:>10} バイト ({received*100//max(expected_size,1):>3}%)", end='', flush=True)

        if done or (expected_size > 0 and received >= expected_size):
            break

    print()

    with open(dest_path, 'wb') as f:
        f.write(data)
    return len(data)

# ---- メイン ----
dev = open_device()

print("\nファイル一覧を取得中...")
files = query_file_list(dev)
print(f"デバイス上のファイル数: {len(files)}")

targets = files[:100]
print(f"\n先頭 {len(targets)} ファイルを {DEST} にダウンロードします\n")

for i, f in enumerate(targets):
    dest = os.path.join(DEST, f['name'])
    size_str = fmt_size(f['size'])
    dur_str  = fmt_duration(f['size'])
    print(f"[{i+1:2d}/{len(targets)}] {f['name']}  {size_str:>10}  {dur_str:>6}")
    if os.path.exists(dest):
        print("  スキップ (既存)")
        continue
    received = download_file(dev, f['name'], dest, f['size'], seq=10 + i)
    match = "✓" if received == f['size'] else f"! 期待={f['size']} 実際={received}"
    print(f"  保存完了: {match}")

print("\n完了")
