import pcbnew, sys, collections, math
b=pcbnew.LoadBoard(sys.argv[1]); c=collections.Counter(); n=collections.Counter()
for t in b.GetTracks():
    if t.GetClass()!="PCB_TRACK": continue
    L=math.hypot(t.GetEnd().x-t.GetStart().x,t.GetEnd().y-t.GetStart().y)/1e6
    c[round(t.GetWidth()/1e6,3)]+=L; n[round(t.GetWidth()/1e6,3)]+=1
tot=sum(c.values())
for w in sorted(c): print(f"{w:6.3f} mm: {c[w]:8.1f} mm ({100*c[w]/tot:4.1f} %), {n[w]} seg")
