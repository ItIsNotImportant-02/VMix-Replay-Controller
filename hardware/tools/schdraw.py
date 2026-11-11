"""Hand-laid-out, single-sheet KiCad schematic drawing.

Parts and their nets come from circuit.py (one source of truth). The layout code
(layout.py) places every symbol at chosen coordinates, draws wires, labels and
power symbols. verify() exports the netlist with kicad-cli and checks that the
drawing connects exactly the nets that circuit.py defines.
"""
import math
from sexpr import Sym, dump
from schgen import uid, _prop

POWER_LIB = {"GND": "power:GND", "+3V3": "power:+3V3", "+5V": "power:+5V", "+1V1": "power:+1V1",
             "VBUS": "power:VBUS", "+5V_LED": "vrc:+5V_LED", "+3V3A": "vrc:+3V3A"}
DIRS = {"right": (1, 0), "left": (-1, 0), "up": (0, -1), "down": (0, 1)}


def r2(v):
    return round(v + 0.0, 3)


def _rot(px, py, ang):
    a = math.radians(ang)
    c, s = round(math.cos(a)), round(math.sin(a))
    return px * c - py * s, px * s + py * c


def _dir_of(ang):
    # lib pin angle = direction from connection point towards the body
    return {0: "left", 180: "right", 90: "down", 270: "up"}[int(ang) % 360]


