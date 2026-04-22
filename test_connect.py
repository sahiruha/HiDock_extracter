"""HIDOCK P1 接続テスト - QUERY_FILE_LIST"""
import usb.core
import struct

VID = 0x10D6
PID = 0xB00E
EP_OUT = 0x01
EP_IN  = 0x82
CMD_QUERY_FILE_LIST = 0x0004

def build_packet(cmd, seq=0, body=b''):
    header = bytes([0x12, 0x34, (cmd >> 8) & 0xFF, cmd & 0xFF]) + \
             struct.pack('>I', seq) + \
             struct.pack('>I', len(body))
    return header + body

dev = usb.core.find(idVendor=VID, idProduct=PID)
if dev is None:
    print("デバイスが見つかりません")
    exit(1)

print(f"デバイス発見: HiDock P1")

try:
    if dev.is_kernel_driver_active(0):
        dev.detach_kernel_driver(0)
        print("カーネルドライバをデタッチしました")
except Exception as e:
    print(f"detach スキップ: {e}")

dev.set_configuration()
usb.util.claim_interface(dev, 0)
print("インターフェース確保完了")

pkt = build_packet(CMD_QUERY_FILE_LIST, seq=1)
print(f"送信: {pkt.hex()}")

dev.write(EP_OUT, pkt, timeout=3000)
print("コマンド送信完了。レスポンス待機中...")

resp = bytes(dev.read(EP_IN, 65536, timeout=5000))
print(f"\n受信 {len(resp)} バイト")

body = resp[12:]
# 先頭4バイトはフラグ/カウント
print(f"body先頭4バイト: {body[:4].hex()}")

# エントリ構造 (stride=57):
#   [0:5]  5バイト メタデータ
#   [5]    1バイト ファイル名長 (0x1b=27)
#   [6:33] 27バイト ファイル名+null
#   [33:37] 4バイト ファイルサイズ (big-endian)
#   [37:41] 4バイト フォーマット等
#   [41:57] 16バイト MD5ハッシュ
ENTRY_SIZE = 57
ENTRY_START = 4

print(f"\n{'No':>4}  {'FileName':<35} {'Size(bytes)':>12}  {'MD5'}")
print("-" * 90)

files = []
offset = ENTRY_START
entry_no = 0
while offset + ENTRY_SIZE <= len(body):
    entry = body[offset:offset + ENTRY_SIZE]
    fname_len = entry[5]
    fname = entry[6:6 + fname_len - 1].decode('ascii', errors='replace')  # null除く
    fsize = struct.unpack('>I', entry[33:37])[0]
    fmt   = struct.unpack('>I', entry[37:41])[0]
    md5   = entry[41:57].hex()
    files.append({'name': fname, 'size': fsize, 'format': fmt, 'md5': md5})
    print(f"{entry_no:>4}  {fname:<35} {fsize:>12}  {md5}")
    offset += ENTRY_SIZE
    entry_no += 1
    if entry_no >= 30:  # 先頭30件のみ表示
        print(f"  ... (以下省略, 合計 {(len(body) - ENTRY_START) // ENTRY_SIZE} エントリ)")
        break
