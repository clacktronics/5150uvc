"""Tiny KiCad schematic builder for a single, fully wired sheet.

Symbols are placed with `place()`, which returns their pin end points. Signals are drawn with `route()`
(orthogonal polylines) and every pin a route touches is recorded in `expected`, so the KiCad netlist can be
checked against the intended connectivity afterwards. Power pins get a short stub and a power symbol.
"""
import math
import uuid as _uuid
from collections import defaultdict, namedtuple

from sexp import Sym, dump, find, find1, lib_symbol, symbol_pins

S = Sym
GRID = 1.27
POWER_NETS = {'GND', '+3V3', '+1V0', '+1V8', '+5V', 'VBUS'}
PROJECT = '5150UVC'

Pin = namedtuple('Pin', 'ref num x y ox oy')


def uid():
    return str(_uuid.uuid4())


def snap(v):
    return round(round(v / GRID) * GRID, 4)


def font(size=1.27, bold=False):
    f = [S('font'), [S('size'), size, size]]
    if bold:
        f.append([S('bold'), S('yes')])
    return f


def effects(size=1.27, justify=None, hide=False, bold=False):
    e = [S('effects'), font(size, bold)]
    if justify:
        e.append([S('justify')] + [S(j) for j in justify.split()])
    if hide:
        e.append([S('hide'), S('yes')])
    return e


def prop(name, value, x, y, angle=0, hide=False, justify=None):
    return [S('property'), name, value, [S('at'), x, y, angle], effects(justify=justify, hide=hide)]


# ---------------------------------------------------------------- custom symbols

def make_symbol(name, left=(), right=(), top=(), bottom=(), ref='U', value=None, footprint='', datasheet='',
                description='', cw=1.1):
    """Four-sided IC symbol. Side lists hold (num, name, type) or None for a gap.

    Left/right row i sits at lib y = -i*2.54, so two symbols whose row lists match line up pin for pin when
    placed at the same y. Top/bottom pins are centred on x = 0.
    """
    n = max(len(left), len(right), 1)
    ln = lambda ps: max([len(p[1]) for p in ps if p] + [0])  # noqa: E731
    mt = math.ceil((ln(top) * cw + 2) / 2.54) * 2.54 if top else 0
    mb = math.ceil((ln(bottom) * cw + 2) / 2.54) * 2.54 if bottom else 0
    w = max((ln(left) + ln(right)) * cw + 8, (max(len(top), len(bottom)) + 1) * 2.54, 15.24)
    w = math.ceil(w / 5.08) * 5.08
    y_top = 2.54 + mt
    y_bot = -(n - 1) * 2.54 - 2.54 - mb
    items = [S('symbol'), f'{name}_1_1']
    for side, pins in (('L', left), ('R', right), ('T', top), ('B', bottom)):
        x0 = -math.floor((len(pins) - 1) / 2) * 2.54
        for i, p in enumerate(pins):
            if not p:
                continue
            num, pname, ptype = p
            if side in 'LR':
                at = [-w / 2 - 2.54 if side == 'L' else w / 2 + 2.54, -i * 2.54, 0 if side == 'L' else 180]
            else:
                at = [x0 + i * 2.54, y_top + 2.54 if side == 'T' else y_bot - 2.54, 270 if side == 'T' else 90]
            items.append([S('pin'), S(ptype), S('line'), [S('at')] + at, [S('length'), 2.54],
                          [S('name'), pname, effects()], [S('number'), str(num), effects()]])
    ymid = (y_top + y_bot) / 2
    return [S('symbol'), f'Custom:{name}', [S('pin_names'), [S('offset'), 0.762]],
            [S('exclude_from_sim'), S('no')], [S('in_bom'), S('yes')], [S('on_board'), S('yes')],
            prop('Reference', ref, 0, round(ymid + 2.54, 2)),
            prop('Value', value or name, 0, round(ymid - 2.54, 2)),
            prop('Footprint', footprint, 0, 0, hide=True),
            prop('Datasheet', datasheet, 0, 0, hide=True),
            prop('Description', description, 0, 0, hide=True),
            [S('symbol'), f'{name}_0_1',
             [S('rectangle'), [S('start'), -w / 2, y_top], [S('end'), w / 2, y_bot],
              [S('stroke'), [S('width'), 0.254], [S('type'), S('default')]], [S('fill'), [S('type'), S('background')]]]],
            items]


# ---------------------------------------------------------------- sheet

