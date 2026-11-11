"""Project symbol library (lib/vrc.kicad_sym), generated from simple pin lists."""
from sexpr import Sym, dump


def _pin(ptype, num, name, x, y, ang, length=2.54, hide_name=False):
    return [Sym("pin"), Sym(ptype), Sym("line"), [Sym("at"), x, y, ang], [Sym("length"), length],
            [Sym("name"), name, [Sym("effects"), [Sym("font"), [Sym("size"), 1.27, 1.27]]]],
            [Sym("number"), num, [Sym("effects"), [Sym("font"), [Sym("size"), 1.27, 1.27]]]]]


def _prop(k, v, x, y, hide):
    e = [Sym("effects"), [Sym("font"), [Sym("size"), 1.27, 1.27]]]
    if hide:
        e.append([Sym("hide"), Sym("yes")])
    return [Sym("property"), k, v, [Sym("at"), x, y, 0], e]


def box_symbol(name, ref, value, left, right, top=(), bottom=(), width=20.32, footprint="", desc="",
               datasheet="", keywords=""):
    """left/right/top/bottom: lists of (num, name, type) or None for a gap."""
    n = max(len(left), len(right), 1)
    h = (n + 1) * 2.54
    half_w = width / 2
    top_y = round(((n - 1) * 2.54) / 2 / 1.27) * 1.27 + 2.54
    pins = []
    for i, p in enumerate(left):
        if p:
            pins.append(_pin(p[2], p[0], p[1], -half_w - 2.54, top_y - 2.54 - i * 2.54, 0))
    for i, p in enumerate(right):
        if p:
            pins.append(_pin(p[2], p[0], p[1], half_w + 2.54, top_y - 2.54 - i * 2.54, 180))
    bot_y = top_y - 2.54 - (n - 1) * 2.54 - 2.54
    for i, p in enumerate(top):
        if p:
            pins.append(_pin(p[2], p[0], p[1], -half_w + 2.54 + i * 2.54, top_y + 2.54, 270))
    for i, p in enumerate(bottom):
        if p:
            pins.append(_pin(p[2], p[0], p[1], -half_w + 2.54 + i * 2.54, bot_y - 2.54, 90))
    rect = [Sym("rectangle"), [Sym("start"), -half_w, top_y], [Sym("end"), half_w, bot_y],
            [Sym("stroke"), [Sym("width"), 0.254], [Sym("type"), Sym("default")]],
            [Sym("fill"), [Sym("type"), Sym("background")]]]
    return [Sym("symbol"), name, [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")],
            [Sym("on_board"), Sym("yes")],
            _prop("Reference", ref, -half_w, top_y + 1.27, False),
            _prop("Value", value, -half_w, bot_y - 1.27, False),
            _prop("Footprint", footprint, 0, 0, True),
            _prop("Datasheet", datasheet, 0, 0, True),
            _prop("Description", desc, 0, 0, True),
            _prop("ki_keywords", keywords, 0, 0, True),
            [Sym("symbol"), name + "_0_1", rect],
            [Sym("symbol"), name + "_1_1"] + pins]


def build():
    syms = []
    # IS31FL3236A, QFN-44 5x5 (pin table from Lumissil datasheet Rev. I)
    outs = {}
    for i in range(16):
        outs[i + 3] = i + 1          # pins 1..16 = OUT3..OUT18
    for i in range(18):
        outs[i + 19] = i + 18        # pins 18..35 = OUT19..OUT36
    outs[1] = 43
    outs[2] = 44
    right = [(str(outs[k]), "OUT%d" % k, "output") for k in range(1, 37)]
    left = [("38", "VCC", "power_in"), None, ("41", "SDA", "bidirectional"), ("42", "SCL", "input"),
            ("36", "~{SDB}", "input"), ("37", "AD", "input"), None, ("40", "R_EXT", "passive")]
    left += [None] * 24 + [("17", "GND", "power_in"), ("39", "GND", "passive"), ("45", "EP", "passive")]
    syms.append(box_symbol("IS31FL3236A-QFN44", "U", "IS31FL3236A", left, right, width=17.78,
                           footprint="vrc:QFN-44-1EP_5x5mm_P0.4mm",
                           desc="36-channel constant-current LED driver, I2C, 22 kHz PWM, QFN-44 5x5",
                           datasheet="https://www.lumissil.com/assets/pdf/core/IS31FL3236A_DS.pdf",
                           keywords="LED driver I2C PWM"))
    # PB26-13M RGB: SPDT switch + common-anode RGB LED
    syms.append(box_symbol("PB26-13M-RGB", "SW", "PB26-13M-RGB",
                           [("1", "COM", "passive"), ("2", "NO", "passive"), ("3", "NC", "passive")],
                           [("A", "LED+", "passive"), ("R", "R-", "passive"), ("G", "G-", "passive"), ("B", "B-", "passive")],
                           width=12.7, footprint="vrc:PB26-13M-RGB",
                           desc="Honyone PB26-13M 15x15 mm push button, SPDT, RGB LED common anode (hand soldered)"))
    # TS5: tact switch (1-2 and 3-4 internally joined) + single LED
    syms.append(box_symbol("TS5-LED", "SW", "TS5",
                           [("1", "S1", "passive"), ("2", "S1", "passive"), ("3", "S2", "passive"), ("4", "S2", "passive")],
                           [("6", "LED+", "passive"), ("5", "LED-", "passive")],
                           width=10.16, footprint="vrc:TS5-9.2mm-LED",
                           desc="Honyone TS5 9.2x9.2 mm tact switch with LED (hand soldered)"))
    lib = [Sym("kicad_symbol_lib"), [Sym("version"), 20241209], [Sym("generator"), "vrc_customlib"],
           [Sym("generator_version"), "9.0"]] + syms
    return lib


def write(path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(dump(build()) + "\n")
