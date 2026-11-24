"""Route the connections the autorouter left open.

Grid maze router (A*, 0.05 mm grid, F.Cu + B.Cu only, 45-degree moves, vias allowed).
Obstacles are every copper item of another net plus holes and the 0.3 mm board-edge band,
inflated by clearance + half the track width, so a path found on the grid is DRC clean by
construction. The inner layers are never touched (In1 = GND plane, In2 = +5V_LED plane).

usage (inside the KiCad container):  python3 tools/leftover.py <board.kicad_pcb>
"""
import heapq, math, sys
import numpy as np
import pcbnew

RES = 0.05                     # grid step, mm
CLR = 0.16                     # copper clearance, mm (rule 0.15 + 0.01 for grid rounding)
HOLE_CLR = 0.25                # copper to hole edge
EDGE = 0.4                     # copper to board edge (0.3 rule; the edge rule areas are 0.35 wide)
HI = {"VBUS", "+5V"}           # class clearance 0.2 instead of 0.15


def extra(net):
    return 0.05 if net in HI else 0.0
VIA_D, VIA_DRILL = 0.6, 0.3
SKIP = {"GND", "+5V_LED"}      # plane nets, connected through the inner layers
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In2_Cu)   # In2 only as a last resort (inner=True)
NL = len(LAYERS)
INNER_COST = 3.0
BIG_EXP = 30_000_000            # expansion cap of the whole-board search
ESC_R = 0.6                    # escape pass: foreign copper this close to an unreached pin is torn out               # a step on In2 costs this much more (keeps the +5V_LED plane whole)
VIA_COST = 24                  # in grid steps (= 1.2 mm of track)
WINDOW = 6.0
DEBUG = False                  # search window margin around the two clusters, mm


def T(v):
    return pcbnew.ToMM(v)


def M(v):
    return pcbnew.FromMM(float(v))


def width_of(net):
    if net in ("VBUS", "+5V"):
        return 0.6
    if net in ("+3V3", "+3V3A", "+1V1"):
        return 0.25
    if net.startswith("/USB_"):
        return 0.28
    if net.startswith("/ETH_") or net.startswith("/W_"):
        return 0.22
    return 0.15


# ------------------------------------------------------------ shapes --------
# every copper item becomes ("rect", x0, y0, x1, y1) | ("cap", xa, ya, xb, yb, r) on a set of layers
def pad_shapes(p):
    b = p.GetBoundingBox()
    x0, y0, x1, y1 = T(b.GetX()), T(b.GetY()), T(b.GetRight()), T(b.GetBottom())
    try:
        sh = p.GetShape(pcbnew.F_Cu)
    except TypeError:
        sh = p.GetShape()
    w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if sh == pcbnew.PAD_SHAPE_CIRCLE:
        return ("cap", cx, cy, cx, cy, w / 2)
    if sh == pcbnew.PAD_SHAPE_OVAL:
        if w >= h:
            return ("cap", cx - (w - h) / 2, cy, cx + (w - h) / 2, cy, h / 2)
        return ("cap", cx, cy - (h - w) / 2, cx, cy + (h - w) / 2, w / 2)
    return ("rect", x0, y0, x1, y1)


def dist_field(shape, X, Y):
    if shape[0] == "rect":
        _, x0, y0, x1, y1 = shape
        ex = np.maximum(x0 - X, X - x1)
        ey = np.maximum(y0 - Y, Y - y1)
        out = np.hypot(np.maximum(ex, 0), np.maximum(ey, 0))
        return np.where((ex < 0) & (ey < 0), np.maximum(ex, ey), out)     # signed: negative inside
    _, xa, ya, xb, yb, r = shape
    vx, vy = xb - xa, yb - ya
    L2 = vx * vx + vy * vy
    if L2 == 0:
        return np.hypot(X - xa, Y - ya) - r
    t = np.clip(((X - xa) * vx + (Y - ya) * vy) / L2, 0, 1)
    return np.hypot(X - (xa + t * vx), Y - (ya + t * vy)) - r


def bbox(shape, m):
    if shape[0] == "rect":
        return shape[1] - m, shape[2] - m, shape[3] + m, shape[4] + m
    _, xa, ya, xb, yb, r = shape
    return min(xa, xb) - r - m, min(ya, yb) - r - m, max(xa, xb) + r + m, max(ya, yb) + r + m


