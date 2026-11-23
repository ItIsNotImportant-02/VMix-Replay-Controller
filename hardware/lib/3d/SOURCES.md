# 3D modely (jen pro náhled a STEP pro Fusion, do výroby nejdou)

| Soubor | Díl | Zdroj | Zarovnání na footprint KiCadu |
|---|---|---|---|
| PB26-13M-RGB.step | tlačítko PB26 RGB | vlastní model z Fusionu (majitel projektu) | offset (-7.675, -7.675, 0) |
| HRO_TYPE-C-31-M-12.step | USB-C J1 | github.com/jfedor2/hid-remapper, custom-boards/v7/kicad/Type-C.pretty | rot X -90°, offset (-4.47, -3.645, 0) |
| HanRun_HR911105A.step | RJ45 J4 | github.com/Neumi/ethersweep, electronic_design/production/ethersweep405/3d_files | offset (4.45, -6.355, 0) |
| XKB_TS-1187A.step | SW1, SW2 | github.com/jrsteensen/OpenHornet, ECAD/lib/OH_3DModels | bez úprav |
| Honyone_TS5.step | TS5 F1–F10 (SW30–SW39) | github.com/eesakiii/SilverbackPCBs, SumoBot/2.1/Joysticks2.1/LIB („Honyone TS5-2 Button v1“) | offset (6.0, 2.16, -4.6) |
| JST_S8B-PH-SM4-TB.step | J5, J6 | github.com/issus/altium-library, STEP/Connector | offset (0, -1.35, 0) |

Zarovnání ověřené 23. 11. 2026: vývody modelu (z exportu VRML) proti padům footprintu, chyba do 0,01 mm
u vývodů, u SMD konektoru podle montážních plošek a čela těla (výkres na F.Fab).
