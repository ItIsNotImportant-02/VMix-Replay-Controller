"""Export JLCPCB assembly files (BOM + CPL) from the board.

    python3 tools/jlc.py [board.kicad_pcb [outdir]]   ->  build/jlc/BOM-JLCPCB.csv, build/jlc/CPL-JLCPCB.csv

Plain Python 3, no KiCad needed (reads the .kicad_pcb directly), so it runs on Windows too.
Run it again after every change of placement: the CPL holds positions.

Rotation and origin corrections: JLCPCB places parts by the EasyEDA footprint of the LCSC part,
whose zero orientation and origin differ from KiCad's for some packages. Each entry below was
derived by comparing the pad coordinates of the KiCad footprint with the EasyEDA footprint of the
LCSC part (easyeda2kicad export, 2026-11-11): pin 1 position -> rotation, pad centroid -> offset.
Always check the JLCPCB placement preview before paying anyway.
"""
import csv, fnmatch, math, os, sys
from collections import OrderedDict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, findall, find

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# footprint name pattern -> (rotation to add [deg, CCW], (dx, dy) of the EasyEDA origin in KiCad footprint coords [mm])
CORRECTIONS = [
    ("QFN-56-1EP_7x7mm_P0.4mm*", 0, (0, 0)),          # RP2040: pin 1 left-top in both
    ("LQFP-48_7x7mm_P0.5mm", 270, (0, 0)),             # W5500: EasyEDA pin 1 bottom-left
    ("QFN-44-1EP_5x5mm_P0.4mm", 270, (0, 0)),          # IS31FL3236A: EasyEDA pin 1 bottom-left
    ("Texas_RTW_WQFN-24-1EP*", 270, (0, 0)),           # TCA9555: EasyEDA pin 1 bottom-left
    ("SOIC-8_5.3x5.3mm_P1.27mm", 270, (0, 0)),         # W25Q128: EasyEDA pin 1 bottom-left
    ("SOT-23-6", 270, (0, 0)),                         # USBLC6: EasyEDA pin 1 bottom-left
    ("SOT-223-3_TabPin2", 180, (0, 0)),                # LDL1117: EasyEDA tab on the left
    ("USB_C_Receptacle_HRO_TYPE-C-31-M-12", 0, (0, -1.39)),   # origin at the locating pegs + 1.21
    ("RJ45_Hanrun_HR911105A_Horizontal", 0, (4.45, 4.35)),     # KiCad origin = pin 1, EasyEDA = body centre
    ("JST_PH_S8B-PH-SM4-TB*", 0, (0, 0.03)),
    ("R_Array_Convex_4x0603", 270, (0, 0)),            # C1980: EasyEDA pin 1 bottom-left, pins in a row
    ("LED_0603_1608Metric", 0, (0, 0)),                # XL-1608: cathode = pad 1 on -x in both (datasheet p. 7)
    # 2-pad passives, crystals, SOD-123F, fuse, TS-1187A: identical orientation and origin
]


def correction(fpname):
    for pat, rot, off in CORRECTIONS:
        if fnmatch.fnmatch(fpname, pat):
            return rot, off
    return 0, (0, 0)


def footprints(path):
    t = parse(open(path, encoding="utf-8").read())
    for fp in findall(t, "footprint"):
        lib = fp[1]
        props = {p[1]: p[2] for p in findall(fp, "property")}
        at = find(fp, "at")
        x, y = float(at[1]), float(at[2])
        rot = float(at[3]) if len(at) > 3 else 0.0
        layer = find(fp, "layer")[1]
        attr = [str(a) for a in (find(fp, "attr") or [])[1:]]
        yield dict(ref=props.get("Reference", ""), value=props.get("Value", ""), lcsc=props.get("LCSC", ""),
                   fp=lib.split(":")[-1], x=x, y=y, rot=rot, layer=layer, attr=attr, dnp="dnp" in attr)


def main():
    board = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HW, "vmix-replay-controller.kicad_pcb")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HW, "build", "jlc")
    os.makedirs(out, exist_ok=True)
    bom = OrderedDict()
    cpl = []
    missing = []
    for f in sorted(footprints(board), key=lambda f: (f["ref"].rstrip("0123456789"), int("0" + "".join(c for c in f["ref"] if c.isdigit())))):
        if "exclude_from_bom" in f["attr"] or f["dnp"]:
            continue
        if not f["lcsc"] or f["lcsc"] == "?":
            missing.append(f["ref"])
            continue
        key = (f["value"], f["fp"], f["lcsc"])
        bom.setdefault(key, []).append(f["ref"])
        if "exclude_from_pos_files" in f["attr"]:
            continue
        drot, (dx, dy) = correction(f["fp"])
        a = math.radians(f["rot"])
        # KiCad: y down, rotation CCW as seen from the top -> offset rotates with the part
        ox = dx * math.cos(a) + dy * math.sin(a)
        oy = -dx * math.sin(a) + dy * math.cos(a)
        bottom = f["layer"].startswith("B")
        rot = (f["rot"] + drot) % 360
        if bottom:
            rot = (180 - rot) % 360   # JLCPCB convention for bottom side (no bottom parts on this board)
        cpl.append([f["ref"], "%.3f" % (f["x"] + ox), "%.3f" % -(f["y"] + oy), "Bottom" if bottom else "Top", "%g" % rot])
    with open(os.path.join(out, "BOM-JLCPCB.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (val, fp, lcsc), refs in bom.items():
            w.writerow([val, ",".join(refs), fp, lcsc])
    with open(os.path.join(out, "CPL-JLCPCB.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        w.writerows(cpl)
    print("BOM: %d lines, %d parts; CPL: %d placements -> %s" % (len(bom), sum(len(v) for v in bom.values()), len(cpl), out))
    if missing:
        print("WITHOUT LCSC NUMBER (not assembled):", ", ".join(missing))
        sys.exit(1)


if __name__ == "__main__":
    main()
