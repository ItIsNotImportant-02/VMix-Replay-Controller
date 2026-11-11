"""Single-page schematic layout (A2), drawn in blocks like a dev-board schematic.

Coordinates are grid units (1 gu = 2.54 mm). Each block function gets its origin
(ox, oy) and draws in local grid units. Nets come from circuit.py.
"""
from schdraw import Drawing, POWER_LIB, DIRS
import circuit

G = 2.54


def g(n):
    return round(n * G, 3)


class Collector:
    """Stand-in for schgen.Project: collects Part objects and notes from circuit.build()."""
    class _S:
        def __init__(self, name):
            self.name, self.parts, self.notes = name, [], []

        def add(self, p):
            self.parts.append(p)
            return p

        def note(self, t):
            self.notes.append(t)

    def __init__(self):
        self.sheets, self.flags = [], []

    def sheet(self, name, filename, title=""):
        s = Collector._S(name)
        self.sheets.append(s)
        return s

    def flag(self, net, sheet):
        self.flags.append(net)


class B:
    """Block-local drawing helpers (grid units)."""
    def __init__(self, d, ox, oy):
        self.d, self.ox, self.oy = d, ox, oy

    def P(self, x, y):
        return g(self.ox + x), g(self.oy + y)

    def place(self, ref, x, y, rot=0, **kw):
        X, Y = self.P(x, y)
        if "ref_at" in kw:
            kw["ref_pos"] = self.P(*kw.pop("ref_at"))
        if "val_at" in kw:
            kw["val_pos"] = self.P(*kw.pop("val_at"))
        self.d.place(ref, X, Y, rot, **kw)

    def wire(self, *pts):
        self.d.wire(*[self.P(*p) for p in pts])

    def junction(self, x, y):
        self.d.junction(*self.P(x, y))

    def label(self, name, x, y, direction):
        self.d.label_at(name, *self.P(x, y), direction)

    def power(self, net, x, y, direction="up"):
        self.d.power_at(net, *self.P(x, y), direction)

    def pin(self, ref, pin):
        x, y, dd = self.d.pin(ref, pin)
        return x / G - self.ox, y / G - self.oy, dd

    def term(self, ref, pin, L=1, **kw):
        self.d.term(ref, pin, g(L), **kw)

    def side(self, ref, direction):
        for p in self.d.libs.pins(self.d.parts[ref].lib_id):
            if self.d.pin(ref, p["num"])[2] == direction:
                return p["num"]
        raise KeyError(ref + " has no pin facing " + direction)

    def v2(self, ref, x, y, rot=0, Lt=None, Lb=None, **kw):
        """Vertical 2-pin part; power nets get a symbol right on the pin, signals a short label stub."""
        self.place(ref, x, y, rot, **kw)
        for side, L in (("up", Lt), ("down", Lb)):
            p = self.side(ref, side)
            net = self.d.net(ref, p)
            if L is False:
                continue
            self.term(ref, p, (0 if net in POWER_LIB else 1) if L is None else L)

    def h2(self, ref, x, y, Ll=1, Lr=1, rot=90, **kw):
        self.place(ref, x, y, rot, **kw)
        if Ll is not False:
            self.term(ref, self.side(ref, "left"), Ll)
        if Lr is not False:
            self.term(ref, self.side(ref, "right"), Lr)

    def to_point(self, ref, pin, x, y, first="h"):
        """Wire from a pin to a local point (one bend)."""
        px, py, _ = self.pin(ref, pin)
        if first == "h":
            self.wire((px, py), (x, py), (x, y))
        else:
            self.wire((px, py), (px, y), (x, y))
        self.d._mark(ref, pin)

    def rail(self, ref, pins, y, net_x=None, direction="up"):
        """Join several pins facing up (or down) to a horizontal rail at local y with one power symbol."""
        xs = []
        for p in pins:
            px, py, _ = self.pin(ref, p)
            self.wire((px, py), (px, y))
            self.d._mark(ref, p)
            xs.append(px)
        xs = sorted(set(xs))
        if len(xs) > 1:
            self.wire((xs[0], y), (xs[-1], y))
            for x in xs[1:-1]:
                self.junction(x, y)
        net = self.d.net(ref, pins[0])
        nx = xs[0] if net_x is None else net_x
        if net_x is not None and net_x not in xs:
            self.wire((min(xs + [nx]), y), (max(xs + [nx]), y))
        elif len(xs) > 1 and nx in xs[1:-1]:
            pass
        if len(xs) > 1 and nx in (xs[0], xs[-1]):
            pass
        self.power(net, nx, y, direction) if net in POWER_LIB else self.label(net, nx, y, direction)

    def caprow(self, refs, x, y, pitch=4):
        """Row of decoupling caps: tops joined by a rail with one power symbol, bottoms by a GND rail."""
        d = self.d
        tops, bots = [], []
        for i, ref in enumerate(refs):
            cx = x + pitch * i
            self.place(ref, cx, y)
            tops.append((self.side(ref, "up"), cx))
            bots.append((self.side(ref, "down"), cx))
        tnet = {d.net(r, p) for r, (p, _) in zip(refs, tops)}
        bnet = {d.net(r, p) for r, (p, _) in zip(refs, bots)}
        assert len(tnet) == 1 and bnet == {"GND"}, (refs, tnet, bnet)
        for pins, dy, net, dirn in ((tops, -1, tnet.pop(), "up"), (bots, 1, "GND", "down")):
            ry = None
            for r, (p, cx) in zip(refs, pins):
                px, py, _ = self.pin(r, p)
                ry = py + dy
                self.wire((px, py), (px, ry))
                d._mark(r, p)
            self.wire((x - 1.5, ry), (x + pitch * (len(refs) - 1), ry))
            self.power(net, x - 1.5, ry, dirn)

    def expand(self, ref, pins):
        out = []
        for p in pins:
            m = [q["num"] for q in self.d.libs.pins(self.d.parts[ref].lib_id) if q["name"] == p]
            out += m if m else [str(p)]
        return out

    def column(self, ref, pins, x, direction="left"):
        """Join several pins on one side to a vertical wire at local x (e.g. RSVD -> GND), symbol at the end."""
        pins = self.expand(ref, pins)
        ys = []
        for p in pins:
            px, py, _ = self.pin(ref, p)
            self.wire((px, py), (x, py))
            self.d._mark(ref, p)
            ys.append(py)
        ys = sorted(set(ys))
        net = self.d.net(ref, pins[0])
        if net == "GND":
            self.wire((x, ys[0]), (x, ys[-1] + 1))
            for y in ys[1:]:
                self.junction(x, y)
            self.power("GND", x, ys[-1] + 1, "down")
        else:
            self.wire((x, ys[0] - 1), (x, ys[-1]))
            for y in ys[:-1]:
                self.junction(x, y)
            self.power(net, x, ys[0] - 1, "up") if net in POWER_LIB else self.label(net, x, ys[0] - 1, "up")


