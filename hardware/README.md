# Hardware (KiCad 9)

Hlavní deska ovladače. Popis návrhu a otevřené body: [DESIGN.md](DESIGN.md), piny a mapování tlačítek/LED: [PINMAP.md](PINMAP.md).

- `vmix-replay-controller.kicad_pro` a `vmix-replay-controller.kicad_sch`: projekt a jednostránkové blokové schéma (generované z `tools/circuit.py` + `tools/layout.py`, needitovat ručně)
- `lib/`: vlastní symboly a footprinty (PB26, TS5, IS31FL3236A QFN-44)
- `tools/`: generátor schématu a footprintů (`gen.py`) a kontrola netlistu (`verify.py`)
- `production/`: výrobní data pro JLCPCB (Gerber, BOM, CPL), doplní se po návrhu desky
