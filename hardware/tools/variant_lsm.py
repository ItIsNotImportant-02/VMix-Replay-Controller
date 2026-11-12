"""Variant study: one narrow board with the button layout of the EVS LSM VIA (not the main design).

LSM VIA order: top row MENU SHIFT [programmable] CLEAR ENTER, under it F1-F10 across the full width.
Here the programmable keys are left out and their place on the rear edge takes the USB-C and the RJ45,
so the rear edge needs no side connectors and the board is only as wide as the F1-F10 row.

Run in the KiCad container from hardware/:
    python3 tools/variant_lsm.py            # LAYERS=2 or 4 via env, default 4
Outputs in build/lsm/: board.kicad_pcb, panel.svg (button layout drawing).
Board coordinates = panel coordinates in mm, origin top-left of the board, y towards the operator.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcb

HW = pcb.HW
OUT = os.path.join(HW, "build", "lsm")

W, H = 140.0, 152.0
ROW1, FROW, CAMROW, RECROW = 10.0, 29.0, 48.0, 66.5
L, R = 9.5, W - 9.5                       # outer key centres (PB26 courtyard 16 mm, 1.5 mm to the edge)
FPITCH = (R - L) / 9                      # F1 under MENU, F10 under ENTER
NOTCH_X1, NOTCH_Y = 38.0, 57.0            # lever cut-out, open to the left and to the front edge
COL_X, COL_Y0, COL_DY = 47.5, 68.0, 18.5  # PLST..TAKE column right of the lever
JOG = (98.0, 113.0, 22.0, 36.0)           # cx, cy, bearing hole r, knob r (Ø72 knob on the panel)

PB26 = {"MENU": (L, ROW1), "SHIFT": (L + 18.0, ROW1), "CLEAR": (R - 18.0, ROW1), "ENTER": (R, ROW1),
        "CAM_A": (L, CAMROW), "CAM_B": (L + 16.5, CAMROW), "CAM_C": (L + 33.0, CAMROW), "CAM_D": (L + 49.5, CAMROW),
        "PLAY": (R - 37.0, CAMROW), "LAST_CUE": (R - 18.5, CAMROW), "MARK": (R, CAMROW),
        "RECORD": (R - 27.75, RECROW), "PRV_CTL": (R - 9.25, RECROW)}
for i, n in enumerate(("PLST", "BROWSE", "IN", "OUT", "TAKE")):
    PB26[n] = (COL_X, COL_Y0 + i * COL_DY)


def outline(board):
    """Rectangle without the lower-left corner (lever), plus the jog bearing hole."""
    P, mm, pn = pcb.P, pcb.mm, pcb.pcbnew
    pts = [(0, 0), (W, 0), (W, H), (NOTCH_X1, H), (NOTCH_X1, NOTCH_Y), (0, NOTCH_Y), (0, 0)]
    for a, b in zip(pts, pts[1:]):
        s = pn.PCB_SHAPE(board, pn.SHAPE_T_SEGMENT)
        s.SetStart(P(*a)); s.SetEnd(P(*b)); s.SetLayer(pn.Edge_Cuts); s.SetWidth(mm(0.1))
        board.Add(s)
    cx, cy, r, _ = JOG
    s = pn.PCB_SHAPE(board, pn.SHAPE_T_CIRCLE)
    s.SetCenter(P(cx, cy)); s.SetEnd(P(cx + r, cy)); s.SetLayer(pn.Edge_Cuts); s.SetWidth(mm(0.1))
    board.Add(s)


def panel_svg(path):
    """1:1 drawing of the panel layout over the board outline."""
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%gmm" height="%gmm" viewBox="-6 -14 %g %g" '
         'font-family="Arial, sans-serif">' % (W + 12, H + 22, W + 12, H + 22),
         '<rect x="-6" y="-14" width="%g" height="%g" fill="#fff"/>' % (W + 12, H + 22),
         '<path d="M0 0H%g V%g H%g V%g H0 Z" fill="#e8f3ea" stroke="#2c7a3f" stroke-width="0.5"/>'
         % (W, H, NOTCH_X1, NOTCH_Y)]
    cx, cy, r, kr = JOG
    o.append('<circle cx="%g" cy="%g" r="%g" fill="#ddd" fill-opacity="0.7" stroke="#222" stroke-width="0.5"/>' % (cx, cy, kr))
    o.append('<circle cx="%g" cy="%g" r="%g" fill="#fff" stroke="#2c7a3f" stroke-width="0.4" stroke-dasharray="1 1"/>' % (cx, cy, r))
    o.append('<text x="%g" y="%g" font-size="4" text-anchor="middle" font-weight="bold">JOG Ø72</text>' % (cx, cy + 1.5))
    o.append('<rect x="12" y="%g" width="14" height="%g" rx="2" fill="#555"/>' % (NOTCH_Y + 6, H - NOTCH_Y - 12))
    o.append('<text x="19" y="%g" font-size="3.2" fill="#fff" text-anchor="middle" transform="rotate(-90 19 %g)">PÁKA</text>'
             % ((NOTCH_Y + H) / 2, (NOTCH_Y + H) / 2))
    for name, (x, y) in PB26.items():
        o.append('<rect x="%g" y="%g" width="15.3" height="15.3" rx="1" fill="#eef" stroke="#222" stroke-width="0.35"/>'
                 % (x - 7.65, y - 7.65))
        o.append('<text x="%g" y="%g" font-size="2.4" text-anchor="middle" font-weight="bold">%s</text>'
                 % (x, y + 0.9, name.replace("_", " ")))
    for i in range(10):
        x = L + i * FPITCH
        o.append('<rect x="%g" y="%g" width="9.2" height="9.2" rx="1" fill="#fff4c2" stroke="#222" stroke-width="0.35"/>'
                 % (x - 4.6, FROW - 4.6))
        o.append('<text x="%g" y="%g" font-size="2.4" text-anchor="middle" font-weight="bold">F%d</text>' % (x, FROW + 0.9, i + 1))
    for label, x0, w in (("USB-C", 39.5, 9.0), ("RJ45", 84.75, 16.0)):
        o.append('<rect x="%g" y="-1" width="%g" height="%g" fill="#cfe0ff" stroke="#225" stroke-width="0.35"/>'
                 % (x0, w, 8 if label == "USB-C" else 21))
        o.append('<text x="%g" y="-3" font-size="3" text-anchor="middle">%s</text>' % (x0 + w / 2, label))
    o.append('<text x="0" y="-8" font-size="3.4" fill="#333">Varianta LSM VIA · deska %g × %g mm · zadní hrana nahoře</text>' % (W, H))
    o.append('</svg>')
    open(path, "w", encoding="utf-8").write("\n".join(o) + "\n")


def main():
    os.makedirs(OUT, exist_ok=True)
    pcb.LAYERS = int(os.environ.get("LAYERS", 4))
    pcb.OUT_PCB = os.path.join(OUT, "board-%dl.kicad_pcb" % pcb.LAYERS)
    pcb.BOARD = (0.0, 0.0, W, H)
    pcb.LEVER_NOTCH = (-20.0, NOTCH_Y, NOTCH_X1)       # keep-out only; outline() draws the cut-out
    pcb.JOG_HOLE = JOG[:3]
    pcb.outline = outline
    pcb.PB26_POS = PB26
    pcb.FKEY_X0, pcb.FKEY_DX, pcb.FKEY_Y = L, FPITCH, FROW
    pcb.MOUNT_HOLES = [(75.0, 148.5), (W - 4.5, 148.0), (W - 4.5, RECROW), (76.0, CAMROW), (61.0, 62.0)]
    pcb.EDGE_CONN = {"J1": "top", "J4": "top"}
    pcb.EDGE_OVERHANG = 1.0
    pcb.FIXED = {
        "J1": (44.0, None, 180),      # USB-C on the rear edge, between SHIFT and CLEAR
        "J4": (97.2, None, 180),     # RJ45 next to CLEAR (origin = pin 1, body centre 4.45 mm left)
        "U5": (68.0, 13.0, 0),        # W5500 between the two jacks
        "U2": (54.0, 17.0, 0),        # LDO next to the USB input
        "U3": (73.0, 76.0, 0),        # RP2040 between the column and the jog
        "U4": (68.0, 90.0, 0),        # flash
        "U9": (89.0, 62.0, 0),        # expander, right keys
        "U7": (124.0, 85.0, 0),       # LED driver, right
        "U8": (66.0, 108.0, 0),       # expander, left keys
        "U6": (72.0, 123.0, 0),       # LED driver, left
        "J5": (63.0, 140.0, 270),     # lever sensor connector, next to the cut-out
        "J6": (130.0, 112.0, 90),     # jog sensor connector
        "J2": (86.0, 146.0, 90),      # debug header
        "J3": (107.0, 145.0, 90),     # expansion header
        "SW1": (82.0, 82.0, 0), "SW2": (90.0, 82.0, 0),
    }
    pcb.place()
    panel_svg(os.path.join(OUT, "panel.svg"))


if __name__ == "__main__":
    main()