def shape_dist_pt(shape, x, y):
    return float(dist_field(shape, np.array([x]), np.array([y]))[0])


# ------------------------------------------------------------- board --------
class Item:
    def __init__(self, kind, net, shape, layers, obj=None, hole=0.0):
        self.kind, self.net, self.shape, self.layers, self.obj, self.hole = kind, net, shape, layers, obj, hole
        # autorouted copper that may be ripped up to make room (never pads, locked or plane copper)
        self.rip = kind in ("track", "via") and net not in SKIP and net != "" and not (obj is not None and obj.IsLocked())


def collect(board):
    items = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            layers = [i for i, L in enumerate(LAYERS) if p.IsOnLayer(L)]
            hole = T(p.GetDrillSize().x) / 2 if p.GetDrillSize().x > 0 else 0.0
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                c = p.GetPosition()
                items.append(Item("hole", "", ("cap", T(c.x), T(c.y), T(c.x), T(c.y), hole), [0, 1, 2], p, hole))
                continue
            if layers:
                items.append(Item("pad", p.GetNetname(), pad_shapes(p), layers, p, hole))
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            c = t.GetPosition()
            r = T(t.GetWidth(pcbnew.F_Cu)) / 2
            items.append(Item("via", t.GetNetname(), ("cap", T(c.x), T(c.y), T(c.x), T(c.y), r), [0, 1, 2], t,
                              T(t.GetDrillValue()) / 2))
        elif t.GetLayer() in LAYERS:
            s, e = t.GetStart(), t.GetEnd()
            items.append(Item("track", t.GetNetname(),
                              ("cap", T(s.x), T(s.y), T(e.x), T(e.y), T(t.GetWidth()) / 2),
                              [LAYERS.index(t.GetLayer())], t))
    return items


def clusters(net_items):
    """Union-find over the copper of one net (shared layer + touching)."""
    n = len(net_items)
    par = list(range(n))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i

    def pts(it):
        s = it.shape
        if s[0] == "cap":
            return [(s[1], s[2]), (s[3], s[4])]
        return [((s[1] + s[3]) / 2, (s[2] + s[4]) / 2)]

    for i in range(n):
        for j in range(i + 1, n):
            a, b = net_items[i], net_items[j]
            if not set(a.layers) & set(b.layers):
                continue
            touch = False
            for u, v in ((a, b), (b, a)):
                if u.kind in ("track", "via"):
                    r = u.shape[5]
                    for (x, y) in pts(u):
                        if shape_dist_pt(v.shape, x, y) <= r * 0.5 + 1e-3 or \
                                (v.kind in ("track", "via") and shape_dist_pt(v.shape, x, y) <= 1e-3):
                            touch = True
                            break
                if touch:
                    break
            if not touch and a.kind == "pad" and b.kind == "pad":
                touch = shape_dist_pt(a.shape, *pts(b)[0]) <= 0
            if touch:
                par[f(i)] = f(j)
    groups = {}
    for i in range(n):
        groups.setdefault(f(i), []).append(net_items[i])
    return list(groups.values())


