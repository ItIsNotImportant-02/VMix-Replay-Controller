"""Apply a GPIO swap to the routed board without re-placing: new pad nets, the old routes of the
affected nets removed (the grid router routes them again).  python3 tools/renet.py <in.pcb> <out.pcb>"""
import sys, pcbnew
SWAP = {("U3", "4"): "/GP2", ("U3", "5"): "/GP3", ("U3", "6"): "/GP4",
        ("U3", "34"): "/JOG_DO", ("U3", "35"): "/JOG_CLK", ("U3", "36"): "/JOG_CSN",
        ("J3", "7"): "/GP2", ("J3", "8"): "/GP3", ("J3", "9"): "/GP4"}
OLD = {"/JOG_DO", "/JOG_CLK", "/JOG_CSN", "/GP22", "/GP23", "/GP24"}
b = pcbnew.LoadBoard(sys.argv[1])
dead = [t for t in b.GetTracks() if t.GetNetname() in OLD]
assert not any(t.IsLocked() for t in dead)
for t in dead:
    b.Remove(t)
nets = {}
for n in set(SWAP.values()):
    ni = b.FindNet(n)
    if ni is None:
        ni = pcbnew.NETINFO_ITEM(b, n)
        b.Add(ni)
    nets[n] = ni
for (ref, num), n in SWAP.items():
    for p in b.FindFootprintByReference(ref).Pads():
        if p.GetNumber() == num:
            print(ref, num, p.GetNetname(), "->", n)
            p.SetNet(nets[n])
b.Save(sys.argv[2])
print("removed", len(dead), "track/via items")
