"""Project footprints (lib/vrc.pretty). Dimensions marked VERIFY must be checked on real parts."""
import os
from sexpr import Sym, dump


def _pad(num, kind, shape, x, y, w, h, layers, drill=None, extra=None):
    p = [Sym("pad"), num, Sym(kind), Sym(shape), [Sym("at"), x, y], [Sym("size"), w, h]]
    if drill:
        p.append([Sym("drill"), drill])
    p.append([Sym("layers")] + layers)
    if extra:
        p += extra
    return p


def _line(x1, y1, x2, y2, layer, w=0.12):
    return [Sym("fp_line"), [Sym("start"), x1, y1], [Sym("end"), x2, y2],
            [Sym("stroke"), [Sym("width"), w], [Sym("type"), Sym("solid")]], [Sym("layer"), layer]]


def _rect(x1, y1, x2, y2, layer, w=0.12):
    return [Sym("fp_rect"), [Sym("start"), x1, y1], [Sym("end"), x2, y2],
            [Sym("stroke"), [Sym("width"), w], [Sym("type"), Sym("solid")]], [Sym("fill"), Sym("no")], [Sym("layer"), layer]]


def _text(kind, txt, x, y, layer, hide=False):
    t = [Sym("property"), kind, txt, [Sym("at"), x, y, 0], [Sym("layer"), layer],
         [Sym("effects"), [Sym("font"), [Sym("size"), 1, 1], [Sym("thickness"), 0.15]]]]
    if hide:
        t.insert(5, [Sym("hide"), Sym("yes")])
    return t


def footprint(name, descr, attr, items, h):
    return [Sym("footprint"), name, [Sym("version"), 20241229], [Sym("generator"), "vrc_footprints"],
            [Sym("generator_version"), "9.0"], [Sym("layer"), "F.Cu"], [Sym("descr"), descr],
            _text("Reference", "REF**", 0, -h / 2 - 1.5, "F.SilkS"),
            _text("Value", name, 0, h / 2 + 1.5, "F.Fab"),
            [Sym("attr")] + [Sym(a) for a in attr]] + items


THT = ["*.Cu", "*.Mask"]
SMD = ["F.Cu", "F.Paste", "F.Mask"]


def qfn44():
    """Land pattern 1:1 podle doporučení v datasheetu IS31FL3236A Rev. I (str. 16):
    pady 0,25 x 1,00 mm, rozteč 0,4, vnitřní hrany ve vzdálenosti 4,0 mm (střed padu 2,5 mm),
    rohové pady zkrácené na 0,8 mm se zaoblením R0,125 (mezera mezi rohy ~0,2 mm), EP 2,45 x 2,45 mm."""
    items, pitch, n = [], 0.4, 11
    pw = 0.25
    for i in range(44):
        side, k = divmod(i, n)
        off = (k - (n - 1) / 2) * pitch
        corner = k in (0, n - 1)
        pl = 0.8 if corner else 1.0
        pc = 3.0 - pl / 2             # outer edge always 3,0 mm from centre
        if side == 0:   x, y, w, h = -pc, off, pl, pw          # left, top->bottom (pin 1 top-left)
        elif side == 1: x, y, w, h = off, pc, pw, pl           # bottom, left->right
        elif side == 2: x, y, w, h = pc, -off, pl, pw          # right, bottom->top
        else:           x, y, w, h = -off, -pc, pw, pl         # top, right->left
        items.append(_pad(str(i + 1), "smd", "roundrect", round(x, 4), round(y, 4), w, h, SMD,
                          extra=[[Sym("roundrect_rratio"), 0.5 if corner else 0.25]]))
    ep = 2.45
    items.append(_pad("45", "smd", "rect", 0, 0, ep, ep, ["F.Cu", "F.Mask"]))
    # paste 4 okna 0,9 x 0,9 (~54 % plochy EP), mezi nimi kříž prokovů do GND
    for dx in (-0.65, 0.65):
        for dy in (-0.65, 0.65):
            items.append(_pad("", "smd", "roundrect", dx, dy, 0.9, 0.9, ["F.Paste"], extra=[[Sym("roundrect_rratio"), 0.25]]))
    for dx, dy in ((0, 0), (-0.65, 0), (0.65, 0), (0, -0.65), (0, 0.65)):
        items.append(_pad("45", "thru_hole", "circle", dx, dy, 0.4, 0.4, ["*.Cu"], drill=0.2))
    b = 2.5
    items += [_line(-b, -b + 0.4, -b, -b, "F.SilkS"), _line(-b, -b, -b + 0.4, -b, "F.SilkS"),
              _line(b - 0.4, -b, b, -b, "F.SilkS"), _line(b, -b, b, -b + 0.4, "F.SilkS"),
              _line(-b, b - 0.4, -b, b, "F.SilkS"), _line(-b, b, -b + 0.4, b, "F.SilkS"),
              _line(b - 0.4, b, b, b, "F.SilkS"), _line(b, b, b, b - 0.4, "F.SilkS"),
              [Sym("fp_circle"), [Sym("center"), -3.3, -2.6], [Sym("end"), -3.2, -2.6],
               [Sym("stroke"), [Sym("width"), 0.2], [Sym("type"), Sym("solid")]], [Sym("fill"), Sym("yes")], [Sym("layer"), "F.SilkS"]],
              _rect(-b, -b, b, b, "F.Fab", 0.1), _rect(-3.25, -3.25, 3.25, 3.25, "F.CrtYd", 0.05)]
    fp = footprint("QFN-44-1EP_5x5mm_P0.4mm", "QFN-44 5x5 mm, pitch 0.4 mm, EP 2.45 mm, land pattern per IS31FL3236A datasheet Rev. I",
                   ["smd"], items, 6.2)
    fp.insert(7, [Sym("clearance"), 0.1])
    return fp


