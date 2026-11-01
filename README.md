# MSI MEG CoreLiquid S360: USB protocol reference

An independent, clean-room description of the USB protocols spoken by the MSI MEG CoreLiquid S360
all-in-one liquid cooler. The cooler is **two USB devices** on one internal USB 2.0 header:

| Device | USB ID | What it does | Document |
|---|---|---|---|
| Cooler controller | `0DB0:6A05` | pump, pump-cap fan and radiator fans; takes a host temperature feed; reports RPM, duties and the liquid temperature | [msi-coreliquid-s360-controller.md](msi-coreliquid-s360-controller.md) |
| 2.4" LCD controller | `0DB0:9BA6` | the 240 × 320 display: hardware-monitor page, images and video, text banner, clock, weather | [msi-coreliquid-s360-lcd.md](msi-coreliquid-s360-lcd.md) |

Coverage per command and change history: [STATUS.md](STATUS.md).

## Why this exists

The controller side of the S360 was already partly known from open-source software (see Credits). The LCD
side was not documented anywhere public. On 2026-10-28 the USB traffic between MSI Center and both devices was
captured with USBPcap while every function of the LCD page was exercised, and the frames were decoded. This
reference writes down what was seen, what MSI's own software declares, and what is still unknown, so that
anyone writing a driver for this cooler can start from facts rather than guesses. Bench tests on the same unit
with third-party code (2026-10-26 to 2026-11-01) later answered several questions the captures could not, such
as the power-on state, the Default and Smart modes, the missing feed timeout, the two LCD queries the vendor
never sends, and how long the LCD keeps uploaded media (only while powered); those statements are tagged OBSERVED.

## Scope

- The wire protocol of both devices: HID reports, byte layouts, value sets, sequences and timing as observed.
- Not covered: MSI Center's user interface, its log files, and any host-side logic that does not reach the
  USB bus. The LCD document ends with a short host-side section (asset folders and registry value names)
  only to relate the vendor's settings to the frames. The firmware-update protocol of either device is deliberately **not**
  described beyond the warning not to trigger it.
- One unit was observed: controller firmware `0x04`, LCD firmware `0x09`, with MSI Center 2.0.x as the host.
  The metadata was read from Coreliquid component 4.2025.1003.01; the installed component at capture time
  reported 4.2026.0611.01. Other versions may differ.

## How to read the tags

Every statement carries one of these tags.

| Tag | Meaning |
|---|---|
| **CAPTURED** | seen on the USB bus in one of the captures below; the capture and the time of day are given, so the frame can be found in the raw file |
| **METADATA** | read from the public .NET metadata tables of MSI's `API_Coreliquid.dll` (constant values, type, method and parameter names). Metadata says what the software *declares*, not what it sends |
| **HOST** | read from the vendor's installed files or registry key names on the capturing PC (asset sizes, value names); used only to explain wire values |
| **OBSERVED** | seen while driving the hardware with third-party code (not a vendor capture), with the date |
| **INFERRED** | a conclusion drawn from the evidence, not read from any source; the reasoning is given |
| **UNKNOWN** | a gap, with a note on what would close it |

The captures (all 2026-10-28, local time of the capturing PC, UTC-7):

| Capture | Time | What was exercised |
|---|---|---|
| 1 | 06:41 to 06:50 | vendor service cold start, backlight 0/50/100 %, four orientations, °F and °C, the hardware-monitor page with one and with three items, the display on/off toggle |
| 1b | 07:04 to 07:12 | the five clock styles, every image slot, three media uploads, the text banner with three backgrounds, back to the monitor page |
| 1c | 07:23 to 07:28 | the four monitor-page designs, a one-line banner at Fast and at Slow speed |
| 1d | 09:30 to 09:33 | a multi-line banner, a video file, back to the monitor page |
| 1e | 10:04 to 10:07 | the Live Weather page with °C and °F, a banner at Normal speed, back to the monitor page |

The raw capture files are not published because they contain the owner's uploaded media. The decoded
frames quoted in these documents are complete for every command that matters; media payloads are shown
only as their first bytes.

## Clean-room statement

The facts in these documents come from these sources only:

