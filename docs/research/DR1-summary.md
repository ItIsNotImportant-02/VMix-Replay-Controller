# Deep Research #1: shrnutí a co z něj bereme

Plný report z Gemini: [DR1-report-gemini.md](DR1-report-gemini.md). Tady je moje zpracování: co přebíráme, co je potřeba ověřit a co v reportu nesedí.

## Hlavní zjištění

1. **vMix TCP API (port 8099) je správná cesta.** Textový protokol ukončený `\r\n`, odpovědi `OK` / `ER` / délka dat. Umí `FUNCTION <název> <parametry>`, odběr událostí `SUBSCRIBE ACTS` a `SUBSCRIBE TALLY` a cílené dotazy `XMLTEXT` / `REPLAYXMLTEXT` přes XPath, takže ovladač nemusí stahovat celé XML.
2. **MIDI nestačí na páku.** Když je replay pozastavený, `ReplaySetSpeed` z MIDI jen změní rychlost, ale přehrávání nespustí. Ovladač musí poslat sekvenci `ReplayPlay` a hned `ReplaySetSpeed Value=x`. To přes nativní MIDI mapování nejde, přes TCP API ano.
3. **Feedback do LED:** od vMixu 29 existují aktivátory `ReplayLive`, `ReplayChannelA/B/AB`, `ReplayQuadMode` (posílá je `SUBSCRIBE ACTS`). Vybraná kamera, rychlost, IN/OUT a stav přehrávání se musí dotazovat pravidelně (cca 10 Hz) přes `REPLAYXMLTEXT`.
4. **Jog:** sčítat kroky enkodéru hardwarově a posílat souhrnně cca 30× za sekundu `ReplayJumpFrames Value=<delta>`, ne po každém kroku.
5. **Licence vMixu:** HD = 1 kamera v replayi, 4K = 4, Pro/Max = 8. Ovladač to neobejde.
6. **SKAARHOJ** mluví s vMixem přímo po Ethernetu (TCP), Switchblade RP400 je v podstatě MIDI a kvůli tomu potřebuje mezivrstvu (Central Control).

## Co v reportu nesedí nebo je přehnané

- „ESP32 a STM32 budou ztrácet kroky enkodéru“: STM32 má hardwarové čítače pro kvadraturní enkodéry a ESP32 má PCNT. RP2040/RP2350 s PIO je dobrá volba, ale ne jediná možná.
- „ReplaySetSpeed bere 0–1“: rozsah a chování je potřeba ověřit na reálném vMixu (prototyp 7.1).
- Kompozitní USB (MIDI + CDC) na Windows 11 má problémy hlavně s UAC2 audio. Pro nás to není podstatné, MIDI nepotřebujeme.
- Některé citace jsou slabé (fóra, obecné články), ale klíčové věci jsou z oficiální dokumentace vMixu (TCP API, Shortcut Function Reference).

## Návrh architektury (rozhodnutí 2.1)

**Doporučení: RP2040/RP2350 + Ethernet (W5500) přímo na vMix TCP API, USB-C pro napájení a servis.**

- Žádný software na vMix PC, stejně jako SKAARHOJ. Ovladač se po zapnutí sám připojí na IP adresu vMixu.
- USB-C dává napájení 5 V a sériovou linku (CDC) pro nastavení IP, test tlačítek, kalibraci a aktualizaci firmwaru.
- Záložní režim: pokud by Ethernet dělal potíže, stejná deska umí poslat stav přes USB malé aplikaci na PC (varianta B). Deska tedy nic neztratí.
- Firmware nebude parsovat celé XML, jen cílené `REPLAYXMLTEXT` dotazy a `ACTS` události.

**Devboard pro prototyp (7.1):** WIZnet W5500-EVB-Pico (RP2040 + W5500 na jedné desce) nebo Raspberry Pi Pico + modul W5500. Stejná kombinace pak půjde na naši desku.

**Senzory:** páka = magnetický snímač úhlu (AS5600 nebo podobný) + kalibrace po zapnutí; jog = enkodér čtený přes PIO.

## Co ověřit na prototypu

1. Páka: `ReplayPlay` + `ReplaySetSpeed` rozjede přehrávání plynule a bez škubání; filtr a mrtvá zóna kolem nuly.
2. Jog: plynulost `ReplayJumpFrames` při rychlém točení.
3. Latence `REPLAYXMLTEXT` dotazů při zatíženém vMixu.
4. Které stavy (kamera, rychlost, IN/OUT) se dají spolehlivě číst pro LED.