def pb26():
    # Pin positions from espena/kicad-libs SW_PUSH_Honyone_PB26_13M_B_WT_RGB_N (third party). VERIFY on a real button.
    # Seller: L2 = common anode, L1 = red, L4 = green, L3 = blue.
    pads = [("1", -5.08, 5.08), ("2", 0, 5.08), ("3", 5.08, 5.08),
            ("R", 2.54, 1.27), ("A", -2.54, 1.27), ("B", -2.54, -1.27), ("G", 2.54, -1.27)]
    items = []
    for num, x, y in pads:
        items.append(_pad(num, "thru_hole", "rect" if num in ("1", "A") else "circle", x, y, 1.9, 1.9, THT, drill=1.2))
    h = 7.65
    items += [_rect(-h, -h, h, h, "F.SilkS"), _rect(-h, -h, h, h, "F.Fab", 0.1), _rect(-8, -8, 8, 8, "F.CrtYd", 0.05),
              [Sym("fp_text"), Sym("user"), "COM NO NC", [Sym("at"), 0, 6.9, 0], [Sym("layer"), "F.Fab"],
               [Sym("effects"), [Sym("font"), [Sym("size"), 0.8, 0.8], [Sym("thickness"), 0.12]]]]]
    return footprint("PB26-13M-RGB", "Honyone PB26-13M 15x15 mm SPDT push button with RGB LED (common anode). Pin positions VERIFY.",
                     ["through_hole"], items, 15.3)


def ts5():
    """Podle výkresu Honyone TS5-2X-XA-1XS rev. A1 (PCB layout, pohled shora): 1 a 2 nahoře, 3 a 4 dole,
    rastr 5,08 x 5,08 mm, otvory spínače Ø1,0; LED uprostřed: 6 (+) vlevo, 5 (-) vpravo, otvory Ø0,8.
    Uvnitř jsou spojené 1-2 a 3-4. Rastr je souměrný, takže tlačítko jde zasunout i otočené o 180°:
    spínači je to jedno, LED by ale byla obráceně -> na desce je u padu 6 značka "+".
    Ještě ověřit na skutečném kusu (multimetr: polarita LED, propojení vývodů)."""
    pads = [("1", -2.54, -2.54), ("2", 2.54, -2.54), ("3", -2.54, 2.54), ("4", 2.54, 2.54)]
    items = [_pad(num, "thru_hole", "rect" if num == "1" else "circle", x, y, 1.7, 1.7, THT, drill=1.0)
             for num, x, y in pads]
    items += [_pad("6", "thru_hole", "circle", -2.54, 0, 1.5, 1.5, THT, drill=0.9),
              _pad("5", "thru_hole", "circle", 2.54, 0, 1.5, 1.5, THT, drill=0.9)]
    h = 4.6
    items += [_rect(-h, -h, h, h, "F.SilkS"), _rect(-h, -h, h, h, "F.Fab", 0.1), _rect(-5, -5, 5, 5, "F.CrtYd", 0.05),
              _line(-4.3, 0, -3.7, 0, "F.SilkS", 0.15), _line(-4.0, -0.3, -4.0, 0.3, "F.SilkS", 0.15),
              _line(-4.3, 0, -3.7, 0, "B.SilkS", 0.15), _line(-4.0, -0.3, -4.0, 0.3, "B.SilkS", 0.15)]
    return footprint("TS5-9.2mm-LED", "Honyone TS5 9.2x9.2 mm tact switch with LED, per drawing TS5-2X-XA-1XS A1. VERIFY on the real part.",
                     ["through_hole"], items, 9.2)


def write(outdir):
    os.makedirs(outdir, exist_ok=True)
    for fp in (qfn44(), pb26(), ts5()):
        with open(os.path.join(outdir, fp[1] + ".kicad_mod"), "w", encoding="utf-8") as f:
            f.write(dump(fp) + "\n")
