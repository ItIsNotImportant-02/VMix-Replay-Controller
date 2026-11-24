"""Hand placement of the ICs' support parts (replaces the auto-placer for everything listed here).

Rules (LAYOUT-NOTES.md, datasheets, Hardware design with RP2040):
- every decoupling capacitor sits at the power pin it belongs to, power pad towards the pin,
  GND pad away from the chip (a GND via goes next to it, straight into the In1 GND plane);
- crystals right at their oscillator pins, load capacitors at the crystal, nothing else between;
- QSPI flash next to the QSPI pins of the RP2040, USB series resistors next to its USB pins;
- Ethernet terminations in signal order between the W5500 and the RJ45, pairs side by side;
- USB ESD protection right behind the USB-C pins, power path in one direction: jack, fuse, TVS, caps, LDO;
- passives of one group in one row with the same orientation (easy to inspect, easy for JLC);
- at least ~1.5 mm from pads of hand-soldered THT parts (soldering iron).

Usage inside the KiCad container, from hardware/:
    python3 tools/arrange.py [in.kicad_pcb] [out.kicad_pcb]
or from pcb.py: arrange.apply(board).
"""
import math, os, sys
import pcbnew

OX, OY = 20.0, 20.0

# ------------------------------------------------------------------ ICs -----
IC = {
    "U5": (88.0, 12.5, 180),   # W5500: Ethernet pins 1-12 face the RJ45 (right), SPI faces left/down
    "U3": (97.0, 67.5, 0),     # RP2040 as in the reference design: flash upper left, crystal below
    "U4": (88.4, 59.0, 180),   # QSPI flash, CS/SD1/SD2 (pins 1-3) face the QSPI corner of the RP2040
    "U2": (68.0, 14.0, 0),     # LDO: input pin on the left (from the USB), output tab on the right
    "U9": (89.6, 46.4, 180),   # button expander for the right half (rotated: GPIO sides face its buttons)
    "U8": (97.0, 92.0, 0),     # button expander for the left half (right of the bus corridor)
    "U6": (88.15, 111.5, 270),  # LED driver, left half (rotated: outputs face the left buttons, control pins right)
    "U7": (131.3, 82.5, 180),   # LED driver, right half (rotated: outputs face up to its buttons)
}

# Routing channels kept free of parts by the solver (x0, y0, x1, y1).
KEEP_CLEAR = [
    (91.6, 62.0, 96.0, 63.6),     # RP2040 QSPI pins 51-56 fanning out to the flash (upper left)
    (97.8, 58.6, 98.6, 63.6),     # RP2040 USB D-/D+ (pins 46/47) straight up to R3/R4
    (99.2, 71.2, 100.6, 72.8),    # RP2040 SPI (pins 27/28)
    (100.8, 69.2, 104.6, 71.4),   # RP2040 SPI (pins 29-32) out to the right
]

