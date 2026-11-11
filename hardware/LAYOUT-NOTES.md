# Poznámky pro rozmístění a routování desky

Sbírka požadavků z datasheetů a referenčních návrhů, které se projeví až na DPS. Doplňuje se při procházení schématu blok po bloku.

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
