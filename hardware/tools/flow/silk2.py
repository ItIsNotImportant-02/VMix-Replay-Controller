import pcbnew, sys, math, re, os
# silkscreen tidy-up: clip footprint silk that touches mask openings / board edge,
# place reference designators so they touch nothing (pads, other silk, edge, holes)
src = sys.argv[1]; dst = sys.argv[2] if len(sys.argv) > 2 else src
PASSIVES = "passives" in sys.argv
b = pcbnew.LoadBoard(src)
T = pcbnew.ToMM
PADC, SILKC, EDGEC = 0.15, 0.15, 0.4
def seg_pts(s):
    if s.GetShape() == pcbnew.SHAPE_T_SEGMENT:
        return [(T(s.GetStart()), T(s.GetEnd()))]
    if s.GetShape() == pcbnew.SHAPE_T_RECTANGLE:
        x0, y0 = T(s.GetStart()); x1, y1 = T(s.GetEnd())
        c = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        return [(c[i], c[(i + 1) % 4]) for i in range(4)]
    if s.GetShape() == pcbnew.SHAPE_T_CIRCLE:
        cx, cy = T(s.GetCenter()); r = T(s.GetRadius())
        c = [(cx + r * math.cos(2 * math.pi * i / 48), cy + r * math.sin(2 * math.pi * i / 48)) for i in range(48)]
        return [(c[i], c[(i + 1) % 48]) for i in range(48)]
    if s.GetShape() == pcbnew.SHAPE_T_ARC:
        cx, cy = T(s.GetCenter()); r = T(s.GetRadius())
        a0 = s.GetArcAngleStart().AsRadians(); da = s.GetArcAngle().AsRadians()
        n = max(4, int(abs(da) / 0.1))
        c = [(cx + r * math.cos(a0 + da * i / n), cy + r * math.sin(a0 + da * i / n)) for i in range(n + 1)]
        return [(c[i], c[i + 1]) for i in range(n)]
    if s.GetShape() == pcbnew.SHAPE_T_POLY:
        out = []
        ps = s.GetPolyShape()
        for o in range(ps.OutlineCount()):
            ol = ps.Outline(o); n = ol.PointCount()
            c = [(T(ol.CPoint(i).x), T(ol.CPoint(i).y)) for i in range(n)]
            out += [(c[i], c[(i + 1) % n]) for i in range(n)]
        return out
    bb = s.GetBoundingBox()
    x0, y0, x1, y1 = T(bb.GetX()), T(bb.GetY()), T(bb.GetRight()), T(bb.GetBottom())
    c = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return [(c[i], c[(i + 1) % 4]) for i in range(4)]
def pt_seg(px, py, a, c):
    ax, ay = a; bx, by = c; dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
    u = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(ax + u * dx - px, ay + u * dy - py)
def seg_x(a, c, p, q):
    def o(p1, p2, p3): return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])
    return (o(a, c, p) * o(a, c, q) < 0) and (o(p, q, a) * o(p, q, c) < 0)
def seg_seg(a, c, p, q):
    if seg_x(a, c, p, q): return 0
    return min(pt_seg(*a, p, q), pt_seg(*c, p, q), pt_seg(*p, a, c), pt_seg(*q, a, c))
def rect_seg(r, a, c):
    x0, y0, x1, y1 = r
    if x0 <= a[0] <= x1 and y0 <= a[1] <= y1: return 0
    if x0 <= c[0] <= x1 and y0 <= c[1] <= y1: return 0
    cs = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for i in range(4):
        if seg_x(a, c, cs[i], cs[(i + 1) % 4]): return 0
    d = min(pt_seg(px, py, a, c) for px, py in cs)
    for p in (a, c):
        dx = max(x0 - p[0], 0, p[0] - x1); dy = max(y0 - p[1], 0, p[1] - y1); d = min(d, math.hypot(dx, dy))
    return d
def rr(r1, r2, m):
    return not (r1[2] + m <= r2[0] or r2[2] + m <= r1[0] or r1[3] + m <= r2[1] or r2[3] + m <= r1[1])
