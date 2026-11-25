import json, sys
from PIL import Image, ImageDraw, ImageFont
d=json.load(open(sys.argv[1])); x0,y0,x1,y1,S=map(float,sys.argv[3:8]); hl=sys.argv[8].split(",")
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',10)
W,H=int((x1-x0)*S),int((y1-y0)*S)
im=Image.new('RGB',(W,H),(15,15,15)); g=ImageDraw.Draw(im); f=lambda x,y:((x-x0)*S,(y-y0)*S)
cols={"F.Cu":(200,50,50),"In2.Cu":(40,150,60),"B.Cu":(60,100,220)}
for layer in ("B.Cu","In2.Cu","F.Cu"):
    for t in d["tr"]:
        if t[6]!=layer: continue
        c=(255,255,0) if t[5] in hl else cols[layer]
        g.line([f(t[0],t[1]),f(t[2],t[3])],fill=c,width=max(1,int(t[4]*S)))
for p in d["pads"]:
    if not p[5]: continue
    g.rectangle([f(p[0],p[1]),f(p[2],p[3])],outline=(255,255,0) if p[4] in hl else (170,170,170),width=2)
for v in d["via"]:
    g.ellipse([f(v[0]-v[2],v[1]-v[2]),f(v[0]+v[2],v[1]+v[2])],outline=(255,255,0) if v[3] in hl else (230,230,230),width=2)
    g.text(f(v[0]+v[2],v[1]),v[3].strip('/')[:9],fill=(200,200,200),font=font)
for p in d["pads"]:
    if p[5]: g.text(f(p[0],p[3]+0.05),p[4].strip('/')[:9],fill=(255,180,180),font=font)
# grid
import math
for gx in range(int(x0),int(x1)+1): g.line([f(gx,y0),f(gx,y1)],fill=(50,50,50))
for gy in range(int(y0),int(y1)+1): g.line([f(x0,gy),f(x1,gy)],fill=(50,50,50))
im.save(sys.argv[2])
