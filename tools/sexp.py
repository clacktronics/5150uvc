"""Minimal KiCad s-expression reader/writer and library symbol helpers."""
import re

KICAD_SYM = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"

_tok = re.compile(r'\s*(\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+)')


class Sym(str):
    """Bare (unquoted) atom."""


def parse(text):
    stack, cur = [], []
    pos = 0
    while True:
        m = _tok.match(text, pos)
        if not m:
            break
        pos = m.end()
        t = m.group(1)
        if t == '(':
            stack.append(cur)
            cur = []
        elif t == ')':
            done = cur
            cur = stack.pop()
            cur.append(done)
        elif t.startswith('"'):
            cur.append(t[1:-1].replace('\\"', '"').replace('\\\\', '\\'))
        else:
            cur.append(Sym(t))
    return cur[0]


def q(s):
    s = str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    return '"' + s + '"'


def dump(node, indent=0):
    if isinstance(node, list):
        if not node:
            return '()'
        simple = all(not isinstance(x, list) for x in node)
        if simple:
            return '(' + ' '.join(dump(x) for x in node) + ')'
        pad = '\t' * (indent + 1)
        parts = [dump(node[0])]
        out = '(' + parts[0]
        for x in node[1:]:
            if isinstance(x, list):
                out += '\n' + pad + dump(x, indent + 1)
            else:
                out += ' ' + dump(x)
        return out + '\n' + '\t' * indent + ')'
    if isinstance(node, Sym):
        return str(node)
    if isinstance(node, bool):
        return 'yes' if node else 'no'
    if isinstance(node, (int, float)):
        return fmt_num(node)
    return q(node)


def fmt_num(v):
    if isinstance(v, int):
        return str(v)
    s = f'{v:.4f}'.rstrip('0').rstrip('.')
    return s if s not in ('-0', '') else '0'


def find(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def find1(node, key):
    r = find(node, key)
    return r[0] if r else None


_lib_cache = {}


def load_lib(lib):
    if lib not in _lib_cache:
        with open(f'{KICAD_SYM}/{lib}.kicad_sym') as f:
            tree = parse(f.read())
        _lib_cache[lib] = {s[1]: s for s in find(tree, 'symbol')}
    return _lib_cache[lib]


def lib_symbol(lib, name):
    """Return a flattened copy of a library symbol renamed to 'lib:name'."""
    import copy
    syms = load_lib(lib)
    s = copy.deepcopy(syms[name])
    ext = find1(s, 'extends')
    if ext:
        parent = copy.deepcopy(lib_symbol(lib, ext[1]))
        pname = ext[1]
        props = {p[1]: p for p in find(s, 'property')}
        body = []
        for x in parent[2:]:
            if isinstance(x, list) and x[0] == 'property' and x[1] in props:
                body.append(props.pop(x[1]))
            elif isinstance(x, list) and x[0] == 'symbol':
                x[1] = x[1].replace(pname.split(':')[-1], name, 1)
                body.append(x)
            else:
                body.append(x)
        body += list(props.values())
        s = [Sym('symbol'), name] + body
    s[1] = f'{lib}:{name}'
    return s


def symbol_pins(sym):
    """Yield (unit, number, name, type, x, y, angle, length) for every pin in a lib symbol."""
    base = sym[1].split(':')[-1]
    out = []
    for sub in find(sym, 'symbol'):
        m = re.match(re.escape(base) + r'_(\d+)_(\d+)$', sub[1])
        unit = int(m.group(1)) if m else 0
        for p in find(sub, 'pin'):
            at = find1(p, 'at')
            ln = find1(p, 'length')
            name = find1(p, 'name')[1]
            num = find1(p, 'number')[1]
            out.append(dict(unit=unit, num=num, name=name, type=str(p[1]),
                            x=float(at[1]), y=float(at[2]),
                            angle=float(at[3]) if len(at) > 3 else 0.0,
                            length=float(ln[1]) if ln else 0))
    return out