def bbox(o):
    bb = o.GetBoundingBox(); return (T(bb.GetX()), T(bb.GetY()), T(bb.GetRight()), T(bb.GetBottom()))
# obstacles
SIDE = pcbnew.F_Cu if '--back' not in sys.argv else pcbnew.B_Cu
SILK = pcbnew.F_SilkS if SIDE == pcbnew.F_Cu else pcbnew.B_SilkS
MASK = pcbnew.F_Mask if SIDE == pcbnew.F_Cu else pcbnew.B_Mask
CRT = pcbnew.F_CrtYd if SIDE == pcbnew.F_Cu else pcbnew.B_CrtYd
pads = []
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.IsOnLayer(MASK) or p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
            pads.append(bbox(p))
edges = []
for d in b.GetDrawings():
    if d.GetLayer() == pcbnew.Edge_Cuts: edges += seg_pts(d)
for fp in b.GetFootprints():
    for g in fp.GraphicalItems():
        if g.GetLayer() == pcbnew.Edge_Cuts and isinstance(g, pcbnew.PCB_SHAPE): edges += seg_pts(g)
# 1) clip footprint silk graphics touching mask openings or the edge
removed = 0; torm = []
for fp in b.GetFootprints():
    for g in [g for g in fp.GraphicalItems()]:
        if g.GetLayer() != SILK or not isinstance(g, pcbnew.PCB_SHAPE): continue
        w = T(g.GetWidth()) / 2
        bad = False
        for a, c in seg_pts(g):
            if any(rect_seg(p, a, c) < w + 0.05 for p in pads if rr(p, (min(a[0], c[0]), min(a[1], c[1]), max(a[0], c[0]), max(a[1], c[1])), 1)):
                bad = True; break
            if any(seg_seg(a, c, *e) < w + 0.2 for e in edges): bad = True; break
        if bad: torm.append((fp, g)); removed += 1
for fp, g in torm: fp.Remove(g)
print("silk graphics removed:", removed)
silks = []
for fp in b.GetFootprints():
    for g in fp.GraphicalItems():
        if g.GetLayer() == SILK and isinstance(g, pcbnew.PCB_SHAPE):
            silks += [(a, c, T(g.GetWidth()) / 2) for a, c in seg_pts(g)]
for d in b.GetDrawings():
    if d.GetLayer() == SILK:
        if isinstance(d, pcbnew.PCB_SHAPE): silks += [(a, c, T(d.GetWidth()) / 2) for a, c in seg_pts(d)]
        else: pads.append(bbox(d))
