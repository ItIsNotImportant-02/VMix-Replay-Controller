"""Build the main board (vmix-replay-controller.kicad_pcb) from the schematic netlist.

Run inside the kicad/kicad:9.0 container from hardware/:
    kicad-cli sch export netlist --format kicadsexpr -o build/net.net vmix-replay-controller.kicad_sch
    python3 tools/pcb.py place      # outline, fixed parts, auto-placed passives, zones -> build/placed.kicad_pcb
    (freerouting on build/board.dsn -> build/board.ses)
    python3 tools/pcb.py finish     # import routes, fill zones -> vmix-replay-controller.kicad_pcb

Coordinates in the layout section are panel coordinates in mm (panel-layout-v0.5.svg),
origin top-left of the 250 x 190 mm panel; y grows towards the operator.
"""
import math, os, sys
import pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, find, findall

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPDIR = "/usr/share/kicad/footprints"
OX, OY = 20.0, 20.0          # board offset on the KiCad page

# ---------------------------------------------------------------- layout ----
BOARD = (4.0, 4.0, 246.0, 186.0)            # x0, y0, x1, y1 (panel coords)
CORNER_R = 4.0
LEVER_NOTCH = (42.0, 58.0, 76.0)            # x0, y_top, x1 : open notch down to the bottom edge
JOG_HOLE = (192.0, 126.0, 22.0)             # cx, cy, r : bearing housing of the jog shaft
MOUNT_HOLES = [(10, 62), (10, 180), (84, 180), (150, 9), (240, 100), (240, 180), (150, 180), (88, 120)]

# Panel buttons: name -> (x, y) centre, from the approved layout v0.5
PB26_POS = {"MENU": (33.95, 22.0), "SHIFT": (52.45, 22.0), "CLEAR": (197.55, 22.0), "ENTER": (216.05, 22.0),
            "CAM_A": (33.95, 44.0), "CAM_B": (50.45, 44.0), "CAM_C": (66.95, 44.0), "CAM_D": (83.45, 44.0),
            "PLST": (107.45, 70.0), "BROWSE": (107.45, 88.5), "IN": (107.45, 107.0), "OUT": (107.45, 125.5),
            "TAKE": (107.45, 144.0), "PLAY": (160.0, 44.0), "LAST_CUE": (178.5, 44.0), "MARK": (197.0, 44.0),
            "RECORD": (169.0, 62.5), "PRV_CTL": (187.5, 62.5)}
FKEY_X0, FKEY_DX, FKEY_Y = 68.75, 12.5, 22.0

# Fixed parts: ref -> (x, y, rotation). Edge connectors are snapped to the board edge in code.
FIXED = {
    "J1": (14.0, None, 180),      # USB-C, rear edge, top-left
    "J4": (240.0, None, 180),     # RJ45, rear edge, top-right
    "U3": (135.0, 88.0, 0),       # RP2040
    "U4": (135.0, 104.0, 0),      # flash
    "U5": (224.0, 58.0, 0),       # W5500
    "U6": (88.0, 92.0, 0),        # LED driver, left
    "U7": (145.0, 46.0, 0),       # LED driver, right
    "U8": (88.0, 66.0, 0),        # expander, left
    "U9": (124.0, 46.0, 0),       # expander, right
    "U2": (14.0, 30.0, 0),        # LDO
    "J5": (88.0, 150.0, 270),     # lever sensor connector, cable towards the notch
    "J6": (160.0, 112.0, 90),     # jog sensor connector
    "J2": (126.0, 140.0, 0),      # debug header
    "J3": (140.0, 128.0, 0),      # expansion header
    "SW1": (122.0, 112.0, 0), "SW2": (148.0, 112.0, 0),
}
# Passives are placed next to the pad they connect to; these overrides pick the "home" part.
HOME = {}
for r in ("C80", "C81", "R60", "R61", "R62", "R63", "R64", "R65", "R66", "R67"):
    HOME[r] = "J5"
for r in ("C82", "C83", "R68", "R69", "R70", "R71", "R72", "R73", "R74", "R75"):
    HOME[r] = "J6"
for r in ("C60", "C61", "R40"):
    HOME[r] = "U6"
for r in ("C62", "C63", "R41"):
    HOME[r] = "U7"
