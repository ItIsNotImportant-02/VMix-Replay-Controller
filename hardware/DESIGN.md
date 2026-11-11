# Návrh hlavní desky (schéma v1)

Podle [SPEC-v1](../docs/SPEC-v1.md) a layoutu [v0.5](../docs/layout/panel-layout-v0.5.pdf). Přiřazení pinů, tlačítek a LED kanálů: [PINMAP.md](PINMAP.md).

## Jak se schéma vyrábí

Schéma není kreslené ručně. Popis zapojení je v Pythonu ([tools/circuit.py](tools/circuit.py)) a skript [tools/gen.py](tools/gen.py) z něj vygeneruje KiCad 9 soubory (`*.kicad_sch`), knihovnu `lib/vrc.kicad_sym` a `PINMAP.md`. Každý pin má krátký vývod s globálním labelem nebo napájecím symbolem, takže se schéma dá číst i kontrolovat v KiCadu (ERC).

Proč takto: změna (např. přehození tlačítka na jiný kanál kvůli routování) je jeden řádek, všechny listy i tabulky se přegenerují a nic se nezapomene. Ruční úpravy v KiCadu by se při dalším generování přepsaly, proto se mění `circuit.py`.

Spuštění (KiCad 9 v Dockeru, stejně jako v cloudu):

```
docker run --rm -u $(id -u) -v $PWD/hardware:/hw -w /hw kicad/kicad:9.0 python3 tools/gen.py
docker run --rm -u $(id -u) -v $PWD/hardware:/hw -w /hw kicad/kicad:9.0 kicad-cli sch erc vmix-replay-controller.kicad_sch
```

## Bloky

| List | Obsah |
|---|---|
| Power and USB | USB-C (HRO TYPE-C-31-M-12), 2× 5,1k na CC, ESD USBLC6-2SC6, 27R v D+/D−, polyswitch 0,75 A, TVS 5 V, ferit → `+5V_LED`, LDO LDL1117S33R (SOT-223) → `+3V3`, dělič 5 V do ADC, testovací body |
| MCU | RP2040, 16 MB flash W25Q128JV, krystal 12 MHz, BOOTSEL a RESET, stavová LED, debug konektor (SWD + UART), rozšiřující konektor 2×8 |
| Ethernet | W5500 + RJ45 HR911105A s magnetikou, analogová část podle reference WIZnet, `+3V3A` přes ferit |
| LED drivers | 2× IS31FL3236A (QFN-44), VCC = 5 V, R_EXT 3,9k (max 19,5 mA/kanál), I2C pull-upy 2,2k na 3,3 V |
| Buttons | 18× PB26-13M RGB, 10× TS5 (ruční pájení) |
| Inputs | 2× TCA9555 (0x20, 0x21), společné INT |
| Sensors | 2× JST-PH 8pin pro destičky s MT6701 (páka, jog), sériové 33R, pull-upy 10k, RC filtr na analogový výstup |

## Rozhodnutí v návrhu

- **LDO místo AMS1117:** ST LDL1117S33R (LCSC C435835, skladem) má úbytek pod 0,3 V při 200 mA a je v SOT-223, takže se neuvaří (odběr 3,3 V větve ~200 mA, W5500 bere nejvíc). AP2112K v SOT-23-5 by při 0,3 W topil přes 70 °C nad okolí.
- **IS31FL3236A na 5 V:** výstupy OUTx snesou max. VCC + 0,3 V. Anody LED jsou na 5 V (modrá a zelená potřebují až 3,6 V), takže VCC budiče musí být 5 V. Logické vstupy mají pevné prahy (VIH 1,4 V), I2C na 3,3 V tedy funguje.
- **Senzory:** MT6701 má piny 6/7/8 sdílené mezi ABZ, SSI a I2C a pin MODE volí ABZ nebo I2C/SSI. MODE proto řídí MCU, aby šlo jog jednou naprogramovat přes I2C (rozlišení ABZ v EEPROM) a pak číst ABZ, a páku číst přes SSI. Analogový/PWM výstup jde do ADC jako záloha. Destičky senzorů jsou samostatný malý projekt (bude v `hardware/sensor-board/`).
- **Debug bez prototypu:** SWD + UART konektor, testovací body na všech napájeních a na I2C/INT/SDB, rezervní GPIO (GP10, 11, 22, 23, 24, 28) a 4 volné vstupy expandéru na konektoru J3 spolu s I2C (např. pro OLED později).
- **Firmware kompatibilita:** W5500 na stejných pinech jako WIZnet W5500-EVB-Pico (SPI0, GP16–21), takže jdou použít jejich knihovny beze změn.

## Co je ještě potřeba ověřit před objednávkou

1. **Footprinty PB26-13M a TS5** (vlastní, `lib/vrc.pretty`): rozteče vývodů podle popisu prodejce, ověří se vytištěním 1:1 a přiložením skutečného tlačítka.
2. **Footprint QFN-44 5×5 pro IS31FL3236A**: podle výkresu z datasheetu.
3. **LCSC čísla** označená `?` v `circuit.py` (pasivní součástky, krystaly, LDO, polyswitch, TVS, ferity, JST): doplnit a zkontrolovat skladovost a Basic/Extended.
4. **W5500 TOCAP a 1V2O**: podle datasheetu TOCAP 4,7 µF, 1V2O 10 nF (některé moduly mají opačně), ověřit v aktuálním datasheetu.
5. **Zátěžové kondenzátory krystalů**: 12 MHz X322512MSB4SI má CL 20 pF (27 pF), 25 MHz X322525MOB4SI má CL 12 pF (15 pF). Ověřit, že RP2040 rozkmitá krystal s CL 20 pF (alternativa: 12 MHz s CL 10 pF a 15 pF).
6. **Polarita pinu MODE u MT6701** (datasheet ji v textu neuvádí); deska to řeší tím, že MODE řídí MCU.