1. USB captures of the vendor software (MSI Center) talking to the cooler, made with USBPcap on the owner's own PC.
2. The public .NET metadata tables of MSI's `API_Coreliquid.dll` (ECMA-335 Constant, Field, MethodDef and
   Param tables), read with a small standard-library parser to obtain constant values and the names of types,
   methods and parameters.
3. For the host-side notes only: the sizes and names of the vendor's installed asset files, the container and
   codec headers of the media files it transcoded (profile, size, frame rate), and the value names of its
   registry key, all read without modification.
4. For the OBSERVED statements: the devices' own replies and behaviour when driven by independently written
   third-party code on the same PC (frames built from sources 1 and 2).

No code was decompiled or disassembled. No MSI source code was used or seen. The only MSI strings reproduced
here are the command and enumeration names from the metadata tables and the ASCII strings that appear on the
wire. Facts about the controller that were first published by the open-source projects below are credited to
them and were re-checked against the captures where possible.

## Credits

- **[liquidctl](https://github.com/liquidctl/liquidctl)** documented the report-`0xD0` protocol family on the
  MSI MPG CoreLiquid K360 (status, duty and temperature configuration, the host temperature feed, the
  report-`0x01` firmware queries). The S360 controller speaks the same family. liquidctl is GPL-3.0; nothing
  from it is copied here, only the protocol facts it established.
- **[LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor)** drives the S360
  controller (`0DB0:6A05`) on Windows and documented the shared `Global\Access_USB_Sensors` mutex, the 64-byte
  report length and the `0x33` echo quirk. MPL-2.0; again only facts are reused.
- **[coreliquid_driver](https://github.com/sarzeaud/coreliquid_driver)**, a Linux userspace driver for the
  S360, confirmed the preset mode values and the feed layout on this exact controller.
- **MSI** is the vendor whose software, MSI Center, was observed. All product and command names are MSI's.

## Related work

Prior public work on these coolers, as found by a web search on 2026-10-28. Each entry is **reported from
the web and not verified by us**; descriptions summarise what each project states about itself.

- **sakir** (https://github.com/elmsomr/sakir, GPL-3.0, first release 2026-10-20): an MSI Center replacement
  for the S280 and S360 LCD that drives MSI's `API_Coreliquid.dll` by reflection rather than speaking USB
  itself. Its `docs/PROTOCOL.md` lists command names and codes (`GET_DEV_ID` 0x10, `GET_DEV_INFO` 0x14,
  `SEND_FILE_NODE` 0x20, `SEND_HOST_CPU_INFO` 0x30, `SEND_HOST_GPU_INFO` 0x3C, `SET_DISPLAY_MODE` 0x50),
  display modes 0 to 7 and the 240 × 320 panel. For the Dynamic mode (7) it reports the node names
  `M7-S0-O-R0` / `M7-S0-O-R1`, a `SwitchMode` call on every frame, and a fall-back to the panel's stored loop
  after about 400 ms without an update. It gives no report IDs or byte layouts. It reports the S280 LCD as
  PID `0x75B6` with LCD firmware `0x1B`, and marks the S360 as declared but untested.
- **corecontrol** (https://github.com/diethylene/corecontrol): pump and fan control over HID for the S280
  (`6A04`), S360 (`6A05`, channel mapping marked unverified) and K360 (`B130`); no LCD support.
- **coreliquid_driver** (https://github.com/sarzeaud/coreliquid_driver): a Linux fan-mode driver for the
  S360 that ignores the display.
- **liquidctl**: the K360-family driver (`liquidctl/driver/msi.py`). Pull request
  https://github.com/liquidctl/liquidctl/pull/784 proposed the S360 as `0db0:6a05` and was closed unmerged on
  2026-01-04; a commenter there noted the second device `0db0:9ba6` and that reads from it raised `OSError`.
  Issue https://github.com/liquidctl/liquidctl/issues/758 (S360 descriptors) was closed as not planned, and
  issue https://github.com/liquidctl/liquidctl/issues/579 concerns the S280.
- **LibreHardwareMonitor**: `MsiCoreLiquidController` drives the S360 controller on Windows (credited above).

**What this reference adds.** As far as that search found, no public source documents the LCD's USB report
bytes: the framing, the reply path, the payload layouts, the upload protocol and the host data frames are
new here. The Dynamic-mode details above (node names, per-frame `SwitchMode`, the 400 ms fall-back) are not
covered by our captures and remain unverified.

**Firmware.** No public firmware download or change log exists for the S360 as far as the search found;
MSI Center's live update is the only update path.

## Licence

The documents in this folder are released under the **Creative Commons Attribution 4.0 International
licence (CC BY 4.0)**: use, copy, translate and build on them for any purpose, with credit to this work. See
`LICENSE`. Any scripts or source files published alongside them are under the **MIT License**, see `LICENSE-MIT`.
Decided by the maintainer on 2026-10-28.

## Tools

Two small Python scripts (no dependencies, Python 3.10 or later) live in `tools/` under the MIT License
(see `LICENSE-MIT`):

- `usbpcap_parse.py <capture.pcap> addresses|summary|dump [device]`: reads a USBPcap capture (link type 249),
  lists the device addresses with their VID:PID from the injected descriptors, counts transfers per endpoint, or
  dumps every transfer with its payload.
- `lcd_decode.py <capture.pcap> [notes.txt] [--device N]`: decodes the LCD frames (opcodes, lengths, examples,
  a timeline of the non-periodic commands next to your own timestamped notes). It finds the LCD by its VID:PID
  when the capture was taken with `--inject-descriptors`.

They were used to produce every captured example in these documents.

## How to capture more

Everything here was obtained with [USBPcap](https://desowin.org/usbpcap/) on Windows 11, filtered to the two
S360 device addresses so that nothing else on the bus lands in the file.

1. Install USBPcap. Run `USBPcapCMD.exe` once without arguments: it lists the root hubs (`\\.\USBPcap1`,
   `\\.\USBPcap2`, ...) and, under each, the connected devices with their **device address** and VID:PID.
   Note the root hub and the two addresses of `0DB0:6A05` and `0DB0:9BA6`.
2. Capture (elevated prompt), for example with the LCD at address 18 and the controller at 19:

   ```
   USBPcapCMD.exe -d \\.\USBPcap1 --devices 18,19 -I -o s360.pcap
   ```

   `-I` injects the device and configuration descriptors at the start of the file, which is how the
   endpoint sizes in these documents were confirmed. Stop with Ctrl+C.
3. Do one thing at a time in MSI Center and write down the clock time of each action. The vendor software
   sends a live-data frame to the LCD about three times a second, so the interesting frames are found by
   filtering those out and lining the rest up against the notes.
4. Read the file with Wireshark (link type 249, "USBPcap") or any pcap reader. Each USBPcap record starts
   with a header: `u16 headerLength, u64 irpId, u32 status, u16 function, u8 info, u16 bus, u16 device,
   u8 endpoint, u8 transferType, u32 dataLength`, followed for control transfers by one `u8 stage` byte and
   then the data. Transfer type 2 is control (the LCD's commands), 1 is interrupt (the controller's
   reports and the LCD's file data).

Still uncaptured, in case you want to contribute: `SET_DEV_TIME`, `STOP_MEDIA_NODE` / `PAUSE_MEDIA_NODE`,
`SAVE_FILE_NODE`, the "Dynamic" display mode, a 12-hour clock (`hourFormat` 0), and weather frames with rain,
snow or a non-zero precipitation chance. (`GET_DEV_ID` and `GET_DISPLAY_MODE` are never sent by the vendor;
their replies were read by sending them directly, see the LCD document.) See [STATUS.md](STATUS.md).

## Safety

Both controllers can be reset or re-flashed over the same interfaces. Each document lists those commands
with a do-not-send warning. Apart from the OBSERVED statements, nothing in this reference has been tested
beyond observing the vendor software; anyone sending frames to their own cooler does so at their own risk,
and should keep the pump duty high while experimenting.

**The controller has no feed timeout** (OBSERVED for 10 minutes, controller document section 6): presets and
custom curves keep acting on the last temperature the host sent. If your driver stops, the cooler stays at
whatever that value asked for, idle duties included. Keep a safe pump floor in every curve, send 100 °C when
your temperature source fails, and consider a watchdog that writes a fixed safe duty if your driver dies.
