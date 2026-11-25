"""Routing of the main board (4 layers), run inside the KiCad container from hardware/.

Stack-up (JLC7628, 1.6 mm): L1 signals + parts | 0.2 mm | L2 (In1) solid GND, no tracks |
1.065 mm core | L3 (In2) +5V_LED plane, no tracks | 0.2 mm | L4 signals.
Why: every fast signal (USB, QSPI, SPI to the W5500, Ethernet, crystals) runs on L1 right above an
unbroken GND plane (0.2 mm away), so its return current flows directly under it. L3 carries the LED
supply, which reaches all 28 buttons; L4 is for slow signals (buttons, LED cathodes, I2C, sensors),
which reference the +5V_LED plane (decoupled to GND at the drivers). Low-current rails (+3V3, +3V3A,
+1V1, +5V, VBUS) are routed as wide tracks. L1 and L4 are filled with GND and stitched to L2.

Steps:
    python3 tools/route.py prep       # rules, fan-out vias for GND / +5V_LED, EP vias -> build/prep.kicad_pcb + build/route.dsn
    java -jar freerouting.jar -de build/route.dsn -do build/route.ses ...
    python3 tools/route.py finish     # import routes, stitching vias, zones -> vmix-replay-controller.kicad_pcb
"""
import math, os, re, sys
import pcbnew

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(HW, "vmix-replay-controller.kicad_pcb")
BUILD = os.path.join(HW, "build")
PREP = os.path.join(HW, "build", "prep.kicad_pcb")
DSN = os.path.join(HW, "build", "route.dsn")
SES = os.path.join(HW, "build", "route.ses")

PLANE = {"GND": pcbnew.In1_Cu, "+5V_LED": pcbnew.In2_Cu}
VIA_D, VIA_DRILL = float(os.environ.get("VIA_D") or 0.6), float(os.environ.get("VIA_DRILL") or 0.3)
CLR = 0.2                      # clearance used when placing vias (rules allow 0.15)
DEFAULT_W = float(os.environ.get("DEFAULT_W", "0.2"))   # signal tracks; Freerouting necks down to 0.15 at fine-pitch pins

# net classes: name -> (track, clearance, diff pair gap or None, nets regex)
# USB: 0.28/0.2 on L1 over 0.2 mm 7628 (Er ~4.4) ~ 90 ohm differential; Ethernet 0.22/0.2 ~ 100 ohm.
CLASSES = [
    ("USB", 0.28, 0.15, 0.2, r"^/USB_(CONN_)?D[PM]$"),
    ("ETH", 0.22, 0.15, 0.2, r"^/(W_(TX|RX)[PN]|ETH_(TD|RD)[PN]|ETH_R[XN][PN]?_T|ETH_RX[PN]_T)$"),
    ("PWR_HI", 0.6, 0.2, None, r"^(VBUS|\+5V)$"),
    # plane nets: Freerouting never sees them (stripped from the DSN), so it can only keep the
    # default clearance to their pads -> the class clearance must equal the default
    ("PLANE", 0.5, 0.15, None, r"^(\+5V_LED|GND)$"),
    ("PWR", 0.25, 0.15, None, r"^(\+3V3|\+3V3A|\+1V1)$"),
]


def mm(v):
    return pcbnew.FromMM(v)


def T(v):
    return pcbnew.ToMM(v)


# ------------------------------------------------------------- rules --------
def write_rules():
    """Net classes and JLC-friendly design rules into the .kicad_pro (KiCad 9 keeps them there)."""
    import json
    pro = os.path.join(HW, "vmix-replay-controller.kicad_pro")
    d = json.load(open(pro, encoding="utf-8"))
    rules = {"min_clearance": 0.15, "min_track_width": 0.15, "min_via_diameter": 0.5,
             "min_through_hole_diameter": 0.2, "min_via_annular_width": 0.1, "min_hole_clearance": 0.25,
             "min_hole_to_hole": 0.25, "min_copper_edge_clearance": 0.3, "min_silk_clearance": 0.0,
             "min_resolved_spokes": 2}
    d.setdefault("board", {}).setdefault("design_settings", {}).setdefault("rules", {}).update(rules)

    def nc(name, track, clr, gap, prio):
        return {"name": name, "clearance": clr, "track_width": track, "via_diameter": VIA_D, "via_drill": VIA_DRILL,
                "diff_pair_width": track, "diff_pair_gap": gap or 0.25, "diff_pair_via_gap": 0.25,
                "microvia_diameter": 0.3, "microvia_drill": 0.1,
                "wire_width": 6, "bus_width": 12, "line_style": 0, "priority": prio,
                "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)"}
    classes = [nc("Default", DEFAULT_W, 0.15, None, 2147483647)]
    pats = []
    for i, (name, w, clr, gap, rx) in enumerate(CLASSES):
        classes.append(nc(name, w, clr, gap, i))
        pats.append({"netclass": name, "pattern": rx})
    d["net_settings"] = {"meta": {"version": 4}, "classes": classes, "netclass_patterns": pats}
    json.dump(d, open(pro, "w", encoding="utf-8"), indent=2)


