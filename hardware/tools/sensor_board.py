"""Sensor board for the lever and the jog: MT6701 + decoupling + JST-PH 8 pin.

One design, two pieces (lever, jog). Mechanical interface is fixed by docs ("Mechanika jogu a páky"):
  board 28 x 28 mm, MT6701 package centre = board centre, front side = chip side = reference plane,
  4x Ø3.2 holes on a 22 x 22 mm square (two for M3 screws, two for printed locating pins),
  nothing taller than the SOP-8 on the front, side-entry JST-PH 8 pin on the back, cable leaving past the edge.

Connector pinout is the same as J5/J6 on the main board, cable straight (pin 1 to pin 1):
  1 +3V3, 2 GND, 3 MODE, 4 P6 = A/SDA/DO, 5 P7 = B/SCL/CLK, 6 P8 = Z/CSN, 7 OUT, 8 GND.
MT6701 SOP-8: 1 VDD, 2 MODE, 3 OUT, 4 GND, 5 PUSH (unused), 6 A/SDA/DO, 7 B/SCL/CLK, 8 Z/CSN.

Run inside the kicad/kicad:9.0 container from hardware/:
    python3 tools/sensor_board.py sch
    kicad-cli sch export netlist --format kicadsexpr -o sensor-board/build/net.net sensor-board/sensor-board.kicad_sch
    python3 tools/sensor_board.py pcb
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
HW = os.path.dirname(HERE)
OUT = os.path.join(HW, "sensor-board")
NAME = "sensor-board"

# ------------------------------------------------------------------ circuit --
# verified on JLCPCB 2026-11-23: MT6701CT-STD-R C3003196 (448 pcs, the plain -STD has 0), H3V3HD3U C20615801 (Preferred)
LCSC = {"MT6701": "C3003196", "100nF": "C14663", "1uF": "C15849", "TVS": "C20615801"}


def parts():
    from schgen import Part
    P = []
    P.append(Part("U1", "Sensor_Magnetic:MT6701CT", "MT6701CT-STD", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
                  pins={"1": "+3V3", "2": "SNS_MODE", "3": "SNS_OUT", "4": "GND",
                        "6": "SNS_DO", "7": "SNS_CLK", "8": "SNS_CSN"},
                  lcsc=LCSC["MT6701"], mpn="MT6701CT-STD-R"))
    P.append(Part("C1", "Device:C", "100nF", "Capacitor_SMD:C_0603_1608Metric", pins={"1": "+3V3", "2": "GND"},
                  lcsc=LCSC["100nF"]))
    P.append(Part("C2", "Device:C", "1uF", "Capacitor_SMD:C_0603_1608Metric", pins={"1": "+3V3", "2": "GND"},
                  lcsc=LCSC["1uF"]))
    # unidirectional ESD/TVS, VRWM 3.3 V (datasheet: TVS on VDD "recommended for better reliability"); pad 1 = cathode
    P.append(Part("D1", "Device:D", "H3V3HD3U", "Diode_SMD:D_SOD-323", pins={"1": "+3V3", "2": "GND"},
                  lcsc=LCSC["TVS"], mpn="hongjiacheng H3V3HD3U", desc="ESD/TVS 3.3 V unidirectional, Preferred"))
    P.append(Part("J1", "Connector_Generic:Conn_01x08", "SENSOR", "Connector_JST:JST_PH_S8B-PH-K_1x08_P2.00mm_Horizontal",
                  pins={"1": "+3V3", "2": "GND", "3": "SNS_MODE", "4": "SNS_DO", "5": "SNS_CLK", "6": "SNS_CSN",
                        "7": "SNS_OUT", "8": "GND"},
                  mpn="S8B-PH-K-S", in_bom=False, fields={"Assembly": "ruční pájení"}))
    return {p.ref: p for p in P}


def sch():
    import schgen
    from schdraw import Drawing
    from layout import B
    libs = schgen.SymbolLibs()
    d = Drawing(NAME, libs, parts(), paper="A4", title="vMix Replay Controller - destička snímače (páka, jog)",
                rev="1.0", date="2026-11-23")
    b = B(d, 10, 10)
    d.block("Snímač úhlu MT6701 (SSI), destička 28 x 28 mm", 25.4, 25.4, 25.4 + 160, 25.4 + 90,
            note="MT6701 přesně ve středu desky, magnet Ø6 x 2,5 diametrální 3,0 mm nad přední stranou desky.\n"
                 "Konektor = J5/J6 hlavní desky, kabel 1:1. Pin 5 PUSH nezapojen. MODE řídí hlavní deska.")
    b.place("U1", 28, 22)
    for p in ("1", "2", "3", "4", "5", "6", "7", "8"):
        b.term("U1", p, 2)
    b.v2("C1", 12, 22)
    b.v2("C2", 16, 22)
    b.v2("D1", 20, 22, 90)
    b.place("J1", 50, 22)
    for p in range(1, 9):
        b.term("J1", str(p), 2)
    # power comes in through the connector: flag +3V3 and GND on the J1 stubs
    from schdraw import DIRS
    for p in ("1", "2"):
        x, y, dd = d.pin("J1", p)
        dx, dy = DIRS[dd]
        d.flag(x + dx * 5.08, y + dy * 5.08)
    os.makedirs(OUT, exist_ok=True)
    d.write(os.path.join(OUT, NAME + ".kicad_sch"))
    missing = d.check_all_done()
    if missing or d.pin_on_wire:
        sys.exit("unhandled pins: %s / pins lying on wires: %s" % (missing, d.pin_on_wire))
    write_pro()
    print("schematic ok")


def write_pro():
    pro = os.path.join(OUT, NAME + ".kicad_pro")
    rules = {"min_clearance": 0.15, "min_track_width": 0.15, "min_via_diameter": 0.5,
             "min_through_hole_diameter": 0.3, "min_via_annular_width": 0.1, "min_hole_clearance": 0.25,
             "min_hole_to_hole": 0.25, "min_copper_edge_clearance": 0.3, "min_silk_clearance": 0.0,
             "min_resolved_spokes": 1}

    def nc(name, track, via_d, via_drill, prio):
        return {"name": name, "clearance": 0.2, "track_width": track, "via_diameter": via_d, "via_drill": via_drill,
                "diff_pair_width": 0.2, "diff_pair_gap": 0.25, "microvia_diameter": 0.3, "microvia_drill": 0.1,
                "wire_width": 6, "bus_width": 12, "line_style": 0, "priority": prio,
                "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)"}
    d = {"board": {"design_settings": {"rules": rules}},
         "meta": {"filename": NAME + ".kicad_pro", "version": 3},
         "net_settings": {"meta": {"version": 4},
                          "classes": [nc("Default", 0.25, 0.6, 0.3, 2147483647), nc("Power", 0.4, 0.6, 0.3, 0)],
                          "netclass_patterns": [{"netclass": "Power", "pattern": n} for n in ("+3V3", "GND")]},
         "sheets": [], "text_variables": {}}
    json.dump(d, open(pro, "w", encoding="utf-8"), indent=2)


# --------------------------------------------------------------------- board --
SIZE = 28.0
HOLE = 11.0          # holes at (±11, ±11) from the centre
CX = CY = 100.0      # board centre on the KiCad page


def pcb():
    import pcbnew
    import pcb as main
    mm, V = pcbnew.FromMM, lambda x, y: pcbnew.VECTOR2I(pcbnew.FromMM(CX + x), pcbnew.FromMM(CY + y))
    comps, nets = main.read_netlist(os.path.join(OUT, "build", "net.net"))
    board = pcbnew.CreateEmptyBoard()
    board.SetCopperLayerCount(2)
    ds = board.GetDesignSettings()
    ds.m_TrackMinWidth, ds.m_MinClearance, ds.m_CopperEdgeClearance = mm(0.15), mm(0.15), mm(0.3)
    ni = {}
    for n in sorted(nets):
        ni[n] = pcbnew.NETINFO_ITEM(board, n)
        board.Add(ni[n])
    pinnet = {(r, p): n for n, nodes in nets.items() for r, p in nodes}

    # outline with 1 mm corner radius
    h, r = SIZE / 2, 1.0
    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts)
        s.SetStart(V(*a)); s.SetEnd(V(*b)); s.SetWidth(mm(0.1)); board.Add(s)
    def arc(c, a, ang):
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_ARC); s.SetLayer(pcbnew.Edge_Cuts)
        s.SetCenter(V(*c)); s.SetStart(V(*a)); s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T), True)
        s.SetWidth(mm(0.1)); board.Add(s)
    seg((-h + r, -h), (h - r, -h)); seg((h, -h + r), (h, h - r)); seg((h - r, h), (-h + r, h)); seg((-h, h - r), (-h, -h + r))
    arc((h - r, -h + r), (h - r, -h), 90); arc((h - r, h - r), (h, h - r), 90)
    arc((-h + r, h - r), (-h + r, h), 90); arc((-h + r, -h + r), (-h, -h + r), 90)

    def put(ref, x, y, rot=0, back=False):
        c = comps[ref]
        fp = main.load_fp(c["footprint"])
        fp.SetReference(ref); fp.SetValue(c["value"])
        fp.Value().SetVisible(False)
        fp.SetPosition(V(x, y)); fp.SetOrientationDegrees(rot)
        path = pcbnew.KIID_PATH("/" + c["tstamp"])
        fp.SetPath(path)
        if ref == "J1":
            fp.SetExcludedFromBOM(True)
        for k, v in c["props"].items():
            if k in ("LCSC", "MPN", "Assembly"):
                fp.SetField(k, v)
                fp.GetFieldByName(k).SetVisible(False)
        for pad in fp.Pads():
            n = pinnet.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(ni[n])
        board.Add(fp)
        if back:
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        return fp

    # MT6701: package centre exactly on the board centre (the Hall element sits in the package centre)
    u1 = put("U1", 0, 0, 0)
    # decoupling next to VDD (pin 1, upper left), TVS next to it
    put("C1", -5.4, -1.9, 90)
    put("C2", -7.2, -1.9, 90)
    put("D1", -5.6, -5.0, 0)
    # JST-PH side entry on the back, pin row 7 mm below the centre, body and cable towards the lower edge
    j1 = put("J1", 0, 7.0, 0, back=True)
    # centre the pin row: mirrored on the back, pin 1 at x = +7 ... pin 8 at x = -7 (seen from the front)
    p1 = [p for p in j1.Pads() if p.GetNumber() == "1"][0]
    off = pcbnew.ToMM(p1.GetPosition().x) - CX - 7.0
    j1.Move(pcbnew.VECTOR2I(mm(-off), 0))

    # U1 GND pin straight to a via into the back ground pour (the signals fence the pin in on the front)
    t = pcbnew.PCB_TRACK(board); t.SetStart(V(-2.475, 1.905)); t.SetEnd(V(-4.1, 1.905)); t.SetWidth(mm(0.4))
    t.SetLayer(pcbnew.F_Cu); t.SetNet(ni["GND"]); board.Add(t)
    v = pcbnew.PCB_VIA(board); v.SetPosition(V(-4.1, 1.905)); v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3))
    v.SetNet(ni["GND"]); board.Add(v)

    # mounting holes: M3 screws on one diagonal, printed locating pins on the other
    # H1/H2 (rear edge, away from the connector) = M3 screws, H3/H4 (connector side) = printed locating pins
    for i, (x, y) in enumerate(((-HOLE, -HOLE), (HOLE, -HOLE), (-HOLE, HOLE), (HOLE, HOLE))):
        fp = pcbnew.FootprintLoad("/usr/share/kicad/footprints/MountingHole.pretty", "MountingHole_3.2mm_M3")
        fp.SetReference("H%d" % (i + 1)); fp.SetPosition(V(x, y)); board.Add(fp)
        fp.SetBoardOnly(True)

    # printed standoffs Ø7 sit on the front around the holes: keep every front part 4 mm away from the hole centres
    import math
    for fp in board.GetFootprints():
        if fp.GetReference().startswith("H"):
            continue
        for pad in fp.Pads():
            px, py = pcbnew.ToMM(pad.GetPosition().x) - CX, pcbnew.ToMM(pad.GetPosition().y) - CY
            for hx in (-HOLE, HOLE):
                for hy in (-HOLE, HOLE):
                    if math.hypot(px - hx, py - hy) < 4.0 + 0.8:
                        sys.exit("%s pad %s too close to the standoff at %s,%s" % (fp.GetReference(), pad.GetNumber(), hx, hy))

    # silk: centre cross and magnet circle on the front, labels
    def silk(a, b, layer=pcbnew.F_SilkS):
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(layer)
        s.SetStart(V(*a)); s.SetEnd(V(*b)); s.SetWidth(mm(0.15)); board.Add(s)
    circ = pcbnew.PCB_SHAPE(board); circ.SetShape(pcbnew.SHAPE_T_CIRCLE); circ.SetLayer(pcbnew.F_Fab)
    circ.SetCenter(V(0, 0)); circ.SetEnd(V(3, 0)); circ.SetWidth(mm(0.1)); board.Add(circ)
    for (a, b) in (((-13, 0), (-11.8, 0)), ((11.8, 0), (13, 0)), ((0, -13), (0, -11.8))):
        silk(a, b)
    for txt, (x, y), layer, mirror in (("MT6701 v1.0", (5.0, -10.5), pcbnew.F_SilkS, False),
                                       ("VRC SENSOR", (0, -10.5), pcbnew.B_SilkS, True)):
        t = pcbnew.PCB_TEXT(board); t.SetText(txt); t.SetPosition(V(x, y)); t.SetLayer(layer)
        t.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8))); t.SetTextThickness(mm(0.12)); t.SetMirrored(mirror)
        board.Add(t)

    # ground pours on both sides
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board); z.SetLayer(layer); z.SetNet(ni["GND"])
        z.SetLocalClearance(mm(0.25)); z.SetMinThickness(mm(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(mm(0.3)); z.SetThermalReliefSpokeWidth(mm(0.4))
        ol = z.Outline(); ol.NewOutline()
        for x, y in ((-h, -h), (h, -h), (h, h), (-h, h)):
            ol.Append(mm(CX + x), mm(CY + y))
        board.Add(z)

    os.makedirs(os.path.join(OUT, "build"), exist_ok=True)
    board.Save(os.path.join(OUT, "build", "placed.kicad_pcb"))
    bb = j1.GetCourtyard(pcbnew.B_CrtYd).BBox()
    print("J1 courtyard x %.2f..%.2f y %.2f..%.2f" % (pcbnew.ToMM(bb.GetX()) - CX, pcbnew.ToMM(bb.GetRight()) - CX,
                                                     pcbnew.ToMM(bb.GetY()) - CY, pcbnew.ToMM(bb.GetBottom()) - CY))
    # report pad positions for routing
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname():
                print(fp.GetReference(), p.GetNumber(), p.GetNetname(),
                      round(pcbnew.ToMM(p.GetPosition().x) - CX, 3), round(pcbnew.ToMM(p.GetPosition().y) - CY, 3),
                      "B" if fp.IsFlipped() else "F")


if __name__ == "__main__":
    {"sch": sch, "pcb": pcb}[sys.argv[1]]()