def xtal(b, Y, cl, cr, x, y, rpar=None):
    """Crystal with load caps (and optional parallel R above), joined to the chip by labels."""
    d = b.d
    b.place(Y, x, y, 0, ref_at=(x - 1.2, y - 1.6), val_at=(x + 1.8, y - 1.6))
    b.term(Y, "2", 0)
    x1, y1, _ = b.pin(Y, "1")
    x3, y3, _ = b.pin(Y, "3")
    ext = 4 if rpar else 3
    b.wire((x1, y1), (x1 - ext, y1))
    b.wire((x3, y3), (x3 + ext, y3))
    b.label(d.net(Y, "1"), x1 - ext, y1, "left")
    b.label(d.net(Y, "3"), x3 + ext, y3, "right")
    d._mark(Y, "1"); d._mark(Y, "3")
    d.shunt(cl, *b.P(x1 - 2, y1), "down", L=g(1))
    d.shunt(cr, *b.P(x3 + 2, y3), "down", L=g(1))
    if rpar:
        ry = y - 4
        b.place(rpar, x, ry, 90, ref_at=(x, ry - 1.2), val_at=(x, ry + 1.2))
        lx, _, _ = b.pin(rpar, b.side(rpar, "left"))
        rx, _, _ = b.pin(rpar, b.side(rpar, "right"))
        b.wire((lx, ry), (x1 - 3, ry), (x1 - 3, y1))
        b.wire((rx, ry), (x3 + 3, ry), (x3 + 3, y3))
        d._mark(rpar, "1"); d._mark(rpar, "2")


