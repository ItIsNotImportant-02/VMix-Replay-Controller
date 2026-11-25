"""Placement optimiser for the IC groups of the main board (host side, pure python + numpy).

Moves rigid groups (an IC with its decoupling / support parts) and rotates them in 90 degree steps,
re-assigns LED driver channels and expander ports to the buttons for every placement, and scores
total connection length plus a RUDY congestion estimate. Usage:
    python3 opt.py base.json out_dir [seed] [iterations]
"""
import json, math, random, sys, os, itertools, re
import numpy as np

BASE = json.load(open(sys.argv[1]))["fps"]
OUT = sys.argv[2]
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 1
ITERS = int(sys.argv[4]) if len(sys.argv) > 4 else 4000
random.seed(SEED)
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- board ----
W, H = 159.8, 154.65
LEVER_NOTCH = (-20.0, 58.65, 64.0)
JOG = (121.8, 115.15, 22.0)
MOUNT = [(97.975, 49.5), (155.3, 68.5), (87.15, 150.15), (155.3, 150.15)]


def in_keepout(bb):
    if bb[0] < 1 or bb[1] < 1 or bb[2] > W - 1 or bb[3] > H - 1:
        return True
    nx0, ny, nx1 = LEVER_NOTCH
    if bb[0] < nx1 + 1 and bb[3] > ny - 1:
        return True
    cx, cy, r = JOG
    px, py = min(max(cx, bb[0]), bb[2]), min(max(cy, bb[1]), bb[3])
    if math.hypot(px - cx, py - cy) < r + 1.0:
        return True
    for hx, hy in MOUNT:
        if bb[0] < hx + 3.5 and hx - 3.5 < bb[2] and bb[1] < hy + 3.5 and hy - 3.5 < bb[3]:
            return True
    return False


GROUPS = {
    "U3": "U3 U4 C21 C16 C15 C19 C18 C17 R3 R4 C22 C14 C13 C8 R7 R6 R13 D3 C10 C11 R43 R44 TP10 TP11 "
          "C20 C12 R10 Y1 C23 C24 R12 TP5 TP7 C25 R11".split(),
    "SW": ["SW1", "SW2"],
    "U9": "U9 RN4 RN5 RN6 RN7 TP13 C71 R50".split(),
    "U8": "U8 RN1 RN2 RN3 C70".split(),
    "U6": "U6 TP12 C60 C61 R40 R42".split(),
    "U7": "U7 C62 C63 R41".split(),
    "J2": ["J2"],
    "J3": ["J3"],
}
MEMBER = {r: g for g, rs in GROUPS.items() for r in rs}
ANCHOR = {g: BASE[rs[0]] for g, rs in GROUPS.items()}


def rot(dx, dy, d):
    """Rotate a board vector by d degrees CCW as seen on screen (y down)."""
    d %= 360
    if d == 0:
        return dx, dy
    if d == 90:
        return dy, -dx
    if d == 180:
        return -dx, -dy
    return -dy, dx


