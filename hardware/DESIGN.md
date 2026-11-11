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
- **W5500 (ověřeno proti datasheetu v1.1.0):** TOCAP 4,7 µF, 1V2O 10 nF, EXRES1 12,4k 1 %, VBG nezapojený, PMODE = 111 (auto-negotiation), RSVD 23 na GND. RSVD 38–42 jsou od revize 1.0.2 „NC“ (dřív „tie to GND“), na GND zůstávají, vyhovuje to oběma revizím. LED výstupy jsou aktivní v nule a snesou ~8 mA, proto 330R. Krystal 25 MHz X322525MOB4SI (CL 12 pF, ±10 ppm) s 2× 18 pF a 1M paralelně jako WIZ850io. Analogová část 1:1 podle WIZ850io V1.1 (sériově 3,3R, TX 49,9R na +3V3A, TCT 10R + 22 nF, RX 6,8 nF v sérii, 49,9R + 49,9R do RCT + 10 nF). Pull-upy na INT, RST a CS.
- **HR911105A (ověřeno z výkresu HanRun):** P1 TD+, P2 TD−, P3 RD+, P6 RD−, P4 TCT, P5 RCT (oddělené), P7 NC, P8 CHS GND (interní 4× 75R + 1000 pF/2 kV, „connect to PCB ground“). Zelená LED: anoda 9, katoda 10; žlutá: anoda 12, katoda 11. Pozor: WIZnet reference s J1B1211CCD má zelenou obráceně, nekopírovat. W5500 neumí auto-MDIX; PC i switche ho mají, takže to nevadí.
- **FB1 (ferit pro LED):** Bourns MH3261-601Y (2 A, 100 mΩ). Původní GZ2012D601TF (C1017) má jen 500 mA a 300 mΩ, při plném proudu LED by byl přetížený.
- **IS31FL3236A (ověřeno proti datasheetu Rev. I, 10/2024):** pinout QFN-44 sedí se symbolem. Footprint je 1:1 podle doporučeného land patternu (pady 0,25 × 1,0, rohové 0,8 se zaoblením, EP 2,45 mm). I_MAX = 58,5 × 1,3 V / R_EXT, 3,9k → 19,5 mA (datasheet: min. R_EXT 2k, max. 38 mA). OUTx max VCC + 0,3 V → VCC = +5V_LED. Logika VIH 1,4 V pevně, I2C max 400 kHz. 1 µF + 100 nF na VCC a 100k pull-down na SDB jako v aplikačním zapojení. θJA 32,7 °C/W: při všech LED naplno bílé by jeden čip ztrácel ~1,5 W (+50 °C); firmware omezuje celkový proud, PWM 22 kHz (méně pískání MLCC, datasheet to doporučuje).
- **TCA9555 (ověřeno proti datasheetu TI SCPS200E):** VCC 1,65–5,5 V, I2C 400 kHz, SDA/SCL VIH 0,7 × VCC (na 3,3 V v pořádku). Po zapnutí jsou všechny piny vstupy s interním pull-upem (~100 kΩ), tlačítka spínají proti GND. INT je open-drain, pull-up 10k (R50) jako v datasheetu. A0–A2 nesmí plavat → U8 000 (0x20), U9 A0 = 1 (0x21). Thermal pad: GND nebo nezapojený, máme GND. ESD ±2 kV HBM. Nemá reset pin.
- **Metalová tlačítka na panelu:** PB26 mají kovové pouzdro. Kovový čelní panel spojit se zemí desky (šrouby/distanční sloupky na GND), aby výboj z prstu šel do země a ne do vstupů expandérů (ty mají jen ±2 kV HBM).
- **Firmware kompatibilita:** W5500 na stejných pinech jako WIZnet W5500-EVB-Pico (SPI0, GP16–21), takže jdou použít jejich knihovny beze změn.

## Co je ještě potřeba ověřit před objednávkou

1. **Footprinty PB26-13M a TS5** (vlastní, `lib/vrc.pretty`): rozteče vývodů podle popisu prodejce, ověří se vytištěním 1:1 a přiložením skutečného tlačítka.
3. **LCSC čísla** označená `?` v `circuit.py` (pasivní součástky, krystaly, LDO, polyswitch, TVS, ferity, JST): doplnit a zkontrolovat skladovost a Basic/Extended.
6. **Polarita pinu MODE u MT6701** (datasheet ji v textu neuvádí); deska to řeší tím, že MODE řídí MCU.

## Poznámky pro firmware (z datasheetů)

- **W5500:** po zapnutí tvrdý reset (RST v nule ≥ 500 µs, pak čekat na PLL ≤ 1 ms), počkat na link (PHYCFGR.LNK), až pak DHCP; DHCP opakovat, při ztrátě linku znovu připojit; volitelně pevná IP. SPI režim 0, začít na ~20 MHz.
- **I2C sběrnice:** po startu RP2040 provést obnovu sběrnice (9 pulzů SCL, pak STOP), protože TCA9555 nemá reset a po resetu MCU uprostřed přenosu může držet SDA v nule. IS31FL3236A resetuje I2C náběžnou hranou SDB.
- **TCA9555 INT:** INT se nuluje jen čtením vstupního registru portu, který ho vyvolal (0x00 pro P0, 0x01 pro P1) → při INT číst vždy oba. Přerušení během ACK se může ztratit, proto navíc pomalé pravidelné čtení (např. každých 20 ms) jako záloha. Debounce softwarově.
- **IS31FL3236A:** PWM 22 kHz (registr 0x4B = 1) kvůli pískání MLCC; po nastavení registrů SDB do 1; celkový proud LED držet pod limitem USB podle měření VSENSE_5V.
