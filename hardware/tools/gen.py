"""Regenerate the schematic: python3 gen.py (inside the kicad/kicad:9.0 container)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import customlib, schgen, circuit

HW = os.path.dirname(HERE)
LIB = os.path.join(HW, "lib", "vrc.kicad_sym")
os.makedirs(os.path.dirname(LIB), exist_ok=True)
customlib.write(LIB)
import footprints
footprints.write(os.path.join(HW, "lib", "vrc.pretty"))
libs = schgen.SymbolLibs(extra_libs={"vrc": LIB})
prj = schgen.Project("vmix-replay-controller", libs, paper="A3", title="vMix Replay Controller", rev="1.0")
circuit.build(prj)
prj.write(HW)
print("ok")

# ---- PINMAP.md (generated tables for firmware) ----------------------------
import re
src = open(os.path.join(HERE, "circuit.py"), encoding="utf-8").read()
gp_block = re.search(r"gp = \{(.*?)\}", src, re.S).group(1)
gp = dict((int(k), v) for k, v in re.findall(r"(\d+): \"([^\"]+)\"", gp_block))
L = ["# Přiřazení pinů (generováno z tools/circuit.py, needitovat ručně)", "",
     "## RP2040 GPIO", "", "| GPIO | Síť |", "|---|---|"]
L += ["| GP%d | `%s` |" % (k, gp[k]) for k in sorted(gp)]
L += ["", "## Tlačítka → TCA9555", "", "| Tlačítko | Expandér | Port |", "|---|---|---|"]
addr = {"U8": "U8 (0x20)", "U9": "U9 (0x21)"}
L += ["| %s | %s | %s |" % (n, addr[c], p) for n, (c, p) in circuit.TCA_MAP.items()]
L += ["| (volné, na J3) | %s | %s |" % (addr[c], p) for c, p in circuit.SPARE_EXP]
L += ["", "## LED → IS31FL3236A", "", "| LED | Budič | Kanál |", "|---|---|---|"]
addr = {"U6": "U6 (0x3C)", "U7": "U7 (0x3F)"}
L += ["| %s | %s | OUT%d |" % (n[4:], addr[c], ch) for n, (c, ch) in sorted(circuit.LED_MAP.items(), key=lambda x: (x[1][0], x[1][1]))]
open(os.path.join(HW, "PINMAP.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