class Drawing:
    def __init__(self, name, libs, parts, paper="A2", title="", rev="", date=""):
        self.name, self.libs, self.parts = name, libs, parts
        self.paper, self.title, self.rev, self.date = paper, title, rev, date
        self.uuid = uid(name, "root-flat")
        self.items = []
        self.libs_used = {}
        self.placed = {}
        self.done = set()            # (ref, pin) handled
        self.pwr_n = 0
        self.n = 0

    # ----------------------------------------------------------- basics ----
    def _u(self, *k):
        self.n += 1
        return uid(self.name, "item", self.n, *k)

    def net(self, ref, pin):
        p = self.parts[ref]
        pins = self.libs.pins(p.lib_id)
        num = self._num(ref, pin)
        name = [x["name"] for x in pins if x["num"] == num][0]
        if num in p.pinmap:
            return p.pinmap[num]
        if name in p.pinmap:
            return p.pinmap[name]
        return None

    def _num(self, ref, pin):
        pins = self.libs.pins(self.parts[ref].lib_id)
        pin = str(pin)
        if any(x["num"] == pin for x in pins):
            return pin
        m = [x["num"] for x in pins if x["name"] == pin]
        if not m:
            raise KeyError("%s has no pin %s" % (ref, pin))
        return m[0]

    def place(self, ref, x, y, rot=0, ref_pos=None, val_pos=None, hide_val=False):
        part = self.parts[ref]
        if ref in self.placed:
            raise ValueError(ref + " placed twice")
        sym = self.libs.get(part.lib_id)
        self.libs_used[part.lib_id] = sym
        x, y = r2(x), r2(y)
        self.placed[ref] = (x, y, rot)
        bx0, bx1, by0, by1 = self.libs.bbox(part.lib_id)
        if rot in (90, 270):
            bx0, bx1, by0, by1 = -by1, -by0, bx0, bx1
        w, h = bx1 - bx0, by1 - by0
        if ref_pos is None:
            if w < 4.5:                       # tall narrow (vertical R/C/D)
                ref_pos, val_pos = (x + 2.0, y - 1.0), (x + 2.0, y + 1.6)
            elif h < 4.5:                     # flat wide (horizontal R/C/D)
                ref_pos, val_pos = (x, y - 2.3), (x, y + 2.9)
            else:
                ref_pos, val_pos = (x + bx0, y - by1 - 3.0), (x + bx0, y - by1 - 1.0)
        just = ["left"] if ref_pos[0] > x + 1 or ref_pos[0] < x - 1 else None
        u = uid(self.name, part.ref)
        node = [Sym("symbol"), [Sym("lib_id"), part.lib_id], [Sym("at"), x, y, rot], [Sym("unit"), 1],
                [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes" if part.in_bom else "no")],
                [Sym("on_board"), Sym("yes")], [Sym("dnp"), Sym("yes" if part.dnp else "no")], [Sym("uuid"), u],
                _prop("Reference", part.ref, r2(ref_pos[0]), r2(ref_pos[1]), justify=just, ang=(90 if rot in (90, 270) else 0)),
                _prop("Value", part.value, r2(val_pos[0]), r2(val_pos[1]), justify=just, hide=hide_val, ang=(90 if rot in (90, 270) else 0)),
                _prop("Footprint", part.footprint, x, y, hide=True),
                _prop("Datasheet", part.datasheet, x, y, hide=True),
                _prop("Description", part.desc, x, y, hide=True)]
        extra = dict(part.fields)
        if part.lcsc:
            extra["LCSC"] = part.lcsc
        if part.mpn:
            extra["MPN"] = part.mpn
        for k, v in extra.items():
            node.append(_prop(k, v, x, y, hide=True))
        for p in self.libs.pins(part.lib_id):
            node.append([Sym("pin"), p["num"], [Sym("uuid"), uid(u, "pin", p["num"])]])
        node.append([Sym("instances"), [Sym("project"), self.name,
                     [Sym("path"), "/" + self.uuid, [Sym("reference"), part.ref], [Sym("unit"), 1]]]])
        self.items.append(node)
        return self

    def pin(self, ref, pin):
        """(x, y, outward_direction) of a pin's connection point."""
        x, y, rot = self.placed[ref]
        num = self._num(ref, pin)
        p = [q for q in self.libs.pins(self.parts[ref].lib_id) if q["num"] == num][0]
        rx, ry = _rot(p["x"], p["y"], rot)
        return r2(x + rx), r2(y - ry), _dir_of(p["ang"] + rot)

    def _mark(self, ref, pin):
        """Mark a pin and all pins stacked on the same point as handled."""
        x, y, _ = self.pin(ref, pin)
        for q in self.libs.pins(self.parts[ref].lib_id):
            qx, qy, _ = self.pin(ref, q["num"])
            if (qx, qy) == (x, y):
                self.done.add((ref, q["num"]))

    def wire(self, *pts):
        pts = [(r2(a), r2(b)) for a, b in pts]
        for a, b in zip(pts, pts[1:]):
            if a == b:
                continue
            self.items.append([Sym("wire"), [Sym("pts"), [Sym("xy"), a[0], a[1]], [Sym("xy"), b[0], b[1]]],
                               [Sym("stroke"), [Sym("width"), 0], [Sym("type"), Sym("default")]], [Sym("uuid"), self._u()]])

    def junction(self, x, y):
        self.items.append([Sym("junction"), [Sym("at"), r2(x), r2(y)], [Sym("diameter"), 0],
                           [Sym("color"), 0, 0, 0, 0], [Sym("uuid"), self._u()]])

    def label_at(self, name, x, y, direction):
        ang = {"right": 0, "up": 90, "left": 180, "down": 270}[direction]
        just = "left" if direction in ("right", "up") else "right"
        self.items.append([Sym("label"), name, [Sym("at"), r2(x), r2(y), ang],
                           [Sym("effects"), [Sym("font"), [Sym("size"), 1.27, 1.27]], [Sym("justify"), Sym(just), Sym("bottom")]],
                           [Sym("uuid"), self._u()]])

    def power_at(self, net, x, y, direction="up"):
        lib_id = POWER_LIB[net]
        self.libs_used[lib_id] = self.libs.get(lib_id)
        if net == "GND":
            rot = {"down": 0, "up": 180, "left": 270, "right": 90}[direction]
        else:
            rot = {"up": 0, "down": 180, "left": 90, "right": 270}[direction]
        self.pwr_n += 1
        ref = "#PWR%03d" % self.pwr_n
        u = self._u("pwr")
        vx, vy = x, y
        off = 5.08 if net == "GND" else 3.56
        dx, dy = DIRS[direction]
        vx, vy = x + dx * off, y + dy * off
        self.items.append([Sym("symbol"), [Sym("lib_id"), lib_id], [Sym("at"), r2(x), r2(y), rot], [Sym("unit"), 1],
                           [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("no")], [Sym("on_board"), Sym("yes")],
                           [Sym("dnp"), Sym("no")], [Sym("uuid"), u],
                           _prop("Reference", ref, r2(x), r2(y), hide=True),
                           _prop("Value", net, r2(vx), r2(vy)),
                           _prop("Footprint", "", r2(x), r2(y), hide=True), _prop("Datasheet", "", r2(x), r2(y), hide=True),
                           [Sym("pin"), "1", [Sym("uuid"), uid(u, "p1")]],
                           [Sym("instances"), [Sym("project"), self.name,
                            [Sym("path"), "/" + self.uuid, [Sym("reference"), ref], [Sym("unit"), 1]]]]])

    def flag(self, x, y):
        lib_id = "power:PWR_FLAG"
        self.libs_used[lib_id] = self.libs.get(lib_id)
        self.pwr_n += 1
        ref = "#FLG%03d" % self.pwr_n
        u = self._u("flg")
        self.items.append([Sym("symbol"), [Sym("lib_id"), lib_id], [Sym("at"), r2(x), r2(y), 0], [Sym("unit"), 1],
                           [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("no")], [Sym("on_board"), Sym("yes")],
                           [Sym("dnp"), Sym("no")], [Sym("uuid"), u],
                           _prop("Reference", ref, r2(x), r2(y), hide=True), _prop("Value", "PWR_FLAG", r2(x), r2(y - 3.81), hide=True),
                           _prop("Footprint", "", r2(x), r2(y), hide=True), _prop("Datasheet", "", r2(x), r2(y), hide=True),
                           [Sym("pin"), "1", [Sym("uuid"), uid(u, "p1")]],
                           [Sym("instances"), [Sym("project"), self.name,
                            [Sym("path"), "/" + self.uuid, [Sym("reference"), ref], [Sym("unit"), 1]]]]])

    def nc_at(self, x, y):
        self.items.append([Sym("no_connect"), [Sym("at"), r2(x), r2(y)], [Sym("uuid"), self._u()]])

    def text(self, s, x, y, size=1.27, bold=False):
        font = [Sym("font"), [Sym("size"), size, size]]
        if bold:
            font.append([Sym("bold"), Sym("yes")])
        self.items.append([Sym("text"), s, [Sym("exclude_from_sim"), Sym("no")], [Sym("at"), r2(x), r2(y), 0],
                           [Sym("effects"), font, [Sym("justify"), Sym("left"), Sym("top")]], [Sym("uuid"), self._u()]])

    def block(self, title, x0, y0, x1, y1, note=None):
        self.items.append([Sym("rectangle"), [Sym("start"), r2(x0), r2(y0)], [Sym("end"), r2(x1), r2(y1)],
                           [Sym("stroke"), [Sym("width"), 0.3], [Sym("type"), Sym("dash")], [Sym("color"), 0, 0, 132, 1]],
                           [Sym("fill"), [Sym("type"), Sym("none")]], [Sym("uuid"), self._u()]])
        self.text(title, x0 + 2.54, y0 + 2.0, size=2.5, bold=True)
        if note:
            self.text(note, x0 + 2.54, y1 - 2.0 - 1.6 * (note.count("\n") + 1), size=1.27)

    # ------------------------------------------------------- terminals ----
    def term(self, ref, pin, L=2.54, side_power=True, name=None):
        """Stub from a pin ending in a power symbol, label, or no-connect flag (by its net)."""
        if (ref, self._num(ref, pin)) in self.done:
            return
        x, y, d = self.pin(ref, pin)
        net = self.net(ref, pin)
        self._mark(ref, pin)
        if net is None:
            self.nc_at(x, y)
            return
        dx, dy = DIRS[d]
        ex, ey = x + dx * L, y + dy * L
        self.wire((x, y), (ex, ey))
        if net in POWER_LIB:
            if d in ("left", "right") and not side_power:
                up = "down" if net == "GND" else "up"
                ey2 = ey + (2.54 if up == "down" else -2.54)
                self.wire((ex, ey), (ex, ey2))
                self.power_at(net, ex, ey2, up)
            else:
                self.power_at(net, ex, ey, d)
        else:
            self.label_at(name or net, ex, ey, d)

    def auto(self, ref, L=2.54, side_power=True):
        for p in self.libs.pins(self.parts[ref].lib_id):
            if p["type"] == "no_connect" and p["num"] not in self.parts[ref].pinmap:
                self.done.add((ref, p["num"]))
                continue
            self.term(ref, p["num"], L, side_power)

    def link(self, ra, pa, rb, pb, first="h"):
        """Orthogonal wire between two pins (one bend)."""
        ax, ay, _ = self.pin(ra, pa)
        bx, by, _ = self.pin(rb, pb)
        if ax == bx or ay == by:
            self.wire((ax, ay), (bx, by))
        elif first == "h":
            self.wire((ax, ay), (bx, ay), (bx, by))
        else:
            self.wire((ax, ay), (ax, by), (bx, by))
        self._mark(ra, pa)
        self._mark(rb, pb)

    def two_pin_rot(self, ref, d, near_pin):
        """Rotation that points `near_pin` of a 2-pin part against direction d (i.e. towards the source)."""
        pins = self.libs.pins(self.parts[ref].lib_id)
        near = [p for p in pins if p["num"] == self._num(ref, near_pin)][0]
        for rot in (0, 90, 180, 270):
            if _dir_of(near["ang"] + rot) == {"right": "left", "left": "right", "up": "down", "down": "up"}[d]:
                return rot
        raise ValueError

    def inline(self, src_ref, src_pin, ref, gap=2.54, near_pin=None):
        """Place 2-pin part `ref` in line with the pin, continuing in its outward direction."""
        x, y, d = self.pin(src_ref, src_pin)
        net = self.net(src_ref, src_pin)
        if near_pin is None:
            near_pin = [p["num"] for p in self.libs.pins(self.parts[ref].lib_id) if self.net(ref, p["num"]) == net][0]
        rot = self.two_pin_rot(ref, d, near_pin)
        # pin offset from symbol origin after rotation
        pins = self.libs.pins(self.parts[ref].lib_id)
        near = [p for p in pins if p["num"] == self._num(ref, near_pin)][0]
        nx, ny = _rot(near["x"], near["y"], rot)
        dx, dy = DIRS[d]
        tx, ty = x + dx * gap, y + dy * gap
        self.place(ref, tx - nx, ty + ny, rot)
        self.wire((x, y), (tx, ty))
        self._mark(src_ref, src_pin)
        self._mark(ref, near_pin)
        far = [p["num"] for p in pins if p["num"] != self._num(ref, near_pin)][0]
        return far

    def chain(self, src_ref, src_pin, refs, gap=2.54, end=True, L=2.54):
        """Series chain of 2-pin parts from a pin, ending in a label/power symbol."""
        r, p = src_ref, src_pin
        for ref in refs:
            far = self.inline(r, p, ref, gap)
            r, p = ref, far
        if end:
            self.term(r, p, L)
        return r, p

    def shunt(self, ref, x, y, direction="down", L=0):
        """Vertical/horizontal 2-pin part whose first pin touches point (x, y) on a wire."""
        pins = self.libs.pins(self.parts[ref].lib_id)
        # pin that should touch the point: the one NOT on a power net if any
        nets = {p["num"]: self.net(ref, p["num"]) for p in pins}
        near = [n for n in nets if nets[n] not in POWER_LIB] or [pins[0]["num"]]
        near = near[0]
        rot = self.two_pin_rot(ref, direction, near)
        p = [q for q in pins if q["num"] == near][0]
        nx, ny = _rot(p["x"], p["y"], rot)
        dx, dy = DIRS[direction]
        tx, ty = x + dx * L, y + dy * L
        self.place(ref, tx - nx, ty + ny, rot)
        if L:
            self.wire((x, y), (tx, ty))
        self._mark(ref, near)
        far = [q["num"] for q in pins if q["num"] != near][0]
        self.term(ref, far, 0 if self.net(ref, far) in POWER_LIB else 2.54)
        return far

    def cap_row(self, refs, x, y, pitch=7.62, top_net_label=False):
        """Row of vertical 2-pin parts between a rail (top) and GND (bottom), connected by power symbols."""
        for i, ref in enumerate(refs):
            cx = x + i * pitch
            self.place(ref, cx, y, 0, ref_pos=(cx + 1.6, y - 1.0), val_pos=(cx + 1.6, y + 1.6))
            for p in ("1", "2"):
                net = self.net(ref, p)
                self.term(ref, p, 0 if net in POWER_LIB else 2.54)

    def bus_power(self, ref, pins, net_dir_len=2.54):
        """Join several same-side pins (e.g. RSVD) with one vertical wire and a single power symbol/label."""
        pts = [self.pin(ref, p) for p in pins]
        d = pts[0][2]
        dx, dy = DIRS[d]
        ends = []
        for (x, y, _), p in zip(pts, pins):
            ex, ey = x + dx * net_dir_len, y + dy * net_dir_len
            self.wire((x, y), (ex, ey))
            ends.append((ex, ey))
            self._mark(ref, p)
        ends.sort(key=lambda e: (e[1], e[0]))
        self.wire(*ends)
        for e in ends[1:-1]:
            self.junction(*e)
        net = self.net(ref, pins[0])
        last = ends[-1] if net == "GND" else ends[0]
        if net == "GND":
            self.wire(last, (last[0], last[1] + 2.54))
            self.junction(*last) if len(ends) > 1 else None
            self.power_at(net, last[0], last[1] + 2.54, "down")
        elif net in POWER_LIB:
            self.wire(last, (last[0], last[1] - 2.54))
            self.junction(*last) if len(ends) > 1 else None
            self.power_at(net, last[0], last[1] - 2.54, "up")
        else:
            self.label_at(net, last[0], last[1], d)

    # ----------------------------------------------------------- output ----
    def check_all_done(self):
        missing = []
        for ref, part in self.parts.items():
            if ref not in self.placed:
                missing.append(ref + " (not placed)")
                continue
            for p in self.libs.pins(part.lib_id):
                if p["type"] == "no_connect" and p["num"] not in part.pinmap and p["name"] not in part.pinmap:
                    continue
                if (ref, p["num"]) not in self.done:
                    missing.append("%s.%s(%s)" % (ref, p["num"], p["name"]))
        return missing

    def _normalize(self):
        """Split wires at junctions and T-joins, so every connection is at a segment end."""
        wires = [it for it in self.items if it[0] == "wire"]
        others = [it for it in self.items if it[0] != "wire"]
        segs = []
        for w in wires:
            pts = w[1]
            segs.append(((float(pts[1][1]), float(pts[1][2])), (float(pts[2][1]), float(pts[2][2]))))
        cut = set()
        for it in others:
            if it[0] == "junction":
                cut.add((float(it[1][1]), float(it[1][2])))
        for a, b in segs:
            cut.add(a)
            cut.add(b)
        self.pin_on_wire = []
        pinpts = set()
        for ref in self.placed:
            for q in self.libs.pins(self.parts[ref].lib_id):
                x, y, _ = self.pin(ref, q["num"])
                pinpts.add((x, y, ref, q["num"]))

        def inside(p, a, b):
            if a[0] == b[0] == p[0]:
                return min(a[1], b[1]) < p[1] < max(a[1], b[1])
            if a[1] == b[1] == p[1]:
                return min(a[0], b[0]) < p[0] < max(a[0], b[0])
            return False
        out = []
        for a, b in segs:
            inner = sorted([p for p in cut if inside(p, a, b)], key=lambda p: abs(p[0] - a[0]) + abs(p[1] - a[1]))
            for x, y, ref, num in pinpts:
                if inside((x, y), a, b):
                    self.pin_on_wire.append("%s.%s @%.2f,%.2f" % (ref, num, x, y))
            chain = [a] + inner + [b]
            for p0, p1 in zip(chain, chain[1:]):
                out.append((p0, p1))
        # junction wherever 3+ wire ends meet
        cnt = {}
        for a, b in out:
            cnt[a] = cnt.get(a, 0) + 1
            cnt[b] = cnt.get(b, 0) + 1
        have = {(float(it[1][1]), float(it[1][2])) for it in others if it[0] == "junction"}
        self.items = others
        for a, b in out:
            self.items.append([Sym("wire"), [Sym("pts"), [Sym("xy"), a[0], a[1]], [Sym("xy"), b[0], b[1]]],
                               [Sym("stroke"), [Sym("width"), 0], [Sym("type"), Sym("default")]],
                               [Sym("uuid"), self._u("w", a, b)]])
        for p, n in cnt.items():
            if n >= 3 and p not in have:
                self.junction(*p)

    def write(self, path):
        self._normalize()
        size = {"A1": None, "A2": None}
        root = [Sym("kicad_sch"), [Sym("version"), 20250114], [Sym("generator"), "vrc_schdraw"],
                [Sym("generator_version"), "9.0"], [Sym("uuid"), self.uuid], [Sym("paper"), self.paper],
                [Sym("title_block"), [Sym("title"), self.title], [Sym("date"), self.date], [Sym("rev"), self.rev],
                 [Sym("comment"), 1, "Generated from hardware/tools/circuit.py + layout.py"]],
                [Sym("lib_symbols")] + list(self.libs_used.values())] + self.items + \
               [[Sym("sheet_instances"), [Sym("path"), "/", [Sym("page"), "1"]]], [Sym("embedded_fonts"), Sym("no")]]
        with open(path, "w", encoding="utf-8") as f:
            f.write(dump(root) + "\n")
