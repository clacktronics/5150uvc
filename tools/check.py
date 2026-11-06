"""Check the generated schematic: KiCad netlist vs the connections the generator intended to draw.

Run: .venv/bin/python -I tools/check.py
"""
import os
import subprocess
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
import design  # noqa: E402
from sexp import parse  # noqa: E402

CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
SCH = os.path.join(design.HW, '5150UVC.kicad_sch')


def kicad_nets(path):
    out = path + '.net'
    subprocess.run([CLI, 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', out, SCH], check=True,
                   capture_output=True)
    tree = parse(open(out).read())
    os.remove(out)
    nets = {}
    comps = defaultdict(set)
    for node in tree:
        if isinstance(node, list) and str(node[0]) == 'nets':
            for net in node[1:]:
                name = next(str(v[1]) for v in net if isinstance(v, list) and str(v[0]) == 'name')
                members = set()
                for v in net:
                    if isinstance(v, list) and str(v[0]) == 'node':
                        r = next(str(x[1]) for x in v if isinstance(x, list) and str(x[0]) == 'ref')
                        p = next(str(x[1]) for x in v if isinstance(x, list) and str(x[0]) == 'pin')
                        if not r.startswith('#'):
                            members.add((r, p))
                            comps[r].add(p)
                nets[name] = members
    return nets, comps


def main():
    design.REFS.clear()
    sheet = design.build()
    nets, comps = kicad_nets('/tmp/5150uvc')
    where = {m: n for n, ms in nets.items() for m in ms}
    bad = 0
    expected = {n: m for n, m in sheet.expected.items() if m}
    claimed = set()
    for name, members in sorted(expected.items()):
        got = {where.get(m) for m in members}
        if len(got) != 1 or None in got:
            print(f'SPLIT  {name}: {sorted(members)} -> {sorted(map(str, got))}')
            bad += 1
            continue
        kn = got.pop()
        if kn in claimed:
            print(f'MERGED {name} shares KiCad net {kn} with another intended net')
            bad += 1
        claimed.add(kn)
        extra = nets[kn] - members
        if extra:
            print(f'EXTRA  {name} ({kn}) also has {sorted(extra)}')
            bad += 1
    exp_pins = set().union(*expected.values()) | sheet.nc
    for r, pins in comps.items():
        for p in pins:
            if (r, p) not in exp_pins:
                print(f'UNPLANNED pin {r}.{p} on {where.get((r, p))}')
                bad += 1
    for (r, p) in sheet.nc:
        n = where.get((r, p))
        if n and len(nets[n]) > 1:
            print(f'NC pin {r}.{p} is connected on {n}')
            bad += 1
    print(f'{len(expected)} intended nets, {len(nets)} KiCad nets, {bad} problems')
    return bad


if __name__ == '__main__':
    sys.exit(1 if main() else 0)
