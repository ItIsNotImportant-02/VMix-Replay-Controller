"""Build the main board (vmix-replay-controller.kicad_pcb) from the schematic netlist.

Run inside the kicad/kicad:9.0 container from hardware/:
    kicad-cli sch export netlist --format kicadsexpr -o build/net.net vmix-replay-controller.kicad_sch
    python3 tools/pcb.py place      # outline, fixed parts, auto-placed passives, zones -> build/placed.kicad_pcb
    (freerouting on build/board.dsn -> build/board.ses)
    python3 tools/pcb.py finish     # import routes, fill zones -> vmix-replay-controller.kicad_pcb

    python3 tools/pcb.py panel      # 1:1 panel drawing -> docs/layout/panel-layout-v0.6.svg

Coordinates in the layout section are board coordinates in mm, origin top-left of the board
(rear edge), y grows towards the operator. The panel uses the same coordinates.
"""
import math, os, sys
import pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, find, findall

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPDIR = "/usr/share/kicad/footprints"
OX, OY = 20.0, 20.0          # board offset on the KiCad page

# ---------------------------------------------------------------- layout ----
# Layout v0.6 after the EVS LSM VIA (docs/layout/panel-layout-v0.6.svg):
#   rear row   MENU SHIFT  [USB-C ... RJ45]  CLEAR ENTER   (the LSM's programmable keys -> the jacks)
#   F1-F10     across the full width, F1 under MENU, F10 under ENTER
#   CAM A-D    left, above the lever, CAM D half over the PLST..TAKE column;  PLAY LAST CUE MARK right
#   RECORD PRV_CTL under the right block, offset by half a key
#   lever in the open lower-left corner, PLST..TAKE column next to it, jog right
# Every PB26 gap is 3.7 mm (pitch 19 mm). The board is the smallest rectangle around all of it.
PITCH = 19.0                                # PB26 15.3 mm + 3.7 mm gap
KEY_L = 9.5                                 # outer key centre from the board edge (courtyard 16 mm)
ROW1, FKEY_Y, CAMROW = 10.5, 30.0, 49.5
CAMD_X = KEY_L + 3 * PITCH                  # CAM D centre = left edge of the column
COL_X = CAMD_X + 7.65
COL_Y0 = CAMROW + PITCH
JOG_X = COL_X + 7.65 + 4.0 + 36.0           # Ø72 knob 4 mm right of the column
W = JOG_X + 36.0 + 2.0
H = COL_Y0 + 4 * PITCH + 7.65 + 2.5
KEY_R = W - KEY_L
BOARD = (0.0, 0.0, W, H)                    # x0, y0, x1, y1 (panel = board coordinates, y towards the operator)
CORNER_R = 0.0
LEVER_NOTCH = (-20.0, CAMROW + 7.65 + 1.5, COL_X - 7.65 - 1.5)   # open lower-left corner: x0 (keep-out only), y_top, x1
JOG_HOLE = (JOG_X, COL_Y0 + 7.65 + 3.0 + 36.0, 22.0)             # cx, cy, r : bearing housing of the jog shaft
JOG_KNOB_R = 36.0
USB_X0, RJ_X0 = 46.0, 104.0                 # left edges of the jack bodies on the rear edge
_MID = (COL_X + 7.65 + KEY_R - 1.5 * PITCH - 7.65) / 2           # between the column and RECORD
MOUNT_HOLES = [(_MID, CAMROW), (W - 4.5, CAMROW + PITCH), (COL_X + 13.0, H - 4.5), (W - 4.5, H - 4.5)]

# Panel buttons: name -> (x, y) centre
PB26_POS = {"MENU": (KEY_L, ROW1), "SHIFT": (KEY_L + PITCH, ROW1),
            "CLEAR": (KEY_R - PITCH, ROW1), "ENTER": (KEY_R, ROW1),
            "CAM_A": (KEY_L, CAMROW), "CAM_B": (KEY_L + PITCH, CAMROW), "CAM_C": (KEY_L + 2 * PITCH, CAMROW),
            "CAM_D": (CAMD_X, CAMROW),
            "PLAY": (KEY_R - 2 * PITCH, CAMROW), "LAST_CUE": (KEY_R - PITCH, CAMROW), "MARK": (KEY_R, CAMROW),
            "RECORD": (KEY_R - 1.5 * PITCH, CAMROW + PITCH), "PRV_CTL": (KEY_R - 0.5 * PITCH, CAMROW + PITCH)}
for _i, _n in enumerate(("PLST", "BROWSE", "IN", "OUT", "TAKE")):
    PB26_POS[_n] = (COL_X, COL_Y0 + _i * PITCH)
FKEY_X0, FKEY_DX = KEY_L, (KEY_R - KEY_L) / 9