HOME.update({"C70": "U8", "C71": "U9", "R50": "U9", "R42": "U6", "R43": "U8", "R44": "U8",
             "TP1": "J1", "TP2": "U2", "TP3": "U2", "TP4": "U2", "TP5": "U3", "TP6": "U2", "TP7": "U3",
             "TP10": "U9", "TP11": "U9", "TP12": "U6", "TP13": "U9", "R5": "U2", "D2": "U2",
             "R6": "U2", "R7": "U2", "C8": "U2", "FB1": "U2", "C3": "U2", "C4": "U2", "C5": "U2",
             "C1": "J1", "C2": "J1", "D1": "J1", "F1": "J1", "C6": "U2", "C7": "U2", "R13": "U3", "D3": "U3",
             "R12": "U3", "R11": "U4", "R22": "U5", "R23": "U5"})
# W5500: series R + 49.9R terminations near the chip (LAYOUT-NOTES), LED resistors near the jack
for r in ("R20", "R21", "R24", "R25", "R26", "R27", "R28", "R29", "R30", "R31", "R32", "R35",
          "C48", "C49", "C50", "C51", "C52", "C53", "C54", "C56"):
    HOME[r] = "U5"
for r in ("R33", "R34"):
    HOME[r] = "J4"
# button pull-up arrays next to their expander (U8: first 16 inputs = RN1-RN4, U9: RN5-RN7)
for i in range(1, 8):
    HOME["RN%d" % i] = "U8" if i <= 4 else "U9"

POWER_NETS = {"GND", "+3V3", "+5V", "+5V_LED", "VBUS", "+1V1", "+3V3A"}
NETCLASS_POWER = {"+5V", "+5V_LED", "VBUS", "+3V3", "+3V3A", "+1V1", "GND"}


def mm(v):
    return pcbnew.FromMM(v)


def P(x, y):
    return pcbnew.VECTOR2I(mm(x + OX), mm(y + OY))


# ------------------------------------------------------------- netlist ------
def read_netlist(path):
    t = parse(open(path, encoding="utf-8").read())
    comps = {}
    for c in findall(find(t, "components"), "comp"):
        ref = find(c, "ref")[1]
        props = {find(p, "name")[1]: (find(p, "value")[1] if find(p, "value") else "") for p in findall(c, "property")}
        sp = find(c, "sheetpath")
        comps[ref] = dict(value=find(c, "value")[1], footprint=find(c, "footprint")[1], props=props,
                          sheet_names=find(sp, "names")[1], sheet_tstamps=find(sp, "tstamps")[1],
                          tstamp=find(c, "tstamps")[1])
    nets = {}
    for n in findall(find(t, "nets"), "net"):
        name = find(n, "name")[1]
        nets[name] = [(find(x, "ref")[1], find(x, "pin")[1]) for x in findall(n, "node")]
    return comps, nets


