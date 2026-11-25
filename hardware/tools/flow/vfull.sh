#!/bin/bash
# vfull.sh <var>: widen + silk + rules + DRC + checks on the post-processed main board
N=$1; D=/tmp/claude-0/var/$N; K=/tmp/claude-0/kt/kc; P=/hw/vmix-replay-controller.kicad_pcb
/tmp/claude-0/kt/wloop.sh $N 2>&1 | grep "iter\|widened\|\]" | tail -12
HW=$D $K "python3 /kt/silk2.py $P $P passives && python3 /kt/silk2.py $P $P passives --back" 2>&1 | grep "removed\|placed" | cut -c1-200
python3 - $D/vmix-replay-controller.kicad_pro <<'PY'
import json,sys; p=sys.argv[1]; j=json.load(open(p)); j["board"]["design_settings"]["rules"]["min_track_width"]=0.1; json.dump(j,open(p,"w"),indent=2)
PY
HW=$D $K "python3 /kt/fill.py $P; kicad-cli pcb drc --schematic-parity -o /hw/build/full.rpt $P; python3 /kt/chk.py" 2>&1 | grep -v "Debug\|swig"
grep -oE "^\[[a-z_]+\]" $D/build/full.rpt | sort | uniq -c
