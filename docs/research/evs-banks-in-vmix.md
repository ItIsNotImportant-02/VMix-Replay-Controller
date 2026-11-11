# EVS banky a F-klávesy ve vMixu

## Princip
Ovladač drží vlastní mapu `strana / banka / F-klávesa → ID události ve vMixu`. Do textu události zapisuje číslo klipu ve stylu EVS (např. `112A`), takže mapu lze po restartu obnovit z vMixu.

## Co vMix nabízí (Shortcut Function Reference, help29)
- Přehrání podle ID: `ReplayPlayEventsByID` (Value = seznam ID, Channel), `ReplayPlayEventsByIDToOutput`.
- Přehrání podle pořadí: `ReplayPlayEvent` (Value = číslo události, 0 = spodek seznamu).
- Text události: `ReplaySetLastEventText`, `ReplaySetSelectedEventText`, varianty `...TextCamera` a `Append...`.
- Seznamy: `ReplaySelectEvents1`–`ReplaySelectEvents20`, kopie/přesun do seznamu 0–19 (`ReplayCopyLastEvent`, `ReplayMoveSelectedEvent`).
- Výběr: `ReplaySelectFirstEvent`, `ReplaySelectNextEvent`, `ReplayScrollSelectedEvent` (−10…10).
- **Výběr události podle ID neexistuje.**

## Důsledky
- Vyvolat klip (cue bez přehrání) jde obejít: z XML zjistit pořadí události v seznamu a vybrat ji přes `ReplaySelectFirstEvent` + `ReplayScrollSelectedEvent`, nebo `ReplayPlayEventsByID` a okamžitě pauza. Ověří se na prototypu.
- Struktura XML událostí (`REPLAYEVENTSXML`, `http://127.0.0.1:8088/ReplayEventsAPI/`) není v dokumentaci popsaná. Potřebujeme vzorek z běžícího vMixu, abychom viděli názvy polí pro ID a text.