def load_fp(fpid):
    lib, name = fpid.split(":")
    path = os.path.join(HW, "lib", "vrc.pretty") if lib == "vrc" else os.path.join(FPDIR, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise RuntimeError("footprint not found: " + fpid)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def court_bbox(fp, margin=0.25):
    """Courtyard bounding box in mm (x0,y0,x1,y1), falling back to the item bbox."""
    try:
        sh = fp.GetCourtyard(pcbnew.F_CrtYd)
        bb = sh.BBox() if sh.OutlineCount() else fp.GetBoundingBox(False)
    except Exception:
        bb = fp.GetBoundingBox(False)
    x0, y0 = pcbnew.ToMM(bb.GetX()) - OX, pcbnew.ToMM(bb.GetY()) - OY
    return (x0 - margin, y0 - margin, x0 + pcbnew.ToMM(bb.GetWidth()) + margin, y0 + pcbnew.ToMM(bb.GetHeight()) + margin)


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def in_keepout(bb):
    x0, y0, x1, y1 = BOARD
    m = 1.0
    if bb[0] < x0 + m or bb[1] < y0 + m or bb[2] > x1 - m or bb[3] > y1 - m:
        return True
    nx0, ny, nx1 = LEVER_NOTCH
    if overlap(bb, (nx0 - 1, ny - 1, nx1 + 1, y1 + 5)):
        return True
    cx, cy, r = JOG_HOLE
    px = min(max(cx, bb[0]), bb[2])
    py = min(max(cy, bb[1]), bb[3])
    if math.hypot(px - cx, py - cy) < r + 1.0:
        return True
    for hx, hy in MOUNT_HOLES:
        if overlap(bb, (hx - 3.6, hy - 3.6, hx + 3.6, hy + 3.6)):
            return True
    return False


# ---------------------------------------------------------------- build -----
def outline(board):
    x0, y0, x1, y1 = BOARD
    nx0, ny, nx1 = LEVER_NOTCH
    r = CORNER_R
    pts = [(x0 + r, y0), (x1 - r, y0), ("arc", x1, y0, 1), (x1, y0 + r), (x1, y1 - r), ("arc", x1, y1, 2),
           (x1 - r, y1), (nx1, y1), (nx1, ny), (nx0, ny), (nx0, y1), (x0 + r, y1), ("arc", x0, y1, 3),
           (x0, y1 - r), (x0, y0 + r), ("arc", x0, y0, 4)]
    corners = {1: ((x1 - r, y0), (x1, y0 + r), (x1 - r, y0 + r)), 2: ((x1, y1 - r), (x1 - r, y1), (x1 - r, y1 - r)),
               3: ((x0 + r, y1), (x0, y1 - r), (x0 + r, y1 - r)), 4: ((x0, y0 + r), (x0 + r, y0), (x0 + r, y0 + r))}
    seq = [p for p in pts]
    # straight segments
    straight = [((x0 + r, y0), (x1 - r, y0)), ((x1, y0 + r), (x1, y1 - r)), ((x1 - r, y1), (nx1, y1)),
                ((nx1, y1), (nx1, ny)), ((nx1, ny), (nx0, ny)), ((nx0, ny), (nx0, y1)), ((nx0, y1), (x0 + r, y1)),
                ((x0, y1 - r), (x0, y0 + r))]
    for a, b in straight:
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*a)); s.SetEnd(P(*b)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
        board.Add(s)
    for k, (a, b, c) in corners.items():
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        s.SetCenter(P(*c)); s.SetStart(P(*a)); s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
        board.Add(s)
    cx, cy, rr = JOG_HOLE
    s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_CIRCLE)
    s.SetCenter(P(cx, cy)); s.SetEnd(P(cx + rr, cy)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
    board.Add(s)


def setup_board(board):
    board.SetCopperLayerCount(4)
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(4)
    # JLCPCB 4-layer capabilities with margin
    ds.m_TrackMinWidth = mm(0.127)
    ds.m_MinClearance = mm(0.127)
    ds.m_ViasMinSize = mm(0.45)
    ds.m_MinThroughDrill = mm(0.2)   # QFN-44 EP vias 0.2 mm (JLC 4-layer min 0.15)
    ds.m_ViasMinAnnularWidth = mm(0.1)
    ds.m_HoleClearance = mm(0.25)
    ds.m_HoleToHoleMin = mm(0.25)
    ds.m_CopperEdgeClearance = mm(0.3)
    ds.m_SilkClearance = mm(0.0)
    ns = ds.m_NetSettings
    dflt = ns.GetDefaultNetclass()
    dflt.SetClearance(mm(0.15)); dflt.SetTrackWidth(mm(0.2)); dflt.SetViaDiameter(mm(0.6)); dflt.SetViaDrill(mm(0.3))
    pwr = pcbnew.NETCLASS("Power")
    pwr.SetClearance(mm(0.15)); pwr.SetTrackWidth(mm(0.5)); pwr.SetViaDiameter(mm(0.8)); pwr.SetViaDrill(mm(0.4))
    ns.SetNetclass("Power", pwr)
    for n in NETCLASS_POWER:
        ns.SetNetclassPatternAssignment(n, "Power")
    board.SetLayerName(pcbnew.In1_Cu, "In1.Cu")
    board.SetLayerName(pcbnew.In2_Cu, "In2.Cu")
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    board.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_POWER)


