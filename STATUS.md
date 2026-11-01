# Status and change log

Part of the [S360 protocol reference](README.md). One row per command; the tags are explained in the README.

## Controller `0DB0:6A05`

| Command | Layout | Captured | Notes |
|---|---|---|---|
| `D0 31` status | complete | yes (capture 1) | `R[15]` = tenths of the liquid temperature, OBSERVED 2026-10-31; `R[12..13]`, `R[20..21]` UNKNOWN |
| `D0 32` / `D0 33` readback | complete | no (vendor never reads back); OBSERVED on the bench | `0x33` echoes `0x32`; four-value retention OBSERVED; power-on state mode 4 on all slots, OBSERVED |
| `D0 40` / `D0 41` write | complete | yes (Balance preset) | custom and fixed forms OBSERVED, not captured; modes 4 (Default) and 5 (Smart) behaviour OBSERVED 2026-10-31; mismatched mode bytes UNKNOWN |
| `D0 85` feed | complete | yes | cadence 0.34 s; one 10 °C frame after a mode write; **no timeout within 10 min**, OBSERVED 2026-10-31 |
| `01 B0` firmware | complete | yes | reply `01 5A 04` |
| `01 B1` model index | complete | yes | reply `01 5A 30` |
| `01 B6`, `01 B4`, `01 C0` | from liquidctl (K360) | no | unverified on the S360 |
| `01 C2` buzzer | from liquidctl (K360) | no | accepted but silent, OBSERVED 2026-10-31 |
| `01 D0`, `D0 FA` | do not send | no | reset, ISP |
| interface 0 (bulk) | UNKNOWN | no | |

## LCD `0DB0:9BA6`

| Opcode | Name | Layout | Captured | Open |
|---|---|---|---|---|
| `0x10` | `GET_DEV_ID` | complete: reply `A6 9B 00 00` = PID `0x9BA6` | no (vendor never sends it); OBSERVED 2026-10-31 | |
| `0x14` | `GET_DEV_INFO` | complete | yes | |
| `0x16` | `SET_DEV_TIME` | INFERRED | no | effect |
| `0x18` | `SET_LCM_BACKLIGHT` | complete | yes | |
| `0x1A` | `SET_LCM_DIR` | complete | yes | physical rotation per value |
| `0x1C` | `SET_LCM_RESET` | do not send | no | |
| `0x20` | `SEND_FILE_NODE` | complete | yes | `0x21` reply never read |
| `0x22` | `HMI_SEND_FILE_DATA_START` | complete | yes | |
| `0x24` | | UNKNOWN | no | |
| `0x26` | `HMI_SEND_FILE_DATA_END` | complete | yes | |
| `0x28` | `SAVE_FILE_NODE` | INFERRED | no | persistence |
| `0x2A` | `DEL_FILE_NODE` | do not send | no | |
| `0x30` | `SEND_HOST_CPU_INFO` | complete | yes | |
| `0x32` | `SEND_HOST_FAN_SPEED` | INFERRED | no | unused by the vendor |
| `0x34` | `SEND_HOST_FPS` | INFERRED | no | unused by the vendor |
| `0x36` | `SEND_HOST_TIME` | complete | yes | `hourFormat` 0 never seen (1 in all 46 frames) |
| `0x38` | `SEND_HOST_WEATHER` | partial: temperature f32 °C at 28, humidity u16 at 42, weather u16 at 48 | yes (capture 1e, one sample) | precipitation float position INFERRED (32 or 44); other weather values |
| `0x3A` | `SEND_HOST_MSG` | complete for the unit string | yes | other text, sync-mode string |
| `0x3C` | `SEND_HOST_GPU_INFO` | INFERRED | no | unused by the vendor |
| `0x40` | `PLAY_MEDIA_NODE` | complete; banner speed Fast 7, Normal 4, Slow 1 | yes | axis of `scrollDir`, `x`/`y` units |
| `0x42` | `STOP_MEDIA_NODE` | INFERRED | no | |
| `0x44` | `PAUSE_MEDIA_NODE` | INFERRED | no | |
| `0x50` | `SET_DISPLAY_MODE` | complete for modes 0, 1, 2, 5, 6 | yes | mode 7 (Dynamic); banner background numbering; image slot 6 |
| `0x52` | `GET_DISPLAY_MODE` | complete for modes 0, 1, 2, 5: byte 0 = active flag, then the mode's header and its last selection | no (vendor never sends it); OBSERVED 2026-10-31 | |

