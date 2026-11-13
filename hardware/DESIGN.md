# Návrh hlavní desky (schéma v1)

Podle [SPEC-v1](../docs/SPEC-v1.md) a layoutu [v0.6](../docs/layout/panel-layout-v0.6.pdf) (podle EVS LSM VIA, deska 160 × 155 mm, 4 vrstvy; dřívější [v0.5](../docs/layout/panel-layout-v0.5.pdf)). Přiřazení pinů, tlačítek a LED kanálů: [PINMAP.md](PINMAP.md).

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

- **LDO místo AMS1117:** TI TLV76133DCYR (LCSC C7527500, SOT-223, 1 A; pin 1 GND, 2 + tab OUT, 3 IN podle SBVS349D): úbytek podle datasheetu 0,9 V typ. / 1,6 V max. při 1 A (jiný proud datasheet neuvádí; při našich ~230 mA úměrně ~0,2–0,4 V, takže stačí +5V ≥ ~3,7 V a USB dává i po úbytku na pojistce a kabelu ≥ 4,2 V), stabilní s libovolnými keramickými kondenzátory 1–220 µF (ESR 2–500 mΩ). Původní ST LDL1117 potřebuje podle obr. 20/21 datasheetu ESR ≥ ~11–20 mΩ a nad 22 µF není charakterizovaný; s ~30 µF MLCC na +3V3 by byl na hraně stability (na fóru ST je případ oscilací). AMS1117 má úbytek ~1,1 V a stabilitu zaručuje jen s 22 µF tantalem. Ztráta ~0,35 W → +33 °C v SOT-223.
- **IS31FL3236A na 5 V:** výstupy OUTx snesou max. VCC + 0,3 V. Anody LED jsou na 5 V (modrá a zelená potřebují až 3,6 V), takže VCC budiče musí být 5 V. Logické vstupy mají pevné prahy (VIH 1,4 V), I2C na 3,3 V tedy funguje.
- **Senzory MT6701 (ověřeno proti datasheetu Rev. 1.8):** napájení 3,0–5,5 V, my 3,3 V, takže výstupy (push-pull) jsou 3,3V a jdou přímo do RP2040. Piny 6/7/8 jsou podle režimu A/B/Z, SDA/SCL nebo DO/CLK/CSN; MODE má vnitřní pull-up 200k; podle referenčních zapojení v datasheetu (Rev. 1.9, obr. 22 a obr. 6) je **MODE = 1 (nebo nezapojený) → I2C/SSI, MODE = 0 → ABZ/UVW**. MODE řídí MCU (GP5, GP15), takže jdou oba režimy. **Oba senzory čteme přes SSI** (14bitový absolutní úhel + stav magnetu + CRC, CLK max 15,6 MHz): páka přes SPI1, jog přes PIO na GP2–4. Jog se počítá z rozdílu úhlů (16384 kroků na otáčku), takže není potřeba ABZ ani zápis do EEPROM – ten by podle datasheetu vyžadoval VDD 4,5–5,5 V, což při napájení 3,3 V nejde. Fyzicky jsou to stejné vodiče jako A/B/Z, takže ABZ zůstává jako záloha. OUT (analog/PWM) přes 1k + 10 nF do ADC jako záloha; 1k odděluje kapacitu (datasheet: CL ≤ 1 nF přímo na pinu). Destička senzoru (samostatný projekt `hardware/sensor-board/`): 100 nF + TVS 6 V na VDD (doporučení datasheetu), magnet Ø6 × 2,5 mm diametrálně magnetovaný, mezera 0,5–2 mm, max. 0,3 mm mimo osu.
- **Debug bez prototypu:** SWD + UART konektor, testovací body na všech napájeních a na I2C/INT/SDB, rezervní GPIO (GP10, 11, 22, 23, 24, 28) a 4 volné vstupy expandéru na konektoru J3 spolu s I2C (např. pro OLED později).
- **Krystal RP2040:** Yajingxin TX322512M4DBDE2T (12 MHz, CL 10 pF, ESR max. 60 Ω, ±10 ppm, LCSC C5310728, Extended, 7 766 ks skladem 12. 11. 2026) s 2× 15 pF C0G a 1 kΩ v sérii z XOUT. Obvod je přesně podle *Hardware design with RP2040*; doporučený Abracon ABM8-272-T3 (CL 10 pF, ESR max. 50 Ω, C20625731) má JLC skladem 1 ks, proto náhrada se stejnou CL (pady 1 a 3 krystal, 2 a 4 GND, ověřeno v datasheetu). Raspberry Pi u jiného krystalu doporučuje otestovat rozběh: pojistky jsou `PICO_XOSC_STARTUP_DELAY_MULTIPLIER 64` ve firmwaru a R10 (0603), který jde ručně zmenšit (např. na 330 Ω), kdyby se oscilátor nerozbíhal. Jako rezervu se vyplatí koupit pár kusů ABM8-272-T3 (DigiKey/Mouser/TME). Oscilátor RP2040 je slabý, krystal s CL 20 pF by se rozkmitával hůř; 1 kΩ chrání krystal před přebuzením při IOVDD 3,3 V.
- **W5500 (ověřeno proti datasheetu v1.1.0):** TOCAP 4,7 µF, 1V2O 10 nF, EXRES1 12,4k 1 % (10k + 2,4k), VBG nezapojený, PMODE = 111 (auto-negotiation), RSVD 23 na GND. RSVD 38–42 jsou od revize 1.0.2 „NC“ (dřív „tie to GND“), na GND zůstávají, vyhovuje to oběma revizím. LED výstupy jsou aktivní v nule a snesou ~8 mA, proto 330R. Krystal 25 MHz X322525MOB4SI (CL 12 pF, ±10 ppm) s 2× 18 pF a 1M paralelně jako WIZ850io. Analogová část 1:1 podle WIZ850io V1.1 (sériově 0R místo 3,3R, TX 49,9R na +3V3A, TCT 10R + 22 nF, RX 6,8 nF v sérii, 49,9R + 49,9R do RCT + 10 nF). Pull-upy na INT, RST a CS.
- **HR911105A (ověřeno z výkresu HanRun):** P1 TD+, P2 TD−, P3 RD+, P6 RD−, P4 TCT, P5 RCT (oddělené), P7 NC, P8 CHS GND (interní 4× 75R + 1000 pF/2 kV, „connect to PCB ground“). Zelená LED: anoda 9, katoda 10; žlutá: anoda 12, katoda 11. Pozor: WIZnet reference s J1B1211CCD má zelenou obráceně, nekopírovat. W5500 neumí auto-MDIX; PC i switche ho mají, takže to nevadí.
- **FB1 (ferit pro LED):** Murata BLM18PG121SN1D (2 A, 50 mΩ). Původní GZ2012D601TF (C1017) má jen 500 mA a 300 mΩ, při plném proudu LED by byl přetížený.
- **IS31FL3236A (ověřeno proti datasheetu Rev. I, 10/2024):** pinout QFN-44 sedí se symbolem. Footprint je 1:1 podle doporučeného land patternu (pady 0,25 × 1,0, rohové 0,8 se zaoblením, EP 2,45 mm). I_MAX = 58,5 × 1,3 V / R_EXT, 4,7k → 16,2 mA (LED v PB26 mají max. 20 mA, TS5 25 mA; datasheet: min. R_EXT 2k, max. 38 mA). OUTx max VCC + 0,3 V → VCC = +5V_LED. Logika VIH 1,4 V pevně, I2C max 400 kHz. 1 µF + 100 nF na VCC a 100k pull-down na SDB jako v aplikačním zapojení. θJA 32,7 °C/W: při všech LED naplno bílé by jeden čip ztrácel ~1,5 W (+50 °C); firmware omezuje celkový proud, PWM 22 kHz (méně pískání MLCC, datasheet to doporučuje).
- **TCA9555 (ověřeno proti datasheetu TI SCPS200E):** VCC 1,65–5,5 V, I2C 400 kHz, SDA/SCL VIH 0,7 × VCC (na 3,3 V v pořádku). Po zapnutí jsou všechny piny vstupy s interním pull-upem (~100 kΩ), tlačítka spínají proti GND. INT je open-drain, pull-up 10k (R50) jako v datasheetu. A0–A2 nesmí plavat → U8 000 (0x20), U9 A0 = 1 (0x21). Thermal pad: GND nebo nezapojený, máme GND. ESD ±2 kV HBM. Nemá reset pin.
- **Pull-upy tlačítek RN1–RN7 (4× 4,7k):** interní pull-up TCA9555 (~100k) dá přes kontakt jen ~33 µA. Kontakty PB26 (0,4 VA, materiál neuveden) mohou při tak malém proudu časem oxidovat a „vynechávat“; 4,7k dá ~0,7 mA (wetting current) a nižší impedanci vstupu proti rušení.
- **Metalová tlačítka na panelu:** PB26 mají kovové pouzdro. Kovový čelní panel spojit se zemí desky (šrouby/distanční sloupky na GND), aby výboj z prstu šel do země a ne do vstupů expandérů (ty mají jen ±2 kV HBM).
- **Firmware kompatibilita:** W5500 na stejných pinech jako WIZnet W5500-EVB-Pico (SPI0, GP16–21), takže jdou použít jejich knihovny beze změn.

