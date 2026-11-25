import pcbnew, sys, collections
# merge collinear consecutive segments of same net/layer/width where no other item attaches at the joint
src=sys.argv[1]; b=pcbnew.LoadBoard(src)
def k(p): return (p.x,p.y)
changed=True; tot=0; once=True
while changed and once:
    once=False
    changed=False
    tr=[t for t in b.GetTracks() if t.GetClass()=="PCB_TRACK"]
    ends=collections.defaultdict(list)
    for t in b.GetTracks():
        if t.GetClass()=="PCB_TRACK":
            ends[(k(t.GetStart()),t.GetLayer())].append(t); ends[(k(t.GetEnd()),t.GetLayer())].append(t)
        else:
            for L in range(0,64):
                pass
    vias=set(k(v.GetPosition()) for v in b.GetTracks() if v.GetClass()=="PCB_VIA")
    pads=set()
    for f in b.GetFootprints():
        for p in f.Pads(): pads.add(k(p.GetPosition()))
    gone=set(); rm=[]
    for (pt,L),lst in ends.items():
        if len(lst)!=2 or pt in vias or pt in pads: continue
        a,c=lst
        if id(a) in gone or id(c) in gone or a is c: continue
        if a.GetWidth()!=c.GetWidth() or a.GetNetCode()!=c.GetNetCode(): continue
        oa=a.GetEnd() if k(a.GetStart())==pt else a.GetStart()
        oc=c.GetEnd() if k(c.GetStart())==pt else c.GetStart()
        v1=(pt[0]-oa.x,pt[1]-oa.y); v2=(oc.x-pt[0],oc.y-pt[1])
        cr=v1[0]*v2[1]-v1[1]*v2[0]; dt=v1[0]*v2[0]+v1[1]*v2[1]
        n1=(v1[0]**2+v1[1]**2)**.5; n2=(v2[0]**2+v2[1]**2)**.5
        if dt<=0 or abs(cr)>1e-3*n1*n2: continue
        a.SetStart(oa); a.SetEnd(oc); gone.add(id(a)); gone.add(id(c)); rm.append(c)
    for c in rm: b.Remove(c)
    tot+=len(rm); changed=bool(rm)
print("merged",tot)
b.Save(src)
