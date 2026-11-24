import json, math, re, itertools, collections, sys
P = json.load(open('/home/user/VMix-Replay-Controller/hardware/build/pads.json'))
pad = {(r[0], r[1]): r for r in P}
net = collections.defaultdict(list)
for r in P: net[r[2]].append(r)
def ctr(ref):
    ps = [r for r in P if r[0] == ref]; return (sum(r[3] for r in ps)/len(ps), sum(r[4] for r in ps)/len(ps))
# ---------- LED: channel pads of U6/U7 ----------
def chan_pads(chip):
    out = {}
    for r in P:
        if r[0] != chip: continue
        m = re.search(r'OUT(\d+)', r[2])
        if m: out[int(m.group(1))] = (r[3], r[4], r[1])
    return out
sys.path.insert(0, '/home/user/VMix-Replay-Controller/hardware/tools')
import circuit
ch = {c: chan_pads(c) for c in ("U6", "U7")}
for n, (c, k) in circuit.LED_MAP.items():
    for r in net['/' + n]:
        if r[0] == c: ch[c][k] = (r[3], r[4], r[1])
print({c: len(v) for c, v in ch.items()})
# button LED pads: list of (button, [pad positions in R,G,B order]) ; F keys single
btn_led = {}
for n in circuit.LED_MAP:
    for r in net['/' + n]:
        if r[0].startswith('SW'):
            name = n[4:]; base = name[:-2] if name[-2] == '_' and name[-1] in 'RGB' else name
            btn_led.setdefault(base, {})[name[-1] if base != name else 'X'] = (r[3], r[4])
def segs_led(assign):   # assign: button -> (chip, [channels in R,G,B order])
    S = []
    for b, (c, ks) in assign.items():
        cols = ['R', 'G', 'B'] if len(ks) == 3 else ['X']
        for col, k in zip(cols, ks):
            S.append((b + col, ch[c][k][:2], btn_led[b][col]))
    return S
def cross(S):
    def ccw(a, b, c): return (c[1]-a[1])*(b[0]-a[0]) > (b[1]-a[1])*(c[0]-a[0])
    n = 0
    for (na, a1, a2), (nb, b1, b2) in itertools.combinations(S, 2):
        if ccw(a1, b1, b2) != ccw(a2, b1, b2) and ccw(a1, a2, b1) != ccw(a1, a2, b2): n += 1
    return n
def length(S): return sum(math.dist(a, b) for _, a, b in S)
cur = {}
for b in btn_led:
    if b.startswith('F'): cur[b] = circuit.LED_MAP['LED_' + b][0], [circuit.LED_MAP['LED_' + b][1]]
    else: cur[b] = circuit.LED_MAP['LED_%s_R' % b][0], [circuit.LED_MAP['LED_%s_%s' % (b, c)][1] for c in 'RGB']
S0 = segs_led(cur); print("LED now: crossings", cross(S0), "length %.0f mm" % length(S0))
# ---------- optimise ----------
def bcentre(b): v = list(btn_led[b].values()); return (sum(p[0] for p in v)/len(v), sum(p[1] for p in v)/len(v))
def need(b): return len(btn_led[b])
def optimise_led():
    chips = {c: ctr(c) for c in ("U6", "U7")}
    # split buttons between chips: greedy by distance difference, capacity 36
    order = sorted(btn_led, key=lambda b: math.dist(bcentre(b), chips["U6"]) - math.dist(bcentre(b), chips["U7"]))
    groups = {"U6": [], "U7": []}; used = {"U6": 0, "U7": 0}
    for b in order:
        pref = "U6" if math.dist(bcentre(b), chips["U6"]) <= math.dist(bcentre(b), chips["U7"]) else "U7"
        c = pref if used[pref] + need(b) <= 36 else ("U7" if pref == "U6" else "U6")
        groups[c].append(b); used[c] += need(b)
    best = {}
    for c, bs in groups.items():
        cx, cy = chips[c]
        ang = lambda p: math.atan2(p[1]-cy, p[0]-cx)
        bs = sorted(bs, key=lambda b: ang(bcentre(b)))
        pads = sorted(ch[c], key=lambda k: ang(ch[c][k][:2]))       # 36 channels by angle
        bestL = None
        for shift in range(36):
            for rev in (False, True):
                seq = pads[shift:] + pads[:shift]
                if rev: seq = seq[::-1]
                a = {}; i = 0
                for b in (bs if not rev else bs[::-1]):
                    ks = seq[i:i+need(b)]; i += need(b)
                    if need(b) == 3:   # R,G,B order: best permutation by length
                        cols = ['R', 'G', 'B']
                        ks = min(itertools.permutations(ks), key=lambda pm: sum(math.dist(ch[c][k][:2], btn_led[b][col]) for k, col in zip(pm, cols)))
                    a[b] = (c, list(ks))
                S = segs_led(a); L = cross(S) * 50 + length(S)
                if bestL is None or L < bestL: bestL, bestA = L, a
        best.update(bestA)
    return best