## Díly JLCPCB (ověřeno 11. 11. 2026 přes API JLCPCB, celý katalog Basic + Preferred)

- JLC osazuje 128 dílů, všechny mají LCSC číslo a jsou skladem. Basic a Preferred díly jsou bez poplatku, každý typ Extended stojí cca 3 USD za založení.
- **Extended zůstává 8 typů (~24 USD):** RP2040, W5500, IS31FL3236A, TCA9555 (I/O expandér v Basic/Preferred neexistuje), krystal Y1, USB-C J1, LDO U2 (TLV76133, kvůli stabilitě s keramikou) a polyswitch F1 (Basic/Preferred neobsahuje žádné konektory ani vratné pojistky).
  - Y1: jediný Basic 12 MHz (C9002) má CL 20 pF a ESR 80 Ω, mimo doporučení RP2040. ABM8-272-T3 došel (1 ks) → TX322512M4DBDE2T (C5310728, CL 10 pF, ESR 60 Ω). V náhledu osazení zkontrolovat natočení (delší strana 3,2 mm vodorovně jako footprint).
  - U2: jediný Basic je AMS1117-3.3 (úbytek ~1,1 V, stabilní jen s tantalem) → TLV76133DCYR.
- **Nahrazeno kvůli poplatku:**
  - EXRES1 12,4k → R20 10k + R36 2,4k v sérii (obě Basic 1 %, součet přesně 12,40k).
  - Sériové 3,3R v TX/RX (R24, R25, R29, R30) → 0R (Basic); W5500 je nepotřebuje, footprint zůstává pro případnou změnu.
  - LED: D2 (napájení) červená KT-0603R (C2286, Basic) z +3V3 přes 1k ≈ 1,4 mA; D3 (stav) žlutá NCD0603Y2 (C89811, Preferred) přes 1k ≈ 1,3 mA. Zelená/modrá 0603 v Basic není.
  - U1 ESD: SRV05-4 (C7420376, Preferred) místo USBLC6-2SC6, stejné pouzdro SOT-23-6, každá datová linka má dvě diody (1+4 D+, 3+6 D−), VP na VBUS. Ověřeno v datasheetu Hongjiacheng Rev 2.1: pinout 1 I/O1, 2 GND, 3 I/O2, 4 I/O3, 5 VCC, 6 I/O4; Cj 1 pF typ na kanál → 2 pF na linku (USB FS bez problému; pozor na fóru EEVblog: TVS SM712 se 70 pF USB rozbil); VRWM 5 V, IR max 5 µA.
  - D1 TVS: SMF5.0A od hongjiacheng (C19077497, Preferred), stejné parametry i pouzdro.
  - FB1: Murata BLM18PG121SN1D (C14709, Basic, 0603, 2 A, 50 mΩ, 120 Ω @ 100 MHz). Méně tlumí než 600 Ω, pro napájení LED to stačí.