# -------------------------------------------------------------- grid --------
class Grid:
    def __init__(self, board):
        self.outline = pcbnew.SHAPE_POLY_SET()
        board.GetBoardPolygonOutlines(self.outline)
        bb = self.outline.BBox()
        self.x0, self.y0 = T(bb.GetX()) - 1, T(bb.GetY()) - 1
        self.nx = int((T(bb.GetWidth()) + 2) / RES) + 1
        self.ny = int((T(bb.GetHeight()) + 2) / RES) + 1
        # thresholds: centre-line distance a track of width w (or a via) must keep from foreign copper
        self.widths = sorted({0.15, 0.22, 0.25, 0.28, 0.6, 0.7})
        self.th = {w: CLR + w / 2 for w in self.widths}
        self.th["via"] = CLR + VIA_D / 2
        self.th["via_hi"] = CLR + 0.05 + VIA_D / 2      # vias of the 0.2 mm clearance class
        self.cnt = {k: np.zeros((NL, self.ny, self.nx), np.int16) for k in self.th}
        self.rcnt = {k: np.zeros((NL, self.ny, self.nx), np.int16) for k in self.th}
        self.edge_mask()

    def xy(self, ix, iy):
        return self.x0 + ix * RES, self.y0 + iy * RES

    def idx(self, x, y):
        return int(round((x - self.x0) / RES)), int(round((y - self.y0) / RES))

    def edge_mask(self):
        """Cells closer than EDGE (+ w/2) to the board edge, or outside it, are blocked for good."""
        ys = self.y0 + np.arange(self.ny) * RES
        xs = self.x0 + np.arange(self.nx) * RES
        inside = np.zeros((self.ny, self.nx), bool)
        dmin = np.full((self.ny, self.nx), 1e9)
        X, Y = np.meshgrid(xs, ys)
        for k in range(self.outline.OutlineCount()):
            chains = [self.outline.Outline(k)] + [self.outline.Hole(k, h) for h in range(self.outline.HoleCount(k))]
            for ch in chains:
                pts = [(T(ch.CPoint(i).x), T(ch.CPoint(i).y)) for i in range(ch.PointCount())]
                for (xa, ya), (xb, yb) in zip(pts, pts[1:] + pts[:1]):
                    # even-odd scanline
                    cond = (ya > ys) != (yb > ys)
                    rows = np.nonzero(cond)[0]
                    if len(rows):
                        xi = xa + (ys[rows] - ya) * (xb - xa) / (yb - ya)
                        for r, x in zip(rows, xi):
                            inside[r, :] ^= xs < x
                    # distance band (only near the edge to keep it cheap)
                    x0, x1 = min(xa, xb) - 1, max(xa, xb) + 1
                    y0, y1 = min(ya, yb) - 1, max(ya, yb) + 1
                    i0, j0 = self.idx(x0, y0)
                    i1, j1 = self.idx(x1, y1)
                    i0, j0, i1, j1 = max(i0, 0), max(j0, 0), min(i1, self.nx - 1), min(j1, self.ny - 1)
                    sub = dist_field(("cap", xa, ya, xb, yb, 0), X[j0:j1 + 1, i0:i1 + 1], Y[j0:j1 + 1, i0:i1 + 1])
                    dmin[j0:j1 + 1, i0:i1 + 1] = np.minimum(dmin[j0:j1 + 1, i0:i1 + 1], sub)
        self.edge = {k: (~inside) | (dmin < EDGE + (VIA_D / 2 if str(k).startswith("via") else k / 2)) for k in self.th}

    def raster(self, it, sign=1):
        """Add (sign 1) / remove (-1) an item's keep-away zone to the count grids."""
        for k, t in self.th.items():
            m = t + extra(it.net)
            if it.kind == "hole":
                m = (VIA_D / 2 if str(k).startswith("via") else k / 2) + HOLE_CLR
            x0, y0, x1, y1 = bbox(it.shape, m)
            i0, j0 = self.idx(x0, y0)
            i1, j1 = self.idx(x1, y1)
            i0, j0, i1, j1 = max(i0, 0), max(j0, 0), min(i1 + 1, self.nx - 1), min(j1 + 1, self.ny - 1)
            if i1 < i0 or j1 < j0:
                continue
            xs = self.x0 + np.arange(i0, i1 + 1) * RES
            ys = self.y0 + np.arange(j0, j1 + 1) * RES
            X, Y = np.meshgrid(xs, ys)
            hit = (dist_field(it.shape, X, Y) < m - 1e-6).astype(np.int16) * sign
            for L in it.layers:
                self.cnt[k][L, j0:j1 + 1, i0:i1 + 1] += hit
                if it.rip:
                    self.rcnt[k][L, j0:j1 + 1, i0:i1 + 1] += hit


def path_to_points(path):
    """Collapse grid steps into corner points."""
    out = [path[0]]
    for a, b, c in zip(path, path[1:], path[2:]):
        if a[0] != b[0] or b[0] != c[0]:
            out.append(b)
            continue
        if (b[1] - a[1], b[2] - a[2]) != (c[1] - b[1], c[2] - b[2]):
            out.append(b)
    out.append(path[-1])
    # drop duplicates
    res = [out[0]]
    for p in out[1:]:
        if p != res[-1]:
            res.append(p)
    return res


SOFT = 25        # extra cost per grid step through ripable copper of another net


