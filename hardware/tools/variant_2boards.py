"""Variant study: split into a 2-layer main board + a small 2-layer I/O board (USB-C + W5500 + RJ45).

Not the main design. Takes the current schematic netlist (build/net.net), moves the USB input
and the whole Ethernet block to a small board, joins the cut nets with a 2x8 ribbon connector
(J7 on the main board, J8 on the I/O board) and places both boards with tools/pcb.py.

Run in the KiCad container from hardware/:
    python3 tools/variant_2boards.py
Outputs in build/var2/: main.kicad_pcb, io.kicad_pcb, *.net, BOM/CPL via tools/jlc.py.
"""
import copy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, dump, find, findall, Sym
import pcb

HW = pcb.HW
OUT = os.path.join(HW, "build", "var2")

IO_REFS = {"J1", "R1", "R2", "U1", "F1", "D1", "TP1", "U5", "Y2", "FB2", "J4"}
IO_REFS |= {"R%d" % i for i in range(20, 37)}
IO_REFS |= {"C%d" % i for i in range(40, 57)}

# ribbon pinout (2x8, odd row / even row); grounds between the USB pair and the SPI clock
LINK = {"1": "+5V", "2": "+5V", "3": "GND", "4": "GND", "5": "USB_CONN_DP", "6": "GND", "7": "USB_CONN_DM",
        "8": "GND", "9": "ETH_SCK", "10": "GND", "11": "ETH_MOSI", "12": "ETH_MISO", "13": "ETH_CS",
        "14": "ETH_INT", "15": "ETH_RST", "16": "+3V3"}
for _k, _v in list(LINK.items()):
    if not _v.startswith(("+", "GND")):
        LINK[_k] = "/" + _v      # local labels are hierarchical-path prefixed in the netlist
LINK_FP = "Connector_IDC:IDC-Header_2x08_P2.54mm_Vertical"


def comp(ref, value, fp, lcsc=None, assembly=None):
    c = [Sym("comp"), [Sym("ref"), ref], [Sym("value"), value], [Sym("footprint"), fp]]
    if lcsc:
        c.append([Sym("property"), [Sym("name"), "LCSC"], [Sym("value"), lcsc]])
    if assembly:
        c.append([Sym("property"), [Sym("name"), "Assembly"], [Sym("value"), assembly]])
    c.append([Sym("sheetpath"), [Sym("names"), "/"], [Sym("tstamps"), "/"]])
    c.append([Sym("tstamps"), "var2-%s" % ref])
    return c


def split():
    t = parse(open(os.path.join(HW, "build", "net.net"), encoding="utf-8").read())
    comps = findall(find(t, "components"), "comp")
    nets = findall(find(t, "nets"), "net")
    boards = {}
    for side in ("main", "io"):
        keep = (lambda r: r in IO_REFS) if side == "io" else (lambda r: r not in IO_REFS)
        cs = [c for c in comps if keep(find(c, "ref")[1])]
        link_ref = "J8" if side == "io" else "J7"
        cs.append(comp(link_ref, "LINK", LINK_FP, assembly="ruční pájení"))
        if side == "io":   # bulk + HF cap on +5V right after the fuse/TVS (the main board keeps C1/C2 at the LDO)
            cs.append(comp("C90", "10uF", "Capacitor_SMD:C_0805_2012Metric", lcsc="C15850"))
            cs.append(comp("C91", "100nF", "Capacitor_SMD:C_0603_1608Metric", lcsc="C14663"))
        ns = []
        for n in nets:
            name = find(n, "name")[1]
            nodes = [x for x in findall(n, "node") if keep(find(x, "ref")[1])]
            nodes += [[Sym("node"), [Sym("ref"), link_ref], [Sym("pin"), p]] for p, nn in LINK.items() if nn == name]
            if side == "io" and name in ("+5V", "GND"):
                nodes += [[Sym("node"), [Sym("ref"), "C90"], [Sym("pin"), "1" if name == "+5V" else "2"]],
                          [Sym("node"), [Sym("ref"), "C91"], [Sym("pin"), "1" if name == "+5V" else "2"]]]
            if nodes:
                ns.append([Sym("net"), [Sym("code"), str(len(ns) + 1)], [Sym("name"), name]] + nodes)
        cut = [n for n in nets if any(find(x, "ref")[1] in IO_REFS for x in findall(n, "node"))
               and any(find(x, "ref")[1] not in IO_REFS for x in findall(n, "node"))]
        missing = [find(n, "name")[1] for n in cut if find(n, "name")[1] not in LINK.values()]
        if missing:
            raise SystemExit("cut nets without a link pin: %s" % missing)
        out = [Sym("export"), [Sym("version"), "E"], [Sym("components")] + cs, [Sym("nets")] + ns]
        path = os.path.join(OUT, side + ".net")
        open(path, "w", encoding="utf-8").write(dump(out) + "\n")
        boards[side] = path
    return boards


def rect_outline(board):
    x0, y0, x1, y1 = pcb.BOARD
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    for a, b in zip(pts, pts[1:]):
        s = pcb.pcbnew.PCB_SHAPE(board, pcb.pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcb.P(*a)); s.SetEnd(pcb.P(*b)); s.SetLayer(pcb.pcbnew.Edge_Cuts); s.SetWidth(pcb.mm(0.1))
        board.Add(s)


def main():
    os.makedirs(OUT, exist_ok=True)
    nets = split()
    pcb.LAYERS = 2
    # main board: same outline and buttons, USB/RJ45 gone, ribbon connector where the USB-C was
    pcb.NETLIST, pcb.OUT_PCB = nets["main"], os.path.join(OUT, "main.kicad_pcb")
    pcb.EDGE_CONN = {}
    pcb.FIXED = {k: v for k, v in pcb.FIXED.items() if k not in IO_REFS}
    pcb.FIXED["J7"] = (35.0, 65.0, 0)
    pcb.HOME = {k: ("U2" if v in IO_REFS else v) for k, v in pcb.HOME.items() if k not in IO_REFS}
    pcb.place()
    # I/O board: USB-C and RJ45 side by side on the rear edge, W5500 behind them, ribbon at the front
    pcb.NETLIST, pcb.OUT_PCB = nets["io"], os.path.join(OUT, "io.kicad_pcb")
    W, H = float(os.environ.get("IO_W", 56)), float(os.environ.get("IO_H", 50))
    pcb.BOARD = (0.0, 0.0, W, H)
    pcb.CORNER_R = 1.0
    pcb.LEVER_NOTCH = (-100.0, -100.0, -99.0)
    pcb.JOG_HOLE = (-500.0, -500.0, 1.0)
    pcb.MOUNT_HOLES = [(3.5, H - 3.5), (W - 3.5, H - 3.5)]
    pcb.outline = rect_outline
    pcb.EDGE_CONN = {"J1": "top", "J4": "top"}
    pcb.EDGE_OVERHANG = 1.0
    pcb.FIXED = {"J1": (8.0, None, 180), "J4": (W - 13.0, None, 180), "U5": (W - 21.0, H - 19.5, 0),
                 "J8": (W / 2 - 8.9, H - 6.0, 90)}
    pcb.HOME = {r: ("U5" if r.startswith(("R2", "R3", "C4", "C5", "Y", "FB")) else "J1") for r in IO_REFS}
    pcb.HOME.update({"R33": "J4", "R34": "J4", "C90": "J1", "C91": "J1"})
    pcb.place()


if __name__ == "__main__":
    main()