- **Ručně pájené, kupují se zvlášť:** J4 RJ45 HR911105A (koupit originál HanRun z TME/LCSC, ne levnou kopii z AliExpressu: na fóru Arduino je případ, kdy s náhradní „HR911105A“ nešel link), J5/J6 JST PH 8P SMD (S8B-PH-SM4-TB), tlačítka PB26/TS5, J2/J3. Ušetří to i příplatek za THT osazení RJ45.
- **RN1–RN7:** UNI-ROYAL 4D03WGJ0472T5E (C1980, Basic, 5 %): odpory 1–8, 2–7, 3–6, 4–5, stejně jako symbol R_Pack04.
- **Footprinty porovnané s EasyEDA** (souřadnice padů): QFN-56, QFN-44, WQFN-24, LQFP-48, SOIC-8, SOT-223, SOT-23-6, krystaly 3225, SOD-123F, 1206, TS-1187A, JST PH, HR911105A, USB-C HRO, RN 0603. Rozměry sedí; rozdíly jsou jen v natočení (pin 1 u EasyEDA dole vlevo) a v počátku u J1, obojí řeší `tools/jlc.py`.
- V náhledu osazení JLCPCB zkontrolovat polaritu D2/D3 (katoda = pad 1 v KiCadu) a natočení U1 a U2 (pin 1 SRV05-4 je podle datasheetu vlevo dole, stejně jako u ověřeného footprintu SOT-23-6).

