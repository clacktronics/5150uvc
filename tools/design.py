"""5150UVC: composite video (RCA) -> TVP5150AM1 -> GW2AR-18 -> FT602 USB3 UVC.

Run: .venv/bin/python tools/design.py  -> regenerates the KiCad project in ../hardware and the pin-assignment table in ../docs.
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from kisch import Sheet, make_symbol  # noqa: E402
from sexp import symbol_pins  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
HW = os.path.join(ROOT, 'hardware')
DOCS = os.path.join(ROOT, 'docs')

FP_R = 'Resistor_SMD:R_0402_1005Metric'
FP_C = 'Capacitor_SMD:C_0402_1005Metric'
FP_C0805 = 'Capacitor_SMD:C_0805_2012Metric'
FP_C0603 = 'Capacitor_SMD:C_0603_1608Metric'
FP_FB = 'Inductor_SMD:L_0603_1608Metric'

# ============================================================== FPGA pin map
# (pin, Gowin pin name, bank, net, connects to, note)
FPGA_IO = [
    # bank 7 / 6 (left)
    (4, 'IOL7A/LPLL1_T_in', 7, 'SYS_CLK', '27 MHz oscillator (via 22R)', 'Same as Tang Nano 20K'),
    (10, 'IOL29A/GCLKT_6', 6, 'TVP_SCLK', 'U9 TVP5150 SCLK (pin 9) via 22R', '27 MHz pixel clock, global clock pin'),
    (11, 'IOL29B/GCLKC_6', 6, 'TVP_YOUT0', 'U9 YOUT0 (pin 18)', ''),
    (13, 'IOL45A/LPLL2_T_in', 6, 'TVP_YOUT1', 'U9 YOUT1 (pin 17)', ''),
    (15, 'IOL47A/LPLL2_T_fb', 6, 'TVP_YOUT2', 'U9 YOUT2 (pin 16)', ''),
    (16, 'IOL47B/LPLL2_C_fb', 6, 'TVP_YOUT3', 'U9 YOUT3 (pin 15)', ''),
    (17, 'IOL49A', 6, 'TVP_YOUT4', 'U9 YOUT4 (pin 14)', ''),
    (18, 'IOL49B', 6, 'TVP_YOUT5', 'U9 YOUT5 (pin 13)', ''),
    (19, 'IOL51A', 6, 'TVP_YOUT6', 'U9 YOUT6 (pin 12)', ''),
    (20, 'IOL51B', 6, 'TVP_YOUT7', 'U9 YOUT7/I2CSEL (pin 11)', '10k pull-up on TVP sheet sets I2C addr 0xBA'),
    # bank 5 (bottom)
    (25, 'IOB6A', 5, 'FT_D0', 'U6 FT602 DATA_0 (pin 40)', ''),
    (26, 'IOB6B', 5, 'FT_D1', 'U6 DATA_1 (pin 41)', ''),
    (27, 'IOB8A', 5, 'FT_D2', 'U6 DATA_2 (pin 42)', ''),
    (28, 'IOB8B', 5, 'FT_D3', 'U6 DATA_3 (pin 43)', ''),
    (29, 'IOB14A', 5, 'FT_D4', 'U6 DATA_4 (pin 44)', ''),
    (30, 'IOB14B', 5, 'FT_D5', 'U6 DATA_5 (pin 45)', ''),
    (31, 'IOB18A', 5, 'FT_D6', 'U6 DATA_6 (pin 46)', ''),
    (32, 'IOB18B', 5, 'FT_D7', 'U6 DATA_7 (pin 47)', ''),
    (33, 'IOB24A', 5, 'FT_D8', 'U6 DATA_8 (pin 50)', ''),
    (34, 'IOB24B', 5, 'FT_D9', 'U6 DATA_9 (pin 51)', ''),
    # bank 4 (bottom)
    (35, 'IOB30A/GCLKT_4', 4, 'FT_D10', 'U6 DATA_10 (pin 52)', ''),
    (36, 'IOB30B/GCLKC_4', 4, 'FT_D11', 'U6 DATA_11 (pin 53)', ''),
    (37, 'IOB34A', 4, 'FT_D12', 'U6 DATA_12 (pin 54)', ''),
    (38, 'IOB34B', 4, 'FT_D13', 'U6 DATA_13 (pin 55)', ''),
    (39, 'IOB40A', 4, 'FT_D14', 'U6 DATA_14 (pin 56)', ''),
    (40, 'IOB40B', 4, 'FT_D15', 'U6 DATA_15 (pin 57)', ''),
    (41, 'IOB43A', 4, 'FT_TXE_N', 'U6 TXE_N (pin 8)', 'FT602 -> FPGA, FIFO has space'),
    (42, 'IOB42B', 4, 'FT_WR_N', 'U6 WR_N (pin 11)', 'FPGA -> FT602 write strobe'),
    # bank 3 (right)
    (48, 'IOR49B', 3, 'FT_BE0', 'U6 BE_0 (pin 4)', ''),
    (49, 'IOR49A', 3, 'FT_BE1', 'U6 BE_1 (pin 5)', ''),
    (51, 'IOR45A/RPLL2_T_in', 3, 'FT_BE2', 'U6 BE_2 (pin 6)', ''),
    (52, 'IOR39A/SCLK', 3, 'FT_BE3', 'U6 BE_3 (pin 7)', 'SSPI pin: enable "SSPI as regular IO"'),
    (53, 'IOR38B/DOUT/WE_N', 3, 'FT_SCL', 'U6 SCL (pin 17)', 'FT602 is I2C master, FPGA is slave (AN_434 map)'),
    (54, 'IOR38A/DIN/CLKHOLD_N', 3, 'FT_SDA', 'U6 SDA (pin 18)', 'SSPI pin: enable "SSPI as regular IO"'),
    (55, 'IOR36B/SSPI_CS_N/D0', 3, 'FT_INT_N', 'U6 INT_N (pin 16)', 'SSPI pin: enable "SSPI as regular IO"'),
    (56, 'IOR36A/SO/D1', 3, 'FT_RESET_N', 'U6 RESET_N (pin 15)', '10k pull-up + 100n: FT602 runs even if FPGA blank'),
    (57, 'IOR35A/FASTRD_N/D3', 3, 'TVP_SDA', 'U9 SDA (pin 22)', 'FASTRD_N strap: I2C pull-up keeps it high (normal read)'),
    (63, 'IOR29A/GCLKT_3', 3, 'TVP_SCL', 'U9 SCL (pin 21)', 'FPGA is I2C master for TVP5150'),
    (87, 'IOR30B/MODE1', 3, 'LED_STATUS', 'status LED (330R)', 'MODE1 strap: 1k pull-down (as Tang Nano 20K)'),
    (88, 'IOR30A/MODE0', 3, 'TVP_RESETB', 'U9 RESETB (pin 8)', 'MODE0 strap: 1k pull-down holds TVP in reset during config'),
    # bank 1 (top)
    (69, 'IOT50A', 1, 'FT_D23', 'U6 DATA_23 (pin 67)', ''),
    (70, 'IOT44B', 1, 'FT_D22', 'U6 DATA_22 (pin 66)', ''),
    (71, 'IOT44A', 1, 'FT_D21', 'U6 DATA_21 (pin 65)', ''),
    (72, 'IOT40B', 1, 'FT_D20', 'U6 DATA_20 (pin 64)', ''),
    (73, 'IOT40A', 1, 'FT_D19', 'U6 DATA_19 (pin 63)', ''),
    (74, 'IOT34B', 1, 'FT_D18', 'U6 DATA_18 (pin 62)', ''),
    (75, 'IOT34A', 1, 'FT_D17', 'U6 DATA_17 (pin 61)', ''),
    (76, 'IOT30B/GCLKC_1', 1, 'FT_D16', 'U6 DATA_16 (pin 60)', ''),
    (77, 'IOT30A/GCLKT_1', 1, 'FT_CLK', 'U6 CLK (pin 58) via 33R', '100 MHz FIFO clock, global clock pin'),
    # bank 0 (top)
    (79, 'IOT27B/GCLKC_0', 0, 'FT_D24', 'U6 DATA_24 (pin 69)', ''),
    (80, 'IOT27A/GCLKT_0', 0, 'FT_D25', 'U6 DATA_25 (pin 70)', ''),
    (81, 'IOT17B', 0, 'FT_D26', 'U6 DATA_26 (pin 71)', ''),
    (82, 'IOT17A', 0, 'FT_D27', 'U6 DATA_27 (pin 72)', ''),
    (83, 'IOT6B', 0, 'FT_D28', 'U6 DATA_28 (pin 73)', ''),
    (84, 'IOT6A', 0, 'FT_D29', 'U6 DATA_29 (pin 74)', ''),
    (85, 'IOT4B', 0, 'FT_D30', 'U6 DATA_30 (pin 75)', ''),
    (86, 'IOT4A', 0, 'FT_D31', 'U6 DATA_31 (pin 76)', ''),
    # dedicated-function pins kept for configuration
    (5, 'IOR25B/TMS', 2, 'JTAG_TMS', 'JTAG header', 'Reserved for JTAG'),
    (6, 'IOR26A/TCK', 2, 'JTAG_TCK', 'JTAG header', 'Reserved for JTAG, 4.7k pull-down'),
    (7, 'IOR26B/TDI', 2, 'JTAG_TDI', 'JTAG header', 'Reserved for JTAG'),
    (8, 'IOR25A/TDO', 2, 'JTAG_TDO', 'JTAG header', 'Reserved for JTAG'),
    (9, 'IOR31B/RECONFIG_N', 3, 'RECONFIG_N', 'RECONFIG button + 4.7k pull-up', 'Reserved'),
    (59, 'IOR34B/MCLK/D4', 3, 'MSPI_CLK', 'U5 W25Q64 CLK', 'Config flash, 1k pull-down'),
    (60, 'IOR34A/MCS_N/D5', 3, 'MSPI_CS_N', 'U5 W25Q64 /CS', 'Config flash, 4.7k pull-up'),
    (61, 'IOR33B/MO/D6', 3, 'MSPI_MOSI', 'U5 W25Q64 DI', 'Config flash'),
    (62, 'IOR33A/MI/D7', 3, 'MSPI_MISO', 'U5 W25Q64 DO', 'Config flash'),
]
FPGA_POWER = [
    (1, 'VCC', 'power_in', '+1V0'), (22, 'VCC', 'power_in', '+1V0'), (45, 'VCC', 'power_in', '+1V0'),
    (66, 'VCC', 'power_in', '+1V0'), (14, 'VCCPLLL1', 'power_in', 'VCCPLLL'), (50, 'VCCPLLR1', 'power_in', 'VCCPLLR'),
    (3, 'VCCX/VCCIO2/6/7', 'power_in', '+3V3'), (12, 'VCCX/VCCIO2/6/7', 'power_in', '+3V3'),
    (64, 'VCCX/VCCIO2/6/7', 'power_in', '+3V3'), (78, 'VCCIO0', 'power_in', '+3V3'),
    (67, 'VCCIO1', 'power_in', '+3V3'), (58, 'VCCIO3', 'power_in', '+3V3'), (44, 'VCCIO4', 'power_in', '+3V3'),
    (23, 'VCCIO5', 'power_in', '+3V3'), (47, 'EXTR', 'passive', 'FPGA_EXTR'),
    (2, 'VSS', 'power_in', 'GND'), (21, 'VSS', 'power_in', 'GND'), (24, 'VSS', 'power_in', 'GND'),
    (43, 'VSS', 'power_in', 'GND'), (46, 'VSS', 'power_in', 'GND'), (65, 'VSS', 'power_in', 'GND'),
    (68, 'VSS', 'power_in', 'GND'), (89, 'EPAD', 'power_in', 'GND'),
]


# Symbol row layouts. Left/right row i of one symbol lines up with row i of the part it faces, so the
# FPGA <-> FT602 and FPGA <-> TVP5150 buses are drawn as straight wires.
FPGA_LEFT = [20, 19, 18, 17, 16, 15, 13, 11, None, 10, None, 88, 63, 57] + [None] * 12 + \
            [4, None, None, 87] + [None] * 6 + [60, 59, 61, 62] + [None] * 5 + [9] + [None] * 5 + [6, 7, 8, 5]
FPGA_RIGHT = [53, 54, 55, None, 77, 41, 42, None, 48, 49, 51, 52, None] + list(range(25, 41)) + \
             list(range(76, 68, -1)) + list(range(79, 87)) + [56]
FPGA_TOP = [1, 22, 45, 66, None, None, 14, None, None, 50, None, None, 3, 12, 64, 78, 67, 58, 44, 23]
FPGA_BOTTOM = [2, 21, 24, 43, 46, 65, 68, 89, None, 47]


def fpga_symbol():
    io = {p: (p, n, 'bidirectional') for p, n, *_ in FPGA_IO}
    io.update({p: (p, n, t) for p, n, t, _ in FPGA_POWER})
    side = lambda pins: [io[p] if p else None for p in pins]  # noqa: E731
    used = [p for p in FPGA_LEFT + FPGA_RIGHT + FPGA_TOP + FPGA_BOTTOM if p]
    assert sorted(used) == sorted(io) and len(used) == len(set(used)), 'FPGA symbol pins incomplete'
    return make_symbol('GW2AR-LV18QN88', side(FPGA_LEFT), side(FPGA_RIGHT), side(FPGA_TOP), side(FPGA_BOTTOM),
                       ref='U', value='GW2AR-LV18QN88C8/I7',
                       footprint='Package_DFN_QFN:ArtInChip_QFN-88-1EP_10x10mm_P0.4mm_EP6.74x6.74mm',
                       datasheet='https://www.gowinsemi.com (UG115 GW2AR-18 pinout, UG229 package)',
                       description='Gowin GW2AR-18 FPGA with 64 Mbit SDR SDRAM, QN88')


FT_PINS = {
    **{40 + i: (f'DATA_{i}', 'input') for i in range(8)},
    **{50 + i: (f'DATA_{8 + i}', 'bidirectional') for i in range(8)},
    **{60 + i: (f'DATA_{16 + i}', 'input') for i in range(8)},
    **{69 + i: (f'DATA_{24 + i}', 'input') for i in range(8)},
    4: ('BE_0', 'bidirectional'), 5: ('BE_1', 'bidirectional'), 6: ('BE_2', 'bidirectional'),
    7: ('BE_3', 'bidirectional'), 8: ('TXE_N', 'output'), 9: ('RXF_N', 'output'), 10: ('RESERVED1', 'input'),
    11: ('WR_N', 'input'), 12: ('RESERVED2', 'input'), 13: ('RESERVED3', 'input'), 15: ('RESET_N', 'input'),
    16: ('INT_N', 'input'), 17: ('SCL', 'bidirectional'), 18: ('SDA', 'bidirectional'),
    19: ('RESERVED4', 'no_connect'), 58: ('CLK', 'output'), 21: ('XI', 'input'), 22: ('XO', 'output'),
    23: ('DP', 'bidirectional'), 25: ('DM', 'bidirectional'), 27: ('RREF', 'passive'), 31: ('TODN', 'output'),
    32: ('TODP', 'output'), 34: ('RIDN', 'input'), 35: ('RIDP', 'input'), 37: ('VBUS', 'input'),
    20: ('VCC33', 'power_in'), 24: ('VCC33', 'power_in'), 38: ('VCC33', 'power_in'), 28: ('VDDA', 'power_in'),
    14: ('VCCIO', 'power_in'), 49: ('VCCIO', 'power_in'), 59: ('VCCIO', 'power_in'), 68: ('VCCIO', 'power_in'),
    39: ('DV10', 'power_out'), 3: ('VD10', 'power_in'), 30: ('VD10', 'power_in'), 33: ('VD10', 'power_in'),
    48: ('VD10', 'power_in'), 2: ('AVDD', 'power_in'), 1: ('GND', 'power_in'), 26: ('GND', 'power_in'),
    29: ('GND', 'power_in'), 36: ('GND', 'power_in'), 77: ('EP/GND', 'power_in'),
}
assert sorted(FT_PINS) == list(range(1, 78)), 'FT602 pin table incomplete'

FT_LEFT = [17, 18, 16, None, 58, 8, 11, None, 4, 5, 6, 7, None] + list(range(40, 48)) + list(range(50, 58)) + \
          list(range(60, 68)) + list(range(69, 77)) + [15]
FT_RIGHT = [25, 23, None, None, None, 31, 32, None, 34, 35, None, None, 37, None, None, None, None, 27, None, None,
            9, 10, 12, 13, 19, None, None, 21, 22]
FT_TOP = [20, 24, 38, 28, 14, 49, 59, 68, None, 39, 3, 30, 33, 48, 2]
FT_BOTTOM = [1, 26, 29, 36, 77]


def ft602_symbol():
    side = lambda pins: [(n, *FT_PINS[n]) if n else None for n in pins]  # noqa: E731
    used = [p for p in FT_LEFT + FT_RIGHT + FT_TOP + FT_BOTTOM if p]
    assert sorted(used) == list(range(1, 78)), 'FT602 symbol pins incomplete'
    return make_symbol('FT602Q', side(FT_LEFT), side(FT_RIGHT), side(FT_TOP), side(FT_BOTTOM),
                       ref='U', value='FT602Q-B-T',
                       footprint='Package_DFN_QFN:QFN-76-1EP_9x9mm_P0.4mm_EP5.81x6.31mm',
                       datasheet='https://ftdichip.com/products/ft602q/',
                       description='FTDI FT602 USB 3.1 Gen1 UVC bridge, 32-bit FIFO, QFN-76')


TVP_PINS = {1: ('AIP1A', 'input'), 2: ('AIP1B', 'input'), 3: ('PLL_AGND', 'power_in'), 4: ('PLL_AVDD', 'power_in'),
            5: ('XTAL1/OSC', 'input'), 6: ('XTAL2', 'output'), 7: ('AGND', 'power_in'), 8: ('RESETB', 'input'),
            9: ('SCLK', 'output'), 10: ('IO_DVDD', 'power_in'), 11: ('YOUT7/I2CSEL', 'bidirectional'),
            12: ('YOUT6', 'output'), 13: ('YOUT5', 'output'), 14: ('YOUT4', 'output'), 15: ('YOUT3', 'output'),
            16: ('YOUT2', 'output'), 17: ('YOUT1', 'output'), 18: ('YOUT0', 'output'), 19: ('DGND', 'power_in'),
            20: ('DVDD', 'power_in'), 21: ('SCL', 'bidirectional'), 22: ('SDA', 'bidirectional'),
            23: ('FID/GLCO', 'output'), 24: ('VSYNC/PALI', 'output'), 25: ('HSYNC', 'output'), 26: ('AVID', 'output'),
            27: ('INTREQ/GPCL/VBLK', 'output'), 28: ('PDN', 'input'), 29: ('REFP', 'passive'),
            30: ('REFM', 'passive'), 31: ('CH_AGND', 'power_in'), 32: ('CH_AVDD', 'power_in')}


TVP_LEFT = [1, 2, None, None, None, None, None, 29, None, None, 30, None, None, None, None, 28, None, None, 5, 6]
TVP_RIGHT = list(range(11, 19)) + [None, 9, None, 8, 21, 22, None, 23, 24, 25, 26, 27]
TVP_TOP = [32, 4, None, 20, None, None, 10]
TVP_BOTTOM = [31, 3, 7, 19]


def tvp_symbol():
    side = lambda pins: [(n, *TVP_PINS[n]) if n else None for n in pins]  # noqa: E731
    used = [p for p in TVP_LEFT + TVP_RIGHT + TVP_TOP + TVP_BOTTOM if p]
    assert sorted(used) == list(range(1, 33)), 'TVP5150 symbol pins incomplete'
    return make_symbol('TVP5150AM1PBS', side(TVP_LEFT), side(TVP_RIGHT), side(TVP_TOP), side(TVP_BOTTOM),
                       ref='U', value='TVP5150AM1PBS', footprint='Package_QFP:TQFP-32_7x7mm_P0.8mm',
                       datasheet='https://www.ti.com/lit/ds/symlink/tvp5150am1.pdf',
                       description='TI NTSC/PAL/SECAM video decoder, BT.656 output, TQFP-32')


# ============================================================== helpers
REFS = {}


def ref(prefix):
    REFS[prefix] = REFS.get(prefix, 0) + 1
    return f'{prefix}{REFS[prefix]}'


def cfp(v):
    return FP_C0805 if v in ('10u', '22u') else FP_C0603 if v in ('4.7u', '1u') else FP_C


def offsets(sym):
    """Pin number -> (dx, dy) on the sheet for a symbol placed at the origin, unrotated."""
    return {p['num']: (p['x'], -p['y']) for p in symbol_pins(sym)}


Y0 = 120.65  # sheet y of row 0 of the three big symbols


def row(i):
    return round(Y0 + i * 2.54, 3)


# ============================================================== schematic
def build():
    fpga_sym, ft_sym, tvp_sym = fpga_symbol(), ft602_symbol(), tvp_symbol()
    io_net = {str(p): net for p, _, _, net, *_ in FPGA_IO}
    U = {k: ref('U') for k in ('3v3', '1v0', '1v8', 'fpga', 'flash', 'ft', 'tpd', 'usblc', 'tvp')}
    s = Sheet('5150UVC - composite video to USB3 UVC', '5150UVC.kicad_sch', paper='A2')

    # ---------------------------------------------------------- part helpers
    def h2(lib, pre, val, x, y, fp, lab='above'):
        """Horizontal two-pin part centred at (x, y). Returns (left pin, right pin)."""
        rp, vp = ((x, y - 3.9), (x, y - 2.3)) if lab == 'above' else ((x, y + 2.3), (x, y + 3.9))
        p = s.place(lib, ref(pre), val, x, y, rot=90, footprint=fp, ref_pos=rp, val_pos=vp,
                    ref_just=None, val_just=None)
        return p['1'], p['2']

    def v2(lib, pre, val, x, y1, fp, lab='right', half=3.81):
        """Vertical two-pin part with pin 1 (top) at (x, y1). Returns (top pin, bottom pin)."""
        cy = y1 + half
        dx, j = (1.8, 'left') if lab == 'right' else (-1.8, 'right')
        p = s.place(lib, ref(pre), val, x, cy, footprint=fp, ref_pos=(x + dx, cy - 0.9), val_pos=(x + dx, cy + 0.9),
                    ref_just=j, val_just=j)
        return p['1'], p['2']

    def R_h(val, x, y, lab='above', fp=FP_R):
        return h2('Device:R', 'R', val, x, y, fp, lab)

    def C_h(val, x, y, lab='above'):
        return h2('Device:C', 'C', val, x, y, cfp(val), lab)

    def R_v(val, x, y1, lab='right', fp=FP_R):
        return v2('Device:R', 'R', val, x, y1, fp, lab)

    def C_v(val, x, y1, lab='right'):
        return v2('Device:C', 'C', val, x, y1, cfp(val), lab)

    def FB_h(val, x, y, lab='below'):
        return h2('Device:FerriteBead_Small', 'FB', val, x, y, FP_FB, lab)

    def pull(net, x, y_line, y_node, val, to, lab=None):
        """Tee off a signal at (x, y_line), run to y_node, then a horizontal resistor to a supply/GND symbol."""
        a, b = R_h(val, x + 3.81, y_node, lab or 'above')
        s.route(net, (x, y_line), a)
        if to == 'GND':
            s.sym_at(to, b)
        else:
            tail(to, b)

    def tail(net, pin, dx=2.54):
        """Short wire out of a horizontal part's pin to an upright supply symbol, clear of the part's labels."""
        end = (pin.x + dx, pin.y)
        s.route(net, pin, end)
        s.sym_at(net, end)

    def bank(net, x, y, vals, title=None, step=10.16):
        """Row of decoupling caps between a +V rail and a GND rail."""
        tops, bots = zip(*[C_v(v, x + i * step, y) for i, v in enumerate(vals)])
        s.route(net, *tops)
        s.route('GND', *bots)
        s.sym_at(net, tops[0])
        s.sym_at('GND', bots[0])
        if title:
            s.text(title, x - 2.54, y - 9, 1.27)

    # ---------------------------------------------------------- the three big parts
    X_TL = 111.76
    tvp = s.place('Custom:TVP5150AM1PBS', U['tvp'], 'TVP5150AM1PBS', X_TL - offsets(tvp_sym)['1'][0], Y0,
                  custom=tvp_sym, nets={'23': None, '24': None, '25': None, '26': None})
    X_TR = tvp['11'].x
    X_FL = X_TR + 111.76
    fpga = s.place('Custom:GW2AR-LV18QN88', U['fpga'], 'GW2AR-LV18QN88C8/I7',
                   X_FL - offsets(fpga_sym)['20'][0], Y0, custom=fpga_sym)
    X_FR = fpga['53'].x
    X_TL2 = X_FR + 66.04
    ft = s.place('Custom:FT602Q', U['ft'], 'FT602Q-B-T', X_TL2 - offsets(ft_sym)['17'][0], Y0, custom=ft_sym,
                 nets={'19': None})
    X_TR2 = ft['25'].x
    assert fpga['20'].y == ft['17'].y == tvp['11'].y == Y0

    # ---------------------------------------------------------- TVP5150 -> FPGA (BT.656 bus, I2C, reset)
    for i in range(8):
        s.route(io_net[str(FPGA_LEFT[i])], tvp[str(TVP_RIGHT[i])], fpga[str(FPGA_LEFT[i])])
    a, b = R_h('22R', X_TR + 12.7, row(9))
    s.route('TVP_SCLK_SRC', tvp['9'], a)
    s.route('TVP_SCLK', b, fpga['10'])
    s.route('TVP_RESETB', tvp['8'], fpga['88'])
    s.route('TVP_SCL', tvp['21'], fpga['63'])
    s.route('TVP_SDA', tvp['22'], fpga['57'])
    pull('TVP_SDA', X_TR + 25.4, row(13), row(16), '2.2k', '+3V3')
    pull('TVP_SCL', X_TR + 45.72, row(12), row(19), '2.2k', '+3V3')
    pull('TVP_RESETB', X_TR + 66.04, row(11), row(22), '1k', 'GND')
    pull('TVP_YOUT7', X_TR + 91.44, row(0), row(-4), '10k', '+3V3')
    a, b = R_h('10k', X_TR + 7.62, row(19), 'below')
    s.route('TVP_INTREQ', tvp['27'], a)
    s.sym_at('GND', b)
    s.text('YOUT7/I2CSEL pull-up:\nI2C address 0xBA', X_TR + 82, row(-10.5), 1.27)
    s.text('MODE0 strap (1k):\nTVP5150 in reset until\nthe FPGA is configured', X_TR + 76, row(21.2), 1.27)
    s.text('INTREQ/VBLK must not float', X_TR + 2, row(21.5), 1.27)
    s.text('SCLK 27 MHz to\na global clock\npin (22R series)', X_TR + 3, row(14.6), 1.27)

    # ---------------------------------------------------------- TVP5150 analog side
    s.text('COMPOSITE VIDEO INPUT', 25, 70, 2.5, bold=True)
    s.text('75R termination split 37.4R + 37.4R gives a 2:1 pad (TVP5150 input max 0.75 Vpp).\n'
           'TI recommends an anti-aliasing low-pass filter (~6 MHz) before the coupling cap: not fitted.', 25, 76, 1.27)
    xj = X_TL - 91.44
    j = s.place('Connector:Conn_Coaxial', ref('J'), 'RCA (composite)', xj, row(0), mirror=True, nets={'2': 'GND'},
                footprint='', ref_pos=(xj - 4, row(0) - 5), val_pos=(xj - 4, row(0) - 3.4), ref_just='left',
                val_just='left')
    xd = X_TL - 76.2
    d = s.place('Device:D_TVS', ref('D'), 'TPD1E10B06', xd, row(0) + 3.81, rot=90,
                footprint='Diode_SMD:D_0402_1005Metric', ref_pos=(xd + 4, row(0) + 3),
                val_pos=(xd + 7.5, row(0) + 4.6), ref_just=None, val_just=None)
    s.sym_at('GND', d['1'])
    ra, rb = R_h('37.4R 1%', X_TL - 63.5, row(0))
    st, sb = R_v('37.4R 1%', X_TL - 50.8, row(0))
    s.sym_at('GND', sb)
    ca, cb = C_h('100n', X_TL - 38.1, row(0))
    s.route('VIDEO_IN', j['1'], d['2'], ra)
    s.route('VIDEO_ATT', rb, st, ca)
    s.route('TVP_AIP1A', cb, tvp['1'])
    ct, cbt = C_v('100n', X_TL - 7.62, row(1))
    s.route('TVP_AIP1B', tvp['2'], ct)
    s.sym_at('GND', cbt)
    # ADC references
    qa, qb = C_v('1u', X_TL - 7.62, row(7))
    ma, mb = C_v('1u', X_TL - 15.24, row(10))
    pa, pb = C_v('1u', X_TL - 22.86, row(7), lab='left')
    s.route('TVP_REFP', tvp['29'], qa, pa)
    s.route('TVP_REFM', tvp['30'], qb, ma)
    s.sym_at('GND', mb)
    s.sym_at('GND', pb)
    # PDN: always on
    a, b = R_h('10k', X_TL - 30.48, row(15))
    s.route('TVP_PDN', tvp['28'], b)
    tail('+3V3', a, -2.54)
    # 14.31818 MHz crystal
    x1, x2, xc, yc = X_TL - 25.4, X_TL - 17.78, X_TL - 21.59, row(23)
    y = s.place('Device:Crystal_GND24', ref('Y'), '14.31818MHz', xc, yc, nets={'2': 'GND', '4': 'GND'},
                footprint='Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm', ref_pos=(x1 - 2, yc - 0.8),
                val_pos=(x1 - 2, yc + 0.8), ref_just='right', val_just='right')
    rr1, rr2 = R_h('100k', xc, row(28), 'below')
    c1t, c1b = C_v('27p', x1, row(31), lab='left')
    c2t, c2b = C_v('27p', x2, row(31))
    s.route('TVP_XTAL1', tvp['5'], (x1, row(18)), y['1'], rr1, c1t)
    s.route('TVP_XTAL2', tvp['6'], (x2, row(19)), y['3'], rr2, c2t)
    s.sym_at('GND', c1b)
    s.sym_at('GND', c2b)
    s.text('14.31818 MHz, CL 18 pF\n(27p each side)', x1 - 26, row(36.5), 1.27)
    # supplies
    ytop = tvp['32'].y - 5.08
    caps = [C_v(v, X_TL - 5.08 - 7.62 * i, ytop) for i, v in enumerate(['100n', '100n', '1u'])]
    fa, fb = FB_h('600R@100MHz', X_TL - 30.48, ytop)
    s.route('+1V8A', tvp['32'], (tvp['32'].x, ytop))
    s.route('+1V8A', tvp['4'], (tvp['4'].x, ytop), (tvp['32'].x, ytop), *[c[0] for c in caps], fb)
    s.route('GND', *[c[1] for c in caps])
    s.sym_at('GND', caps[-1][1])
    s.sym_at('+1V8', fa)
    s.pwr_flag(X_TL - 24.13, ytop)
    s.text('Analog 1V8 (CH_AVDD, PLL_AVDD)', X_TL - 36, ytop - 9, 1.27)
    s.stub_power('+1V8', tvp['20'])
    s.stub_power('+3V3', tvp['10'])
    s.route('GND', *[tvp[n] for n in ('31', '3', '7', '19')])
    s.sym_at('GND', tvp['3'])

    # ---------------------------------------------------------- FPGA supplies
    top = lambda nums: [fpga[str(n)] for n in nums]  # noqa: E731
    s.route('+1V0', *top([1, 22, 45, 66]))
    s.sym_at('+1V0', fpga['1'])
    s.route('+3V3', *top([3, 12, 64, 78, 67, 58, 44, 23]))
    s.sym_at('+3V3', fpga['3'])
    y_pll = fpga['14'].y - 17.78
    for pin, net, sgn in ((fpga['14'], 'VCCPLLL', -1), (fpga['50'], 'VCCPLLR', 1)):
        caps = [C_v(v, pin.x + sgn * (22.86 + 7.62 * i), y_pll) for i, v in enumerate(['100n', '4.7u'])]
        fa, fb = FB_h('120R@100MHz', pin.x + sgn * 45.72, y_pll)
        s.route(net, pin, (pin.x, y_pll), *[c[0] for c in caps], fb if sgn < 0 else fa)
        s.route('GND', *[c[1] for c in caps])
        s.sym_at('GND', caps[0][1])
        s.sym_at('+1V0', fa if sgn < 0 else fb)
        s.pwr_flag(pin.x + sgn * 12.7, y_pll)
        s.text(f'{net}1 filter', pin.x + sgn * 26 - (12 if sgn < 0 else 0), y_pll - 9, 1.27)
    s.route('GND', *top([2, 21, 24, 43, 46, 65, 68, 89]))
    s.sym_at('GND', fpga['43'])
    a, b = R_v('10k 1%', fpga['47'].x, fpga['47'].y + 2.54)
    s.route('FPGA_EXTR', fpga['47'], a)
    s.sym_at('GND', b)

    # ---------------------------------------------------------- FPGA: clock, LED, flash, reconfig, JTAG
    xo = X_FL - 60.96
    osc = s.place('Oscillator:ASE-xxxMHz', ref('X'), '27MHz', xo, row(26), nets={'2': 'GND'},
                  footprint='Oscillator:Oscillator_SMD_Abracon_ASE-4Pin_3.2x2.5mm',
                  ref_pos=(xo + 3.5, row(28) + 0.4), val_pos=(xo + 3.5, row(28) + 2), ref_just='left',
                  val_just='left')
    ct, cb = C_v('100n', xo - 15.24, row(23), lab='left')
    s.route('+3V3', osc['1'], (xo - 10.16, row(26)), (xo - 10.16, row(23)), osc['4'])
    s.route('+3V3', (xo - 10.16, row(23)), ct)
    s.sym_at('+3V3', osc['4'])
    s.sym_at('GND', cb)
    a, b = R_h('22R', X_FL - 43.18, row(26))
    s.route('OSC_27M', osc['3'], a)
    s.route('SYS_CLK', b, fpga['4'])
    s.text('27 MHz\nsystem clock', xo + 3.5, row(30.4), 1.27)

    pt, pb = R_v('1k', X_FL - 7.62, row(29))
    ra, rb = R_h('330R', X_FL - 20.32, row(29), 'below')
    led = s.place('Device:LED_Small', ref('D'), 'green', X_FL - 30.48, row(29),
                  footprint='LED_SMD:LED_0603_1608Metric', ref_pos=(X_FL - 30.48, row(29) + 2.3),
                  val_pos=(X_FL - 30.48, row(29) + 3.9), ref_just=None, val_just=None)
    s.route('LED_STATUS', fpga['87'], pt, rb)
    s.route('LED_A', ra, led['2'])
    s.stub_power('GND', led['1'])
    s.sym_at('GND', pb)
    s.text('MODE1 strap', X_FL - 6, row(33.2), 1.27)

    xf = X_FL - 73.66
    fl = s.place('Memory_Flash:W25Q128JVS', U['flash'], 'W25Q64JVSSIQ', xf, row(39), mirror=True,
                 nets={'8': '+3V3', '4': 'GND'}, footprint='Package_SO:SOIC-8_5.3x5.3mm_P1.27mm',
                 ref_pos=(xf - 2.5, row(45.3)), val_pos=(xf - 2.5, row(45.3) + 1.6), ref_just='left',
                 val_just='left')  # mirrored: renders right-justified
    a, b = R_v('4.7k', X_FL - 12.7, row(32), lab='left')
    s.route('MSPI_CS_N', fl['1'], (X_FL - 12.7, row(36)), fpga['60'])
    s.route('MSPI_CS_N', (X_FL - 12.7, row(36)), b)
    s.sym_at('+3V3', a)
    a, b = R_v('1k', X_FL - 20.32, row(40))
    s.route('MSPI_CLK', fl['6'], (X_FL - 20.32, row(37)), fpga['59'])
    s.route('MSPI_CLK', (X_FL - 20.32, row(37)), a)
    s.sym_at('GND', b)
    s.route('MSPI_MOSI', fl['5'], fpga['61'])
    s.route('MSPI_MISO', fl['2'], fpga['62'])
    a, b = R_h('10k', X_FL - 49.53, row(44))
    s.route('FLASH_WP_N', fl['3'], (X_FL - 53.34, row(40)), a)
    tail('+3V3', b)
    a, b = R_h('10k', X_FL - 54.61, row(47))
    s.route('FLASH_HOLD_N', fl['7'], (X_FL - 58.42, row(41)), a)
    tail('+3V3', b)
    s.text('Config flash\n(MSPI boot)', xf - 25, row(35), 1.27)

    sw = s.place('Switch:SW_Push', ref('SW'), 'RECONFIG', X_FL - 30.48, row(45),
                 footprint='Button_Switch_SMD:SW_SPST_TL3342', ref_pos=(X_FL - 30.48, row(45) - 3.9),
                 val_pos=(X_FL - 30.48, row(45) - 2.3), ref_just=None, val_just=None)
    s.route('RECONFIG_N', sw['2'], (X_FL - 12.7, row(45)), fpga['9'])
    pull('RECONFIG_N', X_FL - 12.7, row(45), row(48), '4.7k', '+3V3', 'below')
    s.stub_power('GND', sw['1'])

    xjt = X_FL - 55.88
    jt = s.place('Connector_Generic:Conn_01x06', ref('J'), 'JTAG', xjt, row(52), mirror=True,
                 nets={'1': '+3V3', '6': 'GND'},
                 footprint='Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical',
                 ref_pos=(xjt - 2, row(49)), val_pos=(xjt - 2, row(57)), ref_just=None, val_just=None)
    s.route('JTAG_TCK', jt['2'], (X_FL - 12.7, row(51)), fpga['6'])
    a, b = R_v('4.7k', X_FL - 12.7, row(56))
    s.route('JTAG_TCK', (X_FL - 12.7, row(51)), a)
    s.sym_at('GND', b)
    s.route('JTAG_TDI', jt['3'], fpga['7'])
    s.route('JTAG_TDO', jt['4'], fpga['8'])
    s.route('JTAG_TMS', jt['5'], fpga['5'])
    s.text('JTAG: 1 3V3, 2 TCK, 3 TDI,\n4 TDO, 5 TMS, 6 GND', xjt - 30, row(52), 1.27)

    # ---------------------------------------------------------- FPGA <-> FT602 (245 sync FIFO, I2C, reset)
    for fpin, tpin in zip(FPGA_RIGHT, FT_LEFT):
        assert (fpin is None) == (tpin is None)
        if fpin in (None, 77):
            continue
        s.route(io_net[str(fpin)], fpga[str(fpin)], ft[str(tpin)])
    a, b = R_h('33R', X_TL2 - 10.16, row(4))
    s.route('FT_CLK', fpga['77'], a)
    s.route('FT_CLK_SRC', b, ft['58'])
    pull('FT_SCL', X_FR + 15.24, row(0), row(-3), '2.2k', '+3V3')
    pull('FT_SDA', X_FR + 30.48, row(1), row(-6), '2.2k', '+3V3')
    pull('FT_INT_N', X_FR + 45.72, row(2), row(-9), '10k', '+3V3')
    xr = X_TL2 - 20.32
    pull('FT_RESET_N', xr, row(45), row(48), '10k', '+3V3')
    a, b = C_v('100n', xr, row(48), lab='left')
    s.join('FT_RESET_N', a)
    s.sym_at('GND', b)
    s.text('FT602 is I2C master (FPGA = slave,\nregister map in FTDI AN_434)', X_FR + 4, row(-13.5), 1.27)
    s.text('100 MHz FIFO clock, series\ntermination at the FT602', X_TL2 - 30, row(6.4), 1.27)
    s.text('FT602 runs even with\nthe FPGA blank', xr - 2, row(52.5), 1.27)

    # ---------------------------------------------------------- FT602 supplies
    s.route('+3V3', *[ft[n] for n in ('20', '24', '38', '28', '14', '49', '59', '68')])
    s.sym_at('+3V3', ft['20'])
    p1v0 = [ft[n] for n in ('39', '3', '30', '33', '48', '2')]
    y1v0 = p1v0[-1].y - 12.7
    caps = [C_v(v, p1v0[-1].x + 10.16 * (i + 1), y1v0) for i, v in enumerate(['4.7u'] + ['100n'] * 5)]
    s.route('FT_1V0', *p1v0)
    s.route('FT_1V0', p1v0[-1], (p1v0[-1].x, y1v0), *[c[0] for c in caps])
    s.route('GND', *[c[1] for c in caps])
    s.sym_at('GND', caps[0][1])
    s.text('DV10 = internal 1V0 LDO output -> VD10 / AVDD', p1v0[-1].x - 2, y1v0 - 9, 1.27)
    s.route('GND', *[ft[n] for n in ('1', '26', '29', '36', '77')])
    s.sym_at('GND', ft['29'])

    # ---------------------------------------------------------- FT602 -> USB 3 connector
    x_J = X_TR2 + 116.84
    uj = s.place('Connector:USB3_B_Micro', ref('J'), 'USB3 Micro-B', x_J, row(2), mirror=True,
                 nets={'4': None, '1': 'VBUS'}, footprint='Connector_USB:USB3_Micro-B_Connfly_DS1104-01',
                 ref_pos=(x_J - 2, row(-6)), val_pos=(x_J - 2, row(-4.6)), ref_just='left', val_just='left')
    s.route('GND', uj['SH'], uj['8'], uj['5'])
    s.sym_at('GND', uj['5'])
    x_u = X_TR2 + 25.4
    ul = s.place('Power_Protection:USBLC6-2SC6', U['usblc'], 'USBLC6-2SC6', x_u, row(0),
                 ref_pos=(x_u + 3, row(-3.4)), val_pos=(x_u + 3, row(-2.4)), ref_just='left', val_just='left')
    s.sym_at('VBUS', ul['5'])
    s.sym_at('GND', ul['2'])
    s.route('FT_DM', ft['25'], ul['1'])
    s.route('USB_DM', ul['6'], uj['2'])
    s.route('FT_DP', ft['23'], ul['3'])
    s.route('USB_DP', ul['4'], uj['3'])
    na, nb = C_h('100n', X_TR2 + 12.7, row(5))
    pa, pb = C_h('100n', X_TR2 + 22.86, row(6), 'below')
    s.route('FT_TX_N', ft['31'], na)
    s.route('FT_TX_P', ft['32'], pa)
    ca, cb, xt = X_TR2 + 38.1, X_TR2 + 33.02, X_TR2 + 58.42
    cc, cd = X_TR2 + 76.2, X_TR2 + 81.28
    tp = s.place('Power_Protection:TPD4EUSB30', U['tpd'], 'TPD4EUSB30', xt, row(15),
                 nets={'3': 'GND', '8': 'GND', '6': None, '7': None, '9': None, '10': None},
                 ref_pos=(xt + 3, row(20.5)), val_pos=(xt + 3, row(21.5)), ref_just='left', val_just='left')
    s.route('USB_SSTX_N', nb, (ca, row(5)), (X_TR2 + 86.36, row(5)), (X_TR2 + 86.36, row(3)), uj['6'])
    s.route('USB_SSTX_N', (ca, row(5)), (ca, row(14)), tp['1'])
    s.route('USB_SSTX_P', pb, (cb, row(6)), (X_TR2 + 88.9, row(6)), (X_TR2 + 88.9, row(4)), uj['7'])
    s.route('USB_SSTX_P', (cb, row(6)), (cb, row(16)), tp['2'])
    s.route('USB_SSRX_N', ft['34'], (cc, row(8)), (X_TR2 + 93.98, row(8)), (X_TR2 + 93.98, row(6)), uj['9'])
    s.route('USB_SSRX_N', (cc, row(8)), (cc, row(14)), tp['4'])
    s.route('USB_SSRX_P', ft['35'], (cd, row(9)), (X_TR2 + 96.52, row(9)), (X_TR2 + 96.52, row(7)), uj['10'])
    s.route('USB_SSRX_P', (cd, row(9)), (cd, row(16)), tp['5'])
    s.text('USB 3 Micro-B (device). SSTX AC-coupled at the FT602.\n'
           'Route SS pairs and D+/D- as 90R differential pairs.', X_TR2 + 40, row(-12), 1.27)
    # VBUS detect, RREF, 245-mode straps, crystal
    a, b = R_v('10k', X_TR2 + 5.08, row(12))
    ra, rb = R_h('4.7k', X_TR2 + 13.97, row(12), 'below')
    s.route('FT_VBUS_DET', ft['37'], a, ra)
    s.sym_at('GND', b)
    s.sym_at('VBUS', rb)
    a, b = R_h('1.6k 1%', X_TR2 + 7.62, row(17), 'below')
    s.route('FT_RREF', ft['27'], a)
    s.sym_at('GND', b)
    xp = X_TR2 + 12.7
    rp = s.place('Device:R_Pack04', ref('RN'), '10k', xp, row(21), rot=90,
                 footprint='Resistor_SMD:R_Array_Convex_4x0402', ref_pos=(xp + 12, row(21)),
                 val_pos=(xp + 12, row(22)), ref_just='left', val_just='left')
    for net, fpin, rpin in (('FT_RXF_N', '9', '5'), ('FT_RES1', '10', '6'), ('FT_RES2', '12', '7'),
                            ('FT_RES3', '13', '8')):
        s.route(net, ft[fpin], rp[rpin])
    s.route('+3V3', rp['4'], rp['3'], rp['2'], rp['1'])
    s.sym_at('+3V3', rp['4'])
    s.text('245 mode: RXF_N, RESERVED1-3\npulled up (DS table 3.1)', xp + 7, row(24.5), 1.27)
    xy = X_TR2 + 11.43
    yx = s.place('Device:Crystal_GND24', ref('Y'), '30MHz', xy, row(32), nets={'2': 'GND', '4': 'GND'},
                 footprint='Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm', ref_pos=(xy + 6, row(31.6)),
                 val_pos=(xy + 6, row(32.6)), ref_just='left', val_just='left')
    c1t, c1b = C_v('27p', xy - 3.81, row(36), lab='left')
    c2t, c2b = C_v('27p', xy + 3.81, row(36))
    s.route('FT_XO', ft['22'], (xy - 3.81, row(28)), yx['1'], c1t)
    s.route('FT_XI', ft['21'], (xy + 3.81, row(27)), yx['3'], c2t)
    s.sym_at('GND', c1b)
    s.sym_at('GND', c2b)

    # ---------------------------------------------------------- power
    yp = 327.66
    s.text('POWER: USB VBUS 5 V -> 3V3 buck (2 A), 1V0 buck (2 A, FPGA core), 1V8 LDO (TVP5150)', 25, yp - 25, 2.5,
           bold=True)
    s.text('Budget: FT602 ~185 mA @ 3V3 (less at SD), TVP5150 ~60 mA @ 1V8, GW2AR-18 core 100-300 mA @ 1V0.\n'
           'All rails come up together from 5 V, as on the Tang Nano 20K.', 25, yp - 18, 1.27)
    s.sym_at('VBUS', (30.48, yp))
    fa, fb = FB_h('600R@100MHz 2A', 40.64, yp)
    s.route('VBUS', (30.48, yp), fa)
    s.sym_at('+5V', fb)
    c5 = [C_v(v, 53.34 + 10.16 * i, yp) for i, v in enumerate(['10u', '100n'])]
    s.route('GND', *[c[1] for c in c5])
    s.sym_at('GND', c5[0][1])
    s.pwr_flag(68.58, yp)
    s.route('+5V', fb, *[c[0] for c in c5], (71.12, yp))

    def buck(x, net_out, rtop, rbot, sw, fbn, in_wire_from):
        u = s.place('Regulator_Switching:TLV62569DBV', U['3v3' if net_out == '+3V3' else '1v0'], 'TLV62569DBV',
                    x, yp + 2.54, nets={'2': 'GND'}, footprint='Package_TO_SOT_SMD:SOT-23-5',
                    ref_pos=(x, yp - 6.4), val_pos=(x, yp - 4.8), ref_just=None, val_just=None)
        cit, cib = C_v('10u', x - 15.24, yp, lab='left')
        s.sym_at('GND', cib)
        s.route('+5V', in_wire_from, cit, u['4'])
        s.route('+5V', u['1'], (x - 10.16, yp + 2.54), (x - 10.16, yp))
        la, lb = h2('Device:L', 'L', '2.2u', x + 15.24, yp, 'Inductor_SMD:L_1008_2520Metric', 'below')
        s.route(sw, u['3'], la)
        xo_ = x + 25.4
        t1, t2 = R_v(rtop, xo_, yp)
        b1, b2 = R_v(rbot, xo_, yp + 7.62)
        s.sym_at('GND', b2)
        s.route(fbn, u['5'], (x + 10.16, yp + 2.54), (x + 10.16, yp + 7.62), t2)
        s.join(fbn, b1)
        co = [C_v('22u', xo_ + 15.24 + 10.16 * i, yp) for i in range(2)]
        s.route('GND', *[c[1] for c in co])
        s.sym_at('GND', co[0][1])
        s.route(net_out, lb, t1, *[c[0] for c in co], (xo_ + 30.48, yp))
        s.sym_at(net_out, (xo_ + 30.48, yp))
        s.pwr_flag(x + 22.86, yp)
        return u

    buck(93.98, '+3V3', '453k 1%', '100k 1%', 'SW_3V3', 'FB_3V3', (71.12, yp))
    s.text('3V3: Vout = 0.6 V x (1 + 453k/100k)', 80, yp + 22, 1.27)
    x2b = 187.96
    s.sym_at('+5V', (x2b - 20.32, yp))
    buck(x2b, '+1V0', '100k 1%', '150k 1%', 'SW_1V0', 'FB_1V0', (x2b - 20.32, yp))
    s.text('1V0: Vout = 0.6 V x (1 + 100k/150k)', x2b - 14, yp + 22, 1.27)
    xl = 281.94
    ldo = s.place('Regulator_Linear:TLV75518PDBV', U['1v8'], 'TLV75518PDBV', xl, yp + 2.54,
                  nets={'2': 'GND', '4': None}, footprint='Package_TO_SOT_SMD:SOT-23-5',
                  ref_pos=(xl, yp - 6.4), val_pos=(xl, yp - 4.8), ref_just=None, val_just=None)
    cit, cib = C_v('1u', xl - 15.24, yp, lab='left')
    cot, cob = C_v('1u', xl + 12.7, yp)
    s.sym_at('GND', cib)
    s.sym_at('GND', cob)
    s.sym_at('+3V3', (xl - 20.32, yp))
    s.route('+3V3', (xl - 20.32, yp), cit, ldo['1'])
    s.route('+3V3', ldo['3'], (xl - 10.16, yp + 2.54), (xl - 10.16, yp))
    s.route('+1V8', ldo['5'], cot, (xl + 17.78, yp))
    s.sym_at('+1V8', (xl + 17.78, yp))
    s.text('1V8 (TVP5150 DVDD, AVDD via ferrite)', xl - 14, yp + 22, 1.27)

    # ---------------------------------------------------------- decoupling (one 100n per supply pin, at the pin)
    yd = 30.48
    s.text('DECOUPLING: place each 100n at its supply pin', 25, 14, 2.5, bold=True)
    x = 27.94
    for net, vals, title in (('+3V3', ['100n', '1u'], 'TVP5150 IO_DVDD'), ('+1V8', ['100n', '1u'], 'TVP5150 DVDD'),
                             ('+3V3', ['100n'], 'Flash'), ('+3V3', ['100n'], '27 MHz osc'),
                             ('+1V0', ['100n'] * 4 + ['4.7u', '22u'], 'FPGA VCC (1V0)'),
                             ('+3V3', ['100n'] * 8 + ['4.7u', '4.7u'], 'FPGA VCCX / VCCIO (3V3)'),
                             ('+3V3', ['10u'] + ['100n'] * 8, 'FT602 VCC33 / VDDA / VCCIO (3V3)')):
        bank(net, x, yd, vals, title)
        x += 10.16 * len(vals) + 12.7

    # ---------------------------------------------------------- notes
    s.text('5150UVC: RCA composite video -> TVP5150AM1 -> GW2AR-18 FPGA -> FT602 -> USB 3 UVC webcam', 325, 302, 2.5,
           bold=True)
    s.text('BT.656 8-bit @ 27 MHz into the FPGA. The FPGA weaves fields in its 64 Mbit SDRAM and streams YUY2\n'
           'to the FT602 (245 synchronous FIFO, 32-bit @ 100 MHz). The FT602 enumerates as UVC and tells the\n'
           'FPGA (its I2C slave) the selected format. The FPGA is I2C master to the TVP5150 on a separate bus.\n'
           'All 66 FPGA user I/O are used: see docs/pin_assignment.csv.\n'
           'Gowin settings: enable "SSPI as regular IO" and "MSPI as regular IO".', 325, 310, 1.5)
    s.text('REVIEW FLAGS (not verified from the downloaded documents)\n'
           '1. FT602 FPGA-side protocol (frame marking, I2C slave register map) is in FTDI AN_434: not downloaded.\n'
           '2. QN88 footprint is a placeholder (ArtInChip QFN-88 10x10): check pads and EP against Gowin UG229.\n'
           '3. RCA jack J1 has no footprint: pick a part (e.g. CUI RCJ-01x).\n'
           '4. Crystal load caps assume CL = 18 pF: recalculate for the parts bought.\n'
           '5. No anti-aliasing filter on the video input (TI recommends one).\n'
           '6. USBLC6 is drawn flow-through: route D+/D- into pins 1/3 and out of 6/4.', 325, 340, 1.5)

    os.makedirs(HW, exist_ok=True)
    assert (U['fpga'], U['flash'], U['ft'], U['tvp']) == ('U4', 'U5', 'U6', 'U9'), 'pin table text assumes these refs'
    s.write(os.path.join(HW, '5150UVC.kicad_sch'), 'Single sheet, fully wired. Generated by tools/design.py')
    write_symbol_lib([fpga_sym, ft_sym, tvp_sym])
    pro = os.path.join(HW, '5150UVC.kicad_pro')
    with open(pro) as f:
        d = json.load(f)
    d['sheets'] = [[s.uuid, 'Root']]
    with open(pro, 'w') as f:
        json.dump(d, f, indent=2)
    return s


def write_symbol_lib(syms):
    """Project-local 'Custom' library so the symbols can be edited and ERC finds them."""
    import copy
    from sexp import Sym, dump
    lib = [Sym('kicad_symbol_lib'), [Sym('version'), 20241209], [Sym('generator'), 'kicad_symbol_editor'],
           [Sym('generator_version'), '9.0']]
    for s in syms:
        s = copy.deepcopy(s)
        s[1] = s[1].split(':', 1)[1]
        lib.append(s)
    with open(os.path.join(HW, '5150UVC.kicad_sym'), 'w') as f:
        f.write(dump(lib) + '\n')
    with open(os.path.join(HW, 'sym-lib-table'), 'w') as f:
        f.write('(sym_lib_table\n  (version 7)\n  (lib (name "Custom")(type "KiCad")(uri "${KIPRJMOD}/5150UVC.kicad_sym")'
                '(options "")(descr "5150UVC project symbols"))\n)\n')


def write_pin_table():
    os.makedirs(DOCS, exist_ok=True)
    rows = sorted(FPGA_IO, key=lambda r: r[0])
    with open(os.path.join(DOCS, 'pin_assignment.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['FPGA pin', 'Gowin pin name', 'Bank', 'VCCIO', 'Net', 'Connects to', 'Notes'])
        for p, name, bank, net, to, note in rows:
            w.writerow([p, name, bank, '3.3 V', net, to, note])
        for p, name, _, net in sorted(FPGA_POWER):
            w.writerow([p, name, '-', '-', net, 'power', ''])
    # Gowin physical constraints, ready to drop into the FPGA project
    with open(os.path.join(DOCS, '5150uvc.cst'), 'w') as f:
        f.write('// GW2AR-LV18QN88C8/I7 pin constraints generated from docs/pin_assignment.csv\n')
        for p, name, bank, net, to, note in rows:
            if net.startswith(('JTAG_', 'MSPI_')) or net == 'RECONFIG_N':
                continue
            port = net.lower()
            if net.startswith('FT_D') and net[4:].isdigit():
                port = f'ft_d[{net[4:]}]'
            elif net.startswith('FT_BE'):
                port = f'ft_be[{net[5:]}]'
            elif net.startswith('TVP_YOUT'):
                port = f'tvp_yout[{net[8:]}]'


if __name__ == '__main__':
    build()
    write_pin_table()
    for old in ('power', 'fpga', 'ft602_usb', 'video_in'):
        p = os.path.join(HW, f'{old}.kicad_sch')
        if os.path.exists(p):
            os.remove(p)
    print('FPGA pins used:', len(FPGA_IO), 'of 66 user I/O')
