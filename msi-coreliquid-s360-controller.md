# MSI MEG CoreLiquid S360: cooler controller protocol (USB `0DB0:6A05`)

Part of the [S360 protocol reference](README.md). Tags (**CAPTURED**, **METADATA**, **OBSERVED**,
**INFERRED**, **UNKNOWN**) and the capture list are explained there. Capture times are 2026-10-28, local time
(UTC-7). `R[n]` is byte *n* of a 64-byte HID report buffer, **including the report ID at `R[0]`**. Integers
are little-endian unless stated otherwise.

## 1. Device

**CAPTURED (capture 1, 06:40:57.129)**, from the injected descriptors:

| Item | Value |
|---|---|
| Device descriptor | `12 01 00 02 00 00 00 40 B0 0D 05 6A 00 01 01 02 03 01`: USB 2.00, VID `0DB0`, PID `6A05`, bcdDevice `0100`, 64-byte EP0, a serial-number string (index 3), one configuration |
| Configuration | `09 02 40 00 02 01 00 80 FA`: two interfaces, bus powered, 500 mA |
| Interface 0 | vendor class `FF/FF/00`, bulk IN `0x83` and bulk OUT `0x04`, 64 bytes. Windows binds WinUSB to it through Microsoft OS descriptors. **Purpose UNKNOWN**; the vendor software never touched it in any capture. Leave it alone |
| Interface 1 | HID (`03/00/00`), report descriptor 154 bytes, interrupt IN `0x81` and interrupt OUT `0x02`, 64 bytes, 5 ms interval. One top-level collection, usage page `0x0001`, usage `0x0000` |
| Product string | "MEG Core Liquid S360" |

Full configuration descriptor as captured:

```
09 02 40 00 02 01 00 80 FA
09 04 00 00 02 FF FF 00 00   07 05 83 02 40 00 00   07 05 04 02 40 00 00
09 04 01 00 02 03 00 00 00   09 21 10 01 00 01 22 9A 00   07 05 81 03 40 00 05   07 05 02 03 40 00 05
```

**Transport (CAPTURED, all captures).** Every command is one 64-byte output report on the interrupt OUT
endpoint, and every reply is one 64-byte input report on the interrupt IN endpoint. Reports are numbered:
`R[0]` is the report ID, `0xD0` for the cooler command set and `0x01` for the firmware and model queries.
Always send exactly 64 bytes including the ID (LibreHardwareMonitor and liquidctl agree; a 65-byte write is a
Linux `hidraw` habit that fails on Windows).

**Shared access (METADATA, credited to LibreHardwareMonitor).** The HID interface is not exclusive. MSI
Center and LibreHardwareMonitor both serialise their request/reply pairs with the named mutex
`Global\Access_USB_Sensors` (the name appears in MSI's string table and in LibreHardwareMonitor's source).
Because every open handle receives a copy of every input report, a reader must flush its queue, send, then
read until the echo byte matches.

## 2. Command set, report `0xD0`

| `R[1]` | Purpose | Direction | Request | Reply | Status |
|---|---|---|---|---|---|
| `0x31` | Get status: RPM, temperatures, duties | request, reply | `D0 31`, rest `00` | 64 B, `D0 31`, layout in section 3 | CAPTURED (capture 1, 1483 pairs) |
| `0x32` | Get duty configuration | request, reply | `D0 32` | `D0 32` + 5 blocks `[mode, d0..d6]` at `R[2]`, `R[10]`, `R[18]`, `R[26]`, `R[34]` | credited to liquidctl and LibreHardwareMonitor; OBSERVED 2026-10-26/27 |
| `0x33` | Get temperature configuration | request, reply | `D0 33` | **`D0 32`** (echo quirk: the reply carries `0x32`) + 5 blocks `[mode, t0..t6]` | credited to liquidctl and LibreHardwareMonitor; OBSERVED 2026-10-26/27 |
| `0x40` | Set duty configuration | request only | `D0 40` + 5 blocks `[mode, d0..d6]` at `R[2..41]`, `R[42..63]` = `00` | none | CAPTURED (capture 1, 06:42:22.027) |
| `0x41` | Set temperature configuration | request only | `D0 41` + 5 blocks `[mode, t0..t6]` | none | CAPTURED (capture 1, 06:42:22.088) |
| `0x85` | Host temperature feed ("CPU status") | request only | `D0 85`, `R[2..3]` = frequency MHz u16, `R[4..5]` = temperature °C u16 | none | CAPTURED (capture 1, 1484 frames) |

