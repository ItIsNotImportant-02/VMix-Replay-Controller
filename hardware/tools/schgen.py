"""Generate a hierarchical KiCad 9 schematic from a Python netlist description.

Every pin gets a short wire stub ending in a global label or a power symbol,
so the drawing is a readable "netlist" schematic that KiCad's ERC can check.
"""
import os, uuid, math, copy
from sexpr import parse, dump, Sym, find, findall

KICAD_SYM_DIR = os.environ.get("KICAD9_SYMBOL_DIR", "/usr/share/kicad/symbols")
GRID = 1.27
POWER_SYMBOLS = {"GND": "power:GND", "+3V3": "power:+3V3", "+5V": "power:+5V",
                 "+1V1": "power:+1V1", "VBUS": "power:VBUS"}

_ns = uuid.UUID("6b1d6c55-8a4e-4f0e-9b61-2f6a1c0de001")


def uid(*parts):
    """Deterministic UUIDs so regenerating keeps diffs small."""
    return str(uuid.uuid5(_ns, "/".join(str(p) for p in parts)))


def snap(v, g=GRID):
    return round(round(v / g) * g, 4)


class SymbolLibs:
    def __init__(self, extra_libs=None):
        self.cache = {}
        self.extra = extra_libs or {}

    def _libfile(self, lib):
        if lib in self.extra:
            return self.extra[lib]
        return os.path.join(KICAD_SYM_DIR, lib + ".kicad_sym")

    def _load_lib(self, lib):
        key = ("lib", lib)
        if key not in self.cache:
            self.cache[key] = parse(open(self._libfile(lib), encoding="utf-8").read())
        return self.cache[key]

    def get(self, lib_id):
        """Return a flattened symbol node named lib_id (for lib_symbols)."""
        if lib_id in self.cache:
            return self.cache[lib_id]
        lib, name = lib_id.split(":", 1)
        tree = self._load_lib(lib)
        syms = {s[1]: s for s in findall(tree, "symbol")}
        node = copy.deepcopy(syms[name])
        ext = find(node, "extends")
        if ext:
            parent = copy.deepcopy(syms[ext[1]])
            pname = ext[1]
            props = findall(node, "property")
            body = [x for x in parent if not (isinstance(x, list) and x[0] == "property")]
            # rename unit sub-symbols
            for x in body:
                if isinstance(x, list) and x[0] == "symbol" and isinstance(x[1], str) and x[1].startswith(pname + "_"):
                    x[1] = name + x[1][len(pname):]
            node = [body[0], name] + [x for x in body[2:] if not (isinstance(x, list) and x[0] in ("symbol",))] \
                + props + [x for x in body if isinstance(x, list) and x[0] == "symbol"]
        node[1] = lib_id
        self.cache[lib_id] = node
        return node

    def pins(self, lib_id, unit=1):
        node = self.get(lib_id)
        out = []
        for sub in findall(node, "symbol"):
            parts = sub[1].rsplit("_", 2)
            u = int(parts[-2])
            if u not in (0, unit):
                continue
            for p in findall(sub, "pin"):
                at = find(p, "at")
                name = find(p, "name")[1]
                num = find(p, "number")[1]
                hidden = any(isinstance(x, Sym) and x == "hide" for x in p) or (find(p, "hide") is not None and find(p, "hide")[1] == "yes")
                out.append(dict(num=num, name=name, x=float(at[1]), y=float(at[2]),
                                ang=float(at[3]) if len(at) > 3 else 0.0, type=str(p[1]), hidden=hidden))
        return out

    def bbox(self, lib_id):
        pins = self.pins(lib_id)
        xs, ys = [0.0], [0.0]
        node = self.get(lib_id)
        for sub in findall(node, "symbol"):
            for r in findall(sub, "rectangle"):
                s, e = find(r, "start"), find(r, "end")
                xs += [float(s[1]), float(e[1])]
                ys += [float(s[2]), float(e[2])]
        for p in pins:
            xs.append(p["x"]); ys.append(p["y"])
        return min(xs), max(xs), min(ys), max(ys)

    def is_power(self, lib_id):
        return find(self.get(lib_id), "power") is not None


class Part:
    def __init__(self, ref, lib_id, value, footprint="", pins=None, lcsc="", mpn="",
                 desc="", datasheet="", dnp=False, in_bom=True, fields=None):
        self.ref, self.lib_id, self.value, self.footprint = ref, lib_id, value, footprint
        self.pinmap = pins or {}
        self.lcsc, self.mpn, self.desc, self.datasheet = lcsc, mpn, desc, datasheet
        self.dnp, self.in_bom = dnp, in_bom
        self.fields = fields or {}


