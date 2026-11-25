# Poznámky pro rozmístění a routování desky

Sbírka požadavků z datasheetů a referenčních návrhů, které se projeví až na DPS. Doplňuje se při procházení schématu blok po bloku.

## Rozměr a konektory (layout v0.6 podle EVS LSM VIA, schváleno 12. 11. 2026)
- Deska 160 × 155 mm, tvar L: levý dolní roh chybí (výřez pro páku, 63 × 96 mm), v něm páka. Cena JLC se počítá z obdélníku 160 × 155. Výkres panelu 1:1: [panel-layout-v0.6.svg](../docs/layout/panel-layout-v0.6.pdf).
- Mezery mezi tlačítky: PB26 rozteč 19 mm (mezera 3,7 mm), F1–F10 rozteč 15,7 mm (mezera 6,5 mm).
- Zadní hrana: MENU, SHIFT, USB-C (J1), RJ45 (J4), CLEAR, ENTER. Místo programovatelných tlačítek LSM VIA jsou tu konektory.
- **Horní strana:** všechno, co osazuje JLC (včetně USB-C J1, rozteč 0,5 mm, ručně se špatně pájí), a tlačítka do panelu.
- **Spodní strana (ruční pájení):** RJ45 J4, konektory senzorů J5 (páka) a J6 (jog), hřebínky J2 (debug) a J3 (rozšíření). JLC Economic osazuje jen jednu stranu, takže na spodní straně nesmí být žádný díl z BOM. USB-C je nad deskou a RJ45 pod ní, otvory v zadní stěně krabičky jsou tedy v různé výšce.
- 4 montážní otvory M3 na GND; panel s tlačítky drží deska přes distanční sloupky.

## Napájení (blok 1)
- FB1 (BLM18PG121SN1D, 0603, 2 A) nese celý proud LED (až ~0,75 A při zásahu pojistky): široké cesty nebo polygon +5V / +5V_LED.
- U2 (SOT-223): tab = VOUT, pod ním měděná plocha jako chladič (ztráta ~0,35 W), C6/C7 přímo u výstupu.
- R3/R4 (27 Ω USB) blízko RP2040, U1 (ESD) blízko konektoru J1. D+/D− jako diferenciální pár 90 Ω, bez prokovů, pokud to jde.

## RP2040 (bloky 2 a 3), podle *Hardware design with RP2040*
- Každý 100nF kondenzátor co nejblíž svému napájecímu pinu (IOVDD ×6, DVDD ×2, USB_VDD, ADC_AVDD); 1 µF u VREG_VIN a VREG_VOUT.
- Krystal Y1 + C23/C24 + R10 těsně u XIN/XOUT, krátké cesty, pod krystalem souvislá GND, žádné signály pod ním.
- Flash U4 co nejblíž QSPI pinům, QSPI cesty krátké a podobně dlouhé.
- EP (pad 57) RP2040 na GND s více prokovy.

## W5500 + RJ45 (blok 4), podle datasheetu W5500 a referenčních schémat WIZnetu
- C48 (TOCAP 4,7 µF) co nejblíž pinu 20, C49 (1V2O 10 nF) u pinu 22.
- Krystal Y2 s C50/C51/R21 co nejblíž pinům 30/31, cesty krátké.
- R20 + R36 (12,4k EXRES1 jako 10k + 2,4k) u pinu 10, zem k AGND.
- Blokovací kondenzátory +3V3A u AVDD pinů, FB2 odděluje +3V3 a +3V3A.
- TX/RX páry (TXP/TXN, RXP/RXN) jako diferenciální 100 Ω, krátké, symetrické, terminace 49,9 Ω blízko W5500.
- Pod magnetikou/RJ45 nevést signály; stínění J4 na GND.

## IS31FL3236A (blok 5)
- Footprint podle land patternu z datasheetu; EP 2,45 mm má 5 prokovů 0,2 mm (kříž mezi okny pasty). Pod EP na vnitřní GND vrstvě souvislá plocha, čip ztrácí až ~1,5 W.
- C60–C63 (1 µF + 100 nF) těsně u VCC (pin 38), R40/R41 u R_EXT (pin 40), krátká zem.
- Výstupy OUTx vedou proud LED (max ~20 mA) – stačí běžné signálové cesty.
- Pozor na rotaci v CPL pro JLCPCB: pin 1 je v našem footprintu vlevo nahoře; JLC knihovna (EasyEDA) má pouzdro otočené o 90°. Před objednávkou zkontrolovat náhled osazení v JLCPCB.

