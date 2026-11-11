"""Minimal S-expression reader/writer for KiCad files."""
import re

_tok = re.compile(r'\s*(?:(\()|(\))|("(?:[^"\\]|\\.)*")|([^\s()"]+))')


class Sym(str):
    """Unquoted atom."""


def parse(text):
    stack, cur, pos = [], [], 0
    n = len(text)
    while pos < n:
        m = _tok.match(text, pos)
        if not m:
            if text[pos:].strip() == "":
                break
            raise ValueError("parse error at %d" % pos)
        pos = m.end()
        if m.group(1):
            stack.append(cur)
            cur = []
        elif m.group(2):
            done = cur
            cur = stack.pop()
            cur.append(done)
        elif m.group(3) is not None:
            s = m.group(3)[1:-1]
            cur.append(s.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\"))
        else:
            cur.append(Sym(m.group(4)))
    return cur[0] if len(cur) == 1 else cur


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def fmt_num(v):
    if isinstance(v, float):
        s = ("%.4f" % v).rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(v)


def dump(node, indent=0):
    if isinstance(node, list):
        if not node:
            return "()"
        simple = all(not isinstance(x, list) for x in node)
        parts = [dump(x, indent + 1) for x in node]
        if simple and sum(len(p) for p in parts) < 100:
            return "(" + " ".join(parts) + ")"
        out = "(" + parts[0]
        for x, p in zip(node[1:], parts[1:]):
            if isinstance(x, list):
                out += "\n" + "\t" * (indent + 1) + p
            else:
                out += " " + p
        return out + "\n" + "\t" * indent + ")"
    if isinstance(node, Sym):
        return str(node)
    if isinstance(node, bool):
        return "yes" if node else "no"
    if isinstance(node, (int, float)):
        return fmt_num(node)
    return q(node)


def find(node, key):
    for x in node:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def findall(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]