# ------------------------------------------------- explicit positions -------
# ref: (x, y, rot). rot 0 = pad 1 left, 90 = pad 1 down, 180 = pad 1 right, 270 = pad 1 up.
EXPLICIT = {
    # USB-C input: ESD right behind the data pins, CC resistors next to the CC pins
    "U1": (50.5, 11.8, 90),
    "R2": (46.6, 11.0, 270), "R1": (54.4, 11.0, 270),
    # power path: VBUS -> F1 -> +5V (TVS, input caps) -> LDO input / FB1
    "TP1": (58.4, 4.4, 0), "F1": (58.4, 9.6, 270), "D1": (58.4, 15.2, 270),
    "TP2": (62.2, 6.4, 0), "C1": (61.6, 11.6, 270), "C2": (61.6, 16.0, 270),
    "C6": (73.9, 12.8, 270), "C7": (73.9, 16.6, 270),       # LDO output (tab) caps
    "TP6": (67.2, 20.0, 0), "TP4": (73.9, 20.4, 0),
    "TP3": (56.6, 21.4, 0), "FB1": (60.4, 20.6, 0),         # +5V -> +5V_LED
    "C5": (60.4, 22.4, 0), "C3": (64.0, 20.4, 0), "C4": (64.0, 22.6, 0),
    "R5": (70.6, 21.6, 0), "D2": (70.6, 23.3, 180),         # power LED (+3V3)
    # W5500 analog supply: FB2 + bulk at the top left of the chip
    "C40": (80.4, 2.4, 0), "FB2": (80.4, 4.4, 0),
    # W5500 top side, in pin order: 1V2O 22, AVDD 21, TOCAP 20, AVDD 17, AVDD 15
    "C49": (84.8, 5.0, 90), "C43": (86.4, 5.0, 90), "C48": (88.0, 5.0, 90), "C42": (89.6, 5.0, 90), "C41": (91.2, 5.0, 90),
    # W5500 crystal at XI/XO (pins 30/31, left side), 1M across it
    "R21": (80.4, 9.0, 0), "Y2": (80.4, 12.6, 90), "C50": (77.0, 11.2, 0), "C51": (77.0, 14.0, 0),
    # W5500 digital side: SPI pull-ups and +3V3 bulk below the crystal
    "R35": (79.6, 16.6, 0), "R22": (79.6, 18.2, 0), "R23": (79.6, 19.8, 0), "C56": (79.6, 21.8, 0),
    # W5500 right side, top to bottom in pin order: EXRES, AVDD 11, AVDD 8, RX pair, AVDD 4, TX pair
    "R20": (95.4, 5.6, 0), "R36": (98.6, 5.6, 0),           # EXRES (pin 10): 10k + 2.4k to GND
    "C46": (95.4, 8.8, 0), "C45": (95.4, 10.4, 0),
    "R29": (95.4, 12.2, 0), "R30": (95.4, 13.8, 0),         # RX series 0R (pins 6/5)
    "C53": (98.6, 12.2, 0), "C54": (98.6, 13.8, 0),         # RX coupling 6.8nF
    "C44": (95.4, 15.6, 0),
    "R24": (95.4, 17.4, 0), "R25": (95.4, 19.0, 0),         # TX series 0R (pins 2/1)
    "R26": (98.6, 17.4, 0), "R27": (98.6, 19.0, 0),         # TX 49.9R to +3V3A
    "R31": (101.6, 18.6, 90), "R32": (103.2, 18.6, 90),     # RX 49.9R to RCT
    "R28": (108.0, 23.0, 0), "C52": (111.2, 23.0, 0),       # TCT (J4 pin 4): 10R + 22nF
    "C55": (114.4, 23.0, 0),                                # RCT (J4 pin 5)
    "R33": (111.4, 1.8, 0), "R34": (114.6, 1.8, 0),         # link / activity LEDs in the jack
    # RP2040, top side: core caps above their pins, USB D-/D+ straight up between them to R3/R4
    "C21": (96.1, 60.4, 90),                                # DVDD pin 50
    "C16": (96.1, 57.2, 90), "C15": (94.5, 57.2, 90),                                # USB_VDD 48 + IOVDD 49 (trace between C21 and USB)
    "C19": (99.4, 60.4, 90), "C18": (101.0, 60.4, 90), "C17": (102.6, 60.4, 90),   # VREG_VOUT 45, VREG_VIN 44, ADC_AVDD 43
    "R3": (97.8, 56.0, 270), "R4": (99.4, 56.0, 270),       # USB 27R, RP2040 side pad down towards pins 46/47
    "C22": (101.2, 55.2, 90),                                # 3V3 bulk 10uF at VREG_VIN
    # RP2040 right side
    "C14": (102.9, 64.9, 0),                                # IOVDD 42
    "C13": (102.9, 68.1, 0),                                # IOVDD 33
    "C8": (106.4, 64.2, 0), "R7": (106.4, 65.8, 0), "R6": (106.4, 62.6, 0),   # +5V sense (pin 41)
    "R13": (106.4, 67.4, 0), "D3": (106.4, 69.0, 180),      # status LED (pin 37)
    # RP2040 left side
    "C10": (91.2, 64.9, 180), "C11": (91.2, 68.5, 180),     # IOVDD 1, IOVDD 10
    "R43": (87.2, 66.6, 0), "R44": (87.2, 68.2, 0),         # I2C pull-ups at the master
    "TP10": (84.0, 65.6, 0), "TP11": (84.0, 68.4, 0),
    # RP2040 bottom: DVDD 23 cap, IOVDD 22 cap behind it, crystal to the lower left
    "C20": (98.2, 73.6, 270), "C12": (97.2, 77.0, 270),
    "R10": (95.0, 73.6, 180),                               # XOUT 1k, XOUT pad towards the RP2040
    "Y1": (92.4, 76.8, 0), "C23": (91.3, 80.2, 270), "C24": (95.4, 77.4, 270),
    "R12": (100.6, 75.4, 90),                               # RUN pull-up
    "TP5": (100.8, 78.6, 0), "TP7": (100.8, 81.4, 0),
    # flash: VCC cap at pin 8, BOOTSEL resistor on CS; BOOTSEL / RESET buttons left below
    "C25": (85.0, 63.4, 0), "R11": (90.0, 54.6, 0),
    "SW1": (108.6, 81.2, 0), "SW2": (116.8, 81.2, 0),      # BOOTSEL, RESET below the RP2040
    # button expander U9 (upper buttons) and its pull-up arrays RN4-7 (16 inputs)
    "RN4": (81.4, 39.6, 0), "RN5": (85.0, 39.6, 0), "RN6": (88.6, 39.6, 0), "RN7": (92.2, 39.6, 0),
    "TP13": (84.3, 45.0, 0), "TP12": (93.4, 109.5, 0),
    # button expander U8 (left column, F4-F7, RECORD, PRV_CTL): pull-up arrays RN1-3 on its right
    "RN1": (103.0, 87.5, 0), "RN2": (103.0, 91.3, 0), "RN3": (103.0, 95.1, 0),
}

