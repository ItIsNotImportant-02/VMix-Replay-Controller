import pcbnew, sys
sys.path.insert(0,'/hw/tools')
import leftover, route
route.sidecar('/hw/build/r2.kicad_pcb')
b=pcbnew.LoadBoard('/hw/build/r.kicad_pcb')
import os
leftover.run(b, ripup=True, max_rips=int(os.environ.get("MR","3")), inner=True, max_rounds=int(os.environ.get("RND","2")), max_victims=int(os.environ.get("MV","2")))
b.Save('/hw/build/r2.kicad_pcb')