def rot_box(b, ax, ay, d, nx, ny):
    pts = [rot(x - ax, y - ay, d) for x, y in ((b[0], b[1]), (b[2], b[3]))]
    xs = [p[0] + nx for p in pts]
    ys = [p[1] + ny for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def ov(a, b, m=0.0):
    return a[0] < b[2] + m and b[0] < a[2] + m and a[1] < b[3] + m and b[1] < a[3] + m


FIXED_BOXES = [(r, b) for r, f in BASE.items() if r not in MEMBER for b in f["boxes"]]
FIXED_BOT = [(r, f["bottom_box"]) for r, f in BASE.items() if r not in MEMBER and f.get("bottom_box")]
FIXED_BOXES += [("H%d" % i, (x - 3.2, y - 3.2, x + 3.2, y + 3.2)) for i, (x, y) in enumerate(MOUNT)]

# ---------------------------------------------------------------- nets -----
PLANES = {"GND", "+5V_LED", ""}
pads = {}          # (ref, num) -> (x, y, net)
for r, f in BASE.items():
    for p in f["pads"]:
        if p[0]:
            pads[(r, p[0])] = (p[1], p[2], p[3])

# LED channels: (chip, channel) -> pad ; button LED pads by net name
LEDS = {}          # name (LED_MENU_R) -> button pad key
chan_pad = {}      # (chip, ch) -> pad key
sys.path.insert(0, "/home/user/VMix-Replay-Controller/hardware/tools")
import importlib.util
spec = importlib.util.spec_from_file_location("circuit_maps", os.environ.get("CIRCUIT", "/home/user/VMix-Replay-Controller/hardware/tools/circuit.py"))
src = open(spec.origin, encoding="utf-8").read()
ns = {}
exec(re.search(r"TCA_PORTS = \[.*?\]", src, re.S).group(0), ns)
exec(re.search(r"TCA_MAP = \{.*?\n\}", src, re.S).group(0), ns)
exec(re.search(r"LED_ASSIGN = \{.*?\n\}", src, re.S).group(0), ns)
TCA_PORTS, TCA_MAP, LED_ASSIGN = ns["TCA_PORTS"], ns["TCA_MAP"], ns["LED_ASSIGN"]
LED_MAP = {}
for n, (c, ks) in LED_ASSIGN.items():
    if len(ks) == 1:
        LED_MAP["LED_%s" % n] = (c, ks[0])
    else:
        for col, k in zip("RGB", ks):
            LED_MAP["LED_%s_%s" % (n, col)] = (c, k)
for key, (x, y, net) in pads.items():
    n = net.lstrip("/")
    if n in LED_MAP:
        if key[0] in ("U6", "U7"):
            chan_pad[LED_MAP[n]] = key
        elif key[0].startswith("SW"):
            LEDS[n] = key
    m = re.search(r"unconnected-\((U[67])-OUT(\d+)", net)
    if m:
        chan_pad[(m.group(1), int(m.group(2)))] = key
assert len(chan_pad) == 72, len(chan_pad)
BTN = {}           # button -> switch pad
port_pad, port_rn = {}, {}
for name, (c, p) in TCA_MAP.items():
    for key, (x, y, net) in pads.items():
        if net == "/BTN_" + name:
            if key[0] == c:
                port_pad[(c, p)] = key
            elif key[0].startswith("RN"):
                port_rn[(c, p)] = key
            elif key[0].startswith("SW"):
                BTN[name] = key
for key, (x, y, net) in pads.items():
    m = re.match(r"/EXP_P(\d+)", net)
    if m and key[0] in ("U8", "U9"):
        port_pad[(key[0], "P" + m.group(1))] = key
SPARE_J3 = sorted(k for k, v in pads.items() if v[2].startswith("/EXP_") and k[0] == "J3")
assert len(port_pad) == 32, len(port_pad)
MAPPED = {v[2] for v in pads.values() if re.match(r"/(LED_(?!SDB)|BTN_(?!INT)|EXP_)", v[2])}
generic = {}
for key, (x, y, net) in pads.items():
    if net in PLANES or net in MAPPED or net.startswith("unconnected-"):
        continue
    generic.setdefault(net, []).append(key)
generic = {n: ks for n, ks in generic.items() if len(ks) > 1}
BUTTONS_LED = {}
for n, key in LEDS.items():
    b = n[4:]
    base = b[:-2] if re.search(r"_[RGB]$", b) and not b.startswith("F") else b
    BUTTONS_LED.setdefault(base, {})[b[-1] if base != b else "X"] = key


# --------------------------------------------------------------- state -----
def pos_fn(state):
    cache = {}

    def P(key):
        r = key[0]
        g = MEMBER.get(r)
        x, y, _ = pads[key]
        if g is None:
            return x, y
        a = ANCHOR[g]
        nx, ny, d = state[g]
        dx, dy = rot(x - a["x"], y - a["y"], d)
        return nx + dx, ny + dy
    return P


def boxes_of(state, g):
    a = ANCHOR[g]
    nx, ny, d = state[g]
    out = []
    for r in GROUPS[g]:
        for b in BASE[r]["boxes"]:
            out.append(rot_box(b, a["x"], a["y"], d, nx, ny))
    return out


def valid(state):
    allb = {g: boxes_of(state, g) for g in GROUPS}
    for g, bs in allb.items():
        for b in bs:
            if in_keepout(b):
                return False, "%s keep-out" % g
            for r, fb in FIXED_BOXES:
                if ov(b, fb, 0.2):
                    return False, "%s hits %s" % (g, r)
    for g in ("J2", "J3"):
        bb = BASE[GROUPS[g][0]].get("bottom_box")
        if bb:
            a = ANCHOR[g]; nx, ny, d = state[g]
            b = rot_box(bb, a["x"], a["y"], d, nx, ny)
            for r, fb in FIXED_BOT:
                if ov(b, fb, 0.3):
                    return False, "%s hits %s (bottom)" % (g, r)
    jb = [rot_box(BASE[GROUPS[g][0]]["bottom_box"], ANCHOR[g]["x"], ANCHOR[g]["y"], state[g][2], state[g][0], state[g][1]) for g in ("J2", "J3")]
    if ov(jb[0], jb[1], 0.3):
        return False, "J2 hits J3 (bottom)"
    gs = list(GROUPS)
    for i in range(len(gs)):
        for j in range(i + 1, len(gs)):
            for b in allb[gs[i]]:
                for c in allb[gs[j]]:
                    if ov(b, c, 0.3):
                        return False, "%s hits %s" % (gs[i], gs[j])
    return True, ""


def mst(points):
    n = len(points)
    if n < 2:
        return []
    inq = [False] * n
    d = [1e18] * n
    par = [-1] * n
    d[0] = 0
    edges = []
    for _ in range(n):
        u = min((i for i in range(n) if not inq[i]), key=lambda i: d[i])
        inq[u] = True
        if par[u] >= 0:
            edges.append((points[par[u]], points[u]))
        for v in range(n):
            if not inq[v]:
                dd = abs(points[u][0] - points[v][0]) + abs(points[u][1] - points[v][1])
                if dd < d[v]:
                    d[v], par[v] = dd, u
    return edges


def assign(state, P):
    """LED channels and expander ports for this placement (angle order round each chip)."""
    led = {}
    cpos = {c: P(chan_pad[(c, 1)]) for c in ("U6", "U7")}
    cc = {}
    for c in ("U6", "U7"):
        ps = [P(chan_pad[(c, k)]) for k in range(1, 37)]
        cc[c] = (sum(p[0] for p in ps) / 36, sum(p[1] for p in ps) / 36)

    def bc(b):
        v = [P(k) for k in BUTTONS_LED[b].values()]
        return (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v))
    need = {b: len(BUTTONS_LED[b]) for b in BUTTONS_LED}
    order = sorted(BUTTONS_LED, key=lambda b: math.dist(bc(b), cc["U6"]) - math.dist(bc(b), cc["U7"]))
    groups, used = {"U6": [], "U7": []}, {"U6": 0, "U7": 0}
    for b in order:
        pref = "U6" if math.dist(bc(b), cc["U6"]) <= math.dist(bc(b), cc["U7"]) else "U7"
        c = pref if used[pref] + need[b] <= 36 else ("U7" if pref == "U6" else "U6")
        groups[c].append(b)
        used[c] += need[b]
    segs = []
    for c, bs in groups.items():
        cx, cy = cc[c]
        ang = lambda p: math.atan2(p[1] - cy, p[0] - cx)
        bs = sorted(bs, key=lambda b: ang(bc(b)))
        ks = sorted(range(1, 37), key=lambda k: ang(P(chan_pad[(c, k)])))
        best = None
        tot = sum(need[b] for b in bs)
        for shift in range(36):
            for rev in (False, True):
                seq = ks[shift:] + ks[:shift]
                if rev:
                    seq = seq[::-1]
                i, a, L = 0, {}, 0.0
                for b in (bs if not rev else bs[::-1]):
                    cols = sorted(BUTTONS_LED[b])
                    chs = seq[i:i + need[b]]
                    i += need[b]
                    if len(chs) == 3:
                        chs = min(itertools.permutations(chs), key=lambda pm: sum(
                            math.dist(P(chan_pad[(c, k)]), P(BUTTONS_LED[b][col])) for k, col in zip(pm, "RGB")))
                        cols = "RGB"
                    a[b] = (c, list(chs))
                    L += sum(math.dist(P(chan_pad[(c, k)]), P(BUTTONS_LED[b][col])) for k, col in zip(chs, cols))
                if best is None or L < best[0]:
                    best = (L, a)
        led.update(best[1])
    # buttons -> expander ports: U8 takes exactly 12 buttons, U9 16 (pull-up arrays come in fours)
    ec = {c: P(port_pad[(c, "P00")]) for c in ("U8", "U9")}
    for c in ("U8", "U9"):
        ps = [P(port_pad[(c, p)]) for p in TCA_PORTS]
        ec[c] = (sum(p[0] for p in ps) / 16, sum(p[1] for p in ps) / 16)
    names = sorted(BTN, key=lambda b: math.dist(P(BTN[b]), ec["U8"]) - math.dist(P(BTN[b]), ec["U9"]))
    bg = {"U8": names[:12], "U9": names[12:]}
    tca = {}
    for c, bs in bg.items():
        cx, cy = ec[c]
        ang = lambda p: math.atan2(p[1] - cy, p[0] - cx)
        bs = sorted(bs, key=lambda b: ang(P(BTN[b])))
        ports = sorted(TCA_PORTS, key=lambda p: ang(P(port_pad[(c, p)])))
        best = None
        for shift in range(16):
            for rev in (False, True):
                seq = ports[shift:] + ports[:shift]
                if rev:
                    seq = seq[::-1]
                a = {b: (c, seq[i]) for i, b in enumerate(bs if not rev else bs[::-1])}
                L = sum(math.dist(P(BTN[b]), P(port_pad[a[b]])) for b in a)
                if best is None or L < best[0]:
                    best = (L, a)
        tca.update(best[1])
    return led, tca


