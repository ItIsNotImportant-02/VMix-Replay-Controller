"""Compare the drawn schematic's netlist with the intended nets in circuit.py."""
import os, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sexpr import parse, find, findall
import schgen, layout, circuit

HW = os.path.dirname(HERE)
net_file = os.path.join(HW, "build", "verify.net")
os.makedirs(os.path.dirname(net_file), exist_ok=True)
subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr", "-o", net_file,
                os.path.join(HW, "vmix-replay-controller.kicad_sch")], check=True, capture_output=True)
t = parse(open(net_file, encoding="utf-8").read())
actual = {}
for n in findall(find(t, "nets"), "net"):
    name = find(n, "name")[1]
    for x in findall(n, "node"):
        actual[(find(x, "ref")[1], find(x, "pin")[1])] = name
libs = schgen.SymbolLibs(extra_libs={"vrc": os.path.join(HW, "lib", "vrc.kicad_sym")})
col = layout.Collector()
circuit.build(col)
want = {}
for s in col.sheets:
    for p in s.parts:
        pins = libs.pins(p.lib_id)
        for q in pins:
            net = p.pinmap.get(q["num"], p.pinmap.get(q["name"], "<unassigned>"))
            want[(p.ref, q["num"])] = net
errors = []
# every intended net must map to exactly one actual net and vice versa
fwd, back = {}, {}
for key, net in want.items():
    if net is None or net == "<unassigned>":
        a = actual.get(key)
        if a and not a.startswith("unconnected-") and sum(1 for v in actual.values() if v == a) > 1:
            errors.append("%s.%s should be unconnected but is on %s" % (key[0], key[1], a))
        continue
    a = actual.get(key)
    if a is None:
        errors.append("%s.%s (%s) missing from drawing netlist" % (key[0], key[1], net))
        continue
    fwd.setdefault(net, set()).add(a)
    back.setdefault(a, set()).add(net)
for net, s in fwd.items():
    if len(s) > 1:
        errors.append("net %s is split into %s" % (net, sorted(s)))
for a, s in back.items():
    if len(s) > 1:
        errors.append("drawn net %s merges %s" % (a, sorted(s)))
for net, s in fwd.items():
    a = next(iter(s))
    if a.lstrip("/") != net and not a.startswith("Net-"):
        errors.append("net %s drawn with name %s" % (net, a))
print("VERIFY:", "OK" if not errors else "%d problems" % len(errors))
for e in errors[:80]:
    print("  ", e)
