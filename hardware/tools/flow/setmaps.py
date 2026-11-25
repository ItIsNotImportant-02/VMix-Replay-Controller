"""Rewrite TCA_MAP / LED_ASSIGN in a circuit.py from an optimiser result."""
import json, re, sys
path, res = sys.argv[1], json.load(open(sys.argv[2]))
s = open(path, encoding="utf-8").read()
tca = "TCA_MAP = {\n" + "".join('    "%s": ("%s", "%s"),\n' % (b, c, p) for b, (c, p) in sorted(res["tca"].items())) + "}"
led = "LED_ASSIGN = {\n" + "".join('    "%s": ("%s", %s),\n' % (b, c, list(ks)) for b, (c, ks) in sorted(res["led"].items())) + "}"
s = re.sub(r"TCA_MAP = \{.*?\n\}", lambda m: tca, s, count=1, flags=re.S)
s = re.sub(r"LED_ASSIGN = \{.*?\n\}", lambda m: led, s, count=1, flags=re.S)
open(path, "w", encoding="utf-8").write(s)
print("maps written:", len(res["tca"]), "buttons,", len(res["led"]), "LED buttons")