def astar(g, net, w, src, dst, anchor, soft=False, big=False, inner=False):
    """src/dst: lists of copper items; the search window spans src and the anchor item of dst.
    Returns list of (layer, ix, iy) or None."""
    xs0, ys0, xs1, ys1 = 1e9, 1e9, -1e9, -1e9
    for it in src + [anchor]:
        a, b, c, d = bbox(it.shape, 0)
        xs0, ys0, xs1, ys1 = min(xs0, a), min(ys0, b), max(xs1, c), max(ys1, d)
    m = 1000.0 if big else WINDOW        # big: the whole board (long detours, e.g. round the jog hole)
    i0, j0 = g.idx(xs0 - m, ys0 - m)
    i1, j1 = g.idx(xs1 + m, ys1 + m)
    i0, j0, i1, j1 = max(i0, 0), max(j0, 0), min(i1, g.nx - 1), min(j1, g.ny - 1)
    W, H = i1 - i0 + 1, j1 - j0 + 1
    # own-net copper never blocks: subtract it locally
    wk = min(k for k in g.widths if k >= w + 2 * extra(net) - 1e-9)
    blk_t = g.cnt[wk][:, j0:j1 + 1, i0:i1 + 1].astype(np.int32)
    vk = "via_hi" if extra(net) else "via"
    blk_v = g.cnt[vk][:, j0:j1 + 1, i0:i1 + 1].astype(np.int32)
    rblk_t = g.rcnt[wk][:, j0:j1 + 1, i0:i1 + 1].astype(np.int32)
    rblk_v = g.rcnt[vk][:, j0:j1 + 1, i0:i1 + 1].astype(np.int32)
    xs = g.x0 + np.arange(i0, i1 + 1) * RES
    ys = g.y0 + np.arange(j0, j1 + 1) * RES
    X, Y = np.meshgrid(xs, ys)
    for it in g.net_items[net]:
        for k, blk, rblk in ((wk, blk_t, rblk_t), (vk, blk_v, rblk_v)):
            hit = (dist_field(it.shape, X, Y) < g.th[k] + extra(net) - 1e-6).astype(np.int32)
            for L in it.layers:
                blk[L] -= hit
                if it.rip:
                    rblk[L] -= hit
    free_t = (blk_t <= 0) & ~g.edge[wk][None, j0:j1 + 1, i0:i1 + 1]
    free_v = (blk_v <= 0).all(axis=0) & ~g.edge["via"][j0:j1 + 1, i0:i1 + 1]
    if not inner:
        free_t[2] = False
    if soft:     # cells blocked only by ripable copper of other nets
        soft_t = ((blk_t - rblk_t) <= 0) & ~free_t & ~g.edge[wk][None, j0:j1 + 1, i0:i1 + 1]
        soft_t[2] = False
        soft_v = ((blk_v - rblk_v) <= 0).all(axis=0) & ~free_v & ~g.edge["via"][j0:j1 + 1, i0:i1 + 1]
    else:
        soft_t = np.zeros_like(free_t)
        soft_v = np.zeros_like(free_v)
    # source / target cells: inside own copper (centre line may start anywhere on the copper)
    def cells(items):
        m = np.zeros((NL, H, W), bool)
        for it in items:
            inside = dist_field(it.shape, X, Y) <= -min(0.05, (it.shape[5] if it.shape[0] == "cap" else 0.1) * 0.5)
            for L in it.layers:
                m[L] |= inside
        return m
    S, D = cells(src), cells(dst)
    S &= free_t | soft_t  # start / end only where a track of this width may sit
    D &= free_t | soft_t
    tgt = np.argwhere(D)
    if not len(tgt) or not S.any():
        if DEBUG:
            print("    empty %s: S=%d D=%d" % (net, S.sum(), D.sum()))
        return None
    tx = (tgt[:, 2].min() + tgt[:, 2].max()) / 2
    ty = (tgt[:, 1].min() + tgt[:, 1].max()) / 2
    ft = free_t.astype(np.uint8).ravel().tobytes()
    fv = free_v.astype(np.uint8).ravel().tobytes()
    sft = soft_t.astype(np.uint8).ravel().tobytes()
    sfv = soft_v.astype(np.uint8).ravel().tobytes()
    dd = D.astype(np.uint8).ravel().tobytes()
    N = W * H
    INF = float("inf")
    import array
    gscore = array.array("d", [INF]) * (NL * N)
    prev = array.array("i", [-1]) * (NL * N)
    HW_ = 2.0 if big else 1.3   # weighted A*: a little longer paths, far fewer expansions
    heap = []
    for L, y, x in np.argwhere(S):
        s = L * N + y * W + x
        gscore[s] = 0.0
        heapq.heappush(heap, (math.hypot(x - tx, y - ty), 0.0, s))
    steps = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
             (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
    found = None
    expanded = 0
    while heap:
        f, gs, s = heapq.heappop(heap)
        if gs > gscore[s]:
            continue
        if dd[s]:
            found = s
            break
        expanded += 1
        if expanded > (BIG_EXP if big else 1_500_000):
            break
        L, r = divmod(s, N)
        y, x = divmod(r, W)
        for dx, dy, c in steps:
            nx_, ny_ = x + dx, y + dy
            if not (0 <= nx_ < W and 0 <= ny_ < H):
                continue
            a1, a2 = L * N + y * W + nx_, L * N + ny_ * W + x
            if dx and dy and not (ft[a1] or dd[a1] or sft[a1]) and not (ft[a2] or dd[a2] or sft[a2]):
                continue          # no squeezing diagonally between two blocked cells
            t = L * N + ny_ * W + nx_
            if ft[t] or dd[t]:
                ng = gs + c * (INNER_COST if L == 2 else 1.0)
            elif sft[t]:
                ng = gs + c + SOFT
            else:
                continue
            # small bend penalty keeps tracks straight
            p = prev[s]
            if p >= 0:
                pL, pr = divmod(p, N)
                py, px = divmod(pr, W)
                if pL == L and (x - px, y - py) != (dx, dy):
                    ng += 0.6
            if ng < gscore[t]:
                gscore[t] = ng
                prev[t] = s
                heapq.heappush(heap, (ng + HW_ * math.hypot(nx_ - tx, ny_ - ty), ng, t))
        if fv[r] or sfv[r]:
            for L2 in range(NL):
                if L2 == L:
                    continue
                t = L2 * N + r
                ng = gs + VIA_COST + (0 if fv[r] else SOFT * 4)
                if (ft[t] or dd[t] or sft[t]) and ng < gscore[t]:
                    gscore[t] = ng
                    prev[t] = s
                    heapq.heappush(heap, (ng + HW_ * math.hypot(x - tx, y - ty), ng, t))
    if found is None:
        if DEBUG:
            print("    fail %s: S=%d Sfree=%d D=%d expanded=%d window=%dx%d" % (net, S.sum(), (S & free_t).sum(), D.sum(), expanded, W, H))
        return None
    path = []
    s = found
    while s >= 0:
        L, r = divmod(s, N)
        y, x = divmod(r, W)
        path.append((L, x + i0, y + j0))
        s = prev[s]
    path = path[::-1]
    # straighten: greedy line-of-sight over the corner points, per layer run
    allowed = free_t | S | D | soft_t

    def visible(a, b):
        L = a[0]
        ax, ay, bx, by = a[1] - i0, a[2] - j0, b[1] - i0, b[2] - j0
        n = int(max(abs(bx - ax), abs(by - ay)) * 4) + 1
        for k in range(n + 1):
            x = int(round(ax + (bx - ax) * k / n))
            y = int(round(ay + (by - ay) * k / n))
            if not allowed[L, y, x]:
                return False
        return True

    corners = path_to_points(path)
    out = [corners[0]]
    i = 0
    while i < len(corners) - 1:
        if corners[i + 1][0] != corners[i][0]:      # via
            out.append(corners[i + 1])
            i += 1
            continue
        j = i + 1
        k = i + 2
        while k < len(corners) and corners[k][0] == corners[i][0]:
            if visible(corners[i], corners[k]):
                j = k
            k += 1
        out.append(corners[j])
        i = j
    return out


def path_shapes(g, net, w, path):
    """The copper a path would add, as Items without board objects (to test before committing)."""
    out = []
    for a, b in zip(path, path[1:]):
        if a[0] != b[0]:
            x, y = g.xy(a[1], a[2])
            out.append(Item("via", net, ("cap", x, y, x, y, VIA_D / 2), [0, 1, 2], None, VIA_DRILL / 2))
        else:
            xa, ya = g.xy(a[1], a[2])
            xb, yb = g.xy(b[1], b[2])
            out.append(Item("track", net, ("cap", xa, ya, xb, yb, w / 2), [a[0]], None))
    return out


def add_path(board, g, net, w, path, lock=False):
    netinfo = board.FindNet(net)
    new = []
    pts = path
    for a, b in zip(pts, pts[1:]):
        if a[0] != b[0]:
            x, y = g.xy(a[1], a[2])
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(M(x), M(y)))
            v.SetWidth(M(VIA_D))
            v.SetDrill(M(VIA_DRILL))
            v.SetNet(netinfo)
            v.SetLocked(lock)
            board.Add(v)
            new.append(Item("via", net, ("cap", x, y, x, y, VIA_D / 2), [0, 1, 2], v, VIA_DRILL / 2))
            continue
        xa, ya = g.xy(a[1], a[2])
        xb, yb = g.xy(b[1], b[2])
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(M(xa), M(ya)))
        t.SetEnd(pcbnew.VECTOR2I(M(xb), M(yb)))
        t.SetWidth(M(w))
        t.SetLayer(LAYERS[a[0]])
        t.SetNet(netinfo)
        t.SetLocked(lock)
        board.Add(t)
        new.append(Item("track", net, ("cap", xa, ya, xb, yb, w / 2), [a[0]], t))
    return new


