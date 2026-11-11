# Deep Research #1 – vMix API a hardwarové ovladače pro replay

**Jak použít:** zkopíruj celý blok níže do Gemini → Deep Research, nech ho doběhnout a výsledný report (ideálně export do Google Docs nebo celý text) vlož zpátky do vlákna. Prompt je záměrně v angličtině, protože skoro všechny zdroje (vMix dokumentace, fóra, GitHub) jsou anglicky a Gemini s nimi pak pracuje přesněji. Report si nech napsat anglicky, zpracuji ho já.

---

```text
ROLE & GOAL
You are a senior broadcast-engineering researcher. I am building a custom hardware replay controller for vMix (Windows live production software) that should feel and behave as close as possible to an EVS LSM remote (the EVS XT/XS slow-motion replay controller with its lever/T-bar, jog knob and colour-coded buttons). I will design my own PCB (KiCad, assembled by JLCPCB) with a microcontroller, RGB buttons, a lever (possibly motorised), a jog wheel, and write my own firmware. I need a deep, source-backed technical study of HOW a custom controller can control vMix — especially vMix Replay — and how existing commercial controllers do it.

Use current documentation (vMix 27/28/29 and newer if available). Cite every factual claim with a link. Prefer primary sources: vmix.com help pages (Developer API, TCP API, Shortcut Function Reference, Replay pages, Control Options / MIDI / X-Keys / Gamepad), official vMix forums, GitHub repositories, manufacturer manuals (SKAARHOJ, Elgato/Companion, X-keys, Switchblade, etc.). Clearly mark anything that is speculation or community workaround.

PART A — vMix control interfaces (be exhaustive and precise)
1. List every way an external device/software can control vMix: HTTP Web API (port, URL format), TCP API (port 8099: commands FUNCTION, XML, XMLTEXT, TALLY, ACTS, SUBSCRIBE, etc.), MIDI (input mapping AND MIDI feedback/output to light LEDs), X-Keys, gamepads/joysticks, keyboard shortcuts, scripting (VB.NET scripts), vMix Call / Companion / UDP if any. For each: latency characteristics, bidirectional feedback ability, whether it needs software running on the vMix PC, and licence-edition limitations (Basic HD / HD / 4K / Pro / Max).
2. Explain the exact TCP API protocol framing (request/response format, line endings, how to subscribe to tally and activator (ACTS) events, how XML state is returned, size framing of XML responses). Give example sessions.
3. How can a controller get real-time FEEDBACK (button LEDs showing state: which replay camera is selected, is replay playing, current speed, IN/OUT marked, live/recorded, event selected, A/B channel)? Which state is exposed via ACTS, which only via polling XML, and which is not exposed at all?

PART B — vMix Replay specifically
4. Produce a complete table of every Replay-related shortcut function in the current vMix Shortcut Function Reference (e.g. ReplayMarkIn, ReplayMarkOut, ReplayPlay, ReplayPause, ReplayLive, ReplaySetSpeed, ReplayChangeSpeed, ReplayJumpFrames, ReplaySelectChannel1/2, ReplayACamera1..8, ReplayPlayEvent, ReplayPlayAllEvents, ReplayFastForward, ReplayFastBackward, ReplaySetTimecode, ReplayToggleLive, ReplayCopyLastEvent, ReplayExport..., playlist/list functions, etc.). For each: parameters (Value, Channel, Input), what it does, and since which version.
5. How do people currently implement a "speed lever" (T-bar controlling playback speed 0–100%, and reverse) and a "jog wheel" (frame-accurate scrubbing) for vMix Replay? What are the known problems (e.g. T-bar via MIDI not working for replay speed, update rate limits, smoothness, the forum thread "T Bar roll replay with MIDI Controller does not work")? What is the best-known approach to achieve EVS-like smooth speed control and frame-accurate jog — which API calls, at what rate, absolute vs relative values?
6. Explain vMix Replay architecture relevant to an EVS-style workflow: recording cameras (A–H), channels A/B, events, event lists, playlists, live vs replay mode, timecode, "Replay Layout", multi-angle. Map EVS LSM concepts (Live/Rec, IN/OUT, Play, Lever, Jog/Shuttle, Cam A/B/C/D, Playlist, Take, Browse, Bank/Page, Clip/Save, F-keys) to the closest vMix equivalents and list gaps where vMix has no equivalent.

PART C — Existing controllers & prior art
7. SKAARHOJ: how do SKAARHOJ panels (Blue Pill / Reactor, Raw Panel protocol, UniSketch) talk to vMix — direct TCP API from the panel over Ethernet, or via a PC? What replay functions do they expose? Any SKAARHOJ "vMix replay" or EVS-style panel configurations?
8. Other relevant products and projects: Switchblade vMix replay controller (RP400), Bitfocus Companion + vMix module (what replay actions/feedbacks exist), Elgato Stream Deck + vMix, X-keys XK-24/XK-60 with jog-shuttle used for vMix replay, Contour ShuttlePRO, Loupedeck, Behringer/Akai MIDI controllers, and any open-source DIY vMix controllers on GitHub (ESP32/Arduino/RP2040 based). For each: connection method, protocol, feedback support, strengths/limitations, price.
9. Any vMix replay controller that specifically imitates EVS — what did they do, what limitations did they hit.

PART D — Recommendations for my hardware
10. Compare these architectures for a DIY controller and recommend one, with reasoning:
   (a) USB MIDI class-compliant device (vMix native MIDI mapping + MIDI feedback),
   (b) USB HID or USB CDC serial device + a small companion app on the vMix PC that talks to the vMix TCP API,
   (c) Ethernet device (e.g. microcontroller + W5500 or ESP32 with Ethernet PHY) talking directly to the vMix TCP API like SKAARHOJ,
   (d) USB composite (MIDI + CDC) or hybrid of the above.
   Criteria: latency, smooth lever/jog, LED feedback, setup simplicity for an operator, robustness during live shows, firmware complexity.
11. Which microcontroller families are commonly used for such controllers (RP2040/RP2350, ESP32-S3, STM32) and why; any known libraries for vMix TCP API or USB MIDI on those MCUs.
12. Risks and unknowns I should test early with a breadboard prototype before ordering a PCB.

OUTPUT FORMAT
- Executive summary (max 15 bullet points) with the recommended architecture.
- Sections A–D as above, with tables where useful (especially the Replay function table and the EVS→vMix mapping table).
- A list of all sources with URLs.
- Write in English. Be concrete: exact function names, ports, message formats, example commands.
```
