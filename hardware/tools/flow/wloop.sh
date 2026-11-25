#!/bin/bash
# wloop.sh <var>: widen sub-0.2 tracks to 0.2, then narrow offenders step by step
D=/tmp/claude-0/var/$1; K=/tmp/claude-0/kt/kc; P=/hw/vmix-replay-controller.kicad_pcb
[ -f $D/build/prewiden.kicad_pcb ] && cp $D/build/prewiden.kicad_pcb $D/vmix-replay-controller.kicad_pcb || cp $D/vmix-replay-controller.kicad_pcb $D/build/prewiden.kicad_pcb
HW=$D $K "python3 /kt/split.py $P 1.0 && python3 /kt/widen.py $P 0.2" 2>&1 | grep "widened\|split"
for i in $(seq 1 ${IT:-10}); do
  HW=$D $K "kicad-cli pcb drc -o /hw/build/w.rpt $P" 2>&1 | grep Found | tr '\n' ' '
  c=$(grep -c '^\[clearance\]\|^\[shorting' $D/build/w.rpt); echo " iter $i clearance=$c"
  [ "$c" = 0 ] && break
  HW=$D STEPS=0.2,0.15,0.112,0.1 MAXW=0.2 $K "python3 /kt/fixw.py $P /hw/build/w.rpt" 2>&1 | grep narrowed
done
grep -oE "^\[[a-z_]+\]" $D/build/w.rpt | sort | uniq -c
for j in $(seq 1 12); do r=$(HW=$D $K "python3 /kt/merge.py $P" 2>&1 | grep merged); [ "$r" = "merged 0" ] && break; done
HW=$D $K "python3 /kt/fill.py $P; kicad-cli pcb drc -o /hw/build/w2.rpt $P" 2>&1 | grep Found; grep -oE "^\[[a-z_]+\]" $D/build/w2.rpt | sort | uniq -c
HW=$D $K "python3 /kt/wstat.py $P" 2>&1 | grep " mm:"