def conflicts(g, net, new):
    """Ripable items of other nets that the new copper comes too close to."""
    hits = []
    for it in new:
        w2 = it.shape[5]
        sx = it.shape
        L = max(math.hypot(sx[3] - sx[1], sx[4] - sx[2]), 1e-6)
        n = int(L / 0.04) + 1
        px = np.array([sx[1] + (sx[3] - sx[1]) * k / n for k in range(n + 1)])
        py = np.array([sx[2] + (sx[4] - sx[2]) * k / n for k in range(n + 1)])
        bx0, by0, bx1, by1 = bbox(sx, 1.0)
        for other, items in g.net_items.items():
            if other == net:
                continue
            for o in items:
                if not o.rip or o in hits or not set(o.layers) & set(it.layers):
                    continue
                ox0, oy0, ox1, oy1 = bbox(o.shape, 0)
                if ox1 < bx0 or ox0 > bx1 or oy1 < by0 or oy0 > by1:
                    continue
                need = CLR - 0.01 + w2 + max(extra(net), extra(other))
                if dist_field(o.shape, px, py).min() < need:
                    hits.append(o)
    return hits


def touches(it, items, x, y):
    for o in items:
        if o is it or not set(o.layers) & set(it.layers):
            continue
        if o.kind == "pad" and shape_dist_pt(o.shape, x, y) <= 0:
            return True
        if o.kind in ("track", "via") and shape_dist_pt(o.shape, x, y) <= 0.01:
            return True
    return False


