"""Variant study 2 of the LSM VIA layout: wider gaps between keys and the right key block raised.

As on the LSM VIA, the right block is two rows: the upper row (PLAY, LAST CUE, MARK) sits above the
camera row and overhangs the lower row (RECORD, PRV CTL) by half a key to the left; the lower row
is level with CAM A-D. All PB26 keys have >= 3.7 mm gap (pitch 19 mm), F1-F10 >= 5 mm.
The band left of the upper right row is free for the RP2040 and the left expander (routing room).

Run in the KiCad container from hardware/:  LAYERS=4 python3 tools/variant_lsm2.py  -> build/lsm2/
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcb
import variant_lsm as v

P = 19.0                                   # PB26 pitch: 15.3 mm key + 3.7 mm gap
v.OUT = os.path.join(pcb.HW, "build", "lsm2")
v.W = 150.0
v.L, v.R = 9.5, v.W - 9.5
v.ROW1, v.FROW = 10.5, 30.0
UPR, CAMROW = 49.0, 68.5                   # upper right row, camera row (= lower right row)
v.FPITCH = (v.R - v.L) / 9
v.NOTCH_X1, v.NOTCH_Y = 38.0, CAMROW + 9.0
v.COL_X, v.COL_Y0, v.COL_DY = 48.0, CAMROW + 9.0 + 3.0 + 7.65 + 0.35, P
v.H = v.COL_Y0 + 4 * P + 7.65 + 2.5
v.USB_X0, v.RJ_X0 = 43.5, 93.55
v.JOG = (102.0, v.H - 40.0, 22.0, 36.0)
L, R = v.L, v.R
v.PB26 = {"MENU": (L, v.ROW1), "SHIFT": (L + P, v.ROW1), "CLEAR": (R - P, v.ROW1), "ENTER": (R, v.ROW1),
          "CAM_A": (L, CAMROW), "CAM_B": (L + P, CAMROW), "CAM_C": (L + 2 * P, CAMROW), "CAM_D": (L + 3 * P, CAMROW),
          "PLAY": (R - 2 * P, UPR), "LAST_CUE": (R - P, UPR), "MARK": (R, UPR),
          "RECORD": (R - 1.5 * P, CAMROW), "PRV_CTL": (R - 0.5 * P, CAMROW)}
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
    pcb.FKEY_X0, pcb.FKEY_DX, pcb.FKEY_Y = L, v.FPITCH, v.FROW
    pcb.MOUNT_HOLES = [(20.0, 49.0), (W - 4.5, CAMROW + 12.5), (78.0, H - 4.5), (W - 4.5, H - 4.5)]
    pcb.EDGE_CONN = {"J1": "top", "J4": "top"}
    pcb.EDGE_OVERHANG = 1.0
    pcb.FIXED = {
        "J1": (48.0, None, 180),      # USB-C, rear edge right of SHIFT
        "J4": (106.0, None, 180),     # RJ45 left of CLEAR (origin = pin 1, body centre 4.45 mm left)
        "U5": (75.0, 13.0, 0),        # W5500 between the jacks
        "U2": (60.0, 18.0, 0),        # LDO next to the USB input
        "U3": (62.0, 49.0, 0),        # RP2040 in the free band left of the upper right row
        "U4": (82.0, 49.0, 90),       # flash
        "SW1": (44.0, 45.0, 0), "SW2": (44.0, 53.0, 0),
        "U8": (31.0, 49.0, 0),        # expander, left keys
        "U6": (68.0, CAMROW + 26.0, 0),  # LED driver, left
        "U9": (100.0, CAMROW + 14.0, 0),  # expander, right keys
        "U7": (128.0, CAMROW + 14.0, 0),  # LED driver, right
        "J5": (64.0, H - 22.0, 270),  # lever sensor connector, next to the cut-out
        "J6": (W - 10.0, cy, 90),     # jog sensor connector
        "J2": (90.0, H - 5.0, 90),    # debug header
        "J3": (112.0, H - 5.0, 90),   # expansion header
    }
    pcb.place()
    v.panel_svg(os.path.join(v.OUT, "panel.svg"))
    print("board %.1f x %.1f mm" % (W, H))


if __name__ == "__main__":
    main()