# =========================================================================
def block_power(d, ox, oy):
    b = B(d, ox, oy)
    d.block("1  USB-C, ochrana a napájení 5 V / 3,3 V", g(ox), g(oy), g(ox + 76), g(oy + 44),
            note="USB-C bez PD (2x 5,1k na CC). Polyswitch 0,75 A, TVS 5 V. +5V_LED napájí anody tlačítek a budiče LED přes ferit.\n"
                 "LDO LDL1117S33R: úbytek < 0,3 V při 200 mA. Celkový odběr (jas LED) omezuje firmware pod 500 mA.")
    b.place("J1", 9, 22)
    # VBUS -> F1 -> +5V node with TVS and caps
    x, y, _ = b.pin("J1", "A4")
    b.wire((x, y), (20, y))
    b.junction(18, y)
    b.wire((18, y), (18, y - 2))
    b.power("VBUS", 18, y - 2)
    d._mark("J1", "A4")
    b.place("F1", 21.5, y, 90, ref_at=(21.5, y - 1.2), val_at=(21.5, y + 1.6))
    d._mark("F1", "1")
    fx, fy, _ = b.pin("F1", "2")
    b.wire((fx, fy), (37, y))
    d._mark("F1", "2")
    b.wire((37, y), (37, y - 2))
    b.power("+5V", 37, y - 2)
    for i, ref in enumerate(("D1", "C1", "C2")):
        xx = 25 + 4.5 * i
        b.junction(xx, y)
        d.shunt(ref, *b.P(xx, y), "down", L=g(1))
    # CC pins -> labels, pull-downs drawn next to them
    b.term("J1", "A5", 2)
    b.term("J1", "B5", 2)
    # D+/D-: join A/B contacts
    for pa, pb in (("A7", "B7"), ("A6", "B6")):
        ax, ay, _ = b.pin("J1", pa)
        bx, by, _ = b.pin("J1", pb)
        b.wire((ax, ay), (ax + 1, ay), (ax + 1, by), (bx, by))
        b.wire((ax + 1, ay), (ax + 3, ay))
        b.junction(ax + 1, ay)
        b.label(d.net("J1", pa), ax + 3, ay, "right")
        d._mark("J1", pa); d._mark("J1", pb)
    b.term("J1", "A8"); b.term("J1", "B8")
    b.term("J1", "A1", 0)
    b.term("J1", "S1", 0)
    # CC pull-downs
    b.v2("R1", 23, 9, Lt=1)
    b.v2("R2", 27, 9, Lt=1)
    # ESD + USB series resistors
    b.place("U1", 30, 33)
    b.term("U1", "1", 1); b.term("U1", "3", 1); b.term("U1", "6", 1); b.term("U1", "4", 1)
    b.term("U1", "5", 0); b.term("U1", "2", 0)
    b.h2("R3", 44, 31)
    b.h2("R4", 44, 35)
    # +5V -> FB1 -> +5V_LED
    b.place("FB1", 43, 12, 90, ref_at=(43, 10.8), val_at=(43, 13.8))
    for side_ in ("left", "right"):
        p = b.side("FB1", side_)
        px, py, _ = b.pin("FB1", p)
        nx = px - 2 if side_ == "left" else px + 2
        b.wire((px, py), (nx, py), (nx, py - 2))
        b.power(d.net("FB1", p), nx, py - 2)
        d._mark("FB1", p)
    b.caprow(["C3", "C4", "C5"], 52, 13)
    # LDO
    b.place("U2", 44, 22)
    for p in ("VI", "VO"):
        px, py, dd = b.pin("U2", p)
        nx = px - 2 if dd == "left" else px + 2
        b.wire((px, py), (nx, py), (nx, py - 2))
        b.power(d.net("U2", p), nx, py - 2)
        d._mark("U2", p)
    b.term("U2", "GND", 0)
    b.caprow(["C6", "C7"], 54, 24)
    # power LED and 5 V sense divider
    b.place("R5", 61, 22)
    b.term("R5", "1", 0)
    b.place("D2", 61, 28, 90)
    b.d.link("R5", "2", "D2", "A")
    b.term("D2", "K", 0)
    b.place("R6", 66, 22)
    b.term("R6", "1", 0)
    b.place("R7", 66, 29)
    d.link("R6", "2", "R7", "1")
    b.term("R7", "2", 0)
    x6, y6, _ = b.pin("R6", "2")
    b.wire((x6, y6 + 1), (x6 + 3, y6 + 1))
    b.label("VSENSE_5V", x6 + 3, y6 + 1, "right")
    d.shunt("C8", *b.P(x6 + 2, y6 + 1), "down", L=g(1))
    # test points
    for i, ref in enumerate(("TP1", "TP2", "TP3", "TP4", "TP5", "TP6", "TP7")):
        b.place(ref, 47 + 3.5 * i, 38, 0, ref_at=(47 + 3.5 * i - 0.8, 35.8), val_at=(47 + 3.5 * i, 41), hide_val=True)
        b.term(ref, "1", 0)
    # PWR_FLAGs on externally fed nets
    for i, net in enumerate(("VBUS", "+5V", "+5V_LED", "GND")):
        x0 = 63 + 3.5 * i
        d.flag(*b.P(x0, 6))
        b.wire((x0, 6), (x0, 7))
        if net == "GND":
            b.power(net, x0, 7, "down")
        else:
            b.wire((x0, 7), (x0, 8))
            b.power(net, x0, 8, "down")


