import pcbnew, collections, math
b=pcbnew.LoadBoard('/hw/vmix-replay-controller.kicad_pcb')
d=collections.defaultdict(collections.Counter)
for t in b.GetTracks():
    if t.GetClass()!="PCB_TRACK": continue
    n=t.GetNetname()
    if n in ("VBUS","+5V","+3V3","+1V1","+5V_LED","GND","+3V3A","VBUS_F") or n.startswith("+"):
        d[n][round(t.GetWidth()/1e6,3)]+=round(math.hypot(t.GetEnd().x-t.GetStart().x,t.GetEnd().y-t.GetStart().y)/1e6,1)
for n in d: print(n, dict(sorted(d[n].items())))