# grid index for silk segments
G = 2.0; grid = {}
for i, (a, c, w) in enumerate(silks):
    for gx in range(int(min(a[0], c[0]) // G) - 1, int(max(a[0], c[0]) // G) + 2):
        for gy in range(int(min(a[1], c[1]) // G) - 1, int(max(a[1], c[1]) // G) + 2):
            grid.setdefault((gx, gy), []).append(i)
pgrid = {}
for i, p in enumerate(pads):
    for gx in range(int(p[0] // G) - 1, int(p[2] // G) + 2):
        for gy in range(int(p[1] // G) - 1, int(p[3] // G) + 2):
            pgrid.setdefault((gx, gy), []).append(i)
def near(gd, r):
    s = set()
    for gx in range(int(r[0] // G), int(r[2] // G) + 1):
        for gy in range(int(r[1] // G), int(r[3] // G) + 1):
            s.update(gd.get((gx, gy), ()))
    return s
def board_contains(x, y):
    return b.GetBoardEdgesBoundingBox().Contains(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
outline = pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(outline)
def inside(r):
    for x, y in ((r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3]), ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)):
        if not outline.Contains(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))): return False
    return all(rect_seg(r, a, c) >= EDGEC for a, c in edges if rr(r, (min(a[0], c[0]), min(a[1], c[1]), max(a[0], c[0]), max(a[1], c[1])), EDGEC + 0.1))
taken = []
DBG = os.environ.get("SILKDBG", "")
def ok(r, own):
    dbg = DBG and own.GetReference() == DBG
    if not inside(r):
        if dbg: print("edge", r)
        return False
    for i in near(pgrid, r):
        if rr(r, pads[i], PADC):
            if dbg: print("pad", r, pads[i])
            return False
    for i in near(grid, r):
        a, c, w = silks[i]
        if rect_seg(r, a, c) < w + SILKC:
            if dbg: print("silk", r, a, c)
            return False
    for q in taken:
        if rr(r, q, SILKC + 0.05):
            if dbg: print("taken", r, q)
            return False
    return True
passive = re.compile(r"^(R|C|D|FB|F|RN|L)\d+$")
fps = sorted(b.GetFootprints(), key=lambda f: (bool(passive.match(f.GetReference())), f.GetReference()))
placed = hidden = 0; failed = []
for fp in fps:
    ref = fp.Reference(); isp = bool(passive.match(fp.GetReference()))
    if fp.GetLayer() != SIDE: continue
    if isp and not PASSIVES:
        ref.SetVisible(False); continue
    if not isp and not ref.IsVisible(): continue
    ref.SetLayer(SILK); ref.SetVisible(True)
    sz = 0.8 if isp else 1.0
    ref.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(sz), pcbnew.FromMM(sz))); ref.SetTextThickness(pcbnew.FromMM(0.15))
    ref.SetKeepUpright(True)
    sh = fp.GetCourtyard(CRT)
    cb = sh.BBox() if sh.OutlineCount() else fp.GetBoundingBox(False, False)
    x0, y0, x1, y1 = T(cb.GetX()), T(cb.GetY()), T(cb.GetRight()), T(cb.GetBottom())
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    best = None
    for ang in (0, 90):
        ref.SetTextAngleDegrees(ang); ref.SetPosition(pcbnew.VECTOR2I(0, 0))
        tb = bbox(ref); w, h = tb[2] - tb[0], tb[3] - tb[1]
        for gap in ((0.15, 0.4, 0.8) if isp else (0.15, 0.4, 0.8, 1.3, 2.0, 3.0)):
            cands = [(cx, y0 - h / 2 - gap), (cx, y1 + h / 2 + gap), (x0 - w / 2 - gap, cy), (x1 + w / 2 + gap, cy),
                     (x0 + w / 2, y0 - h / 2 - gap), (x1 - w / 2, y0 - h / 2 - gap), (x0 + w / 2, y1 + h / 2 + gap), (x1 - w / 2, y1 + h / 2 + gap),
                     (x0 - w / 2 - gap, y0 + h / 2), (x1 + w / 2 + gap, y0 + h / 2), (x0 - w / 2 - gap, y1 - h / 2), (x1 + w / 2 + gap, y1 - h / 2)]
            if not isp:
                for sx in (-0.5, 0.5, -1, 1):
                    cands += [(cx + sx * w, y0 - h / 2 - gap), (cx + sx * w, y1 + h / 2 + gap)]
            if not isp and (x1 - x0) > 8 and (y1 - y0) > 8 and gap == 0.15:   # big parts (switch bodies): label inside the outline
                ins = [(cx, y0 + h / 2 + 1.0), (cx, y1 - h / 2 - 1.0), (x0 + w / 2 + 1.0, y0 + h / 2 + 1.0), (x1 - w / 2 - 1.0, y0 + h / 2 + 1.0), (cx, cy)]
                cands = ins + cands
            for tx, ty in cands:
                r = (tx - w / 2, ty - h / 2, tx + w / 2, ty + h / 2)
                if ok(r, fp):
                    best = (gap, ang, tx, ty, r); break
            if best: break
        if best: break
    if best:
        gap, ang, tx, ty, r = best
        ref.SetTextAngleDegrees(ang)
        ref.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(tx), pcbnew.FromMM(ty)))
        r2 = bbox(ref); taken.append(r2); placed += 1
    else:
        ref.SetLayer(pcbnew.F_Fab if SIDE == pcbnew.F_Cu else pcbnew.B_Fab); hidden += 1; failed.append(fp.GetReference())
print("refs placed:", placed, "moved to fab:", hidden, failed[:60])
b.Save(dst)