## Rozmístění podpůrných součástek (v0.7, `tools/arrange.py`)
Pasivní součástky už nerozmisťuje automat „kam se vejdou“, ale `tools/arrange.py` podle pevných pravidel (pcb.py ho volá na konci `place`):
- Každý blokovací kondenzátor u svého napájecího pinu, napájecí plošku k pinu, GND plošku od čipu (tam patří prokov do GND vrstvy In1).
- RP2040 (otočení 0° jako v referenčním návrhu): flash vlevo nahoře u QSPI pinů 51–56 (CS/SD1/SD2 nejblíž), krystal Y1 vlevo dole u XIN/XOUT s R10 a C23/C24 přímo u krystalu, 1 µF na VREG_VIN/VREG_VOUT a 100 nF na DVDD nad horní stranou. USB D−/D+ (piny 46/47) jdou rovně nahoru k R3/R4, mezi nimi a QSPI nesmí nic stát. C16 (USB_VDD 48 + IOVDD 49) je kvůli místu o řadu výš, cesta k němu vede mezi C21 a USB párem.
- W5500 otočený o 180°: ethernetové piny 1–12 míří k RJ45. Vpravo od čipu v pořadí pinů EXRES, AVDD, RX pár (0R, 6,8 nF), AVDD, TX pár (0R, 49,9R); 49,9R RX a TCT/RCT součástky u pinů RJ45. Krystal Y2 vlevo u XI/XO, TOCAP/1V2O/AVDD kondenzátory v řadě nad čipem v pořadí pinů.
- Napájení v jednom směru: USB-C → ESD (U1) těsně za datovými piny, CC rezistory u CC pinů → F1 → TVS D1 a vstupní kondenzátory → LDO U2 (výstupní kondenzátory u tabu) a FB1 s kondenzátory +5V_LED.
- Expandéry: pull-up pole vedle čipu v řadě, I2C pull-upy R43/R44 u RP2040. LED budiče: 1 µF + 100 nF u VCC, R_EXT u pinu 40.
- Senzorové konektory J5/J6 (dole): sériové 33R, pull-upy a RC na výstupu ve dvou řadách nad konektorem v pořadí jeho pinů.
- Potisk: jen označení. Označení pasivních součástek je na F.Fab (v KiCadu je vidět), na potisku jsou u čipů, konektorů, krystalů, tlačítek a testovacích bodů. Pole LCSC/MPN se netisknou.

## Routování (v0.9, 25. 11. 2026): plně propojená deska
- **Stav:** **0 nepropojených spojů, DRC bez chyb** (clearance, zkraty, šířky, okraje, popisky). Zbývají jen varování:
  - `lib_footprint_mismatch`: u 15 pouzder byly zkráceny rohové značky na potisku, které zasahovaly do masky.
  - `extra_footprint`: montážní díry H1–H4 nejsou ve schématu.
- **Rozmístění** (`tools/flow/opt.py`, uložený stav `tools/flow/placement-v11.json`):
  - Pevné zůstaly konektory, rozměr desky, panelová tlačítka a díry.
  - Skupiny čipů (RP2040 s okolím, TCA9555 ×2, IS31FL3236A ×2, BOOTSEL/RESET, J2, J3) se posouvaly a otáčely simulovaným žíháním. Hodnotila se délka spojů a přeplnění kanálů.
  - Kanály LED driverů a porty expanderů se přiřadily znovu podle polohy. Mapování v `PINMAP.md` je aktuální, firmware se musí řídit jím.
  - Okolí RP2040 (součástky do 5,5 mm od středu) je roztažené o 12 %, tedy asi o 0,5 mm. Blokovací kondenzátory zůstaly u svých pinů.
- **Pravidla:**
  - Prokovy 0,5/0,25 mm (dříve 0,6/0,3), aby se vešly vývody kolem QFN.
  - Signály se routují na 0,15 mm a pak se rozšíří na 0,2 mm všude, kde to clearance dovolí.
  - Napájení: VBUS a +5V 0,6 mm (druhý pár pinů USB-C 0,45 mm), +3V3 a +1V1 0,25 mm.
  - Minimální šířka v DRC je 0,1 mm, kvůli zúžení u pinů jemných pouzder. JLC 4vrstvá deska zvládne 0,09 mm.