def class_of(net):
    for name, w, clr, gap, rx in CLASSES:
        if re.match(rx, net):
            return name, w, clr
    return "Default", 0.2, 0.15


# ---------------------------------------------------------- geometry --------
class Space:
    """Copper obstacles for placing fan-out vias (rectangles per pad, circles per via, segments per track)."""

    def __init__(self, board):
        self.board = board
        self.pads = []      # (x0, y0, x1, y1, net, layers_front, layers_back)
        for fp in board.GetFootprints():
            for p in fp.Pads():
                b = p.GetBoundingBox()
                self.pads.append((T(b.GetX()), T(b.GetY()), T(b.GetRight()), T(b.GetBottom()), p.GetNetname(),
                                  p.IsOnLayer(pcbnew.F_Cu), p.IsOnLayer(pcbnew.B_Cu), p.GetDrillSize().x > 0))
        self.vias = []      # (x, y, r, net)
        self.segs = []      # (x0, y0, x1, y1, half width, net, layer)
        self.outline = pcbnew.SHAPE_POLY_SET()
        board.GetBoardPolygonOutlines(self.outline)
        self.edges = []
        for d in board.GetDrawings():
            if d.GetLayer() != pcbnew.Edge_Cuts:
                continue
            if d.GetShape() == pcbnew.SHAPE_T_CIRCLE:
                c = d.GetCenter()
                self.edges.append(("c", T(c.x), T(c.y), T(d.GetRadius())))
            else:
                self.edges.append(("l", T(d.GetStart().x), T(d.GetStart().y), T(d.GetEnd().x), T(d.GetEnd().y)))

    def inside(self, x, y, margin):
        if not self.outline.Contains(pcbnew.VECTOR2I(mm(x), mm(y))):
            return False
        for e in self.edges:
            if e[0] == "l":
                d = seg_dist(x, y, *e[1:])
            else:
                d = abs(math.hypot(x - e[1], y - e[2]) - e[3])
            if d < margin:
                return False
        return True

    def via_ok(self, x, y, net, r=VIA_D / 2):
        if not self.inside(x, y, 0.5 + r):
            return False
        for x0, y0, x1, y1, n, f, bk, tht in self.pads:
            if n == net and not tht:
                continue
            dx = max(x0 - x, 0, x - x1)
            dy = max(y0 - y, 0, y - y1)
            need = r + (CLR if n != net else 0.25) + (0.25 if tht else 0)
            if dx * dx + dy * dy < need * need:
                return False
        for vx, vy, vr, n in self.vias:
            need = r + vr + (CLR if n != net else 0.15) + (0.1 if n == net else 0)
            if (vx - x) ** 2 + (vy - y) ** 2 < need * need:
                return False
        for sx0, sy0, sx1, sy1, hw, n, layer in self.segs:
            if n == net:
                continue
            if seg_dist(x, y, sx0, sy0, sx1, sy1) < r + hw + CLR:
                return False
        return True

    def track_ok(self, a, b, hw, net, layer, skip=()):
        """Straight track from a to b on F.Cu/B.Cu clear of other nets' pads, vias, tracks."""
        front = layer == pcbnew.F_Cu
        for x0, y0, x1, y1, n, f, bk, tht in self.pads:
            if n == net:
                continue
            if not (f if front else bk):
                continue
            if rect_seg_dist(x0, y0, x1, y1, a, b) < hw + CLR:
                return False
        for vx, vy, vr, n in self.vias:
            if n != net and seg_dist(vx, vy, a[0], a[1], b[0], b[1]) < vr + hw + CLR:
                return False
        for sx0, sy0, sx1, sy1, shw, n, ly in self.segs:
            if n != net and ly == layer and seg_seg_dist(a, b, (sx0, sy0), (sx1, sy1)) < hw + shw + CLR:
                return False
        return True

    def add_via(self, x, y, net):
        v = pcbnew.PCB_VIA(self.board)
        v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        v.SetWidth(mm(VIA_D))
        v.SetDrill(mm(VIA_DRILL))
        v.SetNet(self.board.FindNet(net))
        v.SetLocked(True)
        self.board.Add(v)
        self.vias.append((x, y, VIA_D / 2, net))

    def add_track(self, a, b, net, w, layer=pcbnew.F_Cu):
        if math.hypot(a[0] - b[0], a[1] - b[1]) < 0.01:
            return
        t = pcbnew.PCB_TRACK(self.board)
        t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
        t.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
        t.SetWidth(mm(w))
        t.SetLayer(layer)
        t.SetNet(self.board.FindNet(net))
        t.SetLocked(True)
        self.board.Add(t)
        self.segs.append((a[0], a[1], b[0], b[1], w / 2, net, layer))


