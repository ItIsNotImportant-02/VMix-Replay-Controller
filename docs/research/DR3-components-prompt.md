# Deep Research #3 – komponenty a dostupnost v JLCPCB

Zkopíruj blok do Gemini Deep Research a výsledek vlož do vlákna. Může běžet souběžně s DR2.

```text
ROLE & GOAL
You are a senior hardware engineer experienced with JLCPCB PCBA (SMT assembly) and the LCSC parts catalogue. I am designing a USB-C powered (5 V, under 500 mA budget) broadcast replay controller PCB in KiCad, assembled by JLCPCB, with these requirements:
- MCU: Raspberry Pi RP2040 or RP2350 (with external QSPI flash, crystal), programmed over USB.
- Ethernet: WIZnet W5500 over SPI with an RJ45 jack with integrated magnetics, talking TCP to a PC on port 8099.
- About 15 through-hole RGB push buttons (common-anode RGB LED, no internal resistors; R 1.8–2.6 V, G/B 2.8–3.6 V, max 20 mA, I plan ~5–10 mA per colour) = ~45 LED channels with PWM colour mixing; switches are SPDT (I use COM+NO).
- A lever with a contactless magnetic angle sensor (AS5600 or similar) and a jog wheel with a quadrature encoder.
- Optional small OLED display (I2C/SPI) for timecode/status.
Cite sources and give LCSC part numbers (Cxxxxx) and whether each is a JLCPCB "Basic" or "Extended" part, current stock situation if visible, and approximate unit price. Prefer parts with high stock.

QUESTIONS
1. RP2040 vs RP2350 for this design: availability at JLCPCB, required support parts (flash, crystal, LDO), reference designs and KiCad-friendly references (e.g. Raspberry Pi "Hardware design with RP2040/RP2350" minimal design). Which one should I pick in late 2026 and why?
2. W5500 at JLCPCB: part number, RJ45 jacks with magnetics and LEDs available for assembly (e.g. HR911105A or equivalents), 25 MHz crystal, required passives; known layout pitfalls; reference schematics (W5500-EVB-Pico, WIZnet application notes).
3. LED driving for ~45 common-anode RGB channels: compare constant-current PWM LED driver ICs available at JLCPCB (e.g. TLC5947, TLC59711, TLC5955, IS31FL3236/IS31FL3237, IS31FL3731/IS31FL3741 matrix drivers, PCA9685 + transistors, or shift registers with resistors). Consider: number of channels, constant current vs. resistors, PWM resolution, interface (SPI/I2C), 5 V anode supply with 3.3 V logic, cost, availability, and a recommended topology (direct per-channel drive vs. multiplexing by anode).
4. Reading ~15–20 switches: GPIO direct vs. diode matrix vs. I/O expanders (e.g. MCP23017, TCA9555, 74HC165). Recommend one.
5. Lever sensor: AS5600 vs. AS5600L vs. MT6701 vs. TLE5012 vs. linear Hall (e.g. DRV5055) — accuracy, noise, interface, JLCPCB availability, magnet requirements (diametric magnet size and distance).
6. Jog wheel: affordable encoders suitable for a smooth, heavy, detent-free jog wheel (e.g. optical 100–600 PPR encoders from AliExpress, or magnetic encoders like AS5047/MT6835/AS5600 used as an incremental encoder). Which is the best way to get a smooth jog with frame-accurate steps?
7. USB-C power input: recommended USB-C receptacle at JLCPCB (16-pin, SMT/THT hybrid), CC resistors, ESD protection (e.g. USBLC6-2SC6), polyfuse, 3.3 V LDO or buck (current budget), and whether 5 V for LED anodes needs separate filtering.
8. Suggested complete preliminary BOM (table) with LCSC numbers and Basic/Extended classification, and an estimated assembly cost for 5 boards.

OUTPUT FORMAT
- Executive summary with the recommended part for each block.
- Comparison tables per question.
- Final BOM table (block, part, LCSC number, Basic/Extended, qty, approx price).
- Source list with URLs. Write in English.
```
