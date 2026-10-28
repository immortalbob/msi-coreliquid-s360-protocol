"""Minimal USBPcap (.pcap, link type 249) reader.

usage: python -I usbpcap_parse.py <file.pcap> addresses        -> device address -> VID:PID (from device descriptors)
       python -I usbpcap_parse.py <file.pcap> dump [addr]       -> every transfer (optionally one device), with payload hex
       python -I usbpcap_parse.py <file.pcap> summary [addr]    -> counts per device/endpoint/transfer type
"""
import struct, sys
from datetime import datetime, timezone

TRANSFER = {0: 'iso', 1: 'intr', 2: 'ctrl', 3: 'bulk'}


def packets(path):
    with open(path, 'rb') as f:
        gh = f.read(24)
        if len(gh) < 24:
            return
        magic = struct.unpack('<I', gh[:4])[0]
        if magic == 0xa1b2c3d4:
            endian = '<'
        elif magic == 0xd4c3b2a1:
            endian = '>'
        else:
            raise SystemExit('not a pcap file (magic %08x); pcapng is not supported here' % magic)
        linktype = struct.unpack(endian + 'I', gh[20:24])[0]
        if linktype != 249:
            raise SystemExit('link type %d is not USBPcap (249)' % linktype)
        while True:
            ph = f.read(16)
            if len(ph) < 16:
                return
            ts_sec, ts_usec, incl, orig = struct.unpack(endian + 'IIII', ph)
            rec = f.read(incl)
            if len(rec) < incl:
                return
            if len(rec) < 27:
                continue
            hlen, irp, status, func, info, bus, dev, ep, ttype, dlen = struct.unpack('<HQIHBHHBBI', rec[:27])
            data = rec[hlen:hlen + dlen]
            stage = rec[27] if (ttype == 2 and hlen >= 28) else None
            yield {
                'ts': ts_sec + ts_usec / 1e6, 'irp': irp, 'status': status, 'func': func,
                'out': (info & 1) == 0,  # info bit 0: 1 = PDO -> FDO (from device, i.e. IN completion)
                'bus': bus, 'dev': dev, 'ep': ep, 'ttype': ttype, 'stage': stage, 'data': data, 'dlen': dlen,
            }


def addresses(path):
    found = {}
    for p in packets(path):
        d = p['data']
        if p['ttype'] == 2 and len(d) >= 18 and d[0] == 0x12 and d[1] == 0x01:
            vid, pid = struct.unpack('<HH', d[8:12])
            found[p['dev']] = (vid, pid)
    return found


def fmt_ts(ts):
    return datetime.fromtimestamp(ts).strftime('%H:%M:%S.%f')[:-3]


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    path, cmd = sys.argv[1], sys.argv[2]
    only = int(sys.argv[3]) if len(sys.argv) > 3 else None
    if cmd == 'addresses':
        for dev, (vid, pid) in sorted(addresses(path).items()):
            print('device %3d  %04X:%04X' % (dev, vid, pid))
        return
    if cmd == 'summary':
        counts = {}
        n = 0
        for p in packets(path):
            n += 1
            if only is not None and p['dev'] != only:
                continue
            key = (p['dev'], p['ep'], TRANSFER.get(p['ttype'], str(p['ttype'])), 'OUT' if p['out'] else 'IN')
            counts[key] = counts.get(key, 0) + 1
        print(n, 'packets total')
        for k, v in sorted(counts.items()):
            print('device %3d ep 0x%02X %-4s %-3s : %d' % (k[0], k[1], k[2], k[3], v))
        return
    if cmd == 'dump':
        maxbytes = int(sys.argv[4]) if len(sys.argv) > 4 else 80
        for p in packets(path):
            if only is not None and p['dev'] != only:
                continue
            if p['dlen'] == 0:
                continue
            d = p['data']
            hexs = ' '.join('%02X' % b for b in d[:maxbytes]) + (' ...' if len(d) > maxbytes else '')
            print('%s dev %d ep 0x%02X %-4s %-3s len %4d%s | %s' % (
                fmt_ts(p['ts']), p['dev'], p['ep'], TRANSFER.get(p['ttype'], p['ttype']), 'OUT' if p['out'] else 'IN',
                p['dlen'], (' stage %d' % p['stage']) if p['stage'] is not None else '', hexs))
        return
    raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