def seg_dist(px, py, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - x0) * dx + (py - y0) * dy) / L))
    return math.hypot(px - x0 - t * dx, py - y0 - t * dy)


def seg_seg_dist(a, b, c, d):
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    if orient(a, b, c) * orient(a, b, d) < 0 and orient(c, d, a) * orient(c, d, b) < 0:
        return 0.0                                   # proper crossing
    return min(seg_dist(a[0], a[1], c[0], c[1], d[0], d[1]), seg_dist(b[0], b[1], c[0], c[1], d[0], d[1]),
               seg_dist(c[0], c[1], a[0], a[1], b[0], b[1]), seg_dist(d[0], d[1], a[0], a[1], b[0], b[1]))


def rect_seg_dist(x0, y0, x1, y1, a, b):
    best = 1e9
    n = max(10, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.05))
    for i in range(n + 1):
        t = i / n
        x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        dx = max(x0 - x, 0, x - x1)
        dy = max(y0 - y, 0, y - y1)
        best = min(best, math.hypot(dx, dy))
    return best


# ----------------------------------------------------------- fan-out --------
def pad_xy(p):
    q = p.GetPosition()
    return T(q.x), T(q.y)


def led_vcc(board, add):
    """LED driver VCC pin -> the decoupling cap sitting straight in front of it (pin stub + track).
    Also used after the session import: Freerouting tends to drop the short stub inside the pad."""
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    for ic, caps in (("U6", ("C60", "C61")), ("U7", ("C62", "C63"))):
        for cref in caps:
            cp = [p for p in fps[cref].Pads() if p.GetNetname() == "+5V_LED"][0]
            cx, cy = pad_xy(cp)
            pins = [p for p in fps[ic].Pads() if p.GetNetname() == "+5V_LED"]
            pin = min(pins, key=lambda p: math.hypot(pad_xy(p)[0] - cx, pad_xy(p)[1] - cy))
            px, py = pad_xy(pin)
            # leave the pin straight outwards (perpendicular to its side), then go to the cap
            ic_c = fps[ic].GetPosition()
            side_lr = abs(px - T(ic_c.x)) > abs(py - T(ic_c.y))   # pin on the left / right side
            # only a cap sitting straight in front of the pin gets a track; one further along the
            # side would have to pass next to the neighbouring pins -> it keeps its own plane via
            if (abs(cy - py) if side_lr else abs(cx - px)) > 0.8:
                continue
            if side_lr:
                mid = (px + math.copysign(min(abs(cx - px), 1.0), px - T(ic_c.x)), py)
            else:
                mid = (px, py + math.copysign(min(abs(cy - py), 1.0), py - T(ic_c.y)))
            add((px, py), mid, "+5V_LED", 0.2)
            add(mid, (cx, cy), "+5V_LED", 0.3)


def plain_track(board):
    def add(a, b, net, w):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
        t.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
        t.SetWidth(mm(w))
        t.SetLayer(pcbnew.F_Cu)
        t.SetNet(board.FindNet(net))
        t.SetLocked(True)
        board.Add(t)
    return add


