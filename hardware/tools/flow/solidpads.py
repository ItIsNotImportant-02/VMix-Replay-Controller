import pcbnew, sys, re
src=sys.argv[1]; rpt=open(sys.argv[2]).read()
b=pcbnew.LoadBoard(src); n=0
for blk in rpt.split("\n[")[1:]:
    if not blk.startswith("starved_thermal"): continue
    m=re.search(r"(?i)pad (\S+) \[[^\]]*\] of (\S+)",blk)
    if not m: continue
    f=b.FindFootprintByReference(m.group(2))
    for p in f.Pads():
        if p.GetNumber()==m.group(1): p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL); n+=1
print("solid",n)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); b.Save(src)