class Sheet:
    def __init__(self, name, filename, title=""):
        self.name, self.filename, self.title = name, filename, title or name
        self.parts = []
        self.notes = []

    def add(self, part):
        self.parts.append(part)
        return part

    def note(self, text):
        self.notes.append(text)


def _prop(name, value, x, y, hide=False, ang=0, size=1.27, justify=None):
    eff = [Sym("effects"), [Sym("font"), [Sym("size"), size, size]]]
    if justify:
        eff.append([Sym("justify")] + [Sym(j) for j in justify])
    if hide:
        eff.append([Sym("hide"), Sym("yes")])
    return [Sym("property"), name, value, [Sym("at"), x, y, ang], eff]


class Project:
    def __init__(self, name, libs, paper="A3", title="", rev="", company=""):
        self.name, self.libs, self.paper = name, libs, paper
        self.title, self.rev, self.company = title, rev, company
        self.sheets = []
        self.root_uuid = uid(name, "root")
        self.pwr_flag_nets = set()

    def sheet(self, name, filename, title=""):
        s = Sheet(name, filename, title)
        self.sheets.append(s)
        return s

    # ------------------------------------------------------------------
    def _resolve_pins(self, part):
        pins = self.libs.pins(part.lib_id)
        by_num = {p["num"]: p for p in pins}
        by_name = {}
        for p in pins:
            by_name.setdefault(p["name"], []).append(p)
        assigned = {}
        for key, net in part.pinmap.items():
            key = str(key)
            if key in by_num:
                assigned[key] = net
            elif key in by_name:
                for p in by_name[key]:
                    assigned[p["num"]] = net
            else:
                raise KeyError("%s: pin %s not in %s" % (part.ref, key, part.lib_id))
        missing = [p for p in pins if p["num"] not in assigned and p["type"] != "no_connect"]
        if missing and not self.libs.is_power(part.lib_id):
            raise KeyError("%s (%s): unassigned pins %s" % (part.ref, part.lib_id,
                           ", ".join("%s/%s" % (p["num"], p["name"]) for p in missing)))
        return pins, assigned

    def _title_block(self, sheet_title):
        tb = [Sym("title_block"), [Sym("title"), sheet_title]]
        if self.rev:
            tb.append([Sym("rev"), self.rev])
        if self.company:
            tb.append([Sym("company"), self.company])
        return tb

    def _sheet_file(self, sheet, sheet_uuid, page):
        libs_used = {}
        items = []
        inst_path = "/%s/%s" % (self.root_uuid, sheet_uuid)
        file_uuid = uid(self.name, sheet.filename)
        # layout -----------------------------------------------------
        W, H = (420.0, 297.0) if self.paper == "A3" else (594.0, 420.0)
        x0, y0, xmax = 25.4, 30.48, W - 20
        cx, cy, row_h = x0, y0, 0.0
        lbl_margin = 22.86
        pwr_counter = [0]

        def add_power_or_label(net, x, y, direction, key):
            if net in POWER_SYMBOLS:
                lib_id = POWER_SYMBOLS[net]
                libs_used[lib_id] = self.libs.get(lib_id)
                rot = {"down": 0, "up": 180, "left": 270, "right": 90}[direction] if net == "GND" else \
                      {"up": 0, "down": 180, "left": 90, "right": 270}[direction]
                pwr_counter[0] += 1
                ref = "#PWR%s%03d" % (page, pwr_counter[0])
                u = uid(self.name, sheet.filename, "pwr", key)
                items.append([Sym("symbol"), [Sym("lib_id"), lib_id], [Sym("at"), x, y, rot], [Sym("unit"), 1],
                              [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("no")], [Sym("on_board"), Sym("yes")],
                              [Sym("dnp"), Sym("no")], [Sym("uuid"), u],
                              _prop("Reference", ref, x, y, hide=True),
                              _prop("Value", net, x, y + (3.81 if net == "GND" else -3.81), hide=False),
                              _prop("Footprint", "", x, y, hide=True),
                              _prop("Datasheet", "", x, y, hide=True),
                              [Sym("pin"), "1", [Sym("uuid"), uid(u, "p1")]],
                              [Sym("instances"), [Sym("project"), self.name,
                               [Sym("path"), inst_path, [Sym("reference"), ref], [Sym("unit"), 1]]]]])
            else:
                ang = {"right": 0, "up": 90, "left": 180, "down": 270}[direction]
                just = "left" if direction in ("right", "up") else "right"
                items.append([Sym("global_label"), net, [Sym("shape"), Sym("bidirectional")],
                              [Sym("at"), x, y, ang], [Sym("fields_autoplaced"), Sym("yes")],
                              [Sym("effects"), [Sym("font"), [Sym("size"), 1.27, 1.27]], [Sym("justify"), Sym(just)]],
                              [Sym("uuid"), uid(self.name, sheet.filename, "gl", key)],
                              [Sym("property"), "Intersheetrefs", "${INTERSHEET_REFS}", [Sym("at"), x, y, 0],
                               [Sym("effects"), [Sym("font"), [Sym("size"), 1.27, 1.27]], [Sym("hide"), Sym("yes")]]]])

        for part in sheet.parts:
            sym = self.libs.get(part.lib_id)
            libs_used[part.lib_id] = sym
            pins, assigned = self._resolve_pins(part)
            bx0, bx1, by0, by1 = self.libs.bbox(part.lib_id)
            w = (bx1 - bx0) + 2 * lbl_margin
            h = (by1 - by0) + 15.24
            if cx + w > xmax and cx > x0:
                cx, cy, row_h = x0, cy + row_h, 0.0
            sx = snap(cx + lbl_margin - bx0, 2.54)
            sy = snap(cy + 7.62 + by1, 2.54)   # lib y up -> sheet y down
            cx += w
            row_h = max(row_h, h)
            u = uid(self.name, part.ref)
            node = [Sym("symbol"), [Sym("lib_id"), part.lib_id], [Sym("at"), sx, sy, 0], [Sym("unit"), 1],
                    [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes" if part.in_bom else "no")],
                    [Sym("on_board"), Sym("yes")], [Sym("dnp"), Sym("yes" if part.dnp else "no")],
                    [Sym("fields_autoplaced"), Sym("yes")], [Sym("uuid"), u],
                    _prop("Reference", part.ref, sx + bx1 + 1.27, sy - by1 - 1.27, justify=["left"]),
                    _prop("Value", part.value, sx + bx1 + 1.27, sy - by1 + 1.27, justify=["left"]),
                    _prop("Footprint", part.footprint, sx, sy, hide=True),
                    _prop("Datasheet", part.datasheet, sx, sy, hide=True),
                    _prop("Description", part.desc, sx, sy, hide=True)]
            extra = dict(part.fields)
            if part.lcsc:
                extra["LCSC"] = part.lcsc
            if part.mpn:
                extra["MPN"] = part.mpn
            for k, v in extra.items():
                node.append(_prop(k, v, sx, sy, hide=True))
            for p in pins:
                node.append([Sym("pin"), p["num"], [Sym("uuid"), uid(u, "pin", p["num"])]])
            node.append([Sym("instances"), [Sym("project"), self.name,
                         [Sym("path"), inst_path, [Sym("reference"), part.ref], [Sym("unit"), 1]]]])
            items.append(node)
            # stubs + labels
            for p in pins:
                net = assigned.get(p["num"])
                px, py = sx + p["x"], sy - p["y"]
                if p["num"] not in assigned:
                    continue   # no_connect type pin
                if net is None:
                    items.append([Sym("no_connect"), [Sym("at"), px, py], [Sym("uuid"), uid(u, "nc", p["num"])]])
                    continue
                # outward direction (away from body)
                d = {0: ("left", -1, 0), 180: ("right", 1, 0), 90: ("down", 0, 1), 270: ("up", 0, -1)}[int(p["ang"]) % 360]
                L = 2.54
                ex, ey = px + d[1] * L, py + d[2] * L
                items.append([Sym("wire"), [Sym("pts"), [Sym("xy"), px, py], [Sym("xy"), ex, ey]],
                              [Sym("stroke"), [Sym("width"), 0], [Sym("type"), Sym("default")]],
                              [Sym("uuid"), uid(u, "w", p["num"])]])
                add_power_or_label(net, ex, ey, d[0], (part.ref, p["num"]))
        # PWR_FLAGs for nets requested on this sheet
        fx, fy = W - 60, H - 60
        for i, net in enumerate(sorted(n for n in self.pwr_flag_nets if self._flag_sheet.get(n) == sheet.name)):
            lib_id = "power:PWR_FLAG"
            libs_used[lib_id] = self.libs.get(lib_id)
            x, y = snap(25.4 + i * 22.86, 2.54), snap(H - 30.48, 2.54)
            u = uid(self.name, "flag", net)
            items.append([Sym("symbol"), [Sym("lib_id"), lib_id], [Sym("at"), x, y, 0], [Sym("unit"), 1],
                          [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("no")], [Sym("on_board"), Sym("yes")],
                          [Sym("dnp"), Sym("no")], [Sym("uuid"), u],
                          _prop("Reference", "#FLG%s%02d" % (page, i + 1), x, y - 5, hide=True),
                          _prop("Value", "PWR_FLAG", x, y - 3.81),
                          _prop("Footprint", "", x, y, hide=True), _prop("Datasheet", "", x, y, hide=True),
                          [Sym("pin"), "1", [Sym("uuid"), uid(u, "p")]],
                          [Sym("instances"), [Sym("project"), self.name,
                           [Sym("path"), inst_path, [Sym("reference"), "#FLG%s%02d" % (page, i + 1)], [Sym("unit"), 1]]]]])
            items.append([Sym("wire"), [Sym("pts"), [Sym("xy"), x, y], [Sym("xy"), x, y + 2.54]],
                          [Sym("stroke"), [Sym("width"), 0], [Sym("type"), Sym("default")]], [Sym("uuid"), uid(u, "w")]])
            add_power_or_label(net, x, y + 2.54, "down", ("flag", net))
        # notes
        for i, t in enumerate(sheet.notes):
            items.append([Sym("text"), t, [Sym("exclude_from_sim"), Sym("no")], [Sym("at"), 25.4, 15.24 + 0 * i, 0],
                          [Sym("effects"), [Sym("font"), [Sym("size"), 1.6, 1.6]], [Sym("justify"), Sym("left"), Sym("top")]],
                          [Sym("uuid"), uid(self.name, sheet.filename, "note", i)]])
        if cy + row_h > H - 10:
            raise ValueError("sheet %s overflows paper (%.0f mm)" % (sheet.name, cy + row_h))
        root = [Sym("kicad_sch"), [Sym("version"), 20250114], [Sym("generator"), "vrc_schgen"],
                [Sym("generator_version"), "9.0"], [Sym("uuid"), file_uuid], [Sym("paper"), self.paper],
                self._title_block(sheet.title),
                [Sym("lib_symbols")] + list(libs_used.values())] + items + \
               [[Sym("embedded_fonts"), Sym("no")]]
        return root

    def flag(self, net, sheet_name):
        self.pwr_flag_nets.add(net)
        if not hasattr(self, "_flag_sheet"):
            self._flag_sheet = {}
        self._flag_sheet[net] = sheet_name

    def write(self, outdir):
        if not hasattr(self, "_flag_sheet"):
            self._flag_sheet = {}
        refs = {}
        for s in self.sheets:
            for p in s.parts:
                if p.ref in refs:
                    raise ValueError("duplicate ref " + p.ref)
                refs[p.ref] = s.name
        root_items = []
        x, y = 25.4, 40.64
        for i, s in enumerate(self.sheets):
            su = uid(self.name, "sheet", s.filename)
            page = str(i + 2)
            sx, sy = 25.4 + (i % 4) * 96.52, 40.64 + (i // 4) * 50.8
            root_items.append([Sym("sheet"), [Sym("at"), sx, sy], [Sym("size"), 76.2, 25.4],
                               [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")], [Sym("on_board"), Sym("yes")],
                               [Sym("dnp"), Sym("no")], [Sym("fields_autoplaced"), Sym("yes")],
                               [Sym("stroke"), [Sym("width"), 0.1524], [Sym("type"), Sym("solid")]],
                               [Sym("fill"), [Sym("color"), 0, 0, 0, 0.0]], [Sym("uuid"), su],
                               [Sym("property"), "Sheetname", s.name, [Sym("at"), sx, sy - 0.7, 0],
                                [Sym("effects"), [Sym("font"), [Sym("size"), 1.27, 1.27]], [Sym("justify"), Sym("left"), Sym("bottom")]]],
                               [Sym("property"), "Sheetfile", s.filename, [Sym("at"), sx, sy + 26, 0],
                                [Sym("effects"), [Sym("font"), [Sym("size"), 1.27, 1.27]], [Sym("justify"), Sym("left"), Sym("top")]]],
                               [Sym("instances"), [Sym("project"), self.name, [Sym("path"), "/" + self.root_uuid, [Sym("page"), page]]]]])
            data = self._sheet_file(s, su, page)
            with open(os.path.join(outdir, s.filename), "w", encoding="utf-8") as f:
                f.write(dump(data) + "\n")
        root = [Sym("kicad_sch"), [Sym("version"), 20250114], [Sym("generator"), "vrc_schgen"],
                [Sym("generator_version"), "9.0"], [Sym("uuid"), self.root_uuid], [Sym("paper"), "A4"],
                self._title_block(self.title), [Sym("lib_symbols")]] + root_items + \
               [[Sym("sheet_instances"), [Sym("path"), "/", [Sym("page"), "1"]]], [Sym("embedded_fonts"), Sym("no")]]
        with open(os.path.join(outdir, self.name + ".kicad_sch"), "w", encoding="utf-8") as f:
            f.write(dump(root) + "\n")