The vendor software never sent `0x32` or `0x33` in the captures (it keeps its own copy of the configuration).
Their layouts come from liquidctl (K360) and LibreHardwareMonitor (S360) and were confirmed by reading them
back from this unit on 2026-10-26 and 2026-10-27 (OBSERVED).

## 3. `0x31` status reply

Layout (credited to liquidctl and LibreHardwareMonitor; every field below was checked against capture 1):

| Offset | Size | Field | Notes |
|---|---|---|---|
| 0 | 1 | report ID `D0` | |
| 1 | 1 | echo `31` | reject anything else |
| 2 | 2 | slot 0 RPM (radiator fans) | u16; `0` throughout the captures, because the captured unit's radiator fans were wired to a separate fan hub, not to the cooler |
| 4 | 2 | slot 1 RPM | u16; `0` |
| 6 | 2 | slot 2 RPM | u16; `0`. LibreHardwareMonitor exposes only slot 0 for the S360 (INFERRED: the three radiator fans share one PWM and tach line) |
| 8 | 2 | slot 3 RPM, **pump-cap fan** | u16; see "Slot identities" |
| 10 | 2 | slot 4 RPM, **pump** | u16 |
| 12 | 2 | "inlet" temperature | `00 00` throughout capture 1; meaning UNKNOWN |
| 14 | 1 | **liquid temperature, whole °C** | `0x1F`..`0x22` = 31..34 °C in capture 1 |
| 15 | 1 | **liquid temperature, tenths** (OBSERVED 2026-10-31) | only the values `00`..`09` occur, and the pair steps `1F 09` → `20 00` → `20 01` ... as the liquid warms, so `R[14].R[15]` reads 31.9, 32.0, 32.1 °C. Confirmed by a 20-minute idle / load / idle log (5 s samples, liquid 36.3 → 40.3 → 37.7 °C): at all ten whole-degree changes of `R[14]`, `R[15]` wrapped `09` → `00` on a rise and `00` → `09` on a fall. Liquid °C = `R[14]` + `R[15]` / 10. Earlier open-source readers treat `R[14..15]` as one u16 or ignore `R[15]` |
| 16 | 2 | temperature sensor 1 | u16; `7D 00` = 125 = "no sensor" (LibreHardwareMonitor's rule), constant in capture 1 |
| 18 | 2 | temperature sensor 2 | u16; 125 = absent, constant |
| 20 | 2 | UNKNOWN | `00 00` throughout |
| 22 | 2 | slot 0 duty % | u16 |
| 24 | 2 | slot 1 duty % | u16 |
| 26 | 2 | slot 2 duty % | u16 |
| 28 | 2 | slot 3 duty % | u16 |
| 30 | 2 | slot 4 duty % | u16 |
| 32 | 32 | padding | `00` in all 1483 replies of capture 1 |

Example, **CAPTURED (capture 1, 06:40:57.321)**, the reply to a `0x31` request sent 8 ms earlier:

```
D0 31  00 00  00 00  00 00  27 04  D0 06  00 00  22 00  7D 00  7D 00  00 00  1C 00  00 00  00 00  14 00  32 00  00 .. 00
```

Decoded: radiator 0 RPM (no fans connected on this unit), slot 3 = 1063 RPM, slot 4 = 1744 RPM, inlet 0,
liquid 34.0 °C, sensors 1 and 2 absent, duties 28 / 0 / 0 / 20 / 50 %.

Reply after the vendor's mode write of 06:42:22 (**CAPTURED, 06:42:23.193**): identical layout, liquid
`21 03` = 33.3 °C, duties unchanged (the controller was already in the mode that was written).

**Cadence (CAPTURED).** MSI Center sends `0x31` every 0.34 s and reads the reply within about 8 ms.

### Slot identities

| Slot | Device | Evidence |
|---|---|---|
| 0, 1, 2 | the three radiator fans, driven as one group | credited to liquidctl and LibreHardwareMonitor; not verifiable in these captures (no radiator fans on the captured controller) |
| 3 | the 60 mm fan in the pump cap | CAPTURED: `R[8..9]` equals the value the vendor sends to the LCD as hardware-monitor item 6 "Water Block Fan" in the same second (`0x0427` in the `0x31` reply at 06:40:57.321 and in the LCD frame at 06:40:57.337). Its Balance duty at 0 °C is 20 %, the lowest of the three channels |
| 4 | the pump | CAPTURED: `R[10..11]` equals LCD item 4 "Pump Fan" (`0x06D0` in both frames above), and its Balance duty at 0 °C is 50 %. OBSERVED 2026-10-27 with a third-party driver: slot 4 is the channel that behaves as the pump on this unit. OBSERVED 2026-10-26 by an independent tach: the pump's own tach lead, read on a motherboard fan header, rose from 1769 to 2030-2290 RPM while slot 4 was driven at 62-66 % |

Open-source projects disagreed on slots 3 and 4 (liquidctl's K360 names put the pump on slot 3, Libre-
HardwareMonitor's S360 labels put it on slot 4). The capture settles it for the S360: **slot 4 is the pump.**

## 4. `0x32` / `0x33` configuration readback

Both replies carry `D0 32` at `R[0..1]`. Five 8-byte blocks follow at `R[2]`, `R[10]`, `R[18]`, `R[26]` and
`R[34]`, one per slot, each `[mode, v0, v1, v2, v3, v4, v5, v6]`: duties for `0x32`, temperatures for `0x33`.
`R[42..63]` are UNKNOWN (zero when read on this unit).

**Four-value retention (OBSERVED 2026-10-26 and 2026-10-27, this unit, controller firmware 0x04).** The
firmware keeps only the first four of the seven values of each block written with `0x40` / `0x41`. A
five-point curve read back as its first four points; a fixed block written as `[3, 60,60,60,60,60,60,60]` read
back as `[3, 60,60,60,60,0,0,0]`, with the 60 % duty in effect. Consequences: write at most four curve points
and put the 100 % point among them; compare a readback on the first four values.

**Power-on configuration (OBSERVED 2026-10-26 to 2026-10-31, from `0x32` / `0x33` read before any write at each
host start).** The configuration is not stored in flash. It survives a Windows restart (the controller stays
powered) but not a shutdown: after every cold power-on all five slots read **mode 4 (Default)**, which is what
the cooler runs until a host writes. See section 5 for what mode 4 does.

## 5. `0x40` / `0x41` configuration writes

Layout: `R[0]` = `D0`, `R[1]` = `40` (duties) or `41` (temperatures), five 8-byte blocks at `R[2..41]` as in
section 4, `R[42..63]` = `00`. No reply. Write `0x40` first, then `0x41` (every known writer does; CAPTURED:
the vendor wrote them 61 ms apart). Give the same mode byte to both blocks of a slot; what the firmware does
with mismatched mode bytes is UNKNOWN.

### Mode byte (first byte of each block)

| Value | Name (METADATA, MSI enum `FanMode`; liquidctl and LibreHardwareMonitor use the same numbers) | Encoding |
|---|---|---|
| 0 | Silent | preset: mode byte + 7 zero bytes in both `0x40` and `0x41`; the curve lives in firmware |
| 1 | Balance | preset |
| 2 | Game | preset |
| 3 | Customize | `0x40` carries 7 duties d0..d6, `0x41` carries 7 temperatures t0..t6; point *i* is (t_i, d_i), piecewise-linear (INFERRED from the vendor's UI). Unused points are zero |
| 4 | Default | preset, not offered by the vendor's UI (METADATA). **OBSERVED 2026-10-31: constant, the feed is ignored:** slot 0 60 %, slots 1 and 2 0 %, slot 3 (pump-cap fan) 50 %, slot 4 (pump) 100 %, unchanged while the fed temperature moved 46-62 °C. This is the power-on state (section 4), so from a cold start the pump runs at full speed until a host writes, and fans on slots 1-2 stand still in that window |
| 5 | Smart | preset, not offered by the vendor's UI (METADATA). **OBSERVED 2026-10-31: dynamic, follows the feed** smoothly rather than along a visible fixed curve: pump 64-97 %, slot 0 47-60 %, slots 2 and 3 about 10 points below slot 0, slot 1 0 %, at fed temperatures of 45-65 °C |

**Slew (OBSERVED 2026-10-31).** In every mode the firmware moves a duty towards its new target at roughly 4
percentage points per 3 s, so a mode change takes 10-20 s to settle.

**Fixed duty** has no mode of its own: mode 3 with all duties equal and all temperatures zero (liquidctl's
method). On this unit the stored form is `[3, v,v,v,v,0,0,0]` because of the four-value retention.

**Presets are not autonomous.** The controller has no temperature sensor of its own for the curves
(documented by liquidctl for the K360; consistent with everything captured here): presets and custom curves
are evaluated against the **last value received with `0x85`**. If the host stops feeding, the duties freeze
at the last evaluation (OBSERVED for 10 minutes, section 6). Only a fixed duty, and mode 4, are independent of
the feed.

### Captured example: Balance on all five slots

**CAPTURED (capture 1, 06:42:22.027 and 06:42:22.088)**, written by the vendor software about 80 s after its
service restarted, about 1 s after it initialised the LCD:

```
D0 40  01 00 00 00 00 00 00 00  01 00 00 00 00 00 00 00  01 00 00 00 00 00 00 00  01 00 00 00 00 00 00 00  01 00 00 00 00 00 00 00  00 .. 00
D0 41  01 00 00 00 00 00 00 00  01 00 00 00 00 00 00 00  01 00 00 00 00 00 00 00  01 00 00 00 00 00 00 00  01 00 00 00 00 00 00 00  00 .. 00
```

62 ms later came one feed frame with 10 °C (`D0 85 00 00 0A 00`, 06:42:22.150), then the regular feed
resumed. INFERRED: the vendor sends a fixed low temperature once after a mode change; liquidctl sends 100 °C
in the same place as a safety measure, which is the better choice.

## 6. `0x85` host temperature feed

```
D0 85  <MHz lo> <MHz hi>  <°C lo> <°C hi>  00 .. 00
```

- `R[2..3]`: CPU frequency in MHz, u16. Not used for fan control (credited to coreliquid_driver, which sends a
  constant); the K-series LCD showed it. On the S360 the LCD gets its values by another path (see the LCD
  document), so this field is cosmetic.
- `R[4..5]`: temperature in whole °C, u16. The curves' temperature points are single bytes 0..100, so send
  whole degrees in that range.
- No reply.

**Cadence (CAPTURED, capture 1).** The vendor sends `0x85` every 0.34 s, right after each `0x31` reply, in one
loop: `0x31` request, reply 8 ms later, `0x85` about 15 ms after that, then 0.32 s idle. liquidctl's helper
feeds every 2 s, coreliquid_driver every 2 s; any cadence works, since the controller keeps the last value.

**A zero feed is possible (CAPTURED).** For the whole of capture 1 the vendor sent `D0 85 00 00 00 00`
(frequency 0, temperature 0 °C), because its own telemetry engine had crashed, and the controller ran the
Balance curves at their 0 °C duties (radiator 28 %, pump 50 %, pump-cap fan 20 %). A driver should
never send 0 °C; on sensor failure send a high value (100 °C) so that the curves go to full duty.

**No feed timeout within 10 minutes (OBSERVED 2026-10-31).** With custom curves on all slots, the feed was
stopped at idle after a last value of 45 °C and the `0x31` duties were logged every 5 s for 10 minutes. The
duties settled within seconds on the curves' 45 °C values (radiator 34 %, pump-cap fan 31 %, pump 60 %) and
stayed exactly there for the whole 10 minutes (113 of 115 samples; the other two were the normal slew); the
pump held 1986-2013 RPM. When the feed resumed, the duties followed it again at once. No source documents a
watchdog either. Consequence for drivers: **if the host dies, the cooler stays on its last fed value** (INFERRED
indefinitely; longer than 10 minutes not tried). A driver should keep a safe floor on the pump curve, send a
high value (100 °C) when it loses its own temperature source, and ideally have a separate watchdog that writes a
fixed safe duty if the driver process disappears.

## 7. Report `0x01` queries: firmware and model

Layout credited to liquidctl (K360): `R[0]` = `01`, `R[1]` = sub-command, `R[2..63]` = `CC` fill. The reply
has `R[0..1]` = `01 5A` and the value at `R[2]`, `CC` fill after it.

| Sub-command | Meaning | Status | Captured frames |
|---|---|---|---|
| `B1` | model index | **CAPTURED (capture 1, 06:42:17.164, reply .169)** | request `01 B1 CC .. CC`, reply `01 5A 30 CC .. CC`: model index `0x30` = 48 |
| `B0` | APROM firmware version | **CAPTURED (capture 1, 06:42:17.567, reply .573)** | request `01 B0 CC .. CC`, reply `01 5A 04 CC .. CC`: version byte `0x04` |
| `B6` | LDROM firmware version | liquidctl (K360); not captured on the S360 | reply value at `R[2]` |
| `B4` | LDROM checksum | liquidctl (K360); not captured | `R[8..9]` |
| `C0`, `C2` | volume, buzzer | liquidctl (K360); not captured. **OBSERVED 2026-10-31:** `01 C2` with type 1, 650 Hz was accepted (no error, the controller kept answering normally) and **no sound was heard** next to the PC. INFERRED: the S360 controller has no buzzer, or ignores the K-series command. Volume not tried | |
| `D0` | **reset MCU** | liquidctl lists it (commented out) | **do not send** |

The vendor queries `B1` then `B0` once, at the start of its init, 5 s before the fan-mode write. liquidctl's
K360 reader splits the version byte into nibbles (`(R[2] >> 4).(R[2] & 0xF)`), which would print `0.4` here;
MSI's metadata declares the getter as `Get_FwVersion_APROM(ref byte highVersion, ref byte lowVersion)`, so it
may also read `R[3]`. The names APROM and LDROM are Nuvoton NuMicro boot-loader terms; MSI's
metadata also carries the boot-loader USB ID `0416:3F00` (METADATA, constants `VID_7ZW0_Boot` and
`PID_7ZW0_Boot`), so a controller in ISP mode would re-enumerate under that ID. INFERRED: Nuvoton MCU.

## 8. Commands that must not be sent

| Frame | Effect | Source |
|---|---|---|
| `01 D0 CC .. CC` | resets the MCU | liquidctl (commented out) |
| `D0 FA` | enters the ISP boot loader; the pump's behaviour in that state is UNKNOWN | liquidctl (commented out) |
| anything on interface 0 (WinUSB, bulk `0x04` / `0x83`) | UNKNOWN; possibly the firmware-update path | descriptors |
| K-series LCD and LED commands over report `0xD0` (`0x70`..`0x7F`, `0x83`, `0x86`, `0x90`..`0x93`, `0xC0`..`0xC2`, `0xD0`..`0xD2`, `0xF1`) and feature reports `0x52`, `0x53` | the S360's display is a separate device (`0DB0:9BA6`) and the S360 has no LEDs; the effect of these on the `6A05` firmware is UNKNOWN. `0xC0` / `0xD0` start flash uploads on the K360 | liquidctl (K360) |

Also treat the appearance of a `0416:3F00` device, or the disappearance of `6A05` / `9BA6` without a USB
unplug, as a firmware update in progress and stop all traffic.

## 9. Sequences as the vendor does them (CAPTURED, capture 1)

| Time | Frame | Note |
|---|---|---|
| 06:40:57.313 onwards | `D0 31` / reply / `D0 85`, every 0.34 s | runs from the first second, before any init; stops for about 77 s while the vendor's service restarts (06:41:04 to 06:42:17) |
| 06:42:17.164 | `01 B1` → `01 5A 30` | model index |
| 06:42:17.567 | `01 B0` → `01 5A 04` | firmware |
| 06:42:20.646 to 21.593 | LCD init (see the LCD document) | |
| 06:42:22.027 | `D0 40` Balance ×5 | |
| 06:42:22.088 | `D0 41` Balance ×5 | |
| 06:42:22.150 | `D0 85 00 00 0A 00` | one 10 °C feed |
| 06:42:23.188 onwards | the `0x31` / `0x85` loop continues | |

There is no handshake or "init" command for the controller. A third-party driver's minimal sequence is:
read `0x31`, read `0x32` and `0x33` (keep them as the restore point), start the `0x85` feed, then write
`0x40` and `0x41`.

## 10. Open items

| # | Question | How to settle |
|---|---|---|
| 1 | Meaning of `R[12..13]` (always `00 00` here) and `R[20..21]` of the status reply | read them on a unit with the optional temperature probes, or across a long load sweep |
| 2 | ~~Confirm `R[15]` as tenths~~ **Settled 2026-10-31** (section 3: wraps at every whole-degree change of `R[14]`) | done |
| 3 | ~~Whether the controller has a feed timeout or watchdog~~ **None within 10 minutes** (section 6, 2026-10-31); longer stops not tried | done (10 min) |
| 4 | ~~Behaviour of modes 4 (Default) and 5 (Smart) on the S360~~ **Settled 2026-10-31** (section 5: Default constant, Smart follows the feed) | done |
| 5 | How the firmware resolves mismatched mode bytes between the `0x40` and `0x41` blocks of one slot | bench test |
| 6 | ~~Power-on configuration before any host writes~~ **Mode 4 on all slots after a cold power-on; kept across a restart** (section 4, 2026-10-26 to 31) | done |
| 7 | Purpose of interface 0 (bulk) | descriptor dump and, if ever offered, a capture of the vendor's firmware updater |
| 8 | `01 B6` / `01 B4` on the S360 | one capture of the vendor's updater's version check |
| 9 | Whether the S360 has a buzzer at all (`01 C2` gave no sound, section 7) | vendor information; or try other `type` values and `01 C0` volume |
