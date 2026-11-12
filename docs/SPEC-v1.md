# Specifikace v1: vMix Replay Controller (EVS-like)

Stav: **schváleno 11. 11. 2026** (krok 2.6). Podle ní se kreslí schéma.

## 1. Panel

Layout: [layout/panel-layout-v0.6.pdf](layout/panel-layout-v0.6.pdf) (schváleno 12. 11. 2026, rozložení podle EVS LSM VIA; nahrazuje [v0.5](layout/panel-layout-v0.5.pdf)), předloha: [layout/evs-lsm-reference-photo.jpg](layout/evs-lsm-reference-photo.jpg).

- Deska 160 × 155 mm (tvar L, páka v levém dolním rohu), panel o pár mm větší, bez displeje.
- 18× PB26-13M RGB (15 × 15 mm, SPDT, RGB se společnou anodou), 2 ks rezerva.
- 10× TS5 (9,2 × 9,2 mm, žlutá LED) pro F1–F10.
- Páka: bez motoru, drží polohu třením, zdvih cca 100 mm, magnetický snímač úhlu MT6701 na čepu.
- Jog: kolečko Ø 72 mm na hřídeli v ložiscích, magnet + MT6701 v režimu ABZ, bez aretace.

## 2. Elektronika

| Blok | Řešení |
|---|---|
| MCU | RP2040 + 16 MB QSPI flash (W25Q128JV), krystal 12 MHz |
| Síť | W5500 + RJ45 s magnetikou (HR911105A), TCP klient na vMix port 8099 |
| Napájení | USB-C 5 V (2× 5,1 kΩ na CC), polyswitch, ESD USBLC6-2SC6, LDO 3,3 V s nízkým úbytkem |
| LED | 2× IS31FL3236A (72 kanálů, konstantní proud, PWM 22 kHz), anody z 5 V přes filtr; využito 64 kanálů |
| Tlačítka | 2× TCA9555 (32 vstupů, přerušení), využito 28 |
| Páka | MT6701 přes SSI/SPI |
| Jog | MT6701 v ABZ režimu, dekódování přes PIO |
| Servis | USB CDC (nastavení IP, kalibrace, test, aktualizace firmwaru přes UF2 bootloader) |

Odběr: LED omezí firmware tak, aby celek nepřekročil 500 mA.

## 3. Komunikace

- Ethernet přímo na vMix TCP API (ADR-001). Po zapnutí se ovladač připojí k IP vMixu, pošle `SUBSCRIBE ACTS` a pravidelně (cca 10 Hz) se ptá na stav replaye přes `REPLAYXMLTEXT`.
- Při výpadku spojení LED zablikají a ovladač se znovu připojuje.

## 4. Chování ovládacích prvků

### Páka
- 0–100 % rychlosti, mrtvá zóna cca 2 % u nuly, filtr proti šumu.
- Play-on-move: pohyb z nuly pošle `ReplayPlay` a hned `ReplaySetSpeed`; návrat na nulu = pauza.
- SHIFT + TAKE (Lever) přepne druhý rozsah −100 % až +100 % (zpětný chod).
- Kalibrace uložená v paměti; nová kalibrace podržením SHIFT + RECORD a projetím páky. Volitelně kalibrace po každém zapnutí (nastavení v MENU).

### Jog
- Krokování po snímcích přes `ReplayJumpFrames`, posílá se souhrnně cca 30× za sekundu.
- FAST JOG (SHIFT + MARK) násobí krok (výchozí 10×).
- Pohyb jogem v LIVE přepne do přehrávání ze záznamu.
- V režimu BROWSE jog posouvá výběr v seznamu událostí.

### Banky a klipy (F1–F10)
- Ovladač si drží mapu strana / banka / F-klávesa → ID události ve vMixu; do textu události zapisuje číslo klipu ve stylu EVS (např. `112A`). Podrobně: [research/evs-banks-in-vmix.md](research/evs-banks-in-vmix.md).
- Volná F-klávesa po IN/OUT = uložit klip. Obsazená = vyvolat klip. LED: svítí = obsazeno, bliká = vybraný / hraje.
- SHIFT + F1–F10 = výběr banky, PAGE (SHIFT + PRV CTL) + F = výběr strany.

## 5. Mapa tlačítek

Funkce označené „ověřit“ nejsou potvrzené v oficiální referenci vMixu; ověří se na prototypu.

| Tlačítko | Funkce | vMix | Se SHIFT | LED |
|---|---|---|---|---|
| MENU | nastavení ovladače (IP, jas, kalibrace) | lokálně | | bílá při menu |
| SHIFT | modifikátor | lokálně | | svítí při držení |
| F1–F10 | uložit / vyvolat klip | `ReplayPlayEventsByID`, `ReplaySetLastEventText` | výběr banky | žlutá: obsazeno / bliká |
| CLEAR | zrušit výběr; s F-klávesou smazat klip | `ReplayDeleteSelectedEvent` | | |
| ENTER | potvrdit | lokálně | | |
| CAM A–D | kamera 1–4 | `ReplayACamera1..4` | kamera 5–8 (A'–D') | červená = vybraná |
| PLST | přehrát playlist (seznam událostí) | `ReplaySelectEvents<n>`, `ReplayPlayAllEvents` | Loop (ověřit) | |
| BROWSE | jog prochází události | `ReplayScrollSelectedEvent` | Insert = kopie do playlistu (`ReplayCopySelectedEvent`) | zelená v režimu |
| IN | značka IN | `ReplayMarkIn` | Goto IN (ověřit) | červená po označení |
| OUT | značka OUT | `ReplayMarkOut` | Goto OUT (ověřit) | červená po označení |
| TAKE | přehrát vybranou událost na výstup | `ReplayPlaySelectedEventToOutput` | Lever: druhý rozsah páky | |
| PLAY | přehrát 100 % | `ReplayPlay` | (Network: nevyužito) | červená při přehrávání |
| LAST CUE | skok na poslední událost | `ReplaySelectLastEvent` (ověřit chování) | (Goto TC: nevyužito) | |
| MARK | rychlý klip z živého obrazu | `ReplayMarkInOutLive Value=<s>` | Fast Jog | |
| RECORD | návrat do živého obrazu | `ReplayLive` | Return (`ReplayJumpToNow`) | červená v LIVE |
| PRV CTL | přepnutí ovládání kanálu A/B | `ReplaySwapChannels` (ověřit) | Page | zelená = PRV |

## 6. Otevřené body

1. Struktura XML událostí (ID, text): zjistí se na prototypu u vMixu.
2. Funkce „Goto IN/OUT“, Loop a chování A/B kanálů: ověřit v referenci a na vMixu.
3. Edice vMixu (HD 1, 4K 4, Pro/Max 8 kamer v replayi).