class Sheet:
    def __init__(self, title, filename, paper='A1'):
        self.title, self.filename, self.paper = title, filename, paper
        self.uuid = uid()
        self.items = []
        self.libs = {}
        self.wires = []           # [(x1, y1, x2, y2)]
        self.pin_points = []      # every placed pin end point
        self.expected = defaultdict(set)
        self.nc = set()

    def _lib(self, lib_id, custom):
        if lib_id not in self.libs:
            if custom is not None:
                self.libs[lib_id] = custom
            else:
                lib, name = lib_id.split(':')
                self.libs[lib_id] = lib_symbol(lib, name)
        return self.libs[lib_id]

    @staticmethod
    def _xf(px, py, rot, mirror):
        if mirror:
            px = -px
        r = math.radians(rot)
        return px * math.cos(r) - py * math.sin(r), -(px * math.sin(r) + py * math.cos(r))

    def place(self, lib_id, ref, value, x, y, nets=None, rot=0, mirror=False, footprint=None, custom=None,
              ref_pos=None, val_pos=None, hide_value=False, ref_just='left', val_just='left', fields=None):
        """Place a symbol. nets maps pin number -> power net name (stub + power symbol) or None (no-connect).

        Returns {pin number: Pin} with the pin end points, for routing.
        """
        nets = nets or {}
        sym = self._lib(lib_id, custom)
        x, y = snap(x), snap(y)
        is_power = ref.startswith('#')
        fa = 90 if rot in (90, 270) else 0  # field angles are stored relative to the symbol

        def lib_field(name):
            p = next(p for p in find(sym, 'property') if p[1] == name)
            fx, fy = self._xf(float(p[3][1]), float(p[3][2]), rot, mirror)
            return x + fx, y + fy

        rx, ry = ref_pos or lib_field('Reference')
        vx, vy = val_pos or lib_field('Value')
        custom_sym = lib_id.startswith('Custom:')
        rj = None if custom_sym and not ref_pos else ref_just
        vj = None if custom_sym and not val_pos else val_just
        lib_fp = next((p[2] for p in find(sym, 'property') if p[1] == 'Footprint'), '')
        node = [S('symbol'), [S('lib_id'), lib_id], [S('at'), x, y, rot]]
        if mirror:
            node.append([S('mirror'), S('y')])
        node += [[S('unit'), 1], [S('exclude_from_sim'), S('no')], [S('in_bom'), S('no' if is_power else 'yes')],
                 [S('on_board'), S('no' if is_power else 'yes')], [S('dnp'), S('no')], [S('uuid'), uid()],
                 prop('Reference', ref, round(rx, 3), round(ry, 3), fa, hide=is_power, justify=rj),
                 prop('Value', value, round(vx, 3), round(vy, 3), fa, hide=hide_value, justify=vj),
                 prop('Footprint', footprint if footprint is not None else lib_fp, x, y, hide=True),
                 prop('Datasheet', '', x, y, hide=True)]
        for k, v in (fields or {}).items():
            node.append(prop(k, v, x, y, hide=True))
        pins = {}
        for p in symbol_pins(sym):
            node.append([S('pin'), p['num'], [S('uuid'), uid()]])
            px, py = self._xf(p['x'], p['y'], rot, mirror)
            a = p['angle']
            if mirror:
                a = 180 - a
            a = (a + rot) % 360
            pin = Pin(ref, p['num'], snap(x + px), snap(y + py),
                      -round(math.cos(math.radians(a))), round(math.sin(math.radians(a))))
            pins[p['num']] = pin
            self.pin_points.append((pin.x, pin.y))
        node.append([S('instances'), [S('project'), PROJECT,
                                      [S('path'), '__PATH__', [S('reference'), ref], [S('unit'), 1]]]])
        self.items.append(node)
        done = set()
        for num, net in nets.items():
            p = pins[num]
            if (p.x, p.y) in done:
                if net is not None:
                    self.expected[net].add((ref, num))
                continue
            done.add((p.x, p.y))
            if net is None:
                self.items.append([S('no_connect'), [S('at'), p.x, p.y], [S('uuid'), uid()]])
                self.nc.add((ref, num))
            else:
                self.stub_power(net, p)
        return pins

    # ------------------------------------------------------------ wiring
    def seg(self, x1, y1, x2, y2):
        x1, y1, x2, y2 = snap(x1), snap(y1), snap(x2), snap(y2)
        if (x1, y1) == (x2, y2):
            return
        assert x1 == x2 or y1 == y2, f'non-orthogonal wire {(x1, y1, x2, y2)}'
        self.wires.append((x1, y1, x2, y2))

    def route(self, net, *pts):
        """Polyline through pts (Pin or (x, y)); Pins are recorded as members of net."""
        xy = []
        for p in pts:
            if isinstance(p, Pin):
                self.expected[net].add((p.ref, p.num))
                xy.append((p.x, p.y))
            else:
                xy.append(p)
        for a, b in zip(xy, xy[1:]):
            self.seg(a[0], a[1], b[0], b[1])

    def join(self, net, *pins):
        """Record pins as members of net without drawing (e.g. pins that sit on a drawn route)."""
        for p in pins:
            self.expected[net].add((p.ref, p.num))

    def stub_power(self, net, pin, length=2.54):
        """Short wire out of the pin, then a power symbol. Horizontal pins get an upright symbol."""
        self.expected[net].add((pin.ref, pin.num))
        ex, ey = pin.x + pin.ox * length, pin.y + pin.oy * length
        self.seg(pin.x, pin.y, ex, ey)
        ox, oy = pin.ox, pin.oy
        if oy == 0:
            ox, oy = 0, (1 if net == 'GND' else -1)
        self.power(net, ex, ey, ox, oy)

    def sym_at(self, net, p):
        """Power symbol directly on a pin end or wire point, upright (+V up, GND down)."""
        if isinstance(p, Pin):
            self.expected[net].add((p.ref, p.num))
            p = (p.x, p.y)
        self.power(net, p[0], p[1], 0, 1 if net == 'GND' else -1)

    def power(self, net, x, y, ox=0, oy=-1, lib=None):
        """Power symbol at (x, y) pointing in direction (ox, oy)."""
        if net == 'GND':
            rot = {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270}[(ox, oy)]
        else:
            rot = {(0, -1): 0, (-1, 0): 90, (0, 1): 180, (1, 0): 270}[(ox, oy)]
        d = 4.4 if net == 'GND' else 3.8
        just = 'left' if ox > 0 else 'right' if ox < 0 else None
        self.place(lib or f'power:{net}', '#PWR?', net, x, y, rot=rot, ref_pos=(x, y),
                   val_pos=(x + ox * d, y + oy * d), val_just=just, hide_value=(net == 'GND'))

    def pwr_flag(self, x, y):
        """PWR_FLAG whose pin sits at (x, y), drawn above it."""
        self.place('power:PWR_FLAG', '#FLG?', 'PWR_FLAG', x, y, ref_pos=(x, y - 3), val_pos=(x, y - 4.5),
                   val_just=None)

    def text(self, s, x, y, size=1.5, bold=False):
        self.items.append([S('text'), s, [S('exclude_from_sim'), S('no')], [S('at'), snap(x), snap(y), 0],
                           effects(size, justify='left top', bold=bold), [S('uuid'), uid()]])

    # ------------------------------------------------------------ output
    def _finish_wires(self):
        """Split wires at T-points and add junction dots where three or more connections meet."""
        pois = set(self.pin_points)
        for x1, y1, x2, y2 in self.wires:
            pois.add((x1, y1))
            pois.add((x2, y2))
        out = []
        for x1, y1, x2, y2 in self.wires:
            cuts = [(x1, y1), (x2, y2)]
            for (px, py) in pois:
                if x1 == x2 == px and min(y1, y2) < py < max(y1, y2):
                    cuts.append((px, py))
                elif y1 == y2 == py and min(x1, x2) < px < max(x1, x2):
                    cuts.append((px, py))
            cuts = sorted(set(cuts))
            out += [(a[0], a[1], b[0], b[1]) for a, b in zip(cuts, cuts[1:])]
        deg = defaultdict(int)
        for x1, y1, x2, y2 in out:
            deg[(x1, y1)] += 1
            deg[(x2, y2)] += 1
        for p in self.pin_points:
            if p in deg:
                deg[p] += 1
        for x1, y1, x2, y2 in out:
            self.items.append([S('wire'), [S('pts'), [S('xy'), x1, y1], [S('xy'), x2, y2]],
                               [S('stroke'), [S('width'), 0], [S('type'), S('default')]], [S('uuid'), uid()]])
        for (x, y), d in deg.items():
            if d >= 3:
                self.items.append([S('junction'), [S('at'), x, y], [S('diameter'), 0],
                                   [S('color'), 0, 0, 0, 0], [S('uuid'), uid()]])
        return out

    def write(self, path, comment=''):
        self._finish_wires()
        n = {'#PWR': 0, '#FLG': 0}
        for it in self.items:
            if it[0] == 'symbol':
                refp = next(p for p in it if isinstance(p, list) and p[0] == 'property' and p[1] == 'Reference')
                for pre in n:
                    if refp[2] == pre + '?':
                        n[pre] += 1
                        refp[2] = f'{pre}{n[pre]:03d}'
                        find1(it, 'instances')[1][2][2][1] = refp[2]

        def fix(nd):
            if isinstance(nd, list):
                return [fix(v) for v in nd]
            return f'/{self.uuid}' if nd == '__PATH__' else nd
        tree = [S('kicad_sch'), [S('version'), 20250114], [S('generator'), 'eeschema'],
                [S('generator_version'), '9.0'], [S('uuid'), self.uuid], [S('paper'), self.paper],
                [S('title_block'), [S('title'), self.title], [S('date'), '2026-10-28'], [S('rev'), '0.2'],
                 [S('company'), 'Clacktronics'], [S('comment'), 1, comment]],
                [S('lib_symbols')] + list(self.libs.values())] + fix(self.items) + \
               [[S('sheet_instances'), [S('path'), '/', [S('page'), '1']]], [S('embedded_fonts'), S('no')]]
        with open(path, 'w') as f:
            f.write(dump(tree) + '\n')
