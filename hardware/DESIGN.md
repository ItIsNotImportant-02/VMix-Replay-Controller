# Návrh hlavní desky (schéma v1)

Podle [SPEC-v1](../docs/SPEC-v1.md) a layoutu [v0.5](../docs/layout/panel-layout-v0.5.pdf). Přiřazení pinů, tlačítek a LED kanálů: [PINMAP.md](PINMAP.md).

## Jak se schéma vyrábí

Schéma je jedna stránka A2 rozdělená do orámovaných bloků (napájení, MCU, Ethernet, flash, LED budiče, expandéry, tlačítka, senzory, ladění). Bloky mezi sebou propojují lokální labely se stejným jménem, napájení napájecí symboly.

Schéma se nekreslí ručně. Zapojení (kdo je s kým spojený) je v [tools/circuit.py](tools/circuit.py), rozmístění bloků a kreslení v [tools/layout.py](tools/layout.py). Skript [tools/gen.py](tools/gen.py) z toho vygeneruje `vmix-replay-controller.kicad_sch`, knihovnu `lib/vrc.kicad_sym` a `PINMAP.md`. [tools/verify.py](tools/verify.py) pak vyexportuje netlist z hotového schématu a porovná ho s `circuit.py`, takže se nestane, že by nakreslené dráty spojily něco jiného, než je v popisu.

Proč takto: změna (např. přehození tlačítka na jiný kanál kvůli routování) je jeden řádek, schéma i tabulky se přegenerují a kontrola ověří, že nic nechybí. Ruční úpravy v KiCadu by se při dalším generování přepsaly, proto se mění `circuit.py` / `layout.py`.

Spuštění (KiCad 9 v Dockeru):

```
docker run --rm -u $(id -u) -v $PWD/hardware:/hw -w /hw kicad/kicad:9.0 python3 tools/gen.py
docker run --rm -u $(id -u) -v $PWD/hardware:/hw -w /hw kicad/kicad:9.0 python3 tools/verify.py
docker run --rm -u $(id -u) -v $PWD/hardware:/hw -w /hw kicad/kicad:9.0 kicad-cli sch erc vmix-replay-controller.kicad_sch
```

Deska plošného spoje (`vmix-replay-controller.kicad_pcb`) je zatím jen rozmístěná podle starého hierarchického schématu. Před routováním se v KiCadu udělá *Update PCB from Schematic* (párování podle referencí).

## Rozhodnutí v návrhu

- **LDO místo AMS1117:** ST LDL1117S33R (LCSC C435835, skladem) má úbytek pod 0,3 V při 200 mA a je v SOT-223, takže se neuvaří (odběr 3,3 V větve ~200 mA, W5500 bere nejvíc). AP2112K v SOT-23-5 by při 0,3 W topil přes 70 °C nad okolí.
- **IS31FL3236A na 5 V:** výstupy OUTx snesou max. VCC + 0,3 V. Anody LED jsou na 5 V (modrá a zelená potřebují až 3,6 V), takže VCC budiče musí být 5 V. Logické vstupy mají pevné prahy (VIH 1,4 V), I2C na 3,3 V tedy funguje.
- **Senzory:** MT6701 má piny 6/7/8 sdílené mezi ABZ, SSI a I2C a pin MODE volí ABZ nebo I2C/SSI. MODE proto řídí MCU, aby šlo jog jednou naprogramovat přes I2C (rozlišení ABZ v EEPROM) a pak číst ABZ, a páku číst přes SSI. Analogový/PWM výstup jde do ADC jako záloha. Destičky senzorů jsou samostatný malý projekt (bude v `hardware/sensor-board/`).
- **Debug bez prototypu:** SWD + UART konektor, testovací body na všech napájeních a na I2C/INT/SDB, rezervní GPIO (GP10, 11, 22, 23, 24, 28) a 4 volné vstupy expandéru na konektoru J3 spolu s I2C (např. pro OLED později).
- **Krystal RP2040:** Abracon ABM8-272-T3 (12 MHz, CL 10 pF, ESR max. 50 Ω, LCSC C20625731, Extended) s 2× 15 pF C0G a 1 kΩ v sérii z XOUT, přesně podle *Hardware design with RP2040*. Oscilátor RP2040 je slabý, krystal s CL 20 pF by se rozkmitával hůř; 1 kΩ chrání krystal před přebuzením při IOVDD 3,3 V.
- **W5500 (ověřeno proti datasheetu v1.1.0):** TOCAP 4,7 µF, 1V2O 10 nF, EXRES1 12,4k 1 %, VBG nezapojený, PMODE = 111 (auto-negotiation), RSVD 23 na GND. RSVD 38–42 jsou od revize 1.0.2 „NC“ (dřív „tie to GND“), na GND zůstávají, vyhovuje to oběma revizím. LED výstupy jsou aktivní v nule a snesou ~8 mA, proto 330R. Krystal 25 MHz, datasheet chce ±30 ppm. W5500 neumí auto-MDIX; PC i switche ho mají, takže to nevadí.
- **FB1 (ferit pro LED):** Bourns MH3261-601Y (2 A, 100 mΩ). Původní GZ2012D601TF (C1017) má jen 500 mA a 300 mΩ, při plném proudu LED by byl přetížený.
- **Firmware kompatibilita:** W5500 na stejných pinech jako WIZnet W5500-EVB-Pico (SPI0, GP16–21), takže jdou použít jejich knihovny beze změn.

## Co je ještě potřeba ověřit před objednávkou

1. **Footprinty PB26-13M a TS5** (vlastní, `lib/vrc.pretty`): rozteče vývodů podle popisu prodejce, ověří se vytištěním 1:1 a přiložením skutečného tlačítka.
2. **Footprint QFN-44 5×5 pro IS31FL3236A**: podle výkresu z datasheetu.
3. **LCSC čísla** označená `?` v `circuit.py` (pasivní součástky, krystaly, LDO, polyswitch, TVS, ferity, JST): doplnit a zkontrolovat skladovost a Basic/Extended.
4. **LED piny HR911105A**: zapojení (anody 12 a 9, katody 11 a 10) je podle symbolu z knihovny KiCadu; datasheet HanRun se nepodařilo strojově přečíst, ověřit ve výkresu.
6. **Polarita pinu MODE u MT6701** (datasheet ji v textu neuvádí); deska to řeší tím, že MODE řídí MCU.