def block_mcu(d, ox, oy):
    b = B(d, ox, oy)
    d.block("2  MCU RP2040", g(ox), g(oy), g(ox + 72), g(oy + 70),
            note="GPIO: viz PINMAP.md. SPI0 = W5500 (jako W5500-EVB-Pico), I2C1 = LED budiče + expandéry,\n"
                 "SPI1 = páka (MT6701 SSI), GP2/GP3 = jog A/B pro PIO kvadraturní dekodér, GP29 = měření 5 V.")
    U = "U3"
    b.place(U, 40, 40)
    # power pins on top: +3V3 rail and +1V1 rail
    b.rail(U, ["USB_VDD", "ADC_AVDD", "IOVDD", "VREG_VIN"], 19, net_x=33)
    b.rail(U, ["VREG_VOUT", "DVDD"], 19, net_x=47)
    b.term(U, "GND", 0)
    b.term(U, "TESTEN", 0)
    # left side signals
    for p in ("RUN", "USB_DM", "USB_DP", "~{QSPI_SS}", "QSPI_SCLK", "QSPI_SD0", "QSPI_SD1", "QSPI_SD2",
              "QSPI_SD3", "SWCLK", "SWDIO"):
        b.term(U, p, 2)
    # right side GPIO labels
    for k in range(30):
        name = "GPIO%d" % k if k < 26 else "GPIO%d/ADC%d" % (k, k - 26)
        b.term(U, name, 2)
    # crystal: XIN/XOUT labels, R10 in series, Y1 with load caps (bottom-left)
    b.term(U, "XIN", 2)
    b.term(U, "XOUT", 2)
    b.h2("R10", 9, 50)
    xtal(b, "Y1", "C23", "C24", 9, 57)
    # decoupling rows (top-left)
    b.caprow(["C10", "C11", "C12", "C13", "C14", "C15", "C16", "C17", "C18", "C22"], 5, 9)
    b.caprow(["C19", "C20", "C21"], 50, 9)
    d.text("IOVDD x6, ADC_AVDD, USB_VDD, VREG_VIN, bulk", *b.P(5, 14.5))
    d.text("VREG_VOUT, DVDD x2", *b.P(50, 14.5))


