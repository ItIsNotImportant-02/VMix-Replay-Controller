"""Variant study 3 of the LSM VIA layout (replaces variant 2, which misread the request).

Camera row CAM A-D moved left so that CAM D is centred on the left edge of the PLST..TAKE column
(half of it over the column, half over the lever), as on the LSM VIA where the camera keys sit above
the lever. The board grows to the left; every PB26 gap is >= 3.7 mm (pitch 19 mm).
PLAY / LAST CUE / MARK stay level with the cameras, RECORD / PRV CTL below them, offset by half a key.

Run in the KiCad container from hardware/:  LAYERS=4 python3 tools/variant_lsm3.py  -> build/lsm3/
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcb
import variant_lsm as v

P = 19.0                                   # PB26 pitch: 15.3 mm key + 3.7 mm gap
GAP = P - 15.3
v.OUT = os.path.join(pcb.HW, "build", "lsm3")
L = 9.5
CAMD_X = L + 3 * P                          # CAM D centre = left edge of the column
v.COL_X = CAMD_X + 7.65
ROW1, FROW, CAMROW = 10.5, 30.0, 49.5
v.COL_Y0, v.COL_DY = CAMROW + P, P
v.H = v.COL_Y0 + 4 * P + 7.65 + 2.5
JOG_X = v.COL_X + 7.65 + 4.0 + 36.0         # knob 4 mm right of the column
v.W = JOG_X + 36.0 + 2.0
R = v.W - 9.5
v.L, v.R = L, R
v.ROW1, v.FROW = ROW1, FROW
v.FPITCH = (R - L) / 9
v.NOTCH_X1, v.NOTCH_Y = v.COL_X - 7.65 - 1.5, CAMROW + 7.65 + 1.5
v.JOG = (JOG_X, CAMROW + P + 7.65 + 3.0 + 36.0, 22.0, 36.0)
v.USB_X0, v.RJ_X0 = 46.0, 104.0
v.PB26 = {"MENU": (L, ROW1), "SHIFT": (L + P, ROW1), "CLEAR": (R - P, ROW1), "ENTER": (R, ROW1),
          "CAM_A": (L, CAMROW), "CAM_B": (L + P, CAMROW), "CAM_C": (L + 2 * P, CAMROW), "CAM_D": (CAMD_X, CAMROW),
          "PLAY": (R - 2 * P, CAMROW), "LAST_CUE": (R - P, CAMROW), "MARK": (R, CAMROW),
          "RECORD": (R - 1.5 * P, CAMROW + P), "PRV_CTL": (R - 0.5 * P, CAMROW + P)}
for i, n in enumerate(("PLST", "BROWSE", "IN", "OUT", "TAKE")):
    v.PB26[n] = (v.COL_X, v.COL_Y0 + i * P)


def main():
    W, H = v.W, v.H
    cx, cy = v.JOG[0], v.JOG[1]
    os.makedirs(v.OUT, exist_ok=True)
    pcb.LAYERS = int(os.environ.get("LAYERS", 4))
    pcb.OUT_PCB = os.path.join(v.OUT, "board-%dl.kicad_pcb" % pcb.LAYERS)
    pcb.BOARD = (0.0, 0.0, W, H)
    pcb.LEVER_NOTCH = (-20.0, v.NOTCH_Y, v.NOTCH_X1)
    pcb.JOG_HOLE = v.JOG[:3]
    pcb.outline = v.outline
    pcb.PB26_POS = v.PB26
    pcb.FKEY_X0, pcb.FKEY_DX, pcb.FKEY_Y = L, v.FPITCH, FROW
    mid = (v.COL_X + 7.65 + R - 1.5 * P - 7.65) / 2      # between the column and RECORD
    pcb.MOUNT_HOLES = [(mid, CAMROW), (W - 4.5, CAMROW + P), (v.COL_X + 13.0, H - 4.5), (W - 4.5, H - 4.5)]
    pcb.EDGE_CONN = {"J1": "top", "J4": "top"}
    pcb.EDGE_OVERHANG = 1.0
    # hand-soldered connectors on the bottom (USB-C stays on top: JLC assembles it, 0.5 mm pitch)
    pcb.BOTTOM = {"J4", "J5", "J6", "J2", "J3"}
    pcb.FIXED = {
        "J1": (v.USB_X0 + 4.5, None, 180),   # USB-C, rear edge right of SHIFT
        "J4": (v.RJ_X0 + 3.55, None, 0)  ,  # RJ45 left of CLEAR (origin = pin 1, body centre 4.45 mm left)
        "U5": (88.0, 13.0, 0),        # W5500 between the jacks
        "U2": (64.0, 17.0, 0),        # LDO next to the USB input
        "U3": (mid - 2.0, CAMROW + 16.0, 0),     # RP2040 right of the column
        "U4": (mid - 2.0, CAMROW + 30.0, 0),     # flash
        "SW1": (mid + 9.0, CAMROW + 12.0, 0), "SW2": (mid + 9.0, CAMROW + 20.0, 0),
        "U9": (mid - 9.0, CAMROW - 1.0, 0),      # expander, keys
        "U8": (v.COL_X + 14.0, CAMROW + 46.0, 0),  # expander, left keys
        "U6": (v.COL_X + 14.0, CAMROW + 62.0, 0),  # LED driver, left
        "U7": (R - 1.0 * P, CAMROW + P + 14.0, 0),  # LED driver, right
        "J5": (v.COL_X + 14.0, H - 26.0, 270),   # lever sensor connector (cable under the column to the lever)
        "J6": (W - 9.0, cy + 8.0, 90),           # jog sensor connector
        "J2": (cx - 14.0, H - 4.5, 90),          # debug header
        "J3": (cx + 10.0, H - 4.5, 90),           # expansion header
    }
    pcb.place()
    v.panel_svg(os.path.join(v.OUT, "panel.svg"))
    print("board %.1f x %.1f mm" % (W, H))


if __name__ == "__main__":
    main()
