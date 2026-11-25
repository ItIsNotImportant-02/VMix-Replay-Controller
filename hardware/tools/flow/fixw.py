import pcbnew, re, sys, subprocess
src, rpt = sys.argv[1], sys.argv[2]
b = pcbnew.LoadBoard(src)
txt = open(rpt).read()
pts = []
for blk in txt.split("\n[")[1:]:
    if not blk.startswith("clearance"): continue
    for m in re.finditer(r"@\(([\d.]+) mm, ([\d.]+) mm\): Track \[([^\]]*)\] on ([^ ,]+)", blk):
        pts.append((float(m.group(1)), float(m.group(2)), m.group(3), m.group(4)))
def d(px,py,t):
    ax,ay,bx,by=[v/1e6 for v in (t.GetStart().x,t.GetStart().y,t.GetEnd().x,t.GetEnd().y)]
    dx,dy=bx-ax,by-ay; L=dx*dx+dy*dy
    u=0 if L==0 else max(0,min(1,((px-ax)*dx+(py-ay)*dy)/L))
    return ((ax+u*dx-px)**2+(ay+u*dy-py)**2)**.5
n=0
import os
steps=[int(float(s)*1e6) for s in (os.environ.get("STEPS") or "0.5,0.4,0.3,0.25,0.2,0.15").split(",")]
for t in b.GetTracks():
    if t.GetClass()!="PCB_TRACK": continue
    for px,py,net,lay in pts:
        if t.GetNetname()==net and b.GetLayerName(t.GetLayer())==lay and d(px,py,t)<0.005:
            w=t.GetWidth()
            if w>int(float(os.environ.get("MAXW") or "9")*1e6): continue
            nw=next((s for s in steps if s<w), None)
            if nw: t.SetWidth(nw); n+=1
            break
print("narrowed", n)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(src)