# ------------------------------------------------- decoupling at pins -------
# (part, ic, pin): the solver puts the part right outside that pin (power pad towards the pin).
DECOUPLE = [
    # W5500: TOCAP and 1V2O first, then the AVDD / VDD pins on the top and bottom
    ("C47", "U5", "44"),
    # expanders, LED drivers
    ("C70", "U8", "21"), ("C71", "U9", "21"), ("R50", "U9", "22"),
    ("C60", "U6", "38"), ("C61", "U6", "38"), ("R40", "U6", "40"), ("R42", "U6", "36"),
    ("C62", "U7", "38"), ("C63", "U7", "37"), ("R41", "U7", "40"),
]

# --------------------------------------------------------- rows / groups ----
def rows():
    """Groups laid out as tidy rows: name -> list of (ref, x, y, rot)."""
    out = {}
    # sensor connectors (SMD on the bottom, the top side above them is free):
    # 33R series + 10k pull-ups + RC on OUT, in the order of the connector pins
    for conn, x0, y0, d, refs in (("J5", 85.6, 121.6, 1, ("R60", "R61", "R62", "R63", "R67", "C80", "R64", "R65", "R66", "C81")),
                                  ("J6", 147.0, 116.1, 1, ("R68", "R69", "R70", "R71", "R75", "C82", "R72", "R73", "R74", "C83"))):
        lst = []
        for i, r in enumerate(refs[:6]):
            lst.append((r, x0, y0 + i * 1.9 * d, 0))
        for i, r in enumerate(refs[6:]):
            lst.append((r, x0 + 3.4, y0 + i * 1.9 * d + 1.9, 0))
        out[conn] = lst
    return out


