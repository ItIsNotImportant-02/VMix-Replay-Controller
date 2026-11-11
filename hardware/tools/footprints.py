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
    items, pitch, n = [], 0.4, 11
    # VERIFY lead/EP dimensions against the Lumissil package drawing (pitch 0.4 mm confirmed).
    pl, pw, pc = 0.85, 0.22, 2.425      # pad length, width, centre distance from body centre
    for i in range(44):
        side, k = divmod(i, n)
        off = (k - (n - 1) / 2) * pitch
        if side == 0:   x, y, w, h = -pc, off, pl, pw          # left, top->bottom
        elif side == 1: x, y, w, h = off, pc, pw, pl           # bottom, left->right
        elif side == 2: x, y, w, h = pc, -off, pl, pw          # right, bottom->top
        else:           x, y, w, h = -off, -pc, pw, pl         # top, right->left
        items.append(_pad(str(i + 1), "smd", "roundrect", round(x, 4), round(y, 4), w, h, SMD,
                          extra=[[Sym("roundrect_rratio"), 0.25]]))
    ep = 3.2
    items.append(_pad("45", "smd", "rect", 0, 0, ep, ep, ["F.Cu", "F.Mask"]))
    for dx in (-0.8, 0.8):
        for dy in (-0.8, 0.8):
            items.append(_pad("", "smd", "roundrect", dx, dy, 1.3, 1.3, ["F.Paste"], extra=[[Sym("roundrect_rratio"), 0.25]]))
    for dx in (-1.0, 0, 1.0):
        for dy in (-1.0, 0, 1.0):
            items.append(_pad("45", "thru_hole", "circle", dx, dy, 0.5, 0.5, ["*.Cu"], drill=0.25))
    b = 2.5
    items += [_line(-b, -b + 0.4, -b, -b, "F.SilkS"), _line(-b, -b, -b + 0.4, -b, "F.SilkS"),
              _line(b - 0.4, -b, b, -b, "F.SilkS"), _line(b, -b, b, -b + 0.4, "F.SilkS"),
              _line(-b, b - 0.4, -b, b, "F.SilkS"), _line(-b, b, -b + 0.4, b, "F.SilkS"),
              _line(b - 0.4, b, b, b, "F.SilkS"), _line(b, b, b, b - 0.4, "F.SilkS"),
              [Sym("fp_circle"), [Sym("center"), -3.1, -2.6], [Sym("end"), -3.0, -2.6],
               [Sym("stroke"), [Sym("width"), 0.2], [Sym("type"), Sym("solid")]], [Sym("fill"), Sym("yes")], [Sym("layer"), "F.SilkS"]],
              _rect(-b, -b, b, b, "F.Fab", 0.1), _rect(-3.1, -3.1, 3.1, 3.1, "F.CrtYd", 0.05)]
    return footprint("QFN-44-1EP_5x5mm_P0.4mm", "QFN-44 5x5 mm, pitch 0.4 mm, EP 3.2 mm (IS31FL3236A-QFLS2). VERIFY vs datasheet.",
                     ["smd"], items, 6.2)


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
    # PLACEHOLDER: pin positions not confirmed. Seller: pins 1-4 switch, 5 LED-, 6 LED+, pitch 5.08 mm.
    pads = [("1", -2.54, -2.54), ("2", 2.54, -2.54), ("3", -2.54, 2.54), ("4", 2.54, 2.54),
            ("5", -2.54, 0), ("6", 2.54, 0)]
    items = [_pad(num, "thru_hole", "rect" if num == "1" else "circle", x, y, 1.7, 1.7, THT, drill=1.0)
             for num, x, y in pads]
    h = 4.6
    items += [_rect(-h, -h, h, h, "F.SilkS"), _rect(-h, -h, h, h, "F.Fab", 0.1), _rect(-5, -5, 5, 5, "F.CrtYd", 0.05)]
    return footprint("TS5-9.2mm-LED", "Honyone TS5 9.2x9.2 mm tact switch with LED. PLACEHOLDER pin positions, VERIFY.",
                     ["through_hole"], items, 9.2)


def write(outdir):
    os.makedirs(outdir, exist_ok=True)
    for fp in (qfn44(), pb26(), ts5()):
        with open(os.path.join(outdir, fp[1] + ".kicad_mod"), "w", encoding="utf-8") as f:
            f.write(dump(fp) + "\n")