# Fixed parts: ref -> (x, y, rotation). Edge connectors are snapped to the board edge in code.
_CX, _CY = JOG_HOLE[0], JOG_HOLE[1]
FIXED = {
    "J1": (USB_X0 + 4.5, None, 180),          # USB-C on the rear edge right of SHIFT (top side, JLC assembles it)
    "J4": (RJ_X0 + 3.55, None, 0),            # RJ45 on the rear edge left of CLEAR, bottom side (origin = pin 1)
    "U5": (88.0, 13.0, 0),                    # W5500 between the jacks
    "U2": (64.0, 17.0, 0),                    # LDO next to the USB input
    "U3": (_MID - 2.0, CAMROW + 16.0, 0),     # RP2040 right of the column
    "U4": (_MID - 2.0, CAMROW + 30.0, 0),     # flash
    "SW1": (_MID + 9.0, CAMROW + 12.0, 0), "SW2": (_MID + 9.0, CAMROW + 20.0, 0),
    "U9": (_MID - 9.0, CAMROW - 1.0, 0),      # expander (RN5-RN7) between CAM D and PLAY
    "U8": (COL_X + 14.0, CAMROW + 46.0, 0),   # expander (RN1-RN4) next to the column
    "U6": (COL_X + 14.0, CAMROW + 62.0, 0),   # LED driver, left
    "U7": (KEY_R - PITCH, CAMROW + PITCH + 14.0, 0),   # LED driver, right
    "J5": (COL_X + 14.0, H - 26.0, 270),      # lever sensor connector, bottom side
    "J6": (W - 9.0, _CY + 8.0, 90),           # jog sensor connector, bottom side
    "J2": (_CX - 14.0, H - 4.5, 90),          # debug header, bottom side
    "J3": (_CX + 10.0, H - 4.5, 90),          # expansion header, bottom side
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

# overridable by variant scripts
NETLIST = os.path.join(HW, "build", "net.net")
OUT_PCB = os.path.join(HW, "build", "placed.kicad_pcb")
LAYERS = 4
EDGE_CONN = {"J1": "top", "J4": "top"}      # edge connectors snapped to a board edge
EDGE_OVERHANG = 1.0
BOTTOM = {"J4", "J5", "J6", "J2", "J3"}    # hand-soldered connectors on the bottom (USB-C stays on top: 0.5 mm pitch, JLC)

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
        sh = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
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
    """Rectangle without the lower-left corner (lever), plus the jog bearing hole."""
    x0, y0, x1, y1 = BOARD
    _, ny, nx1 = LEVER_NOTCH
    pts = [(x0, y0), (x1, y0), (x1, y1), (nx1, y1), (nx1, ny), (x0, ny), (x0, y0)]
    for a, b in zip(pts, pts[1:]):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*a)); s.SetEnd(P(*b)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
        board.Add(s)
    cx, cy, rr = JOG_HOLE
    s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_CIRCLE)
    s.SetCenter(P(cx, cy)); s.SetEnd(P(cx + rr, cy)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
    board.Add(s)


def panel(path=None):
    """1:1 drawing of the panel layout over the board outline (no KiCad needed)."""
    path = path or os.path.join(os.path.dirname(HW), "docs", "layout", "panel-layout-v0.6.svg")
    x0, y0, x1, y1 = BOARD
    _, ny, nx1 = LEVER_NOTCH
    w, h = x1 + 12, y1 + 26
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%gmm" height="%gmm" viewBox="-6 -16 %g %g" '
         'font-family="Arial, sans-serif">' % (w, h, w, h),
         '<rect x="-6" y="-16" width="%g" height="%g" fill="#fff"/>' % (w, h),
         '<path d="M0 0H%g V%g H%g V%g H0 Z" fill="#e8f3ea" stroke="#2c7a3f" stroke-width="0.5"/>' % (x1, y1, nx1, ny)]
    cx, cy, r = JOG_HOLE
    o.append('<circle cx="%g" cy="%g" r="%g" fill="#ddd" fill-opacity="0.7" stroke="#222" stroke-width="0.5"/>' % (cx, cy, JOG_KNOB_R))
    o.append('<circle cx="%g" cy="%g" r="%g" fill="#fff" stroke="#2c7a3f" stroke-width="0.4" stroke-dasharray="1 1"/>' % (cx, cy, r))
    o.append('<text x="%g" y="%g" font-size="4" text-anchor="middle" font-weight="bold">JOG Ø72</text>' % (cx, cy + 1.5))
    lx = nx1 / 2
    o.append('<rect x="%g" y="%g" width="14" height="%g" rx="2" fill="#555"/>' % (lx - 7, ny + 6, y1 - ny - 12))
    o.append('<text x="%g" y="%g" font-size="3.2" fill="#fff" text-anchor="middle" transform="rotate(-90 %g %g)">PÁKA</text>'
             % (lx, (ny + y1) / 2, lx, (ny + y1) / 2))
    for name, (x, y) in PB26_POS.items():
        o.append('<rect x="%g" y="%g" width="15.3" height="15.3" rx="1" fill="#eef" stroke="#222" stroke-width="0.35"/>' % (x - 7.65, y - 7.65))
        o.append('<text x="%g" y="%g" font-size="2.4" text-anchor="middle" font-weight="bold">%s</text>' % (x, y + 0.9, name.replace("_", " ")))
    for i in range(10):
        x = FKEY_X0 + i * FKEY_DX
        o.append('<rect x="%g" y="%g" width="9.2" height="9.2" rx="1" fill="#fff4c2" stroke="#222" stroke-width="0.35"/>' % (x - 4.6, FKEY_Y - 4.6))
        o.append('<text x="%g" y="%g" font-size="2.4" text-anchor="middle" font-weight="bold">F%d</text>' % (x, FKEY_Y + 0.9, i + 1))
    for label, xx, bw, bh, note in (("USB-C", USB_X0, 9.0, 8, "horní strana"), ("RJ45", RJ_X0, 16.0, 21, "spodní strana")):
        o.append('<rect x="%g" y="-1" width="%g" height="%g" fill="#cfe0ff" stroke="#225" stroke-width="0.35" stroke-dasharray="%s"/>'
                 % (xx, bw, bh, "none" if label == "USB-C" else "1 0.6"))
        o.append('<text x="%g" y="-3" font-size="3" text-anchor="middle">%s (%s)</text>' % (xx + bw / 2, label, note))
    o.append('<text x="0" y="-9" font-size="3.4" fill="#333">vMix Replay Controller · layout v0.6 podle EVS LSM VIA · deska %.0f × %.0f mm · '
             '1:1 (tisk 100 %%) · zadní hrana nahoře</text>' % (x1, y1))
    o.append('<line x1="0" y1="%g" x2="50" y2="%g" stroke="#222" stroke-width="0.4"/>' % (y1 + 6, y1 + 6))
    o.append('<text x="25" y="%g" font-size="2.8" text-anchor="middle">kontrola tisku: 50 mm</text>' % (y1 + 9.5))
    o.append('</svg>')
    open(path, "w", encoding="utf-8").write("\n".join(o) + "\n")
    print("panel ->", path)


