"""HIDOCK P1 USB通信・Jensenプロトコル実装"""
import struct
import usb.core
import usb.util

VID = 0x10D6
PID = 0xB00E
EP_OUT = 0x01
EP_IN  = 0x82

CMD_QUERY_FILE_LIST = 0x0004
CMD_TRANSFER_FILE   = 0x0005

ENTRY_SIZE  = 57
ENTRY_START = 4


def _build_packet(cmd, seq=0, body=b''):
    header = bytes([0x12, 0x34, (cmd >> 8) & 0xFF, cmd & 0xFF]) + \
             struct.pack('>I', seq) + \
             struct.pack('>I', len(body))
    return header + body


def _parse_jensen_packets(buf):
    """複数Jensenパケットが連結されたバッファを解析してペイロードを結合する。
    body_len=0 のパケットで転送完了。
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
            result.extend(buf[pos:])
            break
    return bytes(result), done


def open_device():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        raise RuntimeError("HiDock P1 が見つかりません。USB接続を確認してください。")
    try:
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
    except Exception:
        pass
    dev.set_configuration()
    usb.util.claim_interface(dev, 0)
    return dev


def query_file_list(dev):
    """デバイス上の全ファイル情報を取得する。
    戻り値: [{'name': str, 'size': int, 'format': int, 'md5': str}, ...]
    """
    dev.write(EP_OUT, _build_packet(CMD_QUERY_FILE_LIST, seq=1), timeout=3000)

    # レスポンスが複数回に分割される場合があるためループで受信
    raw = bytearray()
    while True:
        try:
            chunk = bytes(dev.read(EP_IN, 131072, timeout=10000))
        except usb.core.USBTimeoutError:
            break
        payload, done = _parse_jensen_packets(chunk)
        raw.extend(payload)
        if done:
            break

    body = bytes(raw)
    body = body[4:]  # 先頭4バイト(ffff0000)のフラグを除く
    files = []
    offset = 0
    while offset + 6 <= len(body):
        fname_len = body[offset + 5]
        if fname_len == 0:
            break
        entry_size = 5 + 1 + fname_len + 4 + 4 + 16
        if offset + entry_size > len(body):
            break
        fname = body[offset + 6: offset + 6 + fname_len - 1].decode('ascii', errors='replace')
        base  = offset + 6 + fname_len
        fsize = struct.unpack('>I', body[base:     base + 4])[0]
        fmt   = struct.unpack('>I', body[base + 4: base + 8])[0]
        md5   = body[base + 8: base + 24].hex()
        files.append({'name': fname, 'size': fsize, 'format': fmt, 'md5': md5})
        offset += entry_size
    return files


def download_file(dev, filename, expected_size, seq, on_progress=None):
    """ファイルをダウンロードしてバイト列で返す。"""
    body = filename.encode('ascii') + b'\x00'
    dev.write(EP_OUT, _build_packet(CMD_TRANSFER_FILE, seq=seq, body=body), timeout=3000)

    data = bytearray()
    while True:
        try:
            chunk = bytes(dev.read(EP_IN, 131072, timeout=10000))
        except usb.core.USBTimeoutError:
            break

        payload, done = _parse_jensen_packets(chunk)
        data.extend(payload)

        if on_progress:
            on_progress(len(data), expected_size)

        if done or (expected_size > 0 and len(data) >= expected_size):
            break

    return bytes(data)