Remaining UNKNOWN on the LCD: `SET_DEV_TIME`,
`STOP_MEDIA_NODE` / `PAUSE_MEDIA_NODE` (`0x42` / `0x44`), `hourFormat` 0 and the Dynamic mode (7), plus the
smaller gaps in the table.

Prior public work is listed under "Related work" in the [README](README.md). It is reported from the web and
not verified by us. One project (sakir) describes the Dynamic mode's node names and timing at the level of
MSI's API, without byte layouts.

## Change log

- **2026-10-31, update: bench results.** Statements tagged OBSERVED, from driving the same unit with
  third-party code (README, source 4). Controller: `R[15]` confirmed as the tenths of the liquid temperature
  (20-minute idle / load log); the power-on state (mode 4 on all slots after a cold start, kept across a restart,
  not in flash); what modes 4 (Default: constant, feed ignored, pump 100 %) and 5 (Smart: follows the feed) do;
  the duty slew of about 4 points per 3 s; **no feed timeout within 10 minutes** (duties held the last fed value's
  curve values unchanged), with a driver-safety note in the README; `01 C2` buzzer accepted but silent; the pump
  slot confirmed by an independent tach. LCD: the `GET_DEV_ID` reply (`A6 9B 00 00`, the LCD's PID) and the
  `GET_DISPLAY_MODE` reply for four modes (byte 0 marks the active mode; the active mode's fields are the ones
  set); a stale `0x01F0` status that only a power cycle cleared; late `GET_DEV_INFO` answers after a cold
  power-on; backlight 50 % and 100 % look the same; direction turns firmware pages but not media; the unit string
  has no visible effect on firmware 9. Open items updated in both documents. Later the same evening: the clock
  styles and built-in image slots 0-6 switched by a third-party driver (all worked), which showed that
  `GET_DISPLAY_MODE`'s screen bytes are each mode's own last selection (section 5.6 corrected).

- **2026-10-28, update.** "Related work" section added to the README (sakir, corecontrol, coreliquid_driver,
  liquidctl PR #784 and issues #758 and #579, LibreHardwareMonitor), with notes that no public source
  documents the LCD's report bytes and that no public S360 firmware download exists. The coreliquid_driver
  link is filled in.

- **2026-10-28, update.** Capture 1e added: the weather page (mode 6) and `SEND_HOST_WEATHER` (temperature,
  humidity and weather fields; precipitation position inferred), the banner's Normal speed (4) and the
  line-layout rule for node and `scrollDir`. Monitor-page asset meanings confirmed against the vendor's asset
  folder (`R13` is the unit label, not a second title). The banner image shown to be the host-rendered text.
  New HOST tag and a host-side section in the LCD document (asset folders, registry value names without values).
  Frame counts refreshed for five captures.

- **2026-10-28, first version.** Written from four USBPcap captures of MSI Center (metadata read from component
  4.2025.1003.01) driving one S360 (controller firmware 0x04, LCD firmware 0x09) and from the .NET metadata of
  `API_Coreliquid.dll`. Controller facts cross-checked against liquidctl and LibreHardwareMonitor. New in this
  version compared with what was public before: the whole LCD protocol (framing, every captured opcode, modes,
  node names, upload sequence, settings file, host data and time frames, unit string), the controller's
  `0x31` / `0x85` cadence, the `01 B0` / `01 B1` replies, the slot-4-is-the-pump identification, the tenths byte
  of the liquid temperature, and the four-value retention of configuration blocks.