def setup_board(board):
    board.SetCopperLayerCount(LAYERS)
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(LAYERS)
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
    comps, nets = read_netlist(NETLIST)
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
        if ref in BOTTOM and not fp.IsFlipped():
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(P(x, y))
        if ref in BOTTOM and all(p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD for p in fp.Pads()):
            return            # SMD on the bottom: the top side above it stays free
        placed.append(court_bbox(fp, 0.0))

    # buttons
    value_to_ref = {}
    for ref, c in comps.items():
        if c["footprint"].startswith("vrc:PB26") or c["footprint"].startswith("vrc:TS5"):
            value_to_ref[c["value"]] = ref
    if value_to_ref:
        for name, (x, y) in PB26_POS.items():
            put(value_to_ref[name], x, y)
        for i in range(10):
            put(value_to_ref["F%d" % (i + 1)], FKEY_X0 + i * FKEY_DX, FKEY_Y)
    # edge connectors: snap the courtyard to a board edge
    for ref, side in EDGE_CONN.items():
        if ref not in fps:
            continue
        x, y, rot = FIXED[ref]
        if side in ("left", "right"):
            x = (BOARD[0] + 15) if side == "left" else (BOARD[2] - 15)
        else:
            y = (BOARD[1] + 15) if side == "top" else (BOARD[3] - 15)
        put(ref, x, y, rot)
        placed.pop()
        bb = court_bbox(fps[ref], 0.0)
        o = EDGE_OVERHANG
        if side == "left":
            fps[ref].SetPosition(P(x + BOARD[0] - o - bb[0], y))
        elif side == "right":
            fps[ref].SetPosition(P(x + BOARD[2] + o - bb[2], y))
        elif side == "top":
            fps[ref].SetPosition(P(x, y + BOARD[1] - o - bb[1]))
        else:
            fps[ref].SetPosition(P(x, y + BOARD[3] + o - bb[3]))
        placed.append(court_bbox(fps[ref], 0.0))
    for ref, (x, y, rot) in FIXED.items():
        if ref in EDGE_CONN or ref not in fps:
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
        p = fps[home or ("U3" if "U3" in fps else sorted(r for r in fps if r.startswith("U"))[0])].GetPosition()
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
    if LAYERS == 4:
        add_zone(board, "GND", pcbnew.In1_Cu)
        add_zone(board, "+5V_LED", pcbnew.In2_Cu)
    add_zone(board, "GND", pcbnew.F_Cu)
    add_zone(board, "GND", pcbnew.B_Cu)
    board.Save(OUT_PCB)
    pcbnew.ExportSpecctraDSN(board, os.path.splitext(OUT_PCB)[0] + ".dsn")
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
    {"place": place, "finish": finish, "panel": panel}[sys.argv[1]]()