def fanout(board):
    sp = Space(board)
    report = []
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}

    # 1) QFNs with exposed pad: via grid in the EP, GND pins tied straight into the EP
    ep_grid = {"U3": (3, 1.0), "U6": (0, 0), "U7": (0, 0), "U8": (2, 1.1), "U9": (2, 1.1)}
    for ref, (n, pitch) in ep_grid.items():
        fp = fps[ref]
        ep = [p for p in fp.Pads() if p.GetNetname() == "GND" and p.GetSize().x > mm(2)]
        if not ep:
            continue
        cx, cy = pad_xy(ep[0])
        if n:
            for i in range(n):
                for j in range(n):
                    x = cx + (i - (n - 1) / 2) * pitch
                    y = cy + (j - (n - 1) / 2) * pitch
                    v = pcbnew.PCB_VIA(board)
                    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
                    v.SetWidth(mm(VIA_D)); v.SetDrill(mm(VIA_DRILL))
                    v.SetNet(board.FindNet("GND")); v.SetLocked(True)
                    board.Add(v)
                    sp.vias.append((x, y, VIA_D / 2, "GND"))
        ex = T(ep[0].GetSize().x) / 2
        for p in fp.Pads():
            if p.GetNetname() != "GND" or p is ep[0] or p.GetSize().x > mm(2):
                continue
            px, py = pad_xy(p)
            # into the EP edge along the pin axis
            if abs(px - cx) > abs(py - cy):
                tgt = (cx + math.copysign(ex - 0.2, px - cx), py)
            else:
                tgt = (px, cy + math.copysign(ex - 0.2, py - cy))
            sp.add_track((px, py), tgt, "GND", 0.2)
        report.append("%s: EP vias %d, GND pins tied to EP" % (ref, n * n))

    # 2) LQFP W5500: GND pins inward under the body, one via per group of neighbouring pins
    fp = fps["U5"]
    c = fp.GetPosition(); ux, uy = T(c.x), T(c.y)
    gnd = sorted([p for p in fp.Pads() if p.GetNetname() == "GND"], key=lambda p: int(p.GetNumber()))
    groups, cur = [], []
    for p in gnd:
        if cur and int(p.GetNumber()) == int(cur[-1].GetNumber()) + 1:
            cur.append(p)
        else:
            if cur:
                groups.append(cur)
            cur = [p]
    groups.append(cur)
    for g in groups:
        pts = [pad_xy(p) for p in g]
        mx = sum(x for x, y in pts) / len(pts); my = sum(y for x, y in pts) / len(pts)
        # inward direction
        if abs(mx - ux) > abs(my - uy):
            d = (-math.copysign(1, mx - ux), 0)
        else:
            d = (0, -math.copysign(1, my - uy))
        inner = [(x + d[0] * 1.3, y + d[1] * 1.3) for x, y in pts]
        for a, b in zip(pts, inner):
            sp.add_track(a, b, "GND", 0.25)
        if len(inner) > 1:
            sp.add_track(inner[0], inner[-1], "GND", 0.25)
        vx = (inner[0][0] + inner[-1][0]) / 2 + d[0] * 0.7
        vy = (inner[0][1] + inner[-1][1]) / 2 + d[1] * 0.7
        sp.add_track(((inner[0][0] + inner[-1][0]) / 2, (inner[0][1] + inner[-1][1]) / 2), (vx, vy), "GND", 0.25)
        sp.add_via(vx, vy, "GND")
    report.append("U5: %d GND via groups under the body" % len(groups))

    # 3) LED driver supply: straight track VCC pin -> the cap in front of it
    led_vcc(board, sp.add_track)

    # 4) every other SMD pad on GND / +5V_LED gets its own via, as close as possible
    done = set()
    missing = []
    for fp in board.GetFootprints():
        fc = fp.GetPosition(); fx, fy = T(fc.x), T(fc.y)
        for p in fp.Pads():
            net = p.GetNetname()
            if net not in PLANE or p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            if p.GetSize().x > mm(2) and fp.GetReference() in ep_grid:
                continue
            ref = fp.GetReference()
            if ref in ep_grid or ref == "U5":
                if net == "GND":
                    continue        # handled above
                if ref in ("U6", "U7"):
                    continue        # VCC goes to its caps, the caps get the vias
            px, py = pad_xy(p)
            b = p.GetBoundingBox()
            hx, hy = T(b.GetWidth()) / 2, T(b.GetHeight()) / 2
            layer = pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
            # preferred direction: away from the part centre
            dx, dy = px - fx, py - fy
            if abs(dx) < 1e-3 and abs(dy) < 1e-3:
                dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
            elif abs(dx) >= abs(dy):
                s = math.copysign(1, dx)
                dirs = [(s, 0), (0, -1), (0, 1), (-s, 0)]
            else:
                s = math.copysign(1, dy)
                dirs = [(0, s), (-1, 0), (1, 0), (0, -s)]
            placed = False
            for extra in (0.0, 0.3, 0.6, 1.0, 1.5):
                for d in dirs:
                    for side in (0.0, 0.5, -0.5):
                        ext = (hx if d[0] else hy) + CLR + VIA_D / 2 + extra
                        vx = px + d[0] * ext + (side if d[1] else 0)
                        vy = py + d[1] * ext + (side if d[0] else 0)
                        if not sp.via_ok(vx, vy, net):
                            continue
                        if not sp.track_ok((px, py), (vx, vy), 0.15, net, layer):
                            continue
                        sp.add_track((px, py), (vx, vy), net, 0.3 if net == "GND" else 0.3, layer)
                        sp.add_via(vx, vy, net)
                        placed = True
                        break
                    if placed:
                        break
                if placed:
                    break
            if not placed:
                missing.append("%s.%s" % (ref, p.GetNumber()))
    report.append("fan-out vias: %d, without via: %s" % (len(sp.vias), ", ".join(missing) or "none"))
    return report


