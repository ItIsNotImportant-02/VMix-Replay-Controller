import pcbnew, sys, math
sys.path.insert(0,'/hw/tools')
import route
from route import T, mm
src, dst = sys.argv[1], sys.argv[2]
anchors=[tuple(map(float,a.split(','))) for a in sys.argv[3:]]
b=pcbnew.LoadBoard(src); pcbnew.ZONE_FILLER(b).Fill(b.Zones())
z=[z for z in b.Zones() if z.GetLayer()==pcbnew.In2_Cu][0]
fp=z.GetFilledPolysList(pcbnew.In2_Cu)
ar=[abs(fp.Outline(i).Area()) for i in range(fp.OutlineCount())]; mi=ar.index(max(ar))
main=pcbnew.SHAPE_POLY_SET(); main.AddOutline(fp.Outline(mi))
for h in range(fp.HoleCount(mi)): main.AddHole(fp.Hole(mi,h))
def inm(x,y,r): return all(main.Contains(pcbnew.VECTOR2I(mm(x+r*math.cos(k*math.pi/8)),mm(y+r*math.sin(k*math.pi/8)))) for k in range(16)) and main.Contains(pcbnew.VECTOR2I(mm(x),mm(y)))
sp=route.Space(b)
for t in b.GetTracks():
    if t.GetClass()=="PCB_VIA":
        p=t.GetPosition(); sp.vias.append((T(p.x),T(p.y),T(t.GetWidth(pcbnew.F_Cu))/2,t.GetNetname()))
    else:
        sp.segs.append((T(t.GetStart().x),T(t.GetStart().y),T(t.GetEnd().x),T(t.GetEnd().y),T(t.GetWidth())/2,t.GetNetname(),t.GetLayer()))
best=None
for ax,ay in anchors:
    for rr in [k*0.25 for k in range(3,60)]:
        if best and rr>=best[0]: break
        n=max(8,int(2*math.pi*rr/0.2))
        for k in range(n):
            x=ax+rr*math.cos(2*math.pi*k/n); y=ay+rr*math.sin(2*math.pi*k/n)
            if not inm(x,y,0.6) or not sp.via_ok(x,y,"+5V_LED"): continue
            for L in (pcbnew.F_Cu, pcbnew.B_Cu):
                if sp.track_ok((ax,ay),(x,y),0.3,"+5V_LED",L):
                    best=(rr,(ax,ay),(x,y),L); break
            if best and best[0]==rr: break
print(best)
if best:
    rr,a,v,L=best; sp.add_track(a,v,"+5V_LED",0.3,L); sp.add_via(v[0],v[1],"+5V_LED")
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); b.Save(dst)