def prune(board, g, nets):
    """Remove dangling ends left behind by rip-up (ripable tracks with a free end)."""
    n = 0
    changed = True
    while changed:
        changed = False
        for net in nets:
            for it in list(g.net_items.get(net, [])):
                if it.kind != "track" or not it.rip:
                    continue
                sh = it.shape
                if not touches(it, g.net_items[net], sh[1], sh[2]) or not touches(it, g.net_items[net], sh[3], sh[4]):
                    g.raster(it, -1)
                    g.net_items[net].remove(it)
                    board.Remove(it.obj)
                    n += 1
                    changed = True
    return n


def run(board, only=None, lock=False, ripup=True, max_rips=3, inner=False, escape=False, escape_nets=None, max_rounds=3):
    """only: regex of nets to route (default all); lock: mark the new copper locked;
    ripup: when a connection has no free path, go through other nets' autorouted copper
    (at a cost), tear that copper out and queue its nets again (negotiated rip-up)."""
    import re
    import time
    t0 = time.time()
    items = collect(board)
    g = Grid(board)
    g.net_items = {}
    for it in items:
        g.net_items.setdefault(it.net, []).append(it)
        g.raster(it)
    print("raster %.0fs" % (time.time() - t0))
    nets = sorted(n for n in g.net_items if n and n not in SKIP and (only is None or re.search(only, n)))
    queue = [n for n in nets if len(clusters(g.net_items[n])) > 1]
    if escape_nets is not None:     # trial mode: straight to the escape of the given nets
        queue = []
    print("nets with open connections:", len(queue), "%.0fs" % (time.time() - t0))
    rips = {}
    ripped = {}
    touched = set()
    done = 0

    def centre(c):
        s_ = c[0].shape
        return ((s_[1] + s_[3]) / 2, (s_[2] + s_[4]) / 2)

    steps = 0
    escaped = set()
    rounds = 0
    while True:
      while queue and steps < 600:
          steps += 1
          net = queue.pop(0)
          cl = clusters(g.net_items[net])
          if len(cl) < 2:
              continue
          w = width_of(net)
          cl.sort(key=len, reverse=True)
          tree, rest = cl[0], cl[1:]
          while rest:
              rest.sort(key=lambda c: min(math.dist(centre([a]), centre([b])) for a in tree for b in c))
              c = rest.pop(0)
              t1 = time.time()
              anchor = min(tree, key=lambda a: min(math.dist(centre([a]), centre([b])) for b in c))
              path, w2, soft = None, w, False
              for ww in ([w, 0.15] if w > 0.15 else [w]):
                  path = astar(g, net, ww, c, tree, anchor)
                  if path is None:
                      path = astar(g, net, ww, c, tree, anchor, big=True)
                  if path:
                      w2 = ww
                      break
              if path is None and inner:      # last resort: a short hop on In2
                  path = astar(g, net, 0.15, c, tree, anchor, big=True, inner=True)
                  w2 = 0.15
              if path is None and ripup and rips.get(net, 0) < max_rips:
                  path = astar(g, net, 0.15 if w <= 0.28 else w, c, tree, anchor, soft=True)
                  w2, soft = (0.15 if w <= 0.28 else w), True
              if path is None:
                  print("  %s FAILED" % net)
                  tree = tree + c
                  continue
              if soft:
                  victims = conflicts(g, net, path_shapes(g, net, w2, path))
                  vnets = {v.net for v in victims}
                  # targeted only: at most two other nets, each torn up at most twice in the whole run
                  if len(vnets) > 2 or any(ripped.get(n, 0) >= 2 for n in vnets):
                      print("  %s FAILED (rip-up would hit %s)" % (net, sorted(vnets)))
                      tree = tree + c
                      continue
                  for n in vnets:
                      ripped[n] = ripped.get(n, 0) + 1
              new = add_path(board, g, net, w2, path, lock)
              if soft:
                  for v in victims:
                      g.raster(v, -1)
                      g.net_items[v.net].remove(v)
                      board.Remove(v.obj)
                      touched.add(v.net)
                      if v.net not in queue:
                          queue.append(v.net)
                  rips[net] = rips.get(net, 0) + 1
                  print("  %s ok via rip-up of %s" % (net, sorted({v.net for v in victims})))
              for it in new:
                  g.raster(it)
                  g.net_items[net].append(it)
              tree = tree + c + new
              done += 1
              touched.add(net)
      # escape pass: pins boxed in by other nets' copper. Tear out the foreign autorouted copper
      # right round the unreached pins, route this net first, then the torn nets again.
      failed = [n for n in nets if len(clusters(g.net_items[n])) > 1 and n not in escaped
                and (escape_nets is None or n in escape_nets)]
      rounds += 1
      if not escape or not failed or rounds > max_rounds:
          break
      queue = []
      for net in failed:
          escaped.add(net)
          cl = sorted(clusters(g.net_items[net]), key=len, reverse=True)
          probe = []
          for c in cl[1:] if len(cl) > 2 or net.startswith("+") else cl:
              for it in c:
                  if it.kind == "pad":
                      sh = it.shape
                      x, y = ((sh[1] + sh[3]) / 2, (sh[2] + sh[4]) / 2)
                      probe.append(Item("track", net, ("cap", x, y, x, y, ESC_R), [0, 1, 2]))
          victims = conflicts(g, net, probe)
          for v in victims:
              if v not in g.net_items[v.net]:
                  continue
              g.raster(v, -1)
              g.net_items[v.net].remove(v)
              board.Remove(v.obj)
              touched.add(v.net)
              if v.net not in queue and v.net not in failed:
                  queue.append(v.net)
          print("  escape %s: tore out %d items of %s" % (net, len(victims), sorted({v.net for v in victims})))
      queue = failed + queue
    pruned = prune(board, g, touched)
    failed = sorted(n for n in nets if len(clusters(g.net_items[n])) > 1)
    print("connections made:", done, "dangling ends pruned:", pruned, "still open:", len(failed), failed)
    return failed


if __name__ == "__main__":
    b = pcbnew.LoadBoard(sys.argv[1])
    run(b)
    b.Save(sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