## Export pro JLCPCB

Po rozmístění a routování: Gerbery a vrtání z KiCadu (Fabrication Outputs, nebo `kicad-cli pcb export gerbers/drill`), pak `python3 tools/jlc.py` → `build/jlc/BOM-JLCPCB.csv` a `CPL-JLCPCB.csv`. Skript nepotřebuje KiCad, čte přímo `.kicad_pcb`, a skončí chybou, pokud nějaký osazovaný díl nemá LCSC číslo.

## Co je ještě potřeba ověřit před objednávkou

1. **Footprinty PB26-13M a TS5** (vlastní, `lib/vrc.pretty`): rozteče vývodů podle popisu prodejce, ověří se vytištěním 1:1 a přiložením skutečného tlačítka.
2. **Náhled osazení v JLCPCB** před zaplacením: zkontrolovat hlavně U5–U9, U2, U4, U1, RN1–RN7, J1 a J4 (opravy rotace a počátku jsou v `tools/jlc.py`, odvozené z footprintů EasyEDA, ale náhled je poslední kontrola).
3. **Tlačítka multimetrem (test diod / průchodnost)** před objednáním: u PB26 který vývod je společná anoda a které barvy jsou na ostatních (výkres výrobce se nepodařilo najít; footprint se 13. 11. 2026 shoduje s vlastním footprintem FB26_RGB uživatele, otočeným o 90°: COM = pad 1, NO = pad 2, NC = pad 3, LED A/R/G/B sedí; ten footprint byl na vyrobené desce a tlačítko do něj pasovalo, takže rozměry jsou ověřené; uživatel 13. 11. potvrdil, že vývody na skutečném kuse odpovídají výkresu prodejce: COM, NO, NC v řadě, L2 = LED+ u COM, L1 červená u NC, L4 zelená, L3 modrá, což footprint i zapojení splňují → PB26 ověřené); u TS5 polarita LED (podle výkresu Honyone TS5-2X-XA-1XS: 6 = +, 5 = −) a že jsou spojené vývody 1–2 a 3–4.
4. **Rozběh krystalu Y1** při oživení (náhrada za ABM8-272-T3, viz výše).

## Poznámky pro firmware (z datasheetů)

