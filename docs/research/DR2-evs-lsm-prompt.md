# Deep Research #2 – EVS LSM ovladač (layout, páka, jog, workflow)

Zkopíruj blok do Gemini Deep Research a výsledek vlož do vlákna.

```text
ROLE & GOAL
You are a broadcast replay specialist and industrial designer. I am building a DIY hardware replay controller for vMix that must look, feel and behave as close as possible to the EVS LSM remote controller (used with EVS XT/XS servers, including the newer LSM-VIA). I need a precise, source-backed description of the EVS LSM remote's physical layout and operator behaviour so I can design my own front panel (about 15 square 15x15 mm RGB push buttons, one lever/T-bar with a magnetic angle sensor, one jog wheel) and firmware. Cite every claim with a link; prefer EVS manuals (Multicam LSM operating manual, LSM-VIA user manual), EVS training material, operator videos and forum posts. Mark uncertain information clearly.

PART A — Physical layout
1. Describe the classic EVS LSM remote panel (and LSM-VIA if different): overall dimensions, number and arrangement of buttons (rows/columns), which button is where (F-keys, numeric/function keys, CAM A–F, IN, OUT, PLAY, LIVE/REC, GOTO IN/OUT, RETURN, MARK, PLST, BROWSE, BANK/PAGE, TAKE, SHIFT, MENU, CLEAR, etc.), the position of the lever relative to the jog wheel, and the small LCD/touchscreen. Provide a text diagram (ASCII grid) of the panel.
2. Button colours and illumination: which keys are which colour, which keys light up and when (e.g. PLAY lit while playing, LIVE lit in live mode, CAM keys lit for the selected camera), blinking states.
3. Physical dimensions where known: key size and spacing, lever travel length and angle, jog wheel diameter, panel slope.

PART B — Lever (playback speed lever) behaviour
4. How the lever maps to speed: range (e.g. 0–100 % or 0–200 %), whether there is a reverse direction, the response curve (linear vs. stepped vs. curved), detents or "notches" (e.g. at 100 %), dead zone near 0.
5. Play-on-move: what happens when the operator moves the lever from 0 while paused; what happens when the lever returns to 0 (pause vs. freeze).
6. Calibration: how and when the lever is calibrated on EVS (at power-on sweep? via menu?), what happens if not calibrated.
7. Mechanical feel: friction, spring return or not, the "VAR MAX" / speed limit settings, lever vs. preset speed buttons.

PART C — Jog and modes
8. Jog wheel behaviour: frames per detent/rotation, jog vs. shuttle mode switching, what the jog does in live mode vs. playback, acceleration.
9. Core operator workflows step by step: (a) mark IN/OUT and save a clip, (b) quick replay from live (e.g. "go back 5 s and play at 50 %"), (c) camera switching during replay (CAM A/B/C), (d) building and playing a playlist, (e) PGM/PRV modes and second channel control, (f) Return to live.
10. Which 15 functions are the most essential if an operator only has about 15 buttons? Prioritise them and justify.

PART D — Translation to vMix
11. For each essential EVS function from Part C, suggest the closest vMix Replay shortcut function(s) (e.g. ReplayMarkIn, ReplayMarkOut, ReplayPlay, ReplaySetSpeed, ReplayLive, ReplayACamera1..8, ReplayJumpFrames, ReplayMarkInOut, ReplayPlayEvent, ReplaySwapChannels) and note what cannot be reproduced.

OUTPUT FORMAT
- Executive summary (max 12 bullets).
- ASCII diagram of the EVS LSM panel layout.
- Tables: button list (name, colour, LED behaviour, function), lever behaviour, jog behaviour, EVS→vMix mapping.
- A proposed 15-button layout for my controller with lever and jog, as an ASCII diagram.
- Source list with URLs. Write in English.
```
