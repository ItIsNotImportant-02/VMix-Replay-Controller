# Tlačítka: PB26-13M RGB (Honyone)

Zdroj: popis produktu na AliExpressu (prodejce JC Electronic Components, položka 32999556341), přečteno 11. 11. 2026.
Varianta, kterou máš: **PB26-13M-B-WT-RGB-N (Triple Color RGB LED)**.

## Parametry

| Parametr | Hodnota |
|---|---|
| Rozměr čepičky | 15 × 15 mm (rám 15,3 × 15,3 mm) |
| Spínač | SPDT (COM, NO, NC), momentary, sám se vrací |
| Zatížení kontaktů | 0,4 VA / 28 V DC, přechodový odpor max. 100 mΩ |
| Zdvih / síla | 2,2 ± 0,5 mm, 200 ± 100 gf, slyšitelné cvaknutí |
| Životnost | mechanicky 200 000 cyklů, elektricky 30 000 cyklů |
| Pájení | THT, 350 °C max. 3 s |
| Vývody spínače | piny 1 (COM), 2 (NO), 3 (NC) v rozteči 5,08 mm, otvory Ø 1,2 mm |
| Vývody LED | L2+ (společná anoda), L1− (červená), L4− (zelená), L3− (modrá), rozteč 2,54 mm |

### RGB LED

| Barva | Úbytek napětí | Max. proud |
|---|---|---|
| R | 1,8–2,6 V | 20 mA |
| G | 2,8–3,6 V | 20 mA |
| B | 2,8–3,6 V | 20 mA |

LED je **se společnou anodou a bez vestavěných rezistorů** (prodejce varuje, že přímé připojení na baterii LED zničí).

## Co to znamená pro návrh

1. **LED se budí na straně katod (sink).** Každé tlačítko = 3 kanály. Při 30 tlačítkách je to 90 kanálů, takže potřebujeme LED budiče, ne piny MCU. Kandidáti: budiče s konstantním proudem (např. řada TLC59xx nebo IS31FL3xxx), které nepotřebují rezistory a umí PWM pro míchání barev. Konkrétní čip vybereme podle dostupnosti v JLCPCB (Deep Research #3).
2. **Anoda** může jít z 5 V (modrá a zelená potřebují až 3,6 V, s 3,3 V by nesvítily spolehlivě). Alternativa je multiplex po anodách (řádky) a budič na katodách (sloupce), což sníží počet kanálů i spotřebu.
3. **Rozpočet proudu:** stačí kolem 5–10 mA na barvu. 30 tlačítek × 3 barvy × 10 mA = 0,9 A v nejhorším případě (všechno bíle). To je víc, než dá USB 2.0 (500 mA), takže buď omezit jas firmwarem, USB-C s 1,5/3 A, nebo externí napájení. Patří do rozhodnutí 2.2.
4. **Spínač:** použijeme jen COM a NO. Čtení přes matici s diodami nebo přes IO expandéry / posuvné registry, rozhodne se podle počtu tlačítek.
5. **Footprint:** udělám vlastní footprint podle výkresu (15,3 × 15,3 mm, 3 piny spínače + 4 piny LED). Před objednávkou desky ho ověříme vytištěním 1:1 na papír a přiložením tlačítka, případně posuvkou.
6. Prodejce má i obdélníkovou verzi **PB26-13M-E 15 × 26 mm RGB**, kdyby se hodila na širší tlačítka jako na EVS (např. PLAY / LIVE).

## F1–F10: TS5 (Honyone), 9,2 × 9,2 mm, žlutá LED

Rozhodnuto 11. 11. 2026: řada F1–F10 (banky / klipy) použije 10 ks TS5, které už máš.
- 6 vývodů: 1–4 spínač (tact, SPST), 6 = LED +, 5 = LED −, rozteč 5,08 mm.
- LED bez vestavěného rezistoru, jednobarevná žlutá → jeden kanál budiče na klávesu.
- Zdvih jen cca 0,5 mm (membránový pocit), jiný pocit než PB26.
- Celkem LED kanálů: 15 × 3 (PB26 RGB) + 10 (TS5) = 55 → stačí 2× IS31FL3236A (72 kanálů).
