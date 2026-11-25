import pcbnew, sys, math
src=sys.argv[1]; x,y=map(float,sys.argv[2:4])
b=pcbnew.LoadBoard(src)
f=b.FindFootprintByReference("U3"); c=f.GetPosition(); print("U3 at", c.x/1e6, c.y/1e6, f.GetOrientationDegrees())
near=[t for t in b.GetTracks() if t.GetClass()=="PCB_VIA" and t.GetNetname()=="GND" and math.hypot(t.GetPosition().x/1e6-c.x/1e6,t.GetPosition().y/1e6-c.y/1e6)<4]
print("GND vias within 4mm of U3:", [(round(t.GetPosition().x/1e6,2),round(t.GetPosition().y/1e6,2)) for t in near])
tgt=[t for t in near if abs(t.GetPosition().x/1e6-x)<0.01 and abs(t.GetPosition().y/1e6-y)<0.01]
for t in tgt: b.Remove(t); print("removed")
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); b.Save(src)
