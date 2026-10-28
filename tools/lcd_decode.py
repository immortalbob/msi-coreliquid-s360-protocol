"""Decode the MSI CoreLiquid S360 LCD (0DB0:9BA6) traffic in a USBPcap capture.

usage: python lcd_decode.py <capture.pcap> [notes.txt] [--device N]

The capture must come from USBPcap (link type 249), ideally filtered to the LCD's device address with
USBPcapCMD --devices. The LCD's address is found from the device descriptors in the capture (capture with
--inject-descriptors) or given with --device. The optional notes file holds lines starting with HH:MM:SS that
are printed in the timeline next to the frames.

Prints: the HID requests seen (setup packets), frames grouped by opcode with examples, the timeline of
non-periodic frames and replies, and the interrupt-IN replies. See msi-coreliquid-s360-lcd.md for the meaning.
"""
import os
import struct
import sys
from collections import Counter, defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import usbpcap_parse as u  # noqa: E402

LCD_VID_PID = (0x0DB0, 0x9BA6)
PERIODIC = {0x30, 0x32, 0x34, 0x36, 0x3C}
NAMES = {0x10: 'GET_DEV_ID', 0x11: 'DEV_ID_REPLY', 0x14: 'GET_DEV_INFO', 0x15: 'DEV_INFO_REPLY', 0x16: 'SET_DEV_TIME',
         0x18: 'SET_LCM_BACKLIGHT', 0x1A: 'SET_LCM_DIR', 0x1C: 'SET_LCM_RESET', 0x20: 'SEND_FILE_NODE', 0x21: 'FILE_NODE_REPLY',
         0x22: 'FILE_DATA_START', 0x24: '(0x24 unseen)', 0x26: 'FILE_DATA_END', 0x28: 'SAVE_FILE_NODE', 0x2A: 'DEL_FILE_NODE',
         0x30: 'SEND_HOST_CPU_INFO', 0x32: 'SEND_HOST_FAN_SPEED', 0x34: 'SEND_HOST_FPS', 0x36: 'SEND_HOST_TIME',
         0x38: 'SEND_HOST_WEATHER', 0x3A: 'SEND_HOST_MSG', 0x3C: 'SEND_HOST_GPU_INFO', 0x40: 'PLAY_MEDIA_NODE',
         0x42: 'STOP_MEDIA_NODE', 0x44: 'PAUSE_MEDIA_NODE', 0x50: 'SET_DISPLAY_MODE', 0x52: 'GET_DISPLAY_MODE', 0x53: 'DISPLAY_MODE_REPLY'}


def t(ts):
    return datetime.fromtimestamp(ts).strftime('%H:%M:%S.%f')[:-3]


def hx(b, n=None):
    b = b if n is None else b[:n]
    return ' '.join('%02X' % x for x in b)


def find_lcd(path):
    for dev, (vid, pid) in u.addresses(path).items():
        if (vid, pid) == LCD_VID_PID:
            return dev
    return None


