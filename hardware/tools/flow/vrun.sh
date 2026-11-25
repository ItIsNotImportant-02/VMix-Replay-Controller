#!/bin/bash
# vrun.sh <variant.json or "base"> <name> : regenerate schematic + board for a placement variant and route it
V=$1; N=$2; D=/tmp/claude-0/var/$N
REPO=/home/user/VMix-Replay-Controller/hardware
K=/tmp/claude-0/kt/kc; J=/usr/lib/jvm/java-25-openjdk-amd64/bin/java; FR=/tmp/claude-0/fr25/freerouting-2.5.0-executable.jar
if [ -e $D ]; then echo "$D exists"; exit 1; fi; mkdir -p $D/build
(cd $REPO && tar cf - --exclude=build --exclude=logs --exclude='*.local-backup*' .) | (cd $D && tar xf -)
if [ "$V" != base ]; then cp $V $D/build/variant.json; python3 /tmp/claude-0/kt/setmaps.py $D/tools/circuit.py $V; fi
echo "== place $(date +%T)"
HW=$D $K "python3 tools/gen.py && kicad-cli sch export netlist --format kicadsexpr -o build/net.net vmix-replay-controller.kicad_sch && python3 tools/verify.py | tail -2 && python3 tools/pcb.py place && { [ -f build/variant.json ] && python3 /kt/vapply.py build/variant.json || true; } && python3 tools/pcb.py finish" 2>&1 | grep -v Debug | grep -v "^arrange:" | tail -6
echo "== dsn $(date +%T)"
HW=$D $K "python3 /kt/dsn_in2.py" 2>&1 | grep -v Debug | tail -2
[ -n "$PLACEONLY" ] && { HW=$D $K "kicad-cli pcb drc -o /hw/build/pl.rpt /hw/build/prep.kicad_pcb" >/dev/null 2>&1; grep -oE "^\[[a-z_]+\]" $D/build/pl.rpt | sort | uniq -c | grep -v "unconnected\|silk\|lib_"; exit 0; }
echo "== route $(date +%T)"
(cd $D/build && timeout ${FRT:-3600} $J -Xmx3000m -jar $FR --gui.enabled=false -de full.dsn -do full.ses -mp ${MP:-100} -mt 1 > fr.log 2>&1)
grep -o "Stopping the auto-router.*\|final score.*violations" $D/build/fr.log | tail -2
echo "== finish $(date +%T)"
HW=$D $K "python3 /kt/vfinish.py && kicad-cli pcb drc -o /hw/build/r.rpt /hw/build/r.kicad_pcb" 2>&1 | grep -v Debug | grep Found
echo "== done $(date +%T)"