def add_zone(board, netname, layer, prio=0, poly=None):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(board.FindNet(netname))
    z.SetAssignedPriority(prio)
    z.SetLocalClearance(mm(0.25))
    z.SetMinThickness(mm(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(mm(0.3))
    z.SetThermalReliefSpokeWidth(mm(0.4))
    z.SetIsFilled(False)
    ol = z.Outline()
    ol.NewOutline()
    x0, y0, x1, y1 = BOARD
    for x, y in (poly or [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]):
        ol.Append(mm(x + OX), mm(y + OY))
    board.Add(z)
    return z


def place():
    comps, nets = read_netlist(os.path.join(HW, "build", "net.net"))
    board = pcbnew.CreateEmptyBoard()
    setup_board(board)
    outline(board)
    netitems = {}
    for name in sorted(nets):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netitems[name] = ni
    pin_net = {}
    for name, nodes in nets.items():
        for ref, pin in nodes:
            pin_net[(ref, pin)] = name

    fps = {}
    for ref, c in sorted(comps.items()):
        if not c["footprint"]:
            continue
        fp = load_fp(c["footprint"])
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        for k in ("LCSC", "MPN"):
            if c["props"].get(k):
                fp.SetField(k, c["props"][k])
        path = c["sheet_tstamps"] + c["tstamp"]
        fp.SetPath(pcbnew.KIID_PATH(path))
        fp.SetSheetname(c["props"].get("Sheetname", ""))
        fp.SetSheetfile(c["props"].get("Sheetfile", ""))
        if c["props"].get("Assembly") or ref.startswith(("J2", "J3")) or ref.startswith("TP"):
            fp.SetExcludedFromBOM(ref.startswith(("J2", "J3", "TP")) or bool(c["props"].get("Assembly")))
        for pad in fp.Pads():
            n = pin_net.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(netitems[n])
        board.Add(fp)
        fps[ref] = fp

    placed = []           # bboxes of placed parts

    def put(ref, x, y, rot=0):
        fp = fps[ref]
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(P(x, y))
        placed.append(court_bbox(fp, 0.0))

    # buttons
    value_to_ref = {}
    for ref, c in comps.items():
        if c["footprint"].startswith("vrc:PB26") or c["footprint"].startswith("vrc:TS5"):
            value_to_ref[c["value"]] = ref
    for name, (x, y) in PB26_POS.items():
        put(value_to_ref[name], x, y)
    for i in range(10):
        put(value_to_ref["F%d" % (i + 1)], FKEY_X0 + i * FKEY_DX, FKEY_Y)
    # edge connectors: snap the courtyard to the rear edge
    for ref in ("J1", "J4"):
        x, _, rot = FIXED[ref]
        put(ref, x, 30, rot)
        placed.pop()
        bb = court_bbox(fps[ref], 0.0)
        dy = (BOARD[1] - 1.0) - bb[1]
        fps[ref].SetPosition(P(x, 30 + dy))
        placed.append(court_bbox(fps[ref], 0.0))
    for ref, (x, y, rot) in FIXED.items():
        if ref in ("J1", "J4") or ref not in fps:
            continue
        put(ref, x, y, rot)
    # mounting holes
    for i, (hx, hy) in enumerate(MOUNT_HOLES):
        fp = load_fp("MountingHole:MountingHole_3.2mm_M3_Pad_Via")
        fp.SetReference("H%d" % (i + 1)); fp.SetValue("M3")
        fp.SetPosition(P(hx, hy))
        fp.SetExcludedFromBOM(True); fp.SetExcludedFromPosFiles(True)
        for pad in fp.Pads():
            pad.SetNet(netitems["GND"])
        board.Add(fp)

    # auto-place the rest next to the pad they connect to
    fixed = set(FIXED) | set(value_to_ref.values())
    rest = [r for r in fps if r not in fixed]

    def target(ref):
        home = HOME.get(ref)
        my_nets = [pin_net.get((ref, p.GetNumber())) for p in fps[ref].Pads()]
        sig = [n for n in my_nets if n and n not in POWER_NETS]
        cands = []
        for n in sig:
            for r2, pin in nets[n]:
                if r2 != ref and (r2 in fixed or r2 == home):
                    cands.append((0 if r2 == home else 1, r2, pin))
        if home and not any(c[1] == home for c in cands):
            p = fps[home].GetPosition()
            # nearest pad of home on a shared power net
            best = None
            for pad in fps[home].Pads():
                if pad.GetNetname() in my_nets:
                    best = pad.GetPosition()
                    break
            p = best or p
            return pcbnew.ToMM(p.x) - OX, pcbnew.ToMM(p.y) - OY
        if cands:
            cands.sort()
            _, r2, pin = cands[0]
            for pad in fps[r2].Pads():
                if pad.GetNumber() == pin:
                    return pcbnew.ToMM(pad.GetPosition().x) - OX, pcbnew.ToMM(pad.GetPosition().y) - OY
        # decoupling caps etc: nearest power pad of an IC on the same sheet
        sheet = comps[ref]["sheet_names"]
        for r2 in sorted(fixed):
            if r2 in comps and comps[r2]["sheet_names"] == sheet and r2.startswith("U"):
                for pad in fps[r2].Pads():
                    if pad.GetNetname() in my_nets and pad.GetNetname() != "GND":
                        return pcbnew.ToMM(pad.GetPosition().x) - OX, pcbnew.ToMM(pad.GetPosition().y) - OY
        p = fps[home or "U3"].GetPosition()
        return pcbnew.ToMM(p.x) - OX, pcbnew.ToMM(p.y) - OY

    def sort_key(r):
        # ICs' own passives first; small parts after larger ones
        return (0 if r.startswith(("U", "Y", "F", "FB", "D")) else 1, r)

    used_targets = {}
    for ref in sorted(rest, key=sort_key):
        tx, ty = target(ref)
        fp = fps[ref]
        best = None
        step = 0.5
        for ring in range(0, 120):
            pts = []
            if ring == 0:
                pts = [(0, 0)]
            else:
                for k in range(-ring, ring + 1):
                    pts += [(k, -ring), (k, ring), (-ring, k), (ring, k)]
            for rot in (0, 90):
                for dx, dy in pts:
                    x, y = tx + dx * step, ty + dy * step
                    fp.SetOrientationDegrees(rot)
                    fp.SetPosition(P(x, y))
                    bb = court_bbox(fp, 0.15)
                    if in_keepout(bb) or any(overlap(bb, o) for o in placed):
                        continue
                    best = (x, y, rot)
                    break
                if best:
                    break
            if best:
                break
        if not best:
            raise RuntimeError("no place for " + ref)
        put(ref, *best)

    # planes: In1 = GND, In2 = +5V_LED (everything 5 V for the LEDs and drivers), outer GND pours
    add_zone(board, "GND", pcbnew.In1_Cu)
    add_zone(board, "+5V_LED", pcbnew.In2_Cu)
    add_zone(board, "GND", pcbnew.F_Cu)
    add_zone(board, "GND", pcbnew.B_Cu)
    out = os.path.join(HW, "build", "placed.kicad_pcb")
    board.Save(out)
    pcbnew.ExportSpecctraDSN(board, os.path.join(HW, "build", "board.dsn"))
    print("placed", len(fps), "footprints")


def write_project_rules():
    """KiCad 9 keeps design rules and net classes in the .kicad_pro, not in the board file."""
    import json
    pro = os.path.join(HW, "vmix-replay-controller.kicad_pro")
    d = json.load(open(pro, encoding="utf-8"))
    rules = {"min_clearance": 0.127, "min_track_width": 0.127, "min_via_diameter": 0.45,
             "min_through_hole_diameter": 0.2, "min_via_annular_width": 0.1, "min_hole_clearance": 0.25,
             "min_hole_to_hole": 0.25, "min_copper_edge_clearance": 0.3, "min_silk_clearance": 0.0,
             "min_resolved_spokes": 1}
    d.setdefault("board", {}).setdefault("design_settings", {}).setdefault("rules", {}).update(rules)

    def nc(name, track, via_d, via_drill, prio):
        return {"name": name, "clearance": 0.15, "track_width": track, "via_diameter": via_d, "via_drill": via_drill,
                "diff_pair_width": 0.2, "diff_pair_gap": 0.25, "microvia_diameter": 0.3, "microvia_drill": 0.1,
                "wire_width": 6, "bus_width": 12, "line_style": 0, "priority": prio,
                "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)"}
    d["net_settings"] = {"meta": {"version": 4},
                         "classes": [nc("Default", 0.2, 0.6, 0.3, 2147483647), nc("Power", 0.5, 0.8, 0.4, 0)],
                         "netclass_patterns": [{"netclass": "Power", "pattern": n} for n in sorted(NETCLASS_POWER)]}
    json.dump(d, open(pro, "w", encoding="utf-8"), indent=2)


def finish():
    write_project_rules()
    board = pcbnew.LoadBoard(os.path.join(HW, "build", "placed.kicad_pcb"))
    ses = os.path.join(HW, "build", "board.ses")
    if os.path.exists(ses):
        pcbnew.ImportSpecctraSES(board, ses)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    board.Save(os.path.join(HW, "vmix-replay-controller.kicad_pcb"))
    print("saved")


if __name__ == "__main__":
    {"place": place, "finish": finish}[sys.argv[1]]()