# ----------------------------------------------------------------- engine ---
def P(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x + OX), pcbnew.FromMM(y + OY))


def bbox(fp, margin=0.0):
    top = not fp.IsFlipped()
    if top:
        sh = fp.GetCourtyard(pcbnew.F_CrtYd)
        bb = sh.BBox() if sh.OutlineCount() else fp.GetBoundingBox(False)
    else:
        if all(p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD for p in fp.Pads()):
            return None                       # SMD on the bottom: top side above it is free
        out = []
        for p in fp.Pads():                   # THT on the bottom: each pad (+ iron clearance) on top
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
                continue
            b = p.GetBoundingBox()
            x0, y0 = pcbnew.ToMM(b.GetX()) - OX, pcbnew.ToMM(b.GetY()) - OY
            m = margin + 1.0
            out.append((x0 - m, y0 - m, x0 + pcbnew.ToMM(b.GetWidth()) + m, y0 + pcbnew.ToMM(b.GetHeight()) + m))
        return out
    x0, y0 = pcbnew.ToMM(bb.GetX()) - OX, pcbnew.ToMM(bb.GetY()) - OY
    return (x0 - margin, y0 - margin, x0 + pcbnew.ToMM(bb.GetWidth()) + margin, y0 + pcbnew.ToMM(bb.GetHeight()) + margin)


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def apply(board, keepout=None):
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    rowmap = rows()
    movable = set(IC) | set(EXPLICIT) | {d[0] for d in DECOUPLE} | {r[0] for lst in rowmap.values() for r in lst}
    movable &= set(fps)
    obstacles = [("channel", r) for r in KEEP_CLEAR]
    for ref, fp in fps.items():
        if ref in movable:
            continue
        b = bbox(fp)
        if isinstance(b, list):
            obstacles += [(ref, x) for x in b]
        elif b:
            obstacles.append((ref, b))
    placed = []
    problems = []

    def put(ref, x, y, rot, check=True):
        fp = fps[ref]
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(P(x, y))
        b = bbox(fp, 0.0)
        if check:
            hit = [r for r, o in obstacles + placed if overlap(b, o) and (r != "channel" or ref not in IC)]
            if hit or (keepout and keepout(b)):
                problems.append("%s at (%.1f, %.1f) hits %s" % (ref, x, y, ", ".join(hit) or "keep-out"))
        placed.append((ref, b))

    for ref, (x, y, rot) in IC.items():
        put(ref, x, y, rot)
    for ref, (x, y, rot) in EXPLICIT.items():
        if ref in fps:
            put(ref, x, y, rot)
    for lst in rowmap.values():
        for ref, x, y, rot in lst:
            put(ref, x, y, rot)

    def pad_of(ref, num):
        for p in fps[ref].Pads():
            if p.GetNumber() == num:
                q = p.GetPosition()
                return pcbnew.ToMM(q.x) - OX, pcbnew.ToMM(q.y) - OY
        raise KeyError(ref + "." + num)

    for part, ic, pin in DECOUPLE:
        if part not in fps:
            continue
        px, py = pad_of(ic, pin)
        c = fps[ic].GetPosition()
        cx, cy = pcbnew.ToMM(c.x) - OX, pcbnew.ToMM(c.y) - OY
        dx, dy = px - cx, py - cy
        if abs(dx) >= abs(dy):
            n, t = (1 if dx > 0 else -1, 0), (0, 1)
        else:
            n, t = (0, 1 if dy > 0 else -1), (1, 0)
        # radial: pad 1 (the pin's net) towards the chip
        rot_rad = {(1, 0): 0, (-1, 0): 180, (0, 1): 270, (0, -1): 90}[n]
        rot_tan = 0 if t == (1, 0) else 90
        best = None
        for d in (2.3, 2.9, 3.8, 4.6, 5.5):
            for s in (0, 0.5, -0.5, 1.0, -1.0, 1.5, -1.5, 2.0, -2.0, 2.5, -2.5, 3.0, -3.0, 3.5, -3.5, 4.0, -4.0):
                for rot in (rot_rad, rot_tan):
                    dd = d if rot == rot_rad else d - 0.6
                    x, y = px + n[0] * dd + t[0] * s, py + n[1] * dd + t[1] * s
                    fp = fps[part]
                    fp.SetOrientationDegrees(rot)
                    fp.SetPosition(P(x, y))
                    b = bbox(fp, 0.2)
                    if any(overlap(b, o) for _, o in obstacles + placed) or (keepout and keepout(b)):
                        continue
                    best = (x, y, rot)
                    break
                if best:
                    break
            if best:
                break
        if not best:
            problems.append("no place for %s at %s.%s" % (part, ic, pin))
            continue
        put(part, *best, check=False)
    silk(board)
    return problems


