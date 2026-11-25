import pcbnew, json, sys
T=pcbnew.ToMM
b=pcbnew.LoadBoard(sys.argv[1]); x0,y0,x1,y1=map(float,sys.argv[3:7])
inr=lambda x,y: x0-2<x<x1+2 and y0-2<y<y1+2
out={"pads":[],"tr":[],"via":[]}
for f in b.GetFootprints():
    for p in f.Pads():
        c=p.GetPosition()
        if not inr(T(c.x),T(c.y)): continue
        bb=p.GetBoundingBox()
        out["pads"].append([T(bb.GetX()),T(bb.GetY()),T(bb.GetRight()),T(bb.GetBottom()),p.GetNetname(),p.IsOnLayer(pcbnew.F_Cu),p.IsOnLayer(pcbnew.B_Cu),f.GetReference()+"."+p.GetNumber()])
for t in b.GetTracks():
    if t.GetClass()=="PCB_VIA":
        p=t.GetPosition()
        if inr(T(p.x),T(p.y)): out["via"].append([T(p.x),T(p.y),T(t.GetWidth(pcbnew.F_Cu))/2,t.GetNetname()])
    else:
        s,e=t.GetStart(),t.GetEnd()
        if inr(T(s.x),T(s.y)) or inr(T(e.x),T(e.y)):
            out["tr"].append([T(s.x),T(s.y),T(e.x),T(e.y),T(t.GetWidth()),t.GetNetname(),b.GetLayerName(t.GetLayer())])
json.dump(out,open(sys.argv[2],"w"))