- **MT6701:** po zapnutí čekat ≥ 32 ms; MODE = 1 (I2C/SSI). SSI: rámec začíná sestupnou hranou CSN, senzor mění DO na náběžné hraně CLK → vzorkovat na sestupné. Začít na 1 MHz a ověřit CRC. Stav Mg[1:0] hlásí slabé/silné pole – využít pro diagnostiku.
- **W5500:** po zapnutí tvrdý reset (RST v nule ≥ 500 µs, pak čekat na PLL ≤ 1 ms), počkat na link (PHYCFGR.LNK), až pak DHCP; DHCP opakovat, při ztrátě linku znovu připojit; volitelně pevná IP. SPI režim 0, začít na ~20 MHz.
- **I2C sběrnice:** po startu RP2040 provést obnovu sběrnice (9 pulzů SCL, pak STOP), protože TCA9555 nemá reset a po resetu MCU uprostřed přenosu může držet SDA v nule. IS31FL3236A resetuje I2C náběžnou hranou SDB.
- **TCA9555 INT:** INT se nuluje jen čtením vstupního registru portu, který ho vyvolal (0x00 pro P0, 0x01 pro P1) → při INT číst vždy oba. Přerušení během ACK se může ztratit, proto navíc pomalé pravidelné čtení (např. každých 20 ms) jako záloha. Debounce softwarově.
- **RP2040 krystal:** stejný obvod jako Pico (ABM8-272-T3, 2× 15 pF, 1k), přesto v boardu nastavit `PICO_XOSC_STARTUP_DELAY_MULTIPLIER 64` (jako řada desek třetích stran) – nic to nestojí a pokrývá pomalejší náběh při nízké teplotě.
- **TCA9555 robustnost:** INT obou čipů je spojený → při INT číst všechny 4 vstupní registry (0x20 i 0x21, port 0 i 1). Každých ~1 s zkontrolovat konfigurační registry (0x06/0x07 = 0xFF) a polaritu (0x04/0x05 = 0) a při neshodě přepsat (případ z fóra TI: „zaseknutý“ vstup byl přepsaná konfigurace).
- **MT6701 SSI:** zarovnání dat v rámci závisí na tom, na které hraně CLK se vzorkuje (knihovna SimpleFOC posouvá data o 1 nebo 2 bity podle platformy, na STM32 to dávalo nesmysly). PIO vzorkovat podle časování z datasheetu a vždy ověřit CRC.
- **W5500 kontrola linku:** po resetu přečíst VERSIONR (= 0x04, ověří SPI) a PHYCFGR (bit 0 LNK, bit 1 rychlost, bit 2 duplex). Fungující SPI neznamená fungující krystal ani analogovou část – link ukáže jen PHYCFGR.
- **IS31FL3236A:** po zapnutí je v softwarovém shutdownu (registr 0x00 = 0) → zapsat 0x00 = 0x01; změny PWM/LED registrů se projeví až zápisem 0x00 do 0x25. PWM 22 kHz (registr 0x4B = 1) kvůli pískání MLCC; po nastavení registrů SDB do 1; celkový proud LED držet pod limitem USB podle měření VSENSE_5V.
- **BOOTSEL pod panelem:** tlačítka BOOTSEL a RESET jsou po složení pod panelem. Firmware má umět přejít do bootloaderu po USB (`reset_usb_boot`, např. příkazem nebo kombinací kláves), aby se nový firmware dal nahrát bez rozebírání.
- **Adresy I2C:** IS31FL3236A 0x3C (U6) a 0x3F (U7), TCA9555 0x20 a 0x21. OLED SSD1306 má výchozí 0x3C, tedy kolizi s U6: případný displej na J3 přepnout na 0x3D (propojka na modulu).
- **Rozpočet proudu:** 3,3V část bere ~230 mA (W5500 ~130 mA, RP2040 ~40 mA, 2× MT6701 ~25 mA, zbytek drobnosti). Na LED zbývá z USB 2.0 portu (500 mA) ~250 mA, pojistka F1 drží 0,75 A. Všech 64 kanálů naplno by bylo ~1 A → firmware musí hlídat součet PWM × proud.

## Nezávislá revize zapojení (12. 11. 2026)

Celé zapojení prošlé z netlistu, sporné body ověřené v originálních datasheetech (TLV761 SBVS349D, HR911105A rev. A/2, WIZ850io V1.1 + referenční schéma W5500 v1.1, TCA9555 SCPS200E, IS31FL3236A Rev. I, MT6701 Rev. 1.9, Hardware design with RP2040, výkres Honyone TS5). Pinouty U2, U5, U6/U7, U8/U9, J4 a analogová část Ethernetu sedí. Změny po revizi:
- **TS5 (F1–F10):** footprint podle výkresu výrobce (LED 6 = + vlevo, 5 = − vpravo; původní zástupný footprint měl LED proti výkresu obráceně a bez značky, takže by klávesy F při zasunutí „podle pinu 1“ nesvítily), značka „+“ na desce u padu 6 (tlačítko jde zasunout i o 180° otočené, katodový vývod LED je na součástce barevně označený), otvory LED Ø0,9. Spínač zapojený jen přes úhlopříčné vývody 1 a 4.
- **Y1:** náhrada za nedostupný ABM8-272-T3.
- **Dokumentace:** skutečný úbytek LDO, polarita MODE u MT6701, poznámky pro firmware.

