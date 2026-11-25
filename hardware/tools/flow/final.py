import pcbnew, sys, shutil
sys.path.insert(0,'/hw/tools')
import route
src=sys.argv[1]
b=pcbnew.LoadBoard(src)
route.add_outer_pours(b)
print("stitching vias:", route.stitch(b))
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(route.PCB)
print("saved", route.PCB)
