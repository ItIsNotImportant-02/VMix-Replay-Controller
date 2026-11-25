import pcbnew, collections
T=pcbnew.ToMM
b=pcbnew.LoadBoard('/hw/vmix-replay-controller.kicad_pcb')
for z in [z for z in b.Zones() if not z.GetIsRuleArea()]:
    fp=z.GetFilledPolysList(z.GetLayer())
    ar=sorted([abs(fp.Outline(i).Area())/1e12 for i in range(fp.OutlineCount())],reverse=True)
    print(z.GetNetname(), b.GetLayerName(z.GetLayer()), "pieces",len(ar), [round(a,1) for a in ar[:4]])
L=collections.defaultdict(float); V=collections.Counter(); lay=collections.defaultdict(set); W=collections.defaultdict(set)
for t in b.GetTracks():
    n=t.GetNetname()
    if t.GetClass()=="PCB_VIA": V[n]+=1
    else: L[n]+=T(t.GetLength()); lay[n].add(b.GetLayerName(t.GetLayer())); W[n].add(round(T(t.GetWidth()),3))
for n in sorted(L):
    if any(k in n for k in ("USB_D","ETH_TX","ETH_RX","XIN","XOUT","ETH_XI","ETH_XO","XTAL","X1","X2")):
        print(n, round(L[n],2),"mm vias",V[n], sorted(lay[n]), sorted(W[n]))
print("total vias", sum(V.values()), "GND vias", V["GND"])
