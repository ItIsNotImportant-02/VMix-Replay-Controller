import pcbnew, sys
src=sys.argv[1]; W=int(float(sys.argv[2])*1e6)
b=pcbnew.LoadBoard(src); n=0
for t in b.GetTracks():
    if t.GetClass()!="PCB_TRACK": continue
    if t.GetWidth()<W: t.SetWidth(W); n+=1
print("widened",n)
b.Save(src)
