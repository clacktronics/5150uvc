# 5150UVC: design notes for review (rev 0.2 draft)

RCA composite → TVP5150AM1 → GW2AR-18 FPGA → FT602 → USB 3 UVC webcam, on one board powered from the USB 3 cable.

## Files

| Path | What |
|---|---|
| `hardware/5150UVC.kicad_pro` | KiCad 10 project: one A2 sheet with every signal drawn as a wire (no net labels) |
| `docs/5150UVC_schematic.pdf` | The same schematic as a PDF |
| `docs/pin_assignment.csv` | Every GW2AR-18 QN88 pin: net, destination, notes |
| `docs/5150uvc.cst` | Gowin pin constraints generated from the same table |
| `tools/design.py` | Generator script. Edit the pin map or parts here and re-run `.venv/bin/python tools/design.py` |
| `tools/check.py` | Regenerates the sheet, exports KiCad's netlist and checks it against the connections the generator meant to draw |
| `datasheets/` | FT602Q DS v1.4, TVP5150AM1 (SLES209E), Gowin UG115 (GW2AR-18 pinout), Tang Nano 20K schematic 3921 |

Note: re-running the generator overwrites `hardware/5150UVC.kicad_sch`. Once you start editing in KiCad by hand, stop using the script.

## Checks run

- KiCad ERC: 0 errors, 0 warnings.
- Netlist cross-check (`tools/check.py`): KiCad's netlist matches the 115 intended nets exactly. No net is split or shorted, every pin is either connected as intended or explicitly marked no-connect, and all 66 FPGA pins reach the intended FT602 / TVP5150 / flash / JTAG pins.

## Reading the sheet

- The three big symbols share row positions: FPGA right ↔ FT602 left (FIFO bus, I²C, reset) and FPGA left ↔ TVP5150 right (BT.656 bus, I²C, reset). So the buses are straight wires. Supplies use power symbols; everything else is wired.
- Decoupling banks are along the top edge. Place each 100n at its own supply pin.
- The JTAG header pinout is 1 3V3, 2 TCK, 3 TDI, 4 TDO, 5 TMS, 6 GND. Change it to match your programmer's cable.
- The FT602 RXF_N/RESERVED1-3 pull-ups are a 4 × 10k array (RN1).

## I/O budget (GW2AR-18 QN88)

UG115 lists 66 user I/O on QN88. All 66 are used:

| Use | Pins |
|---|---|
| FT602 FIFO: D[31:0], BE[3:0], CLK, TXE_N, WR_N | 39 |
| FT602 control: RESET_N, INT_N, SCL, SDA | 4 |
| TVP5150: YOUT[7:0], SCLK, SCL, SDA, RESETB | 12 |
| 27 MHz system clock, status LED | 2 |
| JTAG (4), RECONFIG_N, MSPI flash (4) | 9 |

Clocks are on global-clock pins: FT_CLK on pin 77 (GCLKT_1), TVP_SCLK on pin 10 (GCLKT_6), SYS_CLK on pin 4 (as on the Nano). There are no spare pins. If you need more, drop the FT602 INT_N or BE[3:0] once AN_434 confirms they aren't needed (BE could then be tied high).

## Key decisions

- **FT602 in 245 synchronous FIFO mode** at 100 MHz with VCCIO at 3.3 V. Multi-channel mode would need RXF_N as well, and there's no pin for it.
- **Two separate I²C buses.** The FT602 is an I²C *master* with no arbitration. It sends format-select and stream-start commands to an I²C slave, which the FPGA implements (register map in AN_434). The FPGA is in turn the master on the TVP5150 bus.
- **Boot straps copied from the Tang Nano 20K.** MODE0/MODE1 have 1 kΩ pull-downs, which selects MSPI boot from a W25Q64. MODE0 (pin 88) then becomes TVP_RESETB, so the decoder stays in reset until the FPGA is configured. MODE1 (pin 87) drives the LED.
- **FT602 RESET_N has its own 10 kΩ pull-up and 100 nF capacitor,** so the FT602 enumerates and can be programmed with FTDI's configuration utility even when the FPGA is blank.
- **Single 3.3 V I/O everywhere.** On QN88, VCCIO2/6/7 are tied to VCCX inside the package (at 3.3 V, because of the SDRAM).

## Review flags (not verified)

1. **FTDI AN_434 (FT602 UVC bus-master sample) is missing.** ftdichip.com blocks scripted downloads. It defines how the FPGA marks frame boundaries and the I²C slave register map. Download it, together with AN_435 (chip configuration) and AN_437 (I²C), from FTDI's FT602 page.
2. **The QFN-88 footprint is a placeholder** (ArtInChip 10×10 mm, EP 6.74 mm). Check the pad and exposed-pad dimensions against Gowin UG229 before layout.
3. **The RCA jack has no footprint.** The stock KiCad library has none. Choose a part, for example from CUI's RCJ-01x series.
4. **Crystal load capacitors (27 pF) assume CL = 18 pF.** Recalculate for the actual 30 MHz and 14.31818 MHz parts.
5. **TVP5150 anti-aliasing filter is not fitted.** TI recommends one. Consider adding an LC low-pass filter around 6 MHz, or footprints for one.
6. **Gowin power-up sequencing** follows the Tang Nano 20K: all rails come up together from 5 V. Check against the GW2AR datasheet (DS226).
7. **Gowin project settings:** enable "Use SSPI as regular IO" (pins 52–56) and "Use MSPI as regular IO" if Gowin's tools require it for pin 57.
8. **USBLC6 is drawn flow-through.** D+/D- go into pins 1/3 and out of pins 6/4, so the FT602-side and connector-side halves are separate nets in the netlist. Route through the pads.
9. **USB 3 layout:** 90 Ω differential pairs on a 4-layer stack-up with continuous ground. The SSTX AC-coupling capacitors (100 nF) sit near the FT602.