def connections(state, led=None, tca=None):
    P = pos_fn(state)
    if led is None:
        led, tca = assign(state, P)
    E = []
    for n, ks in generic.items():
        E += mst([P(k) for k in ks])
    for b, (c, chs) in led.items():
        cols = "RGB" if len(chs) == 3 else "X"
        for k, col in zip(chs, cols):
            E.append((P(chan_pad[(c, k)]), P(BUTTONS_LED[b][col])))
    for b, cp in tca.items():
        E += mst([P(BTN[b]), P(port_pad[cp])])
        # the pull-up resistor of a port belongs to whoever uses the port: port pad <-> RN pad is local
    used = set(tca.values())
    spare = sorted(p for p in port_pad if p not in used)
    # spares go to J3 (4 of them); unused extra spares stay open
    for sp_, j in zip(spare, SPARE_J3):
        E.append((P(port_pad[sp_]), P(j)))
    return E, led, tca


# RUDY congestion grid (1 mm)
GX, GY = int(W) + 1, int(H) + 1
cap = np.full((GY, GX), 3.0 * 0.45)      # 3 signal layers, ~45 % of the area usable for tracks
yy, xx = np.mgrid[0:GY, 0:GX] + 0.5
cap[(xx < LEVER_NOTCH[2]) & (yy > LEVER_NOTCH[1])] = 0
cap[np.hypot(xx - JOG[0], yy - JOG[1]) < JOG[2]] = 0
PITCH = 0.35                              # 0.2 track + 0.15 gap


