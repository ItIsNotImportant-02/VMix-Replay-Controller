# Deep Research #2 a #3: shrnutí a rozhodnutí

Plné reporty: [DR2-report-gemini.md](DR2-report-gemini.md) (EVS LSM), [DR3-report-gemini.md](DR3-report-gemini.md) (součástky).

## DR2: co bereme z EVS

- **Rozložení:** vlevo blok kamer (CAM A–F) a modifikátory (SHIFT), vpravo transport (IN, OUT, PLAY, LIVE…), vpravo dole **páka a hned vedle ní jog**. Pravá ruka drží páku a prsty točí jogem.
- **Barvy LED:** EVS používá jednoduchou logiku: **červená = aktivní / vybrané / hraje**, **zelená = uloženo / připraveno**, blikání = probíhající akce. RGB tlačítka to zvládnou a navíc můžeme rozlišit skupiny barvou.
- **Páka:** 0–100 % lineárně, drží polohu třením (žádná pružina), malá mrtvá zóna u nuly, play-on-move. S SHIFT druhý rozsah včetně zpětného chodu. VAR MAX omezí horní rychlost a roztáhne ji na celý zdvih.
- **Kalibrace:** podle reportu EVS kalibruje páku ručně v menu, ne při každém zapnutí. Navrhuji: kalibrace se uloží do paměti, nová kalibrace přes kombinaci (např. podržet SHIFT + LIVE a projet páku). Volitelně kalibrace po každém zapnutí, jak jsi chtěl.
- **Jog:** volně se točící, těžké kolečko bez aretace, krokuje po snímcích; FAST JOG násobí krok (výchozí 10×). Pohyb jogem během LIVE přepne do přehrávání ze záznamu.

### Co v DR2 nesedí

- Na několika místech radí MIDI aktivátory nebo HTTP API. Pro nás neplatí, máme TCP API (ADR-001).
- Názvy funkcí `ReplayMarkInRecordedNow`, `ReplayPlayEventToOutput`, `ReplayUpdateEvent`, `SetRateSlowMotion` musím ověřit v oficiální Shortcut Function Reference, část z nich je pravděpodobně nepřesná.
- „35 snímků na otáčku“ jogu je pochybné; bude to nastavitelné.

## Návrh 15 tlačítek (pracovní, doladíme v layoutu)

| Skupina | Tlačítko | vMix funkce (k ověření) | S SHIFT |
|---|---|---|---|
| Kamery | CAM 1–4 | `ReplayACamera1..4` | přepnout kameru v uložené události |
| Značky | IN | `ReplayMarkIn` | GOTO IN |
| Značky | OUT | `ReplayMarkOut` | uložit úpravu IN/OUT |
| Značky | −5 s | `ReplayMarkInOutLive Value=5` | −10 s |
| Transport | PLAY/PAUSE | `ReplayPlayPause` | |
| Transport | LIVE | `ReplayLive` | kalibrace páky (podržet) |
| Transport | FAST | přepíná FAST JOG (lokálně) | |
| Události | PREV / NEXT | `ReplaySelectPrevEvent` / `ReplaySelectNextEvent` | první / poslední |
| Výstup | TAKE | přehrát vybranou událost | |
| Výstup | PGM/PRV | `ReplaySwapChannels` | |
| Modifikátor | SHIFT | lokálně ve firmwaru | |

Oproti návrhu z reportu jsem nahradil UPDATE tlačítkem FAST (FAST JOG je na EVS základní funkce) a UPDATE dal na SHIFT + OUT.

## DR3: součástky

| Blok | Volba | LCSC | Poznámka |
|---|---|---|---|
| MCU | **RP2040** | C2040 (Basic) | Zralý čip, Basic díl, stejný jako na devboardu W5500-EVB-Pico. RP2350 by šel taky (chyba E9 je v novější revizi A4 opravená), ale nic navíc nepotřebujeme. |
| Flash | W25Q128JV (16 MB) | C97521 | |
| Ethernet | **W5500** + RJ45 s magnetikou HR911105A | C32843, C12074 | RJ45 je THT; připájí JLCPCB, nebo ty. |
| LED | **2× IS31FL3236A** (36 kanálů, konstantní proud, PWM 22 kHz, I2C) | C246443 | Bez multiplexu, takže tlačítka nebudou blikat v kameře. Proud nastaví jeden rezistor, bez rezistoru u každé LED. |
| Tlačítka | **TCA9555** I/O expandér s přerušením (I2C) | C140277 | 16 vstupů na kus; při více tlačítkách druhý kus. |
| Páka | **MT6701** magnetický snímač úhlu (14 bit) | C3003196 | Lepší a levnější než AS5600, rychlé SSI rozhraní. Nahrazuje můj původní návrh AS5600. |
| Jog | **MT6701** v režimu ABZ (až 1024 pulzů/ot.) | C3003196 | Kolečko na hřídeli v ložiscích, magnet na konci, žádný optický enkodér. Čte se přes PIO. |
| USB-C | 16pin konektor TYPE-C-31-M-12, 2× 5,1 kΩ na CC, USBLC6-2SC6, polyswitch | C165948, C7519 | |
| 3,3 V | LDO | | **AMS1117 z reportu nechci**: potřebuje ~1,1 V rezervu, z USB 5 V (může klesnout k 4,5 V) je to na hraně. Vyberu LDO s nízkým úbytkem při kreslení schématu. |
| Displej | volitelně OLED SSD1306 (I2C) | | rozhodneme v layoutu |

Odhad ceny podle reportu: zhruba 100 USD za 5 osazených desek (bez dopravy a cla).

## Co dál

1. Layout panelu 1:1 (krok 2.4): rozmístění 15 tlačítek, páky a jogu ve stylu EVS.
2. Ověřit názvy vMix funkcí v oficiální referenci (krok 2.5).
3. Pak specifikace v1 ke schválení (2.6) a schéma.
