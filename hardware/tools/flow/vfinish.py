"""Import the session, clean up with the grid router, link +5V_LED islands, pours; prints the score inputs."""
import pcbnew, sys, shutil, os
sys.path.insert(0,'/hw/tools')
import route
shutil.copy('/hw/build/prep.kicad_pcb','/hw/build/r.kicad_pcb'); route.sidecar('/hw/build/r.kicad_pcb')
b=pcbnew.LoadBoard('/hw/build/r.kicad_pcb'); pcbnew.ImportSpecctraSES(b,'/hw/build/full.ses'); b.Save('/hw/build/r.kicad_pcb')
b=pcbnew.LoadBoard('/hw/build/r.kicad_pcb'); route.led_vcc(b, route.plain_track(b)); pcbnew.ZONE_FILLER(b).Fill(b.Zones()); b.Save('/hw/build/r.kicad_pcb')