def main():
    args = [a for a in sys.argv[1:]]
    device = None
    if '--device' in args:
        i = args.index('--device')
        device = int(args[i + 1])
        del args[i:i + 2]
    if not args:
        raise SystemExit(__doc__)
    path = args[0]
    notes = []
    if len(args) > 1:
        for line in open(args[1], encoding='utf-8', errors='replace'):
            line = line.strip()
            if len(line) > 9 and line[2] == ':' and line[5] == ':':
                notes.append((line[:8], line[9:]))
    if device is None:
        device = find_lcd(path)
        if device is None:
            raise SystemExit('no 0DB0:9BA6 device descriptor in the capture; pass --device N (capture with --inject-descriptors)')
    print('LCD device address', device)

    setups = Counter()
    frames = []        # host -> LCD output reports (data after the setup packet)
    replies = []       # interrupt IN with data
    other = []
    for p in u.packets(path):
        if p['dev'] != device or p['dlen'] == 0:
            continue
        d = p['data']
        if p['ttype'] == 2 and p['stage'] == 0 and len(d) >= 8:
            bm, breq, wval, widx, wlen = struct.unpack('<BBHHH', d[:8])
            setups[(bm, breq, wval, widx, wlen)] += 1
            if bm == 0x21 and breq == 0x09:          # SET_REPORT
                frames.append((p['ts'], d[8:], wlen))
            elif bm == 0xA1 and breq == 0x01:        # GET_REPORT: the data stage carries the reply
                other.append((p['ts'], 'GET_REPORT', d[8:]))
            else:
                other.append((p['ts'], 'ctrl %02X %02X' % (bm, breq), d[8:]))
        elif p['ttype'] == 1 and p['ep'] & 0x80:
            replies.append((p['ts'], d))
        elif p['ttype'] == 1:
            other.append((p['ts'], 'intr OUT ep %02X' % p['ep'], d))
        else:
            other.append((p['ts'], 'type %s ep %02X' % (p['ttype'], p['ep']), d))

    print('=== HID control requests (bmRequestType bRequest wValue wIndex wLength) : count')
    for k, v in setups.most_common():
        print('  %02X %02X %04X %04X %04X : %d' % (k[0], k[1], k[2], k[3], k[4], v))

    print('\n=== output report frame shapes: report id, bytes 1-2, opcode byte 3, byte 4, u32 at 5..8 (length)')
    shapes = Counter()
    for ts, d, wlen in frames:
        if len(d) < 9:
            shapes[('short', len(d))] += 1
            continue
        shapes[(d[0], hx(d[1:3]), d[3], d[4], struct.unpack('<I', d[5:9])[0], wlen, len(d))] += 1
    for k, v in sorted(shapes.items(), key=lambda kv: -kv[1]):
        if k[0] == 'short':
            print('  short frame len', k[1], ':', v)
        else:
            print('  rid %02X  hdr %s  op 0x%02X (%s)  b4 %02X  len32 %d  wLength %d  bytes %d : %d' % (
                k[0], k[1], k[2], NAMES.get(k[2], '?'), k[3], k[4], k[5], k[6], v))

    print('\n=== examples per opcode (first 3)')
    byop = defaultdict(list)
    for ts, d, wlen in frames:
        if len(d) >= 9:
            byop[d[3]].append((ts, d))
    for op in sorted(byop):
        ex = byop[op]
        print('  op 0x%02X %-20s n=%d first %s last %s' % (op, NAMES.get(op, '?'), len(ex), t(ex[0][0]), t(ex[-1][0])))
        for ts, d in ex[:3]:
            print('     %s | %s' % (t(ts), hx(d, 64)))

    print('\n=== timeline of non-periodic frames and replies, with the notes')
    events = []
    for ts, d, wlen in frames:
        if len(d) >= 9 and d[3] not in PERIODIC:
            events.append((ts, 'OUT op 0x%02X %-18s len32=%d | %s' % (d[3], NAMES.get(d[3], '?'), struct.unpack('<I', d[5:9])[0], hx(d, 48))))
    for ts, d in replies:
        if any(d):
            events.append((ts, 'IN  reply %s' % hx(d, 40)))
    for ts, kind, d in other:
        events.append((ts, '%s | %s' % (kind, hx(d, 40))))
    events.sort()
    ni = 0
    for ts, text in events:
        tt = t(ts)
        while ni < len(notes) and notes[ni][0] <= tt[:8]:
            print('  ---- NOTE %s %s' % notes[ni])
            ni += 1
        print('  %s %s' % (tt, text))
    while ni < len(notes):
        print('  ---- NOTE %s %s' % notes[ni])
        ni += 1

    print('\n=== interrupt IN replies with data: distinct first 8 bytes : count')
    rc = Counter(hx(d[:8]) for ts, d in replies if any(d))
    for k, v in rc.most_common(15):
        print('  %s : %d' % (k, v))
    print('replies total', len(replies), 'frames total', len(frames))


if __name__ == '__main__':
    main()