def pad_block(state):
    blk = np.zeros((GY, GX))
    P = pos_fn(state)
    for r, f in BASE.items():
        for p in f["pads"]:
            if not p[0]:
                continue
            x, y = P((r, p[0]))
            w, h = p[4], p[5]
            g = MEMBER.get(r)
            if g and state[g][2] % 180:
                w, h = h, w
            i0, i1 = int(max(0, x - w / 2)), int(min(GX - 1, x + w / 2))
            j0, j1 = int(max(0, y - h / 2)), int(min(GY - 1, y + h / 2))
            layers = 3 if p[6] else 1
            blk[j0:j1 + 1, i0:i1 + 1] += layers * min(1.0, w * h)
    return blk


def score(state, detail=False):
    E, led, tca = connections(state)
    L = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in E)
    dem = np.zeros((GY + 1, GX + 1))
    for a, b in E:
        x0, x1 = sorted((a[0], b[0]))
        y0, y1 = sorted((a[1], b[1]))
        w, h = max(x1 - x0, 1.0), max(y1 - y0, 1.0)
        v = PITCH * (w + h) / (w * h)
        i0, i1 = int(x0), int(x0 + w)
        j0, j1 = int(y0), int(y0 + h)
        i1, j1 = min(i1, GX), min(j1, GY)
        dem[j0, i0] += v
        dem[j0, i1] -= v
        dem[j1, i0] -= v
        dem[j1, i1] += v
    dem = dem.cumsum(0).cumsum(1)[:GY, :GX]
    c = np.maximum(cap - 0.35 * pad_block(state), 0.15)
    c[cap == 0] = 0
    over = np.maximum(dem - c, 0)
    O = float((over ** 2).sum())
    s = L + 20.0 * O
    if detail:
        return s, L, O, led, tca, dem, c
    return s


