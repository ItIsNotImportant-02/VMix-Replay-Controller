import pcbnew, sys, math
sys.path.insert(0,'/hw/tools')
import route, leftover
from route import T, mm
src, dst = sys.argv[1], sys.argv[2]
b = pcbnew.LoadBoard(src)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
z = [z for z in b.Zones() if z.GetLayer()==pcbnew.In2_Cu][0]
fp = z.GetFilledPolysList(pcbnew.In2_Cu)
areas = [abs(fp.Outline(i).Area()) for i in range(fp.OutlineCount())]
mi = areas.index(max(areas))
main = pcbnew.SHAPE_POLY_SET(); main.AddOutline(fp.Outline(mi))
for h in range(fp.HoleCount(mi)): main.AddHole(fp.Hole(mi, h))
def inm(x,y,r=0.0):
    pts=[(x,y)]+[(x+r*math.cos(k*math.pi/8),y+r*math.sin(k*math.pi/8)) for k in range(16)] if r else [(x,y)]
    return all(main.Contains(pcbnew.VECTOR2I(mm(a),mm(c))) for a,c in pts)
def touches_main(x,y,r):   # the copper ring just outside the item overlaps the main fill
    return any(main.Contains(pcbnew.VECTOR2I(mm(x+rr*math.cos(k*math.pi/12)),mm(y+rr*math.sin(k*math.pi/12))))
               for k in range(24) for rr in (r-0.03, r+0.02, r+0.1))
def MAIN(it):
    if it.net!="+5V_LED" or 2 not in it.layers: return False
    s=it.shape
    if s[0]=="cap":
        if it.kind=="track": return main.Contains(pcbnew.VECTOR2I(mm(s[1]),mm(s[2]))) or main.Contains(pcbnew.VECTOR2I(mm(s[3]),mm(s[4])))
        return touches_main(s[1],s[2],s[5]+0.05)
    cx,cy=(s[1]+s[3])/2,(s[2]+s[4])/2
    return touches_main(cx,cy,min(s[3]-s[1],s[4]-s[2])/2+0.05)
leftover.MAIN = MAIN
# candidate vias in the pour near every +5V_LED THT pad / via that the pour does not reach
sp = route.Space(b)
for t in b.GetTracks():
    if t.GetClass()=="PCB_VIA":
        p=t.GetPosition(); sp.vias.append((T(p.x),T(p.y),T(t.GetWidth(pcbnew.F_Cu))/2,t.GetNetname()))
    else:
        sp.segs.append((T(t.GetStart().x),T(t.GetStart().y),T(t.GetEnd().x),T(t.GetEnd().y),T(t.GetWidth())/2,t.GetNetname(),t.GetLayer()))
anchors=[]
for t in b.GetTracks():
    if t.GetClass()=="PCB_VIA" and t.GetNetname()=="+5V_LED":
        p=t.GetPosition(); x,y=T(p.x),T(p.y)
        if not touches_main(x,y,0.35): anchors.append((x,y))
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname()=="+5V_LED" and p.GetDrillSize().x>0:
            c=p.GetPosition(); x,y=T(c.x),T(c.y); r=T(min(p.GetSize(pcbnew.F_Cu).x,p.GetSize(pcbnew.F_Cu).y))/2
            if not touches_main(x,y,r+0.05): anchors.append((x,y))
print("anchors off the pour:", len(anchors), anchors)
cands=[]
for ax,ay in anchors:
    got=0
    for rr in [k*0.5 for k in range(2,24)]:
        n=max(8,int(2*math.pi*rr/0.6))
        for k in range(n):
            x=ax+rr*math.cos(2*math.pi*k/n); y=ay+rr*math.sin(2*math.pi*k/n)
            if inm(x,y,0.5) and sp.via_ok(x,y,"+5V_LED") and all(math.hypot(x-c[0],y-c[1])>1.5 for c in cands):
                sp.add_via(x,y,"+5V_LED"); cands.append((x,y)); got+=1
                if got>=3: break
        if got>=3: break
print("candidate vias:", len(cands))
for t in b.GetTracks():
    if t.GetClass()=="PCB_VIA" and t.GetNetname()=="+5V_LED": t.SetLocked(False)
b.Save(dst); b=pcbnew.LoadBoard(dst)
leftover.SKIP={"GND"}
leftover.run(b, only=r"^\+5V_LED$", ripup=False, max_rounds=1)
leftover.SKIP={"GND","+5V_LED"}
# drop candidate vias nothing was routed to
cs={(round(x,3),round(y,3)) for x,y in cands}
ends=set()
for t in b.GetTracks():
    if t.GetClass()=="PCB_TRACK" and t.GetNetname()=="+5V_LED":
        for p in (t.GetStart(),t.GetEnd()): ends.add((round(T(p.x),3),round(T(p.y),3)))
rm=0
for t in list(b.GetTracks()):
    if t.GetClass()=="PCB_VIA" and t.GetNetname()=="+5V_LED":
        p=t.GetPosition(); k=(round(T(p.x),3),round(T(p.y),3))
        if k in cs and not any(math.hypot(k[0]-e[0],k[1]-e[1])<0.4 for e in ends): b.Remove(t); rm+=1
print("unused candidate vias removed:", rm)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(dst)