def block_flash(d, ox, oy):
    b = B(d, ox, oy)
    d.block("3  Flash, BOOTSEL, RESET, stavová LED", g(ox), g(oy), g(ox + 76), g(oy + 30))
    b.place("U4", 14, 15)
    b.term("U4", "VCC", 0)
    b.term("U4", "GND", 0)
    for p in ("1", "6", "5", "2", "3", "7"):
        b.term("U4", p, 2)
    b.v2("C25", 22, 9)
    # BOOTSEL: QSPI_SS - R11 - SW1 - GND
    b.place("R11", 34, 9, 90)
    b.term("R11", b.side("R11", "left"), 1)
    b.place("SW1", 41, 9, 0, ref_at=(39, 6.5), val_at=(39, 11.5))
    d.link("R11", b.side("R11", "right"), "SW1", "1")
    rx, ry, _ = b.pin("R11", b.side("R11", "right"))
    sx, sy, _ = b.pin("SW1", "2")
    b.wire((sx, sy), (sx + 1, sy), (sx + 1, sy + 1))
    b.power("GND", sx + 1, sy + 1, "down")
    d._mark("SW1", "2")
    # RESET: +3V3 - R12 - RUN - SW2 - GND
    b.place("R12", 34, 19)
    b.term("R12", "1", 0)
    rx, ry, _ = b.pin("R12", "2")
    b.wire((rx, ry), (rx, ry + 1), (rx + 3, ry + 1))
    b.junction(rx, ry + 1)
    b.wire((rx, ry + 1), (rx - 3, ry + 1))
    b.label("RUN", rx - 3, ry + 1, "left")
    d._mark("R12", "2")
    b.place("SW2", rx + 5, ry + 1, 0, ref_at=(rx + 3, ry - 1.5), val_at=(rx + 3, ry + 3.5))
    sx, sy, _ = b.pin("SW2", "2")
    b.wire((sx, sy), (sx + 1, sy), (sx + 1, sy + 1))
    b.power("GND", sx + 1, sy + 1, "down")
    d._mark("SW2", "1"); d._mark("SW2", "2")
    # status LED
    b.place("R13", 56, 9, 90)
    b.term("R13", b.side("R13", "left"), 1)
    b.place("D3", 63, 9, 180)
    d.link("R13", b.side("R13", "right"), "D3", "A")
    dx, dy_, _ = b.pin("D3", "K")
    b.wire((dx, dy_), (dx + 1, dy_), (dx + 1, dy_ + 1))
    b.power("GND", dx + 1, dy_ + 1, "down")
    d._mark("D3", "K")


