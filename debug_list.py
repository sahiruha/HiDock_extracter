"""ファイルリストの生バイトをダンプして構造を調べる"""
import usb.core, usb.util, struct, sys

VID, PID, EP_OUT, EP_IN = 0x10D6, 0xB00E, 0x01, 0x82

def build_packet(cmd, seq=0, body=b''):
    return bytes([0x12, 0x34, (cmd >> 8) & 0xFF, cmd & 0xFF]) + \
           struct.pack('>I', seq) + struct.pack('>I', len(body)) + body

dev = usb.core.find(idVendor=VID, idProduct=PID)
try:
    if dev.is_kernel_driver_active(0): dev.detach_kernel_driver(0)
except: pass
dev.set_configuration()
usb.util.claim_interface(dev, 0)

dev.write(EP_OUT, build_packet(0x0004, seq=1), timeout=3000)
resp = bytes(dev.read(EP_IN, 131072, timeout=10000))
body = resp[12:]

print(f"body長: {len(body)} bytes")
print(f"先頭4バイト(フラグ): {body[:4].hex()}\n")

# エントリ0, 1, 2... を fname_len で可変長に解析
ENTRY_START = 4
offset = ENTRY_START
entries = []
while offset + 6 <= len(body):
    fname_len = body[offset + 5]
    if fname_len == 0:
        break
    entry_size = 5 + 1 + fname_len + 4 + 4 + 16  # meta + len_byte + fname + size + fmt + md5
    if offset + entry_size > len(body):
        print(f"  offset={offset}: 途中で切れた (entry_size={entry_size}, 残り={len(body)-offset})")
        break
    entry = body[offset: offset + entry_size]
    fname = entry[6: 6 + fname_len - 1].decode('ascii', errors='replace')
    fsize = struct.unpack('>I', entry[6 + fname_len:     6 + fname_len + 4])[0]
    md5   = entry[6 + fname_len + 8: 6 + fname_len + 24].hex()
    entries.append((offset, fname_len, entry_size, fname, fsize, md5))
    offset += entry_size

print(f"解析できたエントリ数: {len(entries)}\n")

# 最初の5件と最後の5件を表示
def show(idx, e):
    off, fl, es, fname, fsize, md5 = e
    print(f"  [{idx:>3}] offset={off:>5} fname_len={fl:#04x} entry_size={es} | {fname} | {fsize/1024/1024:.2f} MiB")

print("=== 最初の5件 ===")
for i, e in enumerate(entries[:5]): show(i, e)
print("\n=== 50〜55件目 ===")
for i, e in enumerate(entries[50:56], 50): show(i, e)
print("\n=== 最後の5件 ===")
for i, e in enumerate(entries[-5:], len(entries)-5): show(i, e)

# 境界付近のエントリ生バイトも表示
if len(entries) > 53:
    off = entries[53][0]
    print(f"\nエントリ53 生バイト (offset={off}):")
    print(body[off:off+64].hex())