def silk(board):
    """Silkscreen: only reference designators. Dense 0603 rows would overprint each other, so the
    references of passives stay on F.Fab (visible in KiCad and in the assembly drawing), ICs,
    connectors, crystals, switches and test points keep them on the silkscreen."""
    import re
    for fp in board.GetFootprints():
        for f in fp.GetFields():
            if f.GetName() != "Reference" and f.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
                f.SetVisible(False)
        if re.match(r"^(R|C|D|FB|F|RN)\d+$", fp.GetReference()):
            fp.Reference().SetVisible(False)
    # put each visible reference where it does not touch pads or another reference
    T = pcbnew.ToMM
    pads = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            b = p.GetBoundingBox()
            pads.append((T(b.GetX()), T(b.GetY()), T(b.GetRight()), T(b.GetBottom())))
    eb = board.GetBoardEdgesBoundingBox()
    edge = (T(eb.GetX()) + 0.5, T(eb.GetY()) + 0.5, T(eb.GetRight()) - 0.5, T(eb.GetBottom()) - 0.5)
    taken = []
    for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
        ref = fp.Reference()
        if not ref.IsVisible() or ref.GetLayer() != pcbnew.F_SilkS:
            continue
        sh = fp.GetCourtyard(pcbnew.F_CrtYd)
        if not sh.OutlineCount():
            continue
        cb = sh.BBox()
        x0, y0, x1, y1 = T(cb.GetX()), T(cb.GetY()), T(cb.GetRight()), T(cb.GetBottom())
        ref.SetTextAngleDegrees(0)
        tb = ref.GetBoundingBox()
        w, h = T(tb.GetWidth()), T(tb.GetHeight())
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        cands = [(cx, y0 - h / 2 - 0.15), (cx, y1 + h / 2 + 0.15), (x0 - w / 2 - 0.2, cy), (x1 + w / 2 + 0.2, cy),
                 (x0 + w / 2, y0 - h / 2 - 0.15), (x1 - w / 2, y0 - h / 2 - 0.15),
                 (x0 + w / 2, y1 + h / 2 + 0.15), (x1 - w / 2, y1 + h / 2 + 0.15)]
        best = None
        for tx, ty in cands:
            r = (tx - w / 2 - 0.1, ty - h / 2 - 0.1, tx + w / 2 + 0.1, ty + h / 2 + 0.1)
            if r[0] < edge[0] or r[1] < edge[1] or r[2] > edge[2] or r[3] > edge[3]:
                continue
            if any(overlap(r, q) for q in pads) or any(overlap(r, q) for q in taken):
                continue
            best = (tx, ty, r)
            break
        if best:
            ref.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(best[0]), pcbnew.FromMM(best[1])))
            taken.append(best[2])


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "vmix-replay-controller.kicad_pcb"
    dst = sys.argv[2] if len(sys.argv) > 2 else src
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import pcb
    b = pcbnew.LoadBoard(src)
    probs = apply(b, pcb.in_keepout)
    for p in probs:
        print("!!", p)
    b.Save(dst)
    print("saved", dst, "problems:", len(probs))