def block_ethernet(d, ox, oy):
    b = B(d, ox, oy)
    d.block("4  Ethernet W5500 + RJ45 HR911105A (vMix TCP API)", g(ox), g(oy), g(ox + 72), g(oy + 70),
            note="Analogová část podle referenčního zapojení WIZnet: 33R v sérii, 49,9R terminace na +3V3A,\n"
                 "6,8nF vazba RX, středy vinutí přes 10R/22nF a 10nF. TOCAP 4,7uF, 1V2O 10nF.")
    U = "U5"
    # supply: +3V3 -> FB2 -> +3V3A, decoupling, pull-ups, EXRES/TOCAP/1V2O parts on top
    b.place("FB2", 4, 7, 90, ref_at=(4, 5.8), val_at=(4, 8.8))
    for side_ in ("left", "right"):
        p = b.side("FB2", side_)
        px, py, _ = b.pin("FB2", p)
        nx = px - 1 if side_ == "left" else px + 1
        b.wire((px, py), (nx, py), (nx, py - 1))
        b.power(d.net("FB2", p), nx, py - 1)
        d._mark("FB2", p)
        if side_ == "right":
            b.wire((nx, py), (nx + 1, py))
            d.flag(*b.P(nx + 1, py))
    b.caprow(["C40", "C41", "C42", "C43", "C44", "C45", "C46"], 12, 9)
    b.caprow(["C47"], 41, 9)
    b.v2("R22", 46, 9, Lb=1)
    b.v2("R23", 49, 9, Lb=1)
    b.v2("R20", 55, 9, Lt=1)
    b.v2("C48", 60, 9, Lt=1)
    b.v2("C49", 65, 9, Lt=1)
    # the chip: everything by labels
    b.place(U, 18, 38)
    vx = b.pin(U, "VDD")[0]
    ax = b.pin(U, "AVDD")[0]
    b.rail(U, ["VDD"], 26, net_x=vx - 2)
    b.rail(U, ["AVDD"], 26, net_x=ax + 2)
    b.column(U, ["RSVD"], 1, "left")
    b.term(U, "GND", 0)
    b.term(U, "AGND", 0)
    for p in ("~{SCS}", "SCLK", "MISO", "MOSI", "~{INT}", "~{RST}", "XI/CLKIN", "XO"):
        b.term(U, p, 2)
    b.column(U, ["PMODE0", "PMODE1", "PMODE2"], 4, "left")
    for p in ("SPDLED", "DUPLED", "VBG", "TXN", "TXP", "RXN", "RXP", "LINKLED", "ACTLED", "EXRES1", "TOCAP", "1V2O"):
        b.term(U, p, 2)
    # series resistors W5500 <-> magnetics / LEDs
    for j, r in enumerate(("R24", "R25", "R29", "R30", "R33", "R34")):
        b.h2(r, 40, 24 + 3.5 * j)
    # termination network
    gx, gy = 52, 22
    b.h2("R26", gx + 3, gy, Ll=1, Lr=False)
    b.h2("R27", gx + 3, gy + 3, Ll=1, Lr=False)
    for r in ("R26", "R27"):
        b.to_point(r, b.side(r, "right"), gx + 6, gy + 3)
    b.wire((gx + 6, gy), (gx + 6, gy - 1))
    b.power("+3V3A", gx + 6, gy - 1, "up")
    b.h2("R31", gx + 3, gy + 7, Ll=1, Lr=False)
    b.h2("R32", gx + 3, gy + 10, Ll=1, Lr=False)
    for r in ("R31", "R32"):
        b.to_point(r, b.side(r, "right"), gx + 6, gy + 10)
    b.wire((gx + 6, gy + 10), (gx + 8, gy + 10))
    b.label("ETH_RCT", gx + 8, gy + 10, "right")
    b.h2("C53", gx + 3, gy + 14)
    b.h2("C54", gx + 3, gy + 17)
    b.place("R28", gx + 3, gy + 21, 90)
    b.term("R28", b.side("R28", "left"), 0)
    rx, ry, _ = b.pin("R28", b.side("R28", "right"))
    b.wire((rx, ry), (rx + 3, ry))
    b.label("ETH_TCT", rx + 3, ry, "right")
    d._mark("R28", b.side("R28", "right"))
    d.shunt("C52", *b.P(rx + 1, ry), "down", L=g(1))
    b.v2("C55", gx + 14, gy + 23, Lt=1)
    # RJ45 with magnetics
    b.place("J4", 50, 60)
    for p in ("1", "2", "3", "4", "5", "6", "9", "11"):
        b.term("J4", p, 1)
    for p, dy in (("12", -1.5), ("10", 1.5)):
        px, py, _ = b.pin("J4", p)
        b.wire((px, py), (px + 1, py), (px + 1, py + dy))
        b.power("+3V3", px + 1, py + dy, "up" if dy < 0 else "down")
        d._mark("J4", p)
    b.term("J4", "8", 0)
    b.term("J4", "SH", 0)
    # crystal
    xtal(b, "Y2", "C50", "C51", 12, 58, rpar="R21")