new = optimise_led()
S1 = segs_led(new); print("LED new: crossings", cross(S1), "length %.0f mm" % length(S1))
json.dump({"led_now": S0, "led_new": S1, "led_assign": new}, open('/tmp/claude-0/kt/plan/led.json', 'w'))
# ---------- buttons -> TCA9555 ----------
port_pad = {"U8": {}, "U9": {}}
for name, (c, p) in circuit.TCA_MAP.items():
    for r in net['/BTN_' + name]:
        if r[0] == c: port_pad[c][p] = (r[3], r[4], r[1])
for c, p in circuit.SPARE_EXP:
    for r in P:
        if r[0] == c and r[2].endswith('EXP_' + p[1:]) or (r[0] == c and r[2] == '/EXP_P%s' % p[1:]): port_pad[c][p] = (r[3], r[4], r[1])
print({c: len(v) for c, v in port_pad.items()})
btn_pos = {}
for name in circuit.TCA_MAP:
    for r in net['/BTN_' + name]:
        if r[0].startswith('SW'): btn_pos[name] = (r[3], r[4])
def segs_btn(a): return [(b, port_pad[c][p][:2], btn_pos[b]) for b, (c, p) in a.items()]
T0 = segs_btn(circuit.TCA_MAP); print("BTN now: crossings", cross(T0), "length %.0f mm" % length(T0))
def optimise_btn():
    chips = {c: ctr(c) for c in ("U8", "U9")}
    groups = {"U8": [], "U9": []}
    for b in sorted(btn_pos, key=lambda b: math.dist(btn_pos[b], chips["U8"]) - math.dist(btn_pos[b], chips["U9"])):
        pref = "U8" if math.dist(btn_pos[b], chips["U8"]) <= math.dist(btn_pos[b], chips["U9"]) else "U9"
        c = pref if len(groups[pref]) < 16 else ("U9" if pref == "U8" else "U8")
        groups[c].append(b)
    best = {}
    for c, bs in groups.items():
        cx, cy = chips[c]; ang = lambda p: math.atan2(p[1]-cy, p[0]-cx)
        bs = sorted(bs, key=lambda b: ang(btn_pos[b]))
        ports = sorted(port_pad[c], key=lambda p: ang(port_pad[c][p][:2]))
        bestL = None
        for shift in range(16):
            for rev in (False, True):
                seq = ports[shift:] + ports[:shift]
                if rev: seq = seq[::-1]
                # leave the unused ports where they hurt least: try every window start
                a = {b: (c, seq[i]) for i, b in enumerate(bs if not rev else bs[::-1])}
                S = segs_btn(a); L = cross(S) * 50 + length(S)
                if bestL is None or L < bestL: bestL, bestA = L, a
        best.update(bestA)
    return best
nb = optimise_btn()
T1 = segs_btn(nb); print("BTN new: crossings", cross(T1), "length %.0f mm" % length(T1))
print("split:", {c: sorted(b for b, (cc, p) in nb.items() if cc == c) for c in ("U8", "U9")})
d = json.load(open('/tmp/claude-0/kt/plan/led.json')); d.update(btn_now=T0, btn_new=T1, btn_assign=nb)
json.dump(d, open('/tmp/claude-0/kt/plan/led.json', 'w'))