# ------------------------------------------------------------- zones --------
def zones(board, outer=True):
    """Planes on In1/In2, GND pours on L1/L4. Islands removed, thermal reliefs for hand-soldered THT."""
    for z in list(board.Zones()):
        board.Remove(z)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import pcb
    bx0, by0, bx1, by1 = pcb.BOARD
    x0, y0 = mm(bx0 + pcb.OX - 1), mm(by0 + pcb.OY - 1)
    x1, y1 = mm(bx1 + pcb.OX + 1), mm(by1 + pcb.OY + 1)
    todo = [("GND", pcbnew.In1_Cu, 0), ("+5V_LED", pcbnew.In2_Cu, 0)]
    if outer:
        todo += [("GND", pcbnew.F_Cu, 0), ("GND", pcbnew.B_Cu, 0)]
    for net, layer, prio in todo:
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(board.FindNet(net))
        z.SetAssignedPriority(prio)
        z.SetLocalClearance(mm(0.25))
        z.SetMinThickness(mm(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(mm(0.3))
        z.SetThermalReliefSpokeWidth(mm(0.4))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        ol = z.Outline()
        ol.NewOutline()
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            ol.Append(x, y)
        board.Add(z)


# --------------------------------------------------------------- DSN --------
def strip_dsn_nets(path, nets):
    """Remove plane nets from the DSN network so Freerouting leaves them alone (they are complete via the planes)."""
    s = open(path, encoding="utf-8").read()
    for n in nets:
        for q in (n, '"%s"' % n):
            s = re.sub(r"\(net %s\s*\(pins[^)]*\)\s*\)" % re.escape(q), "", s)
    open(path, "w", encoding="utf-8").write(s)


def strip_zones(src, dst, layers):
    """Remove the zones on the given layers by editing the file (removing zones through the
    Python API corrupts the SWIG wrappers in KiCad 9)."""
    txt = open(src, encoding="utf-8").read()
    out, i = [], 0
    while True:
        js = [x for x in (txt.find("\n\t(" + k, i) for k in ("zone", "segment", "via", "arc")) if x >= 0]
        j = min(js) if js else -1
        if j < 0:
            out.append(txt[i:])
            break
        # find the matching parenthesis
        k, depth = j + 2, 0
        while True:
            ch = txt[k]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        block = txt[j:k + 1]
        head = txt[j + 3:j + 12]
        keep = head.startswith("zone") and not any('(layer "%s")' % l in block for l in layers) and EDGE_KO not in block
        out.append(txt[i:j] + (block if keep else ""))
        i = k + 1
    open(dst, "w", encoding="utf-8").write("".join(out))


EDGE_KO = "EDGE_KEEPOUT"


def edge_keepouts(board, w=0.35):
    """Rule areas (no tracks, no vias) along every Edge.Cuts item: Freerouting keeps only the
    default clearance to the board edge, the fab wants 0.3 mm to routed copper."""
    def area(pts):
        z = pcbnew.ZONE(board)
        z.SetIsRuleArea(True)
        z.SetZoneName(EDGE_KO)
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowCopperPour(False)
        z.SetDoNotAllowFootprints(False)
        z.SetLayerSet(pcbnew.LSET.AllCuMask())
        ol = z.Outline()
        ol.NewOutline()
        for x, y in pts:
            ol.Append(mm(x), mm(y))
        board.Add(z)
    n = 0
    for d in board.GetDrawings():
        if d.GetLayer() != pcbnew.Edge_Cuts:
            continue
        if d.GetShape() == pcbnew.SHAPE_T_CIRCLE:
            c, r = d.GetCenter(), T(d.GetRadius()) + w
            area([(T(c.x) + r * math.cos(a * math.pi / 32), T(c.y) + r * math.sin(a * math.pi / 32)) for a in range(64)])
        else:
            pts = [(T(v.x), T(v.y)) for v in (d.GetStart(), d.GetEnd())]
            if d.GetShape() == pcbnew.SHAPE_T_ARC:
                pts.insert(1, (T(d.GetArcMid().x), T(d.GetArcMid().y)))
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                L = math.hypot(x1 - x0, y1 - y0) or 1
                ux, uy = (x1 - x0) / L * w, (y1 - y0) / L * w
                nx, ny = -uy, ux
                area([(x0 - ux + nx, y0 - uy + ny), (x1 + ux + nx, y1 + uy + ny),
                      (x1 + ux - nx, y1 + uy - ny), (x0 - ux - nx, y0 - uy - ny)])
        n += 1
    return n


CRITICAL = [r"^(VBUS|\+5V)$", r"^/USB_", r"^(/XIN|/XOUT|/W_XI|/W_XO)$", r"^/QSPI_",          # in this order
            r"^(/W_(TX|RX)[PN]|/ETH_(TD|RD)[PN]|/ETH_R[XN][PN]?_T)$", r"^\+1V1$"]


def prep():
    write_rules()
    strip_zones(PCB, PREP, ["F.Cu", "B.Cu"])        # outer GND pours come back after routing
    import shutil                                    # same project file -> same rules and net classes
    shutil.copy(os.path.join(HW, "vmix-replay-controller.kicad_pro"), os.path.splitext(PREP)[0] + ".kicad_pro")
    board = pcbnew.LoadBoard(PREP)                   # (tracks and vias were stripped as text too)
    for line in fanout(board):
        print(line)
    print("edge keep-outs:", edge_keepouts(board))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(PREP)
    pcbnew.ExportSpecctraDSN(board, DSN)
    strip_dsn_nets(DSN, ["GND", "+5V_LED"])
    keep_dsn_nets(DSN, DSN_CRIT, CRITICAL)
    print("prep ->", PREP, DSN, DSN_CRIT)


def keep_dsn_nets(src, dst, regexes):
    """DSN with only the nets matching one of the regexes (the rest are left out of the network)."""
    s = open(src, encoding="utf-8").read()
    a = s.index("(network")

    def keep(m):
        name = m.group(1).strip('"')
        return m.group(0) if any(re.search(r, name) for r in regexes) else ""
    net = re.sub(r"\(net (\S+)\s*\(pins[^)]*\)\s*\)", keep, s[a:])
    open(dst, "w", encoding="utf-8").write(s[:a] + net)


# In2 (+5V_LED plane) may carry short signal hops, but only inside this window around the
# RP2040 / expander column (file coordinates, mm); everywhere else it stays a solid plane.
IN2_WINDOW = (100.0, 58.0, 136.0, 142.0)


def open_in2(path, window=IN2_WINDOW):
    """Let Freerouting use In2.Cu as a signal layer inside the window only."""
    s = open(path, encoding="utf-8").read()
    s = re.sub(r"(\(layer In2\.Cu\s*\(type )power\)", r"\1signal)", s)
    # the plane shrinks to a 0.1 mm speck in the board corner: the net stays known to Freerouting
    # (its fan-out vias survive the session round trip) but In2 is free for the window
    s = re.sub(r"\(plane \+5V_LED \(polygon In2\.Cu[^)]*\)\)",
               "(plane +5V_LED (polygon In2.Cu 0  20000 -20000  20100 -20000  20100 -20100  20000 -20100  20000 -20000))", s)
    x0, y0, x1, y1 = [v * 1000 for v in window]
    ko = ["(keepout \"\" (rect In2.Cu %d %d %d %d))" % r for r in (
        (0, 0, x0, -200000), (x1, 0, 200000, -200000), (x0, 0, x1, -y0), (x0, -y1, x1, -200000))]
    i = s.index("(keepout")
    s = s[:i] + "\n    ".join(ko) + "\n    " + s[i:]
    open(path, "w", encoding="utf-8").write(s)


def crit():
    """Import the autorouted critical nets into the prep board, lock them, export the full DSN."""
    board = pcbnew.LoadBoard(PREP)
    pcbnew.ImportSpecctraSES(board, SES_CRIT)
    board.Save(PREP)
    board = pcbnew.LoadBoard(PREP)
    n = 0
    for t in board.GetTracks():
        if not t.IsLocked():
            t.SetLocked(True)
            n += 1
    board.Save(PREP)
    pcbnew.ExportSpecctraDSN(board, DSN)
    if os.environ.get("IN2_SIGNAL"):
        strip_dsn_nets(DSN, ["GND"])
        in2_signal(DSN)
    elif os.environ.get("IN2_CORRIDOR"):
        strip_dsn_nets(DSN, ["GND"])
        in2_corridor(DSN)
    else:
        strip_dsn_nets(DSN, ["GND", "+5V_LED"])
    print("locked %d critical segments/vias ->" % n, DSN)


# Signal corridor on In2 along the MCU/expander/LED-driver spine (board coordinates, mm):
# open to the front edge, so the +5V_LED plane around it stays one piece (a U).
IN2_CORRIDOR = (75.0, 35.0, 112.0)        # x0, y_top, x1


def in2_signal(path):
    """Full 4-layer use: In1 stays a solid GND plane (reference for every signal layer), In2 becomes
    a third signal layer. +5V_LED is routed as tracks (class PLANE, 0.5 mm) so its connectivity
    never depends on the pour; after routing the In2 +5V_LED pour fills the free space."""
    s = open(path, encoding="utf-8").read()
    s = re.sub(r"(\(layer In2\.Cu\s*\(type )power\)", r"\1signal)", s)
    s, k = re.subn(r"\(plane \+5V_LED \(polygon In2\.Cu[^)]*\)\)", "", s)
    assert k == 1, "plane +5V_LED not found"
    open(path, "w", encoding="utf-8").write(s)


def in2_corridor(path, corr=IN2_CORRIDOR):
    """In2 = +5V_LED plane everywhere except the corridor, where Freerouting may run signals.
    +5V_LED stays in the network, so its vias and pads are known obstacles/targets."""
    import pcb
    s = open(path, encoding="utf-8").read()
    s = re.sub(r"(\(layer In2\.Cu\s*\(type )power\)", r"\1signal)", s)
    x0, yt, x1 = [(v + 20.0) * 1000 for v in corr]
    X1, Y1 = (pcb.W + 20.0) * 1000, (pcb.H + 20.0) * 1000
    pts = [(20000, 20000), (X1, 20000), (X1, Y1), (x1, Y1), (x1, yt), (x0, yt), (x0, Y1), (20000, Y1)]
    poly = "(plane +5V_LED (polygon In2.Cu 0  " + "  ".join("%d %d" % (x, -y) for x, y in pts) + "))"
    s, k = re.subn(r"\(plane \+5V_LED \(polygon In2\.Cu[^)]*\)\)", poly, s)
    assert k == 1, "plane +5V_LED not found"
    # the plane alone does not stop other nets on a signal layer: wire keep-outs outside the
    # corridor (wire_ only, so through vias stay allowed everywhere)
    B = 400000
    ko = ["(wire_keepout \"\" (rect In2.Cu %d %d %d %d))" % r for r in (
        (-B, B, x0, -B), (x1, B, B, -B), (x0, B, x1, -yt))]
    i = s.index("(keepout")
    s = s[:i] + "\n    ".join(ko) + "\n    " + s[i:]
    open(path, "w", encoding="utf-8").write(s)


def add_outer_pours(board):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import pcb
    bx0, by0, bx1, by1 = pcb.BOARD
    x0, y0 = mm(bx0 + pcb.OX - 1), mm(by0 + pcb.OY - 1)
    x1, y1 = mm(bx1 + pcb.OX + 1), mm(by1 + pcb.OY + 1)
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(board.FindNet("GND"))
        z.SetLocalClearance(mm(0.25))
        z.SetMinThickness(mm(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(mm(0.3))
        z.SetThermalReliefSpokeWidth(mm(0.4))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        ol = z.Outline()
        ol.NewOutline()
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            ol.Append(x, y)
        board.Add(z)


def stitch(board, pitch=6.0):
    """GND stitching vias on a grid wherever there is room: ties the L1/L4 pours to the L2 plane."""
    sp = Space(board)
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            sp.vias.append((T(p.x), T(p.y), T(t.GetWidth(pcbnew.F_Cu)) / 2, t.GetNetname()))
        else:
            sp.segs.append((T(t.GetStart().x), T(t.GetStart().y), T(t.GetEnd().x), T(t.GetEnd().y),
                            T(t.GetWidth()) / 2, t.GetNetname(), t.GetLayer()))
    # keep stitching vias out of part courtyards (no vias under ICs, buttons or connectors)
    courts = []
    for fp in board.GetFootprints():
        for layer in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
            sh = fp.GetCourtyard(layer)
            if sh.OutlineCount():
                cb = sh.BBox()
                courts.append((T(cb.GetX()), T(cb.GetY()), T(cb.GetRight()), T(cb.GetBottom())))
    eb = sp.outline.BBox()
    n = 0
    y = T(eb.GetY()) + 2
    while y < T(eb.GetBottom()):
        x = T(eb.GetX()) + 2
        while x < T(eb.GetRight()):
            if not any(c[0] - 0.4 < x < c[2] + 0.4 and c[1] - 0.4 < y < c[3] + 0.4 for c in courts) \
                    and sp.via_ok(x, y, "GND"):
                sp.add_via(x, y, "GND")
                n += 1
            x += pitch
        y += pitch
    return n


ROUTED = os.path.join(HW, "build", "routed.kicad_pcb")
DSN_CRIT, SES_CRIT = os.path.join(HW, "build", "crit.dsn"), os.path.join(HW, "build", "crit.ses")
DSN2, SES2 = os.path.join(HW, "build", "route2.dsn"), os.path.join(HW, "build", "route2.ses")


def finish(src=PREP, ses=SES):
    """Import the autorouter session, close what it left open, pour and stitch, save the board."""
    import shutil
    if src != PREP:
        shutil.copy(src, PREP)
    board = pcbnew.LoadBoard(PREP)
    if os.path.exists(ses):
        pcbnew.ImportSpecctraSES(board, ses)
    board.Save(PREP)
    board = pcbnew.LoadBoard(PREP)       # fresh wrappers after the import
    led_vcc(board, plain_track(board))   # restore the LED driver VCC stubs (dropped by the import)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import leftover                      # connections the autorouter left open
    leftover.run(board)
    board.Save(ROUTED)
    board = pcbnew.LoadBoard(ROUTED)     # fresh wrappers after rip-up (removing items breaks SWIG)
    add_outer_pours(board)
    print("stitching vias:", stitch(board))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(PCB)
    print("saved", PCB)


def sidecar(pcb):
    """LoadBoard takes the rules from the .kicad_pro next to the file and Save writes it back,
    so a board without its own copy would silently fall back to default rules."""
    import shutil
    pro = os.path.splitext(pcb)[0] + ".kicad_pro"
    if os.path.abspath(pro) != os.path.abspath(os.path.join(HW, "vmix-replay-controller.kicad_pro")):
        shutil.copy(os.path.join(HW, "vmix-replay-controller.kicad_pro"), pro)


def pour():
    """Pours and stitching on the routed board."""
    sidecar(ROUTED)
    board = pcbnew.LoadBoard(ROUTED)
    add_outer_pours(board)
    print("stitching vias:", stitch(board))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(PCB)
    print("saved", PCB)


def polish(src, inner=False):
    """Another grid-router pass (with rip-up) over an already routed board, then pours.
    inner: connections still open may take a short hop on In2 (cut out of the +5V_LED plane)."""
    sidecar(src)
    sidecar(ROUTED)
    board = pcbnew.LoadBoard(src)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import leftover
    leftover.run(board, inner=inner)
    board.Save(ROUTED)
    board = pcbnew.LoadBoard(ROUTED)
    add_outer_pours(board)
    print("stitching vias:", stitch(board))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(PCB)
    print("saved", PCB)


def trials(src):
    """Escape attempts one net at a time; an attempt is kept only if fewer nets stay open."""
    import shutil, subprocess
    best = os.path.join(BUILD, "trial_best.kicad_pcb")
    shutil.copy(src, best)
    sidecar(best)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import leftover
    todo = sys.argv[3].split(",")
    n_best = len(todo)
    print("start:", n_best, todo, flush=True)
    for net in todo:
        r = subprocess.run([sys.executable, "-u", __file__, "trial1", best, net], capture_output=True, text=True)
        line = [l for l in r.stdout.splitlines() if l.startswith("RESULT")]
        if not line:
            print(net, "crashed", r.stderr[-300:], flush=True)
            continue
        n = int(line[0].split()[1])
        print(net, "->", n, "open", "(kept)" if n < n_best else "", flush=True)
        if n < n_best:
            n_best = n
            shutil.copy(os.path.join(BUILD, "trial_try.kicad_pcb"), best)
    print("best:", n_best)


def trial1(src, net):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import leftover
    board = pcbnew.LoadBoard(src)
    failed = leftover.run(board, inner=True, escape=True, escape_nets={net}, max_rounds=1)
    out = os.path.join(BUILD, "trial_try.kicad_pcb")
    sidecar(out)
    board.Save(out)
    print("RESULT", len(failed))


BUS = r"^/(BTN_(?!INT$)|LED_(?!SDB$))"      # long key buses: routed last, around the locked local nets
DSN_LOCAL, SES_LOCAL = os.path.join(BUILD, "local.dsn"), os.path.join(BUILD, "local.ses")


def stage(ses, out):
    """Planned order: import an autorouter stage, lock it, export the DSN for the next stage.
    After the critical nets come the short local nets of the MCU/expander spine (out=local),
    then the key buses over what is left (out=full)."""
    board = pcbnew.LoadBoard(PREP)
    pcbnew.ImportSpecctraSES(board, ses)
    board.Save(PREP)
    board = pcbnew.LoadBoard(PREP)
    n = 0
    for t in board.GetTracks():
        if not t.IsLocked():
            t.SetLocked(True)
            n += 1
    board.Save(PREP)
    mcu = sorted({p.GetNetname() for fp in board.GetFootprints() if fp.GetReference() == "U3"
                  for p in fp.Pads()} - {"", "GND", "+3V3", "+3V3A", "+1V1", "+5V_LED"})
    pcbnew.ExportSpecctraDSN(board, DSN)
    if os.environ.get("IN2_SIGNAL"):
        strip_dsn_nets(DSN, ["GND"])
        in2_signal(DSN)
    else:
        strip_dsn_nets(DSN, ["GND", "+5V_LED"])
    if out == "mcu":                     # every RP2040 signal net, end to end, before anything else
        keep_dsn_nets(DSN, DSN_LOCAL, ["^" + re.escape(n) + "$" for n in mcu])
        print("mcu nets:", len(mcu))
    if out == "local":
        keep_dsn_nets(DSN, DSN_LOCAL, [r"^(?!" + BUS[1:] + r")"])
    print("locked %d segments/vias, next stage: %s" % (n, out))


def again():
    """Second autorouter round: the routed board (without pours) back to Freerouting, which now
    only has to finish the open connections and may push the existing tracks aside."""
    board = pcbnew.LoadBoard(ROUTED)
    pcbnew.ExportSpecctraDSN(board, DSN2)
    strip_dsn_nets(DSN2, ["GND", "+5V_LED"])
    print("again ->", DSN2)


if __name__ == "__main__":
    {"prep": prep, "crit": crit, "finish": finish, "again": again, "polish": lambda: polish(sys.argv[2]), "pour": pour, "trials": lambda: trials(sys.argv[2]), "trial1": lambda: trial1(sys.argv[2], sys.argv[3]), "inner": lambda: polish(sys.argv[2], inner=True),
     "finish2": lambda: finish(ROUTED, SES2),
     "stage": lambda: stage(sys.argv[2], sys.argv[3])}[sys.argv[1]]()