def block_leds(d, ox, oy):
    b = B(d, ox, oy)
    d.block("5  Budiče LED 2x IS31FL3236A (I2C, 22 kHz PWM, bez multiplexu)", g(ox), g(oy), g(ox + 78), g(oy + 47),
            note="I_MAX = 58,5 x 1,3 V / R_EXT = 19,5 mA (3,9k). U6 adresa 0x3C (AD=GND), U7 0x3F (AD=VCC).\n"
                 "VCC = 5 V, protože OUTx nesmí přesáhnout VCC + 0,3 V (anody LED jsou na 5 V). SDB stažený k zemi = LED po startu zhasnuté.")
    for i, U in enumerate(("U6", "U7")):
        x0 = 14 + 38 * i
        b.place(U, x0, 23.5)
        b.term(U, "VCC", 0)
        for p in ("SDA", "SCL", "~{SDB}"):
            b.term(U, p, 2)
        b.term(U, "AD", 2 if d.net(U, "AD") not in POWER_LIB else 0)
        b.column(U, ["17", "39", "45"], x0 - 6, "left")
        rx, ry, _ = b.pin(U, "R_EXT")
        r = "R40" if U == "U6" else "R41"
        b.wire((rx, ry), (rx - 2, ry))
        d._mark(U, "R_EXT")
        b.place(r, rx - 2, ry + 3, 0, ref_at=(rx - 1.2, ry + 2.5), val_at=(rx - 1.2, ry + 3.6))
        b.wire((rx - 2, ry), (rx - 2, ry + 1.5))
        d._mark(r, "1")
        b.term(r, "2", 0)
        for k in range(1, 37):
            b.term(U, "OUT%d" % k, 1)
        caps = ("C60", "C61") if U == "U6" else ("C62", "C63")
        b.caprow(list(caps), x0 - 9, 33)
    # SDB pull-down, I2C pull-ups
    b.v2("R42", 66, 37, Lt=1)
    b.place("R43", 70, 37)
    b.term("R43", "1", 0); b.term("R43", "2", 1)
    b.place("R44", 74, 37)
    b.term("R44", "1", 0); b.term("R44", "2", 1)
    for i, ref in enumerate(("TP10", "TP11", "TP12", "TP13")):
        b.place(ref, 66 + 3 * i, 21, 0, ref_at=(66 + 3 * i - 0.8, 18.8), hide_val=True, val_at=(66 + 3 * i, 24))
        b.term(ref, "1", 1)


def block_inputs(d, ox, oy):
    b = B(d, ox, oy)
    d.block("6  Expandéry tlačítek 2x TCA9555 (I2C)", g(ox), g(oy), g(ox + 66), g(oy + 47),
            note="U8 adresa 0x20, U9 0x21. Vstupy mají interní pull-up 100k, tlačítko spíná proti GND.\n"
                 "INT (open drain) společný pro oba, pull-up R50. Volné vstupy U9 P14-P17 jsou na konektoru J3.")
    for i, U in enumerate(("U8", "U9")):
        x0 = 12 + 33 * i
        b.place(U, x0, 22)
        b.term(U, "VCC", 0)
        b.term(U, "GND", 0)
        b.term(U, "EPAD", 0)
        for p in ("SDA", "SCL", "~{INT}"):
            b.term(U, p, 2)
        b.column(U, ["A0", "A1", "A2"] if d.net(U, "A0") == "GND" else ["A1", "A2"], x0 - 9, "left")
        if d.net(U, "A0") != "GND":
            px, py, _ = b.pin(U, "A0")
            b.wire((px, py), (px - 1, py), (px - 1, py + 1.5))
            b.power(d.net(U, "A0"), px - 1, py + 1.5, "down")
            d._mark(U, "A0")
        for k in TCA_PORTS_ALL:
            b.term(U, k, 1)
    b.v2("C70", 4, 7)
    b.v2("C71", 37, 7)
    b.v2("R50", 62, 9, Lb=1)


TCA_PORTS_ALL = ["P00", "P01", "P02", "P03", "P04", "P05", "P06", "P07",
                 "P10", "P11", "P12", "P13", "P14", "P15", "P16", "P17"]


