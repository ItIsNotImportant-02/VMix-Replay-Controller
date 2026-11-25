"""Apply an optimiser state to build/placed.kicad_pcb (rigid group moves), check invariance, save."""
import pcbnew, json, sys, math
T = pcbnew.ToMM
st = json.load(open(sys.argv[1]))["state"]
exec(open('/kt/groups.py').read())       # GROUPS, rot()
b = pcbnew.LoadBoard('/hw/build/placed.kicad_pcb')
fps = {f.GetReference(): f for f in b.GetFootprints()}
def padxy(f):
    return {p.GetNumber(): (T(p.GetPosition().x), T(p.GetPosition().y)) for p in f.Pads()}
before = {r: padxy(fps[r]) for g in GROUPS for r in GROUPS[g] if r in fps}
for g, rs in GROUPS.items():
    nx, ny, d = st[g]
    a = fps[rs[0]]
    ax, ay = T(a.GetPosition().x) - 20, T(a.GetPosition().y) - 20
    for r in rs:
        if r not in fps: continue
        f = fps[r]
        x, y = T(f.GetPosition().x) - 20, T(f.GetPosition().y) - 20
        dx, dy = rot(x - ax, y - ay, d)
        f.SetOrientationDegrees(f.GetOrientationDegrees() + d)
        f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(nx + dx + 20), pcbnew.FromMM(ny + dy + 20)))
import os
SP = float(os.environ.get("SPREAD") or "1")
if SP != 1:
    c = fps["U3"].GetPosition(); cx, cy = c.x, c.y
    for r in GROUPS["U3"][1:]:
        if r not in fps or r in ("Y1",): pass
        if r not in fps: continue
        p = fps[r].GetPosition()
        if math.hypot(p.x - cx, p.y - cy) / 1e6 > float(os.environ.get("SPR_R") or "99"): continue
        fps[r].SetPosition(pcbnew.VECTOR2I(int(cx + (p.x - cx) * SP), int(cy + (p.y - cy) * SP)))
    before = {k: v for k, v in before.items() if k not in GROUPS["U3"]}
    GROUPS = {g: rs for g, rs in GROUPS.items() if g != "U3"}
    print("spread U3 group by", SP)
# rigidity check: distances between every member pad and the anchor's pads unchanged
bad = 0
for g, rs in GROUPS.items():
    A = rs[0]; pa0 = before[A]; pa1 = padxy(fps[A])
    k0 = sorted(pa0)[:3]
    for r in rs[1:]:
        if r not in fps: continue
        p0, p1 = before[r], padxy(fps[r])
        for n in p0:
            for k in k0:
                if abs(math.dist(p0[n], pa0[k]) - math.dist(p1[n], pa1[k])) > 0.01:
                    bad += 1
print("rigidity errors:", bad)
b.Save('/hw/build/placed.kicad_pcb')
