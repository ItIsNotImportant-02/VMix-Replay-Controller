import pcbnew, sys, math
src=sys.argv[1]; MAXL=float(sys.argv[2]) if len(sys.argv)>2 else 1.0
b=pcbnew.LoadBoard(src); n=0
def P(x,y): return pcbnew.VECTOR2I(int(round(x)),int(round(y)))
for t in list(b.GetTracks()):
    if t.GetClass()!="PCB_TRACK": continue
    ax,ay,bx,by=t.GetStart().x,t.GetStart().y,t.GetEnd().x,t.GetEnd().y
    L=math.hypot(bx-ax,by-ay)/1e6
    k=int(math.ceil(L/MAXL))
    if k<2: continue
    pts=[(ax+(bx-ax)*i/k, ay+(by-ay)*i/k) for i in range(k+1)]
    t.SetEnd(P(*pts[1]))
    for i in range(1,k):
        nt=pcbnew.PCB_TRACK(b); nt.SetLayer(t.GetLayer()); nt.SetNet(t.GetNet()); nt.SetWidth(t.GetWidth())
        nt.SetStart(P(*pts[i])); nt.SetEnd(P(*pts[i+1])); b.Add(nt); n+=1
print("split pieces added",n)
b.Save(src)
