# MSI MEG CoreLiquid S360: 2.4" LCD controller protocol (USB `0DB0:9BA6`)

Part of the [S360 protocol reference](README.md). Tags (**CAPTURED**, **METADATA**, **HOST**, **OBSERVED**,
**INFERRED**, **UNKNOWN**) and the capture list are explained there. Capture times are 2026-10-28, local time
(UTC-7). Integers are little-endian. MSI calls this command set "HMI"; the command names below are MSI's,
read from the metadata of `API_Coreliquid.dll` (type `C_S360_DeviceControl`, nested enums `CMD`,
`CMD_LENGTH`, `STATUS_CODE`, `enum_Modes`, `enum_Screens`, `enum_HourFormat`, `enum_HWMonitorInfo`,
`enum_Weathers`). The same command set, with two length differences noted below, is declared by MSI's driver
for its touch panel `1462:4483` (METADATA, `API_Mystic Light.dll`), so this is probably a shared MSI display
module family (INFERRED).

## 1. Device and transport

**CAPTURED (capture 1, 06:40:57.129)**, from the injected descriptors:

| Item | Value |
|---|---|
| Device descriptor | `12 01 10 01 00 00 00 40 B0 0D A6 9B 00 00 01 02 00 01`: USB 1.10 declared, VID `0DB0`, PID `9BA6`, bcdDevice `0000`, **no serial number**, one configuration |
| Configuration | `09 02 29 00 01 01 00 80 32`: one interface, 100 mA |
| Interface 0 | HID (`03/00/00`), report descriptor 36 bytes (`09 21 10 01 00 01 22 24 00`) |
| Endpoint `0x81` | interrupt IN, **wMaxPacketSize 512**, interval 1 |
| Endpoint `0x02` | interrupt OUT, **wMaxPacketSize 1024**, interval 1 |
| HID collection | usage page `0xFF00` (vendor), usage `0x0001` |
| Product string | "USB HID" |
| Panel | 240 × 320 pixels (the vendor's banner background picker asks for 240 × 320 files and the monitor-page background assets are 240 × 320 and 320 × 240 PNGs; CAPTURED, capture 1c) |

Full configuration descriptor:

```
09 02 29 00 01 01 00 80 32
09 04 00 00 02 03 00 00 00   09 21 10 01 00 01 22 24 00
07 05 81 03 00 02 01   07 05 02 03 00 04 01
```

(The OUT endpoint's interval is `01`. The device declares USB 1.10, yet uses 1024-byte interrupt packets and
moved 227 KB in 0.44 s (7.2), both far beyond a full-speed interrupt endpoint. The link speed was not
recorded; INFERRED: the device actually runs at high speed.)

**Transport (CAPTURED, all five captures, 7836 command frames):**

| Direction | Mechanism | Seen |
|---|---|---|
| Host → LCD, every command | HID **SET_REPORT on the control pipe**: `bmRequestType 0x21, bRequest 0x09, wValue 0x0201` (Output report, ID 1), `wIndex 0`, `wLength 64` | every command frame |
| LCD → host, replies | HID **GET_REPORT on the control pipe**: `bmRequestType 0xA1, bRequest 0x01, wValue 0x0101` (Input report, ID 1), `wLength 64`, issued by the host right after a query | once (`GET_DEV_INFO`, capture 1) |
| Host → LCD, file contents | **interrupt OUT `0x02`, report ID 2, 1024 bytes per report** | every upload |
| LCD → host, interrupt IN `0x81` | polled by the host OS; **never carried data** in any capture | |

Nothing travels on the interrupt IN pipe, so a driver that reads replies must use GET_REPORT.

## 2. Frame format

**Output report 1, 64 bytes (CAPTURED for every command listed as captured below):**

| Offset | Size | Field | Value |
|---|---|---|---|
| 0 | 1 | report ID | `01` |
| 1 | 2 | marker | `6B 5A` |
| 3 | 1 | opcode | section 3 |
| 4 | 1 | always `00` | INFERRED: opcode high byte or reserved |
| 5 | 4 | `DATA_LEN`, u32 | the payload length (equals MSI's `CMD_LENGTH` constant for fixed-size commands); for `FILE_DATA_START` it carries the file size instead |
| 9 | `DATA_LEN` | payload | per opcode |
| | | zero padding to 64 | |

**Input report 1 (reply, CAPTURED once, capture 1, 06:42:20.647):** the GET_REPORT data is `6B 5A`, reply
opcode (= request opcode + 1), `00`, u32 length, payload, zero padded to 64. **There is no report-ID byte in
front of the reply data on the wire**, although the HID request names report 1. A reader should accept both
shapes (with and without a leading `01`).

**Patterns (METADATA, confirmed where captured):** every host opcode is even; every reply opcode is the
request's plus one. Opcode `0x24` sits in a gap between `FILE_DATA_START` (`0x22`) and `FILE_DATA_END`
(`0x26`) and is UNKNOWN (never seen; possibly a data or acknowledge code, INFERRED).

**Pacing (CAPTURED).** The vendor sends command frames back to back (eight `PLAY_MEDIA_NODE` frames within
1 ms) and leaves about 1 s between consecutive file uploads. No keep-alive exists: the only periodic frames
are the host-data frame (`0x30`, every 0.34 s) and the time frame (`0x36`, every 60 s), and MSI's class has
no heartbeat method (METADATA).

## 3. Opcode table

`Len` is MSI's `CMD_LENGTH` constant (METADATA). "Captured" means the frame appeared in a capture with the
layout described in section 4.

| Opcode | Name (METADATA) | Len | Reply | Status | Section |
|---|---|---|---|---|---|
| `0x10` | `GET_DEV_ID` | 4 | `0x11`, 4 | never sent by the vendor; OBSERVED 2026-10-31 | 4.1 |
| `0x14` | `GET_DEV_INFO` | 4 | `0x15`, 20 declared, **16 on the wire** | CAPTURED (capture 1, 06:42:20.646) | 4.2 |
| `0x16` | `SET_DEV_TIME` | 4 | none | METADATA only; never sent | 4.3 |
| `0x18` | `SET_LCM_BACKLIGHT` | 4 | none | CAPTURED (capture 1, 6 frames) | 4.4 |
| `0x1A` | `SET_LCM_DIR` | 4 | none | CAPTURED (capture 1, 6 frames) | 4.5 |
| `0x1C` | `SET_LCM_RESET` | 4 | none | METADATA only; **do not send** | 10 |
| `0x20` | `SEND_FILE_NODE` | 35 (max) | `0x21`, 4 | CAPTURED (all captures, 39 frames); the reply was never requested | 7 |
| `0x22` | `HMI_SEND_FILE_DATA_START` | none declared | none | CAPTURED (39 frames) | 7 |
| `0x24` | (none) | | | UNKNOWN; never seen | 2 |
| `0x26` | `HMI_SEND_FILE_DATA_END` | none declared | none | CAPTURED (39 frames) | 7 |
| `0x28` | `SAVE_FILE_NODE` | 32 | none | METADATA only; never sent | 7 |
| `0x2A` | `DEL_FILE_NODE` | 32 | none | METADATA only; **do not send** | 10 |
| `0x30` | `SEND_HOST_CPU_INFO` | 32 | none | CAPTURED (7503 frames) | 8.1 |
| `0x32` | `SEND_HOST_FAN_SPEED` | 4 | none | METADATA only; never sent (fan speeds travel in `0x30`) | 8.1 |
| `0x34` | `SEND_HOST_FPS` | 4 | none | METADATA only; never sent (FPS has a slot in `0x30`) | 8.1 |
| `0x36` | `SEND_HOST_TIME` | 12 | none | CAPTURED (46 frames) | 8.2 |
| `0x38` | `SEND_HOST_WEATHER` | 50 | none | CAPTURED (capture 1e, 4 identical frames); layout partial | 8.3 |
| `0x3A` | `SEND_HOST_MSG` | 55 | none | CAPTURED (11 frames, all carrying the temperature-unit string) | 8.4 |
| `0x3C` | `SEND_HOST_GPU_INFO` | 12 (touch panel: 32) | none | METADATA only; never sent (GPU values travel in `0x30`) | 8.1 |
| `0x40` | `PLAY_MEDIA_NODE` | 42 | none | CAPTURED (103 frames) | 6 |
| `0x42` | `STOP_MEDIA_NODE` | 32 | none | METADATA only; never sent | 6 |
| `0x44` | `PAUSE_MEDIA_NODE` | 32 | none | METADATA only; never sent | 6 |
| `0x50` | `SET_DISPLAY_MODE` | 19 | none | CAPTURED (39 frames, modes 0, 1, 2, 5 and 6) | 5 |
| `0x52` | `GET_DISPLAY_MODE` | 1 | `0x53`, 19 | never sent by the vendor (the touch panel lacks it); OBSERVED 2026-10-31 | 5.6 |

## 4. Device commands

### 4.1 `GET_DEV_ID` (`0x10`) → `0x11`

METADATA: `GetDeviceID(ref byte id_Low, ref byte id_High)`, request payload 4 bytes, reply payload 4 bytes.
Never sent by the vendor, so never captured.

**OBSERVED 2026-10-31** (sent by a third-party driver as `01 6B 5A 10 00 04 00 00 00  00 00 00 00`, reply read
with GET_REPORT like `GET_DEV_INFO`): reply payload **`A6 9B 00 00`**, i.e. id_Low `A6`, id_High `9B`: the
16-bit ID is the LCD's own USB product ID `0x9BA6`, low byte first. The LCD's status stayed idle and its page
unchanged.

### 4.2 `GET_DEV_INFO` (`0x14`) → `0x15`

Request payload: 4 zero bytes. Reply payload: four u32 fields, `fwVer`, `backLight`, `lcmDir`, `statusCode`
(names METADATA, order confirmed by the values). MSI declares a fifth field, `SyncMode`, and a reply length of
20; **this firmware answers 16 bytes with four fields** (CAPTURED).

```
host  06:42:20.646  01 6B 5A 14 00 04 00 00 00  00 00 00 00  00 .. 00
LCD   06:42:20.647     6B 5A 15 00 10 00 00 00  09 00 00 00  64 00 00 00  00 00 00 00  00 00 00 00  00 .. 00
```

Decoded: firmware 9, backlight 100 %, direction 0°, status 0.

`statusCode` values (METADATA, `STATUS_CODE`): `0x0000` `FW_Download_IDLE`; `0x00F0` / `0x01F0` / `0xFFF0`
download OK / in progress / failed; `0x00F1` / `0x01F1` / `0xFFF1` flash OK / in progress / failed; `0x00F2`
/ `0x01F2` / `0xFFF2` reset OK / in progress / failed. INFERRED: any non-zero value means a firmware
operation is under way and the host should stop writing.

**A stale `0x01F0` (OBSERVED 2026-10-28).** After a morning of about 30 vendor file transfers the LCD reported
`0x01F0` ("download in progress") for hours with no firmware update running; the vendor software ignored it and
kept writing, and a full power cycle (PSU off) brought it back to `0x0000`. So `0x00F0` / `0x01F0` alone can be
a left-over transfer flag. A cautious driver treats them as "no file uploads" and keeps the flash, reset and
failure codes as "no writes at all".

**After a cold power-on (OBSERVED 2026-10-28)** the first GET_REPORT for the `GET_DEV_INFO` reply timed out
three times (Windows `ERROR_SEM_TIMEOUT`) before the LCD answered normally: a late answer, not a lost device.
Wait about 2 s after enumeration and retry.

### 4.3 `SET_DEV_TIME` (`0x16`)

METADATA: `SetDeviceTime(long unixTime)`, payload 4 bytes. INFERRED: u32 Unix time. Never sent by the
vendor, which uses `SEND_HOST_TIME` instead. UNKNOWN whether this firmware acts on it.

### 4.4 `SET_LCM_BACKLIGHT` (`0x18`)

Payload: i32 **percent**, 0..100 (CAPTURED). The vendor's brightness slider has steps 0, 5, 10 which it
sends as 0, 50, 100; its init sends 100; its "LCD Display" off/on toggle sends 0 and then the previous value.
Every change is followed by the settings-file write of section 7.3.

```
06:42:20.648  01 6B 5A 18 00 04 00 00 00  64 00 00 00  00 .. 00     (100 %, init)
06:44:11.345  01 6B 5A 18 00 04 00 00 00  00 00 00 00  00 .. 00     (0 %)
06:44:32.515  01 6B 5A 18 00 04 00 00 00  32 00 00 00  00 .. 00     (50 %)
```

OBSERVED 2026-10-28 (sent by a third-party driver): on this panel only 0 (blank) and non-zero look different;
50 % and 100 % are visibly the same.

### 4.5 `SET_LCM_DIR` (`0x1A`)

Payload: i32 **degrees**, one of 0, 90, 180, 270 (CAPTURED; the vendor's "Direction" button has four
positions). Init sends 0. Followed by the settings-file write.

```
06:42:20.754  01 6B 5A 1A 00 04 00 00 00  00 00 00 00  00 .. 00     (0°, init)
06:45:21.830  01 6B 5A 1A 00 04 00 00 00  0E 01 00 00  00 .. 00     (270°)
06:46:04.832  01 6B 5A 1A 00 04 00 00 00  B4 00 00 00  00 .. 00     (180°)
06:46:09.609  01 6B 5A 1A 00 04 00 00 00  5A 00 00 00  00 .. 00     (90°)
```

Which physical rotation each value produces was not recorded; the vendor keeps separate portrait and
landscape asset sets, and the monitor-page background is uploaded in both 240 × 320 and 320 × 240 (section 7.4),
so the firmware is expected to pick the asset for the current direction (INFERRED).

OBSERVED 2026-10-28 (sent by a third-party driver): the direction turns the firmware-drawn pages (the
monitor page turned at 90° and back at 0°), but not a playing media node.

## 5. `SET_DISPLAY_MODE` (`0x50`) and the display modes

Payload, 19 bytes (METADATA parameter names `mode, slideShow, count, screen[]`; semantics CAPTURED):

| Offset | Field | Value |
|---|---|---|
| 0 | `mode` | `enum_Modes` below |
| 1 | second byte | `05` for the monitor page, `00` for every other mode. INFERRED: the page's refresh interval in seconds (MSI's monitor-page method takes a `ReflashTime` byte); MSI names the parameter `slideShow` |
| 2 | `count` | the number of selectable screens of the mode: `0F` (15 items) for the monitor page, `08` for image slots, `01` for the banner and the weather page, `05` for clock styles |
| 3..18 | `screen[16]` | one byte per selectable screen, meaning per mode below |

`enum_Modes` (METADATA): `HWmonitor 0`, `Image 1`, `Banner 2`, `FactoryColorTest 3`, `FactoryLogoTest 4`,
`Clock 5`, `Weather 6`, `Dynamic 7`. Modes 0, 1, 2, 5 and 6 were captured. Modes 3 and 4 are factory tests
(section 10). Mode 7 "Dynamic" has upload methods taking a file name in MSI's class
(METADATA) and was never seen; UNKNOWN whether it is a live-frame path.

### 5.1 Mode 0, hardware monitor

`screen[i]` for `i` = `enum_HWMonitorInfo` item: `00` = hidden, otherwise **the design id of the page**, the
same value in every shown item (CAPTURED, captures 1 and 1c).

| Index | Item (METADATA `enum_HWMonitorInfo`) | Index | Item |
|---|---|---|---|
| 0 | CPU frequency | 8 | liquid temperature |
| 1 | CPU temperature | 9 | FPS |
| 2 | GPU memory frequency | 10 | PSU temperature |
| 3 | GPU usage | 11 | PSU output wattage |
| 4 | pump ("Pump Fan") | 12 | PSU efficiency |
| 5 | radiator fan | 13 | CPU usage (needs LCD firmware ≥ 10, METADATA) |
| 6 | pump-cap fan ("Water Block Fan") | 14 | GPU temperature (needs LCD firmware ≥ 10) |
| 7 | PSU fan | 15 | end marker |

The vendor's UI allows up to five items and four designs. Design ids as sent for the four design thumbnails
in the vendor's order (CAPTURED, capture 1c): thumbnail 1 → `03`, thumbnail 2 → `01`, thumbnail 3 → `02`,
thumbnail 4 → `04`. Designs 1 to 3 need nothing else. **Design 4 is preceded by an upload of 18 PNG assets**
(section 7.4), so it is a host-supplied design while the others are built in (INFERRED).

```
06:42:21.593  01 6B 5A 50 00 13 00 00 00  00 05 0F  00 03 00 00 03 03 00 00 00 00 00 00 00 00 00 00  00 .. 00
              items 1, 4, 5 (CPU temperature, pump, radiator fan), design id 3 (thumbnail 1); the vendor's init
06:49:35.629  01 6B 5A 50 00 13 00 00 00  00 05 0F  00 03 00 00 00 00 00 00 00 00 00 00 00 00 00 00  00 .. 00
              item 1 only
06:50:00.202  01 6B 5A 50 00 13 00 00 00  00 05 0F  03 03 00 00 03 00 00 00 00 00 00 00 00 00 00 00  00 .. 00
              items 0, 1, 4
07:24:06.142  01 6B 5A 50 00 13 00 00 00  00 05 0F  02 02 00 00 02 00 00 00 00 00 00 00 00 00 00 00  00 .. 00
              items 0, 1, 4, design id 2 (thumbnail 3), capture 1c
07:24:38.640  01 6B 5A 50 00 13 00 00 00  00 05 0F  04 04 00 00 04 00 00 00 00 00 00 00 00 00 00 00  00 .. 00
              design id 4, sent right after the 18 asset uploads
```

The values are fed by `SEND_HOST_CPU_INFO` (section 8.1). The "LCD Display" toggle does not change this
frame; it only sets the backlight to 0.

### 5.2 Mode 1, image and video

`screen[slot]` = `01` for the chosen slot 0..7 (one-hot), `count` = 8 (CAPTURED, capture 1b). Slots 0..5 were
selected and played as built-in pictures; slot 7 is the user's media; slot 6 was never selected and its
content is UNKNOWN. Each `SET_DISPLAY_MODE` is followed within 1 ms by **eight
`PLAY_MEDIA_NODE` frames** naming every file the slot could hold (section 6); for slot 7 an upload comes first
(section 7).

```
07:09:29.843  01 6B 5A 50 00 13 00 00 00  01 00 08  01 00 00 00 00 00 00 00 00 .. 00     slot 0
07:09:47.348  01 6B 5A 50 00 13 00 00 00  01 00 08  00 00 00 00 00 00 00 01 00 .. 00     slot 7 (user media)
```

### 5.3 Mode 2, text banner

`screen[0]` = the background number, `count` = 1 (CAPTURED, captures 1b, 1c, 1d). Values `04`, `05`, `06`
were seen for three of the six built-in backgrounds; the full numbering is UNKNOWN. Followed by a PNG upload
of the text and one `PLAY_MEDIA_NODE` (section 6.2).

The text is rendered on the host: the uploaded 752-byte PNG (420 × 39 RGBA) is byte-identical to the image
in which MSI Center renders the banner text with the chosen font, size and colour (HOST, its file
`Coreliquid\LCD\Font\Sample.png`). The LCD only places and scrolls that picture over the background. In
these captures the vendor did not re-render the image after the first banner, so every banner upload carried
the same picture of the word "test"; the scroll fields of 6.2 changed independently of it.

```
07:11:53.480  01 6B 5A 50 00 13 00 00 00  02 00 01  04 00 .. 00     background 4
07:12:32.107  01 6B 5A 50 00 13 00 00 00  02 00 01  05 00 .. 00     background 5
07:28:05.502  01 6B 5A 50 00 13 00 00 00  02 00 01  06 00 .. 00     background 6
```

### 5.4 Mode 5, clock

`screen[style]` = `01` for the chosen style 0..4 (one-hot), `count` = 5 (CAPTURED, capture 1b). Followed at
once by `SEND_HOST_TIME` (section 8.2), which then repeats every 60 s. The vendor's clock page has no
12/24-hour switch, so that field of the time frame was always 1.

```
07:06:41.027  01 6B 5A 50 00 13 00 00 00  05 00 05  00 01 00 00 00 00 .. 00     style 1
07:06:50.783  01 6B 5A 50 00 13 00 00 00  05 00 05  01 00 00 00 00 00 .. 00     style 0
```

### 5.5 Mode 6, weather

`screen[0]` = `01`, `count` = 1 (CAPTURED, capture 1e). The vendor sends a `SEND_HOST_WEATHER` frame
(section 8.3) about 0.2 s after every weather-page `SET_DISPLAY_MODE`, and repeats the pair after each
temperature-unit change. The location comes from the host OS and cannot be changed in the vendor's UI.

```
10:04:08.408  01 6B 5A 50 00 13 00 00 00  06 00 01  01 00 .. 00
10:04:08.639  01 6B 5A 38 00 32 00 00 00  ...                       (weather data, section 8.3)
```

### 5.6 `GET_DISPLAY_MODE` (`0x52`) → `0x53`

METADATA: `GetDisplayMode(byte seekMode, ref byte outMode, ref byte slideShow, ref byte count, ref byte[]
screen)`; request payload 1 byte (the mode to query), reply payload 19 bytes. Never sent by the vendor.

**OBSERVED 2026-10-31** (sent by a third-party driver, reply read with GET_REPORT), with the monitor page
showing (items CPU temperature, pump and liquid temperature in design 3, set earlier by that driver):

| Queried mode | Reply byte 0 | Bytes 1-2 | Bytes 3-18 (`screen[16]`) |
|---|---|---|---|
| 0 monitor | `01` | `05 0F` | `03` at items 1, 4 and 8, `00` elsewhere: exactly the page that was set |
| 5 clock | `00` | `00 05` | `01 01 01 01 01`, then `00` |
| 2 banner | `00` | `00 01` | `01`, then `00` |
| 1 image | `00` | `00 08` | `01` × 6, `00` × 2, then `00` |

Bytes 1-2 are the queried mode's `slideShow` and `count` as in `SET_DISPLAY_MODE`. **Byte 0 is not the mode
number:** it is `01` only for the mode on screen (MSI's `outMode` used as an "is active" flag). The screen bytes
are **each mode's own last selection**, kept while another mode shows. OBSERVED the same evening: after a third-party
driver had shown clock style 4 and then image slot 6 and returned to the monitor page, the queries read monitor
`01 05 0F` + the page, image `00 00 08` + `01` at slot 6 only, clock `00 00 05` + `01` at style 4 only. The first
reads in the table above (`01` × 5 for the clock, × 6 for the images) were therefore the vendor software's earlier
selections of several entries at once (INFERRED: its slideshow sets; image slot 6 plays although it was not
marked). Factory test modes 3 and 4 were not queried. The LCD's status stayed idle throughout.

### 5.7 `enum_Screens` (METADATA)

`Pump_Fan 0`, `Cpu_Freq 1`, `Cpu_Temp 2`, `Fps 3`. Purpose UNKNOWN; it does not match the `screen[]` usage
above and may be a remnant of an older four-item layout (INFERRED).

## 6. `PLAY_MEDIA_NODE` (`0x40`) and node names

Payload, 42 bytes (METADATA names, layout CAPTURED):

| Offset | Size | Field | Value |
|---|---|---|---|
| 0 | 32 | `NodeName` | ASCII, zero padded |
| 32 | 4 | `x` | i32 |
| 36 | 4 | `y` | i32 |
| 40 | 1 | `scrollDir` | `0` or `1` seen |
| 41 | 1 | `scrollSpeed` | `0`, `1`, `7` seen |

### 6.1 Node names

Every on-device file is addressed by a name of the form **`M<mode>-S<slot>-<O|V>-R<resource>.<ext>`**
(CAPTURED; 77 distinct names of this form, plus the settings file of 7.3):

| Part | Meaning | Seen |
|---|---|---|
| `M<mode>` | the display mode the file belongs to | `M0` monitor page, `M1` images, `M2` banner |
| `S<slot>` | the slot, item or style within the mode | `M1-S0`..`M1-S7` image slots; `M0-S<item>` for an item's title assets, `M0-S0` for shared page assets; `M2-S0` |
| `O` or `V` | UNKNOWN. `V` is used for the video (`.mp4`) and for the two monitor-page backgrounds; `O` for still images, glyphs, titles and banner layers | |
| `R<n>` | a resource index within the family, not a rotation | `R0`/`R1` images or backgrounds, `R12`/`R13` item title variants, `R20`..`R29` digit glyphs 0..9, `R2` and `R0` the banner's one-line and multi-line text layers |
| `.<ext>` | `.bmp`, `.jpg`, `.gif`, `.png`, `.mp4` | |

### 6.2 Captured frames

**Image slot (capture 1b, 07:09:29.843).** For a built-in slot the vendor sends eight frames in one burst,
the four extensions times `R0` and `R1`, all with `x = y = 0` and no scroll. The firmware evidently plays
whichever of the eight names exists (INFERRED).

```
01 6B 5A 40 00 2A 00 00 00  "M1-S0-O-R0.bmp" 00 ..  00 00 00 00  00 00 00 00  00 00  00 .. 00
01 6B 5A 40 00 2A 00 00 00  "M1-S0-O-R0.jpg" ...                                 (then .gif, .png, and R1 × 4)
```

**User slot 7 (capture 1b, 07:09:47.349; 1d, 09:33:10.643).** Same eight names for `S7`, with
**`x = y = 350`** (`5E 01 00 00`), after the media upload of section 7.2:

```
01 6B 5A 40 00 2A 00 00 00  4D 31 2D 53 37 2D 4F 2D 52 30 2E 6A 70 67 00 .. 00  5E 01 00 00  5E 01 00 00  00 00  00 .. 00
```

**Banner (captures 1b to 1e).** One frame after the text PNG upload, `x = y = 200` (`C8 00 00 00`):

| Time | Node | `scrollDir` | `scrollSpeed` | Vendor setting |
|---|---|---|---|---|
| 07:11:54.627 | `M2-S0-O-R2.png` | 1 | 1 | One Line, speed not recorded |
| 07:28:06.646 | `M2-S0-O-R2.png` | 1 | **7** | One Line, **Fast** |
| 07:28:28.732 | `M2-S0-O-R2.png` | 1 | **1** | One Line, **Slow** |
| 09:30:48.180 | `M2-S0-O-R0.png` | **0** | 1 | **Multi-Line**, Slow |
| 10:06:41.699 | `M2-S0-O-R0.png` | 0 | **4** | Multi-Line, **Normal** (capture 1e) |

```
07:28:06.646  01 6B 5A 40 00 2A 00 00 00  4D 32 2D 53 30 2D 4F 2D 52 32 2E 70 6E 67 00 .. 00  C8 00 00 00  C8 00 00 00  01 07  00 .. 00
09:30:48.180  01 6B 5A 40 00 2A 00 00 00  4D 32 2D 53 30 2D 4F 2D 52 30 2E 70 6E 67 00 .. 00  C8 00 00 00  C8 00 00 00  00 01  00 .. 00
10:06:41.699  01 6B 5A 40 00 2A 00 00 00  4D 32 2D 53 30 2D 4F 2D 52 30 2E 70 6E 67 00 .. 00  C8 00 00 00  C8 00 00 00  00 04  00 .. 00
```

So the speed setting maps to `scrollSpeed` **Fast 7, Normal 4, Slow 1**, and the line layout picks both the
node and `scrollDir`: One Line uses node `R2` with `scrollDir` 1, Multi-Line uses node `R0` with `scrollDir`
0. The two are independent: the vendor sends the chosen speed even for the multi-line layout. Whether a
multi-line banner moves at all with `scrollDir` 0, the axis of `scrollDir` and the unit of `x`, `y` are
UNKNOWN.

### 6.3 `STOP_MEDIA_NODE` (`0x42`), `PAUSE_MEDIA_NODE` (`0x44`)

METADATA: `StopMediaNode(string NodeName)`, `PauseMediaNode(string NodeName)`, payload 32 bytes. INFERRED:
the node name alone, zero padded. Never sent by the vendor: a mode change simply issues a new
`SET_DISPLAY_MODE`.

## 7. File transfer

### 7.1 Upload sequence (CAPTURED, 39 uploads across the five captures)

1. **`SEND_FILE_NODE` (`0x20`)**, `DATA_LEN` = 4 + name length: payload = u32 file size, then the node
   name in ASCII **without a terminator**. MSI's constant 35 is the maximum (4 + 31 characters).
2. **`HMI_SEND_FILE_DATA_START` (`0x22`)**, with **the file size in the `DATA_LEN` field** and no payload.
3. **⌈size / 1023⌉ interrupt OUT reports of 1024 bytes**: byte 0 = report ID `02`, then 1023 file bytes; the
   last report is zero padded. (A 3-byte file is one report; 227,243 bytes took 223 reports in 0.42 s.)
4. **`HMI_SEND_FILE_DATA_END` (`0x26`)**, `DATA_LEN` 0, no payload.

No reply is read at any step, `0x24` never appears, and `SAVE_FILE_NODE` (`0x28`) is never sent. INFERRED:
uploaded files are volatile, which is why the vendor re-uploads the user's media every time it is selected
(three uploads of the same node name in capture 1b) and re-uploads the banner image before every
`PLAY_MEDIA_NODE`. Whether `SAVE_FILE_NODE` would make them persistent is UNKNOWN.

### 7.2 User media (capture 1b, 1d)

The vendor transcodes the chosen GIF or video on the host to an H.264 MP4 and uploads it as
**`M1-S7-V-R0.mp4`**:

| Time | Size | Reports | Duration |
|---|---|---|---|
| 07:09:47.722 | 96,276 | 95 | 0.63 s to `FILE_DATA_END` |
| 07:09:51.849 | 227,243 | 223 | 0.44 s |
| 07:11:18.157 | 41,047 | 41 | 0.56 s |
| 09:33:11.015 | 101,494 | 100 | 1.19 s |

```
07:09:47.722  01 6B 5A 20 00 12 00 00 00  14 78 01 00  4D 31 2D 53 37 2D 56 2D 52 30 2E 6D 70 34  00 .. 00
              DATA_LEN 18 = 4 + 14; size 0x17814 = 96276; "M1-S7-V-R0.mp4"
07:09:47.739  01 6B 5A 22 00 14 78 01 00  00 .. 00
              DATA_LEN = 96276, no payload
07:09:47.740  02 00 00 00 20 66 74 79 70 69 73 6F 6D ...          first report: "....ftypisom" (MP4 header)
              ... 93 more full reports, then the padded last one
07:09:48.355  01 6B 5A 26 00 00 00 00 00  00 .. 00
```

A video file chosen in the vendor's Video/Image page takes exactly the same path as a GIF (capture 1d).

### 7.3 Settings file (capture 1, after every backlight or direction change)

The vendor persists the LCD's settings by writing a 3-byte file named **`HMI_FW_Setting.ini`** whose content
is the ASCII bytes `MSI` (CAPTURED, 10 times, always identical):

```
06:44:11.345  01 6B 5A 20 00 16 00 00 00  03 00 00 00  48 4D 49 5F 46 57 5F 53 65 74 74 69 6E 67 2E 69 6E 69  00 .. 00
              DATA_LEN 22 = 4 + 18; size 3; "HMI_FW_Setting.ini"
06:44:11.348  01 6B 5A 22 00 03 00 00 00  00 .. 00
06:44:11.348  02 4D 53 49 00 .. 00                              (1024 bytes: "MSI" then zeros)
06:44:11.350  01 6B 5A 26 00 00 00 00 00  00 .. 00
```

INFERRED: the write is a "save settings" trigger (MSI's class has a `SaveSetting()` method and no opcode for
it); the firmware stores its current backlight and direction when this file arrives, and the content is a
signature rather than data. A second name, `HMI_FW_Mode.ini`, exists in MSI's strings (`SaveMode()`), was
never written in the captures, and its content is UNKNOWN. Settings are therefore volatile until this file
is written; a driver that only changes the backlight temporarily need not write it. Writing it is a flash
write (INFERRED); do it sparingly.

### 7.4 Monitor-page assets for design 4 (capture 1c, 07:24:19 to 07:24:37)

Before `SET_DISPLAY_MODE` with design id 4, the vendor first switched the display to image slot 2 (a holding
picture, INFERRED) and then uploaded 18 PNGs, one per second, each with the sequence of 7.1:

| Node | Size | PNG dimensions (from `IHDR`) | Meaning |
|---|---|---|---|
| `M0-S0-V-R0.png` | 7,425 | 240 × 320 | page background, portrait |
| `M0-S0-V-R1.png` | 6,900 | 320 × 240 | page background, landscape |
| `M0-S0-O-R20.png` .. `R29.png` | 528 to 640 each | 42 × 70 | digit glyphs 0..9 |
| `M0-S0-O-R12.png`, `M0-S1-O-R12.png`, `M0-S4-O-R12.png` | 1,267 / 1,334 / 948 | 240 × 67 | title of items 0, 1, 4 (the three items shown) |
| `M0-S0-O-R13.png`, `M0-S1-O-R13.png`, `M0-S4-O-R13.png` | 556 / 399 / 577 | 240 × 32 | unit label of items 0, 1, 4 |

The meanings are confirmed by the vendor's installed asset folder for the monitor page, which has the
sub-folders `background`, `number`, `title` and `unit` holding files of exactly these four sizes (HOST). So
the `R<n>` suffix is a resource index within a node family: `R0`/`R1` backgrounds, `R12` titles, `R13` units,
`R20`..`R29` digits.

Then `SET_DISPLAY_MODE` design 4 at 07:24:38.640 and, 1 ms later, design 3 again (the vendor re-applied the
owner's previous choice). So the monitor page is composed on the device from uploaded glyphs, titles and
units plus the live values of section 8.1, and the three built-in designs carry their own assets in firmware
(INFERRED).

### 7.5 `SAVE_FILE_NODE` (`0x28`), `DEL_FILE_NODE` (`0x2A`)

METADATA: `SaveFileNode(string NodeName)`, `DeleteFileNode(string NodeName)`, payload 32 bytes. INFERRED:
the node name alone, zero padded. Neither was ever sent. `DEL_FILE_NODE` could remove built-in assets or the
settings file: see section 10.

## 8. Host data frames

### 8.1 `SEND_HOST_CPU_INFO` (`0x30`): all live values

Despite its name this is the only live-data frame the vendor sends; `SEND_HOST_FAN_SPEED`, `SEND_HOST_FPS`
and `SEND_HOST_GPU_INFO` never appeared. Payload: **16 × u16, indexed by `enum_HWMonitorInfo`** (section 5.1);
sent every 0.34 s regardless of the current display mode (CAPTURED, 4575 frames). Ranges below are over all
five captures.

| Index | Value | Unit | Seen |
|---|---|---|---|
| 0 | CPU frequency | MHz | 0 throughout (the vendor's telemetry engine was down) |
| 1 | CPU temperature | °C | 0 throughout, same reason |
| 2 | GPU memory frequency | MHz | 405 to 10502 |
| 3 | GPU usage | % | 0 to 97 |
| 4 | pump RPM | RPM | 1724 to 2631; equals slot 4 of the controller's status reply in the same second |
| 5 | radiator fan RPM | RPM | 0 (no radiator fans on the captured controller) |
| 6 | pump-cap fan RPM | RPM | 1052 to 2479; equals slot 3 of the controller's status reply |
| 7 | PSU fan | RPM | 0 (no MSI PSU) |
| 8 | liquid temperature | °C | 30 to 35, whole degrees |
| 9 | FPS | | 0 |
| 10..12 | PSU temperature, wattage, efficiency | | 0 |
| 13 | CPU usage | % | 0 |
| 14 | GPU temperature | °C | 34 to 46 |
| 15 | unused | | 0 |

```
06:40:57.337  01 6B 5A 30 00 20 00 00 00  00 00  00 00  8A 13  10 00  D0 06  00 00  27 04  00 00  22 00  00 00  00 00 00 00 00 00  00 00  29 00  00 00  00 .. 00
              [2] 5002 MHz, [3] 16 %, [4] 1744, [6] 1063, [8] 34 °C, [14] 41 °C
```

The temperature values are sent in °C whether the unit string (8.4) says °C or °F: during capture 1 the unit
was switched to °F at 06:48:48 and back at 06:49:09, and every frame between 06:48:30 and 06:49:20 carried
`[8]` = 31 and `[14]` = 36 (CAPTURED), so the LCD converts for display (INFERRED).

### 8.2 `SEND_HOST_TIME` (`0x36`)

Payload, 12 bytes (METADATA names `hourFormat, jetLag, unixTime`; encoding CAPTURED): i32 `hourFormat`,
f32 `jetLag`, u32 seconds.

- `hourFormat`: `1` in all 46 time frames of the five captures. METADATA `enum_HourFormat`: `Hour_12 0`,
  `Hour_24 1`. The vendor's clock page offers no 12/24-hour switch, so the 12-hour encoding is unverified.
- `jetLag`: always `0.0`.
- seconds: **the local wall-clock time counted as if it were UTC**. At 06:43:20 local (UTC-7) the frame
  carried `0x6AE19988` = 1,793,169,800 = 2026-10-28 06:43:20 **UTC**. The device therefore displays the
  seconds as a UTC clock, and the host does the time-zone shift itself (INFERRED from the one time zone
  observed).
- Sent every 60 s while the vendor runs, whatever the display mode (the phase differs per session: :20 in
  capture 1, :53 in 1b, :44 in 1c, :45 in 1d), plus once immediately after each switch to clock mode or clock
  style (capture 1b, 07:06:41 to 07:06:50).

```
06:43:20.651  01 6B 5A 36 00 0C 00 00 00  01 00 00 00  00 00 00 00  88 99 E1 6A  00 .. 00
```

### 8.3 `SEND_HOST_WEATHER` (`0x38`)

METADATA: `SendHostWeather(float temperature, short humidity, float probabilityPrecipitation, short
weather)`, payload 50 bytes; `enum_Weathers`: `Sunny 0`, `Cloud 1`, `Rain 2`, `Snow 3`.

CAPTURED (capture 1e, 10:04:02.106, 10:04:08.639, 10:05:55.025, 10:06:16.944; four identical frames, one
location, one forecast):

```
10:04:02.106  01 6B 5A 38 00 32 00 00 00
              00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00   offsets 0..27
              00 00 A4 41                                                                         28..31  f32 20.5
              00 00 00 00 00 00 00 00 00 00                                                       32..41
              1E 00                                                                               42..43  u16 30
              00 00 00 00                                                                         44..47
              01 00                                                                               48..49  u16 1
              00 .. 00                                                                            padding to 64
```

| Offset | Size | Field | Value seen | Status |
|---|---|---|---|---|
| 0 | 28 | reserved | all zero | CAPTURED; INFERRED reserved (no city name is sent) |
| 28 | 4 | temperature, f32, **°C** | 20.5 | CAPTURED. Unchanged when the unit was flipped to °F and back: only the unit string of 8.4 changed |
| 32 | 10 | | zero | CAPTURED |
| 42 | 2 | humidity %, u16 | 30 | CAPTURED |
| 44 | 4 | | zero | CAPTURED |
| 48 | 2 | weather, u16, `enum_Weathers` | 1 = Cloud | CAPTURED |

The precipitation-probability float was 0.0, so its position is INFERRED: it sits in one of the zero runs,
32..35 or 44..47. With one sample, every field other than the three non-zero ones is unverified. The weather
icons for values other than Cloud, and any value above 3, are UNKNOWN.

### 8.4 `SEND_HOST_MSG` (`0x3A`) and the temperature-unit string

Payload: 55 bytes, ASCII, zero padded. The only content ever seen is the temperature-unit command string
(CAPTURED, 8 frames): **`55AASETTEMP05AA5`** for °C and **`55AASETTEMP15AA5`** for °F, sent at init, again
about 40 s later, on every unit change in the vendor's general settings (each followed, on the weather page,
by a fresh weather-page `SET_DISPLAY_MODE` and `SEND_HOST_WEATHER`), and occasionally around mode switches
without a change.

```
06:42:21.173  01 6B 5A 3A 00 37 00 00 00  35 35 41 41 53 45 54 54 45 4D 50 30 35 41 41 35  00 .. 00    °C
06:48:47.994  01 6B 5A 3A 00 37 00 00 00  35 35 41 41 53 45 54 54 45 4D 50 31 35 41 41 35  00 .. 00    °F
```

INFERRED: the string is a framed text command (`55AA` ... `5AA5`) interpreted by the display firmware. MSI's
strings also contain `55AASETSYNCMODE##5AA5` with a two-digit decimal in place of `##` (METADATA, method
`SetSyncMode(int)`); it was never sent and its effect is UNKNOWN. Whether arbitrary text in this frame is
displayed anywhere is UNKNOWN.

OBSERVED 2026-10-28: on LCD firmware 9 the unit string has no visible effect on the monitor page, whether sent
by the vendor software or by a third-party driver; the host-data values are shown as sent.

## 9. Sequences

### 9.1 Vendor init (CAPTURED, capture 1, about 80 s after the vendor service restarted)

| Time | Frame |
|---|---|
| 06:42:20.646 | `GET_DEV_INFO` |
| 06:42:20.646 | GET_REPORT → reply (firmware 9, backlight 100, direction 0, status 0) |
| 06:42:20.648 | `SET_LCM_BACKLIGHT` 100 |
| 06:42:20.754 | `SET_LCM_DIR` 0 |
| 06:42:21.173 | `SEND_HOST_MSG` `55AASETTEMP05AA5` |
| 06:42:21.593 | `SET_DISPLAY_MODE` mode 0, items 1, 4, 5, design 3 |
| 06:42:59.852 | `SEND_HOST_MSG`, the same string again |
| 06:43:20.651 | first `SEND_HOST_TIME`, then every 60 s |

`SEND_HOST_CPU_INFO` frames were flowing every 0.34 s from 06:40:57, before and through the init. **No file is
transferred at init**: the user's media is not re-uploaded until it is selected again. How long the LCD
needs after a USB arrival before it accepts commands is UNKNOWN (the captures start with the device already
enumerated); a settle delay of a few seconds is a cautious default (INFERRED).

### 9.2 Changing a setting (CAPTURED)

`SET_LCM_BACKLIGHT` or `SET_LCM_DIR`, then the settings-file write (7.3), all within 5 ms.

### 9.3 Switching modes (CAPTURED)

- Monitor page: one `SET_DISPLAY_MODE` (plus the 18 asset uploads first for design 4).
- Image slot: `SET_DISPLAY_MODE` + eight `PLAY_MEDIA_NODE`. For slot 7 the MP4 upload **follows** the eight
  `PLAY_MEDIA_NODE` frames by about 0.4 s (07:09:47.348 mode, .349 play × 8, .722 upload; the same order at
  07:09:51, 07:11:17 and 09:33:10), so the firmware evidently starts playing a node once its upload completes
  (INFERRED).
- Banner: `SET_DISPLAY_MODE` (background), PNG upload of the text, one `PLAY_MEDIA_NODE` about 1 s later.
- Clock: `SET_DISPLAY_MODE` + `SEND_HOST_TIME`.

OBSERVED 2026-10-31: the clock (all five styles, time correct within a second) and image (built-in slots 0-6,
all showing a picture, slot 6 included) sequences above, sent by a third-party driver exactly as captured, work
without the vendor software; a monitor-page `SET_DISPLAY_MODE` returns to the page. The LCD's status stayed idle.
- Weather: `SET_DISPLAY_MODE` + `SEND_HOST_WEATHER` about 0.2 s later.

## 10. Commands that must not be sent

| Opcode / value | Name | Why |
|---|---|---|
| `0x1C` | `SET_LCM_RESET` (MSI method `ResetMCU()`) | resets the display controller; payload UNKNOWN; never captured |
| `0x2A` | `DEL_FILE_NODE` | deletes an on-device file by name; could remove built-in assets or the settings file; never captured |
| `0x50` with `mode` = 3 or 4 | `FactoryColorTest`, `FactoryLogoTest` | factory test screens; effect and exit path UNKNOWN |
| firmware update | any flow that drives `statusCode` through the `FW_Download_*` / `FW_Flash_*` / `FW_Reset_*` values | the vendor's updater can re-flash this controller; the opcodes it uses were deliberately not captured. A non-zero `statusCode` in `GET_DEV_INFO` means an update is in progress: stop writing |

## 11. Known values at a glance

| Item | Value | Status |
|---|---|---|
| Marker | `6B 5A` after the report ID | CAPTURED |
| Backlight | 0..100, percent, i32 | CAPTURED |
| Direction | 0, 90, 180, 270, degrees, i32 | CAPTURED |
| Panel | 240 × 320 | CAPTURED (asset sizes), INFERRED (orientation handling) |
| Monitor page refresh byte | 5 | CAPTURED; meaning INFERRED |
| Design ids | 1, 2, 3 built in; 4 host-supplied | CAPTURED |
| Image slots | 0..5 built in (6 never selected), 7 user; user media played at `x = y = 350` | CAPTURED |
| Banner | played at `x = y = 200`; One Line = node `R2`, `scrollDir` 1; Multi-Line = node `R0`, `scrollDir` 0; speed Fast 7, Normal 4, Slow 1; host-rendered text, 420 × 39 PNG | CAPTURED |
| Clock styles | 0..4 | CAPTURED |
| Hour format | 1 = 24 h, in all 46 frames; 0 = 12 h never seen | CAPTURED, METADATA |
| Weather | mode 6, `screen[0]` = 1; `SEND_HOST_WEATHER` f32 °C at 28, u16 humidity at 42, u16 weather at 48 | CAPTURED (partial) |
| Time | local clock sent as UTC seconds, `jetLag` 0.0 | CAPTURED |
| Unit strings | `55AASETTEMP05AA5` °C, `55AASETTEMP15AA5` °F in `SEND_HOST_MSG` | CAPTURED |
| Live data | `SEND_HOST_CPU_INFO`, 16 × u16, every 0.34 s | CAPTURED |
| File packets | report 2, 1024 bytes, 1023 payload | CAPTURED |
| Settings file | `HMI_FW_Setting.ini`, content `MSI` | CAPTURED |
| Firmware seen | 9 (items 13 and 14 need ≥ 10) | CAPTURED, METADATA |

## 12. Open items

| # | Question | How to settle |
|---|---|---|
| 1 | `SEND_HOST_WEATHER`: position of the precipitation float, the zero prefix, other weather values | capture the weather page on days with rain or snow, or in another location |
| 2 | ~~`GET_DEV_ID` reply, `GET_DISPLAY_MODE` reply~~ **Answered 2026-10-31** (sections 4.1 and 5.6) | done |
| 3 | `SET_DEV_TIME` effect; `hourFormat` 0 | send the frame; change the Windows or vendor clock format and capture |
| 4 | `STOP_MEDIA_NODE` / `PAUSE_MEDIA_NODE` payloads and effect | send with a known node name |
| 5 | Mode 7 "Dynamic" | never seen; find a vendor path that uses it, or try `SET_DISPLAY_MODE` 7 with a known node |
| 6 | `scrollDir` axis and its effect on a multi-line banner; `x`, `y` units | vary them on the device |
| 7 | `SAVE_FILE_NODE`, `HMI_FW_Mode.ini`, persistence of uploads | upload, save, power-cycle, play by name |
| 8 | `O` versus `V` in node names; the full banner background numbering | more vendor captures |
| 9 | Opcode `0x24`; the `0x21` reply | issue GET_REPORT after `SEND_FILE_NODE` |
| 10 | Which physical rotation each direction value gives | observe the panel |

## 13. Host-side context (HOST)

Not part of the wire protocol. These items help relate the vendor's settings to the frames above. They were
read from the vendor's installed files and registry key names on the capturing PC; nothing was modified.

**Assets.** The vendor's Coreliquid installation keeps the LCD assets in an `LCD` folder:
`HWMonitor\{background,number,title,unit}` for the monitor page (sizes as in 7.4), `ImageV` for user media
with the transcoded MP4s in `ImageV\Video` (file sizes equal to the uploads of 7.2), `Font` with the rendered
banner image `Sample.png` (5.3), and `Weather`.

**Settings.** The vendor keeps the LCD's UI state in its own registry key
`HKLM\SOFTWARE\WOW6432Node\MSI\MSI Center\Component\Coreliquid\LCD`. Value names and how they map to the
wire, without the observed values:

| Value name | Relation to the wire |
|---|---|
| `Brightness` | 0..10 in the UI; sent × 10 as the percent of `SET_LCM_BACKLIGHT` |
| `Direction` | the four positions of `SET_LCM_DIR` |
| `HM_list_S` | 15 flags, one per `enum_HWMonitorInfo` item; the shown items of the mode-0 `screen[]` |
| `CurrentHWDesignIndex` | the design thumbnail; thumbnail 1 is wire design id 3 (5.1) |
| `ClockType` | the clock style of mode 5 |
| `CurrentGifIndex` | the selected image slot of mode 1 |
| `CurrentBannerIndex` | the banner background of mode 2 |
| banner font, size, colour, lines and speed values | host-side rendering of `Sample.png`; lines and speed map to the node and scroll fields of 6.2 |
| `TemperatureUnit` | the unit string of 8.4 |
| `LCD_Switch` | the "LCD Display" toggle, sent as backlight 0 |
| `MSIControl`, `IsRunning` | not reflected on the wire; INFERRED to be a hand-off flag that lets third-party software take over the LCD from MSI Center |