def start_state():
    st = {g: (ANCHOR[g]["x"], ANCHOR[g]["y"], 0) for g in GROUPS}
    for g in ("J2", "J3"):
        if valid(st)[0]:
            break
        done = False
        for y in np.arange(150, 60, -1.0):
            for x in np.arange(85, 155, 1.0):
                for d in (0, 90):
                    st[g] = (float(x), float(y), d)
                    ok, why = valid(st)
                    if ok or not why.startswith(g):
                        done = True
                        break
                if done:
                    break
            if done:
                break
    return st


def neighbour(st):
    s = dict(st)
    g = random.choice(list(GROUPS))
    k = random.random()
    x, y, d = s[g]
    if k < 0.55:
        r = random.choice((1, 2, 4, 8, 15))
        s[g] = (round(x + random.uniform(-r, r), 1), round(y + random.uniform(-r, r), 1), d)
    elif k < 0.75:
        s[g] = (x, y, (d + random.choice((90, 180, 270))) % 360)
    elif k < 0.9:
        h = random.choice([q for q in GROUPS if q != g and q not in ("J2", "J3")] if g not in ("J2", "J3") else ["J2", "J3"])
        s[g], s[h] = (s[h][0], s[h][1], d), (x, y, s[h][2])
    else:
        s[g] = (round(random.uniform(5, W - 5), 1), round(random.uniform(5, H - 5), 1), random.choice((0, 90, 180, 270)))
    return s


if __name__ == "__main__":
    st = start_state()
    ok, why = valid(st)
    s0, L0, O0, *_ = score(st, True)
    print("start valid", ok, why, "score %.0f len %.0f over %.1f" % (s0, L0, O0), flush=True)
    cur, cs = st, s0
    best, bs = cur, cs
    T0 = 300.0
    for it in range(ITERS):
        T = T0 * (1 - it / ITERS) + 1
        nb = neighbour(cur)
        if not valid(nb)[0]:
            continue
        ns_ = score(nb)
        if ns_ < cs or random.random() < math.exp((cs - ns_) / T):
            cur, cs = nb, ns_
            if cs < bs:
                best, bs = cur, cs
        if it % 200 == 0:
            print(it, "cur %.0f best %.0f" % (cs, bs), flush=True)
    s, L, O, led, tca, dem, c = score(best, True)
    print("best score %.0f len %.0f over %.1f" % (s, L, O))
    json.dump({"state": best, "score": s, "len": L, "over": O, "led": led, "tca": tca,
               "start": {"score": s0, "len": L0, "over": O0}}, open(os.path.join(OUT, "best_%d.json" % SEED), "w"), indent=1)
