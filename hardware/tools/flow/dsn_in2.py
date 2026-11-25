import pcbnew, sys
sys.path.insert(0,'/hw/tools')
import route
route.prep()
b=pcbnew.LoadBoard(route.PREP)
pcbnew.ExportSpecctraDSN(b, '/hw/build/full.dsn')
route.strip_dsn_nets('/hw/build/full.dsn', ["GND"])
import os, re
if os.environ.get('IN2_KEEP_PLANE'):
    t=open('/hw/build/full.dsn').read(); t=re.sub(r"(\(layer In2\.Cu\s*\(type )power\)", r"\1signal)", t); open('/hw/build/full.dsn','w').write(t)
else:
    route.in2_signal('/hw/build/full.dsn')
print("dsn ok")
