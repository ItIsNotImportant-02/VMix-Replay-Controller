# ADR-001: Komunikace ovladače s vMixem

- **Stav:** přijato, 11. 11. 2026
- **Rozhodnutí:** ovladač komunikuje s vMixem přímo po Ethernetu přes vMix TCP API (port 8099). Na desce bude MCU RP2040/RP2350 a Ethernet řadič W5500. USB-C slouží pro napájení 5 V a servisní sériovou linku (nastavení IP, kalibrace, test, aktualizace firmwaru).
- **Proč:** na vMix PC nemusí běžet žádný další software (jako u SKAARHOJ), páka může poslat `ReplayPlay` + `ReplaySetSpeed`, což přes MIDI nejde, a feedback do LED jde přes `SUBSCRIBE ACTS` a `REPLAYXMLTEXT`.
- **Zamítnuto:** USB MIDI (páka nerozjede pozastavený replay), jen USB + aplikace na PC (další bod selhání během show; zůstává jako záložní režim firmwaru).
- **Podklady:** [research/DR1-summary.md](../research/DR1-summary.md)