- **Šířky signálů (podíl délky):**
  - 0,2 mm: 67 %
  - 0,15 mm: 20 %
  - 0,11 mm: 1,7 %, jen krátké úseky mezi piny
- **Vrstvy:**
  - In1.Cu je celá GND, jeden kus.
  - In2.Cu nese signály a lití +5V_LED. Ostrůvky odříznuté signály jsou připojené cestou a prokovem.
  - F.Cu a B.Cu mají GND lití a prošívání.
  - 10 plošek (6 anod LED v tlačítkách, 4 GND) je připojeno k lití naplno, bez tepelných můstků. Jejich můstky vedly do odříznutého ostrůvku.
- **Postup** (skripty v `tools/flow/`, cesty v nich jsou z cloudového běhu):
  1. `vrun.sh`: schéma, umístění a DSN. In2 se exportuje jako signálová vrstva, ale s ponechanou rovinou +5V_LED, aby ji Freerouting neroutoval cestami.
  2. Freerouting 2.5 (Java 25), `-mp 40`.
  3. `vpost.sh`: grid router `leftover.py` s rip-upem, připojení ostrůvků +5V_LED (`lo3.py`, `link.py`), lití a prošívání (`final.py`).
  4. `vfull.sh`: rozšíření cest (`wloop.sh`: rozdělení na úseky po 1 mm, rozšíření na 0,2 mm, zúžení kolizních úseků, sloučení), potisk (`silk2.py`), DRC a kontroly (`chk.py`).
- **Zkoušené varianty:** 4 rozmístění × (0,2 / 0,15 mm, s rovinou i bez, prokovy 0,6 / 0,5 mm). Nejlepší ostatní varianty skončily na 2–3 otevřených spojích, vždy u spodní strany RP2040.
- **Potisk:**
  - Označení všech IO, konektorů, tlačítek a testovacích bodů je výška 1 mm.
  - Pasivní součástky mají označení 0,8 mm, pokud se vešlo do 0,8 mm od součástky (152 ze 171).
  - Zbylých 19 (např. C16, C25, R4, R7, R13) je jen ve vrstvě F.Fab, v osazovacím výkresu.
- **Známé kompromisy:**
  - XIN má 12,9 mm a dva prokovy: na B.Cu podbíhá síť XOUT/1k. XOUT má 3,2 mm, jen F.Cu. Pod B.Cu úsekem je souvislá GND rovina In1.
  - USB D− má 15,4 mm (přes In2, 4 prokovy), D+ 7,8 mm (přes B.Cu). RP2040 umí jen full-speed USB (12 Mb/s), kde rozdíl 8 mm (zhruba 50 ps) nehraje roli.
  - ETH RX pár: 13,9 a 11,2 mm, oba přes In2. Rozdíl 2,7 mm je pro 100BASE-TX v pořádku.
- **Montážní díry:** H1–H4 (M3, původní) a nově nahoře H5, H6 (M3, deska 41,0 / 4,5 a 71,0 / 5,0 mm) a H7, H8 (M2,5, deska 5,0 / 22,0 a 155,0 / 22,0 mm). Všechny mají prokovené mezikruží na GND a byly umístěné do míst bez cest, takže se nic nepřeroutovávalo.
- **Podpěry zespodu** (pro 3D tištěnou krabičku):
  - Volné plochy libovolného tvaru se zaoblenými rohy jsou na B.Silkscreen vyšrafované, obrys je i ve vrstvě User.1. Jsou to 3 plochy, celkem 6 800 mm².
  - Plochy vynechávají vývody THT dílů (+1 mm na pájku), plošky a součástky na spodní straně (+0,3–0,5 mm) a potisk. Od okraje desky jsou aspoň 1 mm.
  - Pokrývají vše do 12 mm od středu každého panelového tlačítka.
  - Kolem děr H1–H8 je v User.1 kroužek Ø 8 mm pro sloupek se šroubem.
  - Pro CAD: obrys desky, ploch a kroužků v `jlc/podpery.dxf`, body obrysů v mm od levého horního rohu (pohled shora) v `jlc/podpery-obrysy.txt`.
- **Výrobní data:** `jlc/` obsahuje Gerbery a vrtání (ZIP), BOM a CPL pro JLCPCB a náhledy `render_top.png` a `render_bot.png`.