def block_buttons(d, ox, oy):
    b = B(d, ox, oy)
    d.block("7  Tlačítka panelu: 18x PB26-13M RGB, 10x TS5 se žlutou LED (ruční pájení)", g(ox), g(oy), g(ox + 146), g(oy + 36),
            note="Spínač: COM = GND, NO = vstup expandéru. LED: společná anoda na +5V_LED, katody na kanály IS31FL3236A.")
    refs = ["SW%d" % (10 + i) for i in range(18)] + ["SW%d" % (30 + i) for i in range(10)]
    for i, ref in enumerate(refs):
        col, row = i % 7, i // 7
        x0, y0 = 9 + 20.5 * col, 6 + 7.5 * row
        b.place(ref, x0, y0, 0, ref_at=(x0 - 3, y0 - 3.3), val_at=(x0 + 0.5, y0 - 3.3))
        pins = [p["num"] for p in d.libs.pins(d.parts[ref].lib_id)]
        for p in pins:
            net = d.net(ref, p)
            if net == "GND":
                continue
            b.term(ref, p, 1 if net not in POWER_LIB else 0)
        # GND pins (left side) -> one GND symbol
        gp = [p for p in pins if d.net(ref, p) == "GND"]
        b.column(ref, gp, x0 - 5.5, "left")


def block_sensors(d, ox, oy):
    b = B(d, ox, oy)
    d.block("8  Konektory senzorů páky a jogu (destičky s MT6701, JST-PH 8 pin)", g(ox), g(oy), g(ox + 76), g(oy + 42),
            note="Pin 3 MODE přepíná ABZ / I2C+SSI. P6 = A/SDA/DO, P7 = B/SCL/CLK, P8 = Z/CSN, OUT = analog do ADC (záloha).")
    for i, (J, rs, cs) in enumerate((("J5", ["R60", "R61", "R62", "R63"], ["R64", "R65", "R66", "R67", "C80", "C81"]),
                                     ("J6", ["R68", "R69", "R70", "R71"], ["R72", "R73", "R74", "R75", "C82", "C83"]))):
        yb = 20 * i
        pu, pu2, pu3, rout, cout, cbulk = cs
        x0 = 34
        b.place(J, x0, yb + 10, 0, ref_at=(x0 - 1, yb + 4.5), val_at=(x0 - 1, yb + 5.5))
        for p in ("1", "2", "3", "4", "5", "6", "7", "8"):
            b.term(J, p, 1)
        b.term(J, "MP", 0)
        # series resistors (label to label), pull-ups and analog filter
        for j, r in enumerate(rs + [rout]):
            b.h2(r, 50, yb + 4 + 3 * j)
        b.v2(cbulk, 4, yb + 10)
        for j, r in enumerate((pu, pu2, pu3)):
            b.v2(r, 9 + 4 * j, yb + 10, Lb=1)
        b.v2(cout, 23, yb + 10, Lt=1)


def block_conn(d, ox, oy):
    b = B(d, ox, oy)
    d.block("9  Ladění a rozšíření", g(ox), g(oy), g(ox + 32), g(oy + 22),
            note="J2 SWD + UART (osadit při ladění). J3 rezervní GPIO, I2C, volné vstupy.")
    b.place("J2", 7, 9)
    for p in range(1, 8):
        b.term("J2", str(p), 1)
    b.place("J3", 22, 9)
    for p in range(1, 17):
        b.term("J3", str(p), 1)


def build(libs, title, rev, date):
    col = Collector()
    circuit.build(col)
    parts = {p.ref: p for s in col.sheets for p in s.parts}
    d = Drawing("vmix-replay-controller", libs, parts, paper="A2", title=title, rev=rev, date=date)
    block_power(d, 5, 5)
    block_mcu(d, 83, 5)
    block_ethernet(d, 157, 5)
    block_flash(d, 5, 51)
    block_leds(d, 83, 77)
    block_inputs(d, 163, 77)
    block_buttons(d, 5, 126)
    block_sensors(d, 5, 83)
    block_conn(d, 153, 126)
    return d, None
