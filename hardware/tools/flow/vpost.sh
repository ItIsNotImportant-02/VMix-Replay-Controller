#!/bin/bash
# vpost.sh <name>: grid-router cleanup, +5V_LED island links, pours + stitching, DRC summary
N=$1; D=/tmp/claude-0/var/$N; K=/tmp/claude-0/kt/kc
cp $D/build/r.kicad_pro $D/build/r3.kicad_pro 2>/dev/null; cp $D/build/r.kicad_pro $D/build/r2.kicad_pro 2>/dev/null
HW=$D timeout 2400 $K "python3 -u /kt/vlo.py" 2>&1 | grep -v "Debug\|^    fail" | tail -3
HW=$D $K "python3 /kt/fill.py /hw/build/r2.kicad_pcb && python3 -u /kt/lo3.py /hw/build/r2.kicad_pcb /hw/build/r3.kicad_pcb" 2>&1 | grep -v "Debug\|^    fail" | grep "anchors\|still open\|removed" | cut -c1-120
HW=$D $K "python3 /kt/final.py /hw/build/r3.kicad_pcb && kicad-cli pcb drc -o /hw/build/final.rpt /hw/vmix-replay-controller.kicad_pcb" 2>&1 | grep -v Debug | grep "Found\|stitch"
grep -oE "^\[[a-z_]+\]" $D/build/final.rpt | sort | uniq -c
