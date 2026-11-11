# **Engineering a Replay Controller: Translating the EVS LSM Paradigm to a vMix Hardware Interface**

## **Executive Summary**

* **Architectural Translation:** Transitioning from the industry-standard EVS LSM (Live Slow Motion) environment to a vMix-based software architecture demands the precise translation of a closed-system hardware matrix into an open API network, necessitating careful consideration of tactile ergonomics, cognitive load, and command latency.  
* **Topographical Design:** The classic EVS LSM remote is structurally divided into highly specialized zones: a top-tier row of F-keys for bank navigation, a left-side operational block dedicated to camera routing and modifier states, and a right-side transport block anchored by the playback lever (T-bar) and jog wheel.  
* **Binary Illumination Logic:** To minimize cognitive friction during live broadcasts, EVS utilizes a strict bi-color LED framework. Red illumination strictly denotes an active, selected, or playing state, while green illumination denotes the passive existence of stored data (e.g., a saved clip). Flashing variants communicate transitional or destructive states1.  
* **Variable Speed Mechanics:** The playback lever natively operates on a 0–100% linear speed curve, but incorporates software-defined expansions such as the "Second Lever Range" (activated via a SHIFT modifier to yield \-100% to \+100% or \-200% to \+200% speeds) and flat step-detents for High Frame Rate (HFR) Super Motion cameras at 33% and 50%3.  
* **Hardware Calibration:** Absolute analog positioning requires a baseline. System calibration is manually triggered via the Operational Setup Menu (F4), establishing the absolute zero and maximum bounds of the analog potentiometer, while the VAR MAX software parameter dynamically limits the upper threshold to increase angular resolution3.  
* **Magnetic Encoder Integration:** For custom hardware fabrication, the AS5600 12-bit contactless magnetic encoder presents the optimal substitute for the legacy EVS potentiometer, communicating absolute angular position (0–4095) over I2C with zero mechanical wear, provided a diametric magnet is correctly aligned6.  
* **Scrubbing Dynamics:** The LSM jog dial is engineered for rapid, frame-accurate timeline navigation, traditionally outputting approximately 35 frames per physical revolution1. This is augmented by a configurable "Fast Jog" multiplier (defaulting to 10x) for rapid timeline traversal8.  
* **Live Breakaway:** Operator speed relies on the "Play-on-Move" and instant-search concepts. Nudging the lever from a paused state instantly engages playback proportional to the analog angle, while touching the jog wheel during a live feed instantly breaks the system into a recorded buffer state (Search mode)10.  
* **API Command Mapping:** Translating EVS operations to vMix requires bridging physical microcontroller inputs to vMix TCP/HTTP API commands. Emulating the EVS "PGM/PRV" (Program/Preview) dual-channel architecture requires complex scripting utilizing ReplaySwapChannels and ReplayPlayEventToOutput11.  
* **Minimum Viable Matrix:** Constraining the expansive EVS interface to a 15-button footprint requires aggressive prioritization of core live operations: explicit Camera selection, Mark In/Out, Quick Replay macros, Transport controls, Event Navigation, and a localized hardware SHIFT modifier to double the functional density.  
* **Mechanical Resistance:** Achieving the authentic tactile weight of the LSM remote necessitates the use of 15x15mm broadcast-grade short-travel illuminated switches, paired with a custom-damped torque hinge for the T-bar to simulate the exact analog friction of the EVS lever without relying on a spring-return mechanism.  
* **Feedback Loops:** A true hardware clone must utilize vMix Activators (MIDI feedback) to parse the state of the software and illuminate the physical RGB buttons, closing the loop between the vMix XML state and the physical controller's LED matrix13.

## **Part A: Physical Layout and Ergonomic Architecture**

### **The Classic EVS LSM Remote Topology**

The EVS LSM Remote Control Panel is the defining physical interface for live sports broadcasting. Its architecture is explicitly designed to be operated entirely by muscle memory, ensuring the replay operator never has to divert their eyes from the multiviewer monitors. The chassis is a heavily weighted unit, coming in at approximately 2.9 kg (6.3 lb) for the remote panel itself, which provides the necessary physical inertia to prevent the unit from sliding across a desk during aggressive, high-adrenaline lever pulls15. The overall form factor features a sloped console profile, angling the interface toward the user at approximately 15 to 20 degrees, which optimizes wrist ergonomics for prolonged operational stints.  
The panel is logically divided into strict functional zones. The uppermost section features the display interface. In the classic XT2 and XT3 generations, this is a monochrome or basic color LCD screen that displays operational menus, timecodes, and system states. In the newer LSM-VIA iteration, this has evolved into a fully integrated capacitive touchscreen, allowing operators to directly tap and swipe to manage playlists, assign metadata, and manipulate clip bins16. Immediately below the display sits a horizontal array of soft keys and the primary F-keys (F1 through F0). These F-keys represent discrete memory banks and pages where clips are saved and recalled1.  
The main deck of the remote is split vertically into two distinct hemispheres. The left hemisphere contains the camera selection matrix and modifier keys. The camera keys (CAM A through CAM F) are clustered together, allowing the operator's left hand to rest over the inputs and cut between synchronous camera angles seamlessly during a replay. Below this block reside the routing controls, such as the PGM/PRV (Program/Preview) toggle, the MULTI-PGM selectors, and crucial system modifiers like SHIFT, MENU, CLEAR, and ENTER.  
The right hemisphere is dedicated entirely to transport, marking, and speed manipulation. This zone is designed for the operator's right hand. A cluster of primary action buttons—RECORD, MARK, LAST CUE, PLAY, OUT, GOTO IN, GOTO OUT, and RETURN—surrounds the mechanical speed controls. The bottom right corner is anchored by the Jog Wheel, with the T-Bar Lever positioned immediately adjacent to its left. This specific spatial relationship is non-negotiable in replay hardware design; the operator's right hand must be able to spin the jog wheel with the fingertips while the palm or thumb rests on the lever for instantaneous speed transitions.

### **ASCII Diagram of the EVS LSM Panel Layout**

The following diagram illustrates the classic EVS layout, demonstrating the spatial grouping of the left-hand camera matrix and the right-hand transport cluster.  
\+-------------------------------------------------------------------------+  
\| \| \| \[ LCD / TOUCHSCREEN DISPLAY (Angle Adjustable) \] \| \| \| \| \[ F1 \] \[ F2 \] \[ F3 \] \[ F4 \] \[ F5 \] \[ F6 \] \[ F7 \] \[ F8 \] \[ F9 \] \| \| \| \| \+-- CAM BLOCK \---------+ \+-- TRANSPORT / MARK BLOCK \----------------+ \| \| \| \[CAM A\] \[CAM B\] \| \| \[RECORD\] \[ MARK \] \[ LAST CUE\] \[ PLAY \] \| \| \| \| \| \| \| \| \| \| \[CAM C\] \[CAM D\] \| \| \[GOTO IN\] \[GOTO OUT\] \[ OUT \] \| \| \| \| \| \| \| \| \| \| \[CAM E\] \[CAM F\] \| \| \[ LOOP \] \[ RETURN \] \| \| \| \+----------------------+ \+------------------------------------------+ \| \| \| \| \+-- MODIFIER & MENU \---+ \+-- SPEED & CUE BLOCK \---------------------+ \| \| \| \[SHIFT\] \[MENU\] \| \| \|\| \| \| \| \| \| \| \[ FAST \] \| \| .-------. \| \| \| \| \[CLEAR\] \[ENTER\] \| \| \[ JOG \] \| \| \| \| / \\ \| \| \| \| \| \| \| \| \| \| \| JOG \| \| \| \| \| \[BROWSE\] \[PLST\] \| \| \[ LIVE \] \| \| \| \| \| WHEEL \| \| \| \| \| \| \| \| \| \\ / \| \| \| \| \[PGM/PRV\] \| \| \|\| \`-------' \| \| \| \+----------------------+ \+------------------------------------------+ \| \+-------------------------------------------------------------------------+

### **Tactile Specifications and Physical Dimensions**

The tactile response of a broadcast controller is paramount. Standard broadcast interface panels utilize square keys measuring roughly 15x15 mm or 12x12 mm. These keys feature a short-travel, high-actuation-force mechanical switch (analogous to the NKK KP series of illuminated audio/video switches). The high actuation force prevents accidental triggers when an operator's hand brushes across the panel, while providing a definitive, audible mechanical "click" to confirm engagement without requiring visual verification. The spacing between keys is engineered to be approximately 3 to 5 mm, accommodating rapid, sliding finger movements across the matrix.  
The T-Bar (lever) operates on a travel arc typically ranging between 60 and 75 degrees. The jog wheel diameter is substantial, measuring approximately 60 mm, and is traditionally machined from anodized aluminum. It features a deep finger-dimple near the outer edge. The wheel is freely rotating and heavily damped; it does not utilize a spring-return mechanism, allowing an operator to impart angular momentum (a "flick") that will carry the wheel a short distance before the internal damping brings it to a precise halt.

### **Button Illumination and Color Logic**

In high-stakes live production, cognitive processing time must be minimized. Consequently, the classic EVS remote relies on a strictly binary color logic utilizing red and green LEDs embedded within the switches1.  
The state of an LED directly correlates to the status of the underlying media or hardware routing:

* **Red Illumination (Active/Destructive):** A key lights solid red when it is currently selected or live on air. For example, when CAM A is routed to the active program output, its button glows solid red1. The PLAY button illuminates red when media is actively rolling. If a key is flashing red, it communicates a destructive or critical action in progress, such as a networked clip being actively deleted across the XNet infrastructure1.  
* **Green Illumination (Passive/Stored):** Green indicates the existence of stored data or a ready state. An F-key (F1–F0) lights solid green to signal to the operator that a video clip has been saved to that specific memory register and is available for immediate recall1. If an F-key is flashing green, it signifies that a clip is actively being written or created at that register.  
* **System Modifiers:** Keys like CLEAR and MENU flash green to indicate that the remote panel has been unlocked or is currently in a configuration state, warning the operator that standard transport commands may be overridden17.

### **Table: EVS Button Attributes and Functionality**

| Button Name | LED Colour | LED State | System Function |
| :---- | :---- | :---- | :---- |
| **CAM A–F** | Red | Solid | Indicates the active camera angle currently routed to the Program (PGM) output1. |
| **F-Keys (F1–F0)** | Green / Red | Solid G / Flashing G | Solid Green: Clip exists in register. Flashing Green: Clip is currently being created. Solid Red: The associated clip is playing or queued1. |
| **PLAY** | Red | Solid | Initiates playback. Remains illuminated red while media is actively rolling. |
| **LIVE** | Red | Solid | Switches the output from a recorded buffer to the end-to-end (E2E) live camera feed. |
| **MARK (IN/OUT)** | Red | Solid | Registers precise timecode points in the buffer for clip creation. |
| **CLEAR / MENU** | Green | Flashing | Indicates the remote is in an unlocked setup or configuration state17. |
| **GOTO IN / OUT** | Red | Solid | Jumps the playhead to the previously marked IN or OUT point of the active clip. |

## **Part B: Lever (Playback Speed) Mechanics**

### **Speed Mapping, Detents, and Response Curves**

The EVS lever dictates the variable playback speed of the video server. The standard mechanical range of the lever maps to a linear 0–100% playback speed curve. When the lever is pulled fully toward the operator (0%), the video is in a hard pause or freeze-frame state. When pushed fully away from the operator (100%), the video plays at standard real-time speed1.  
However, the architecture supports complex software-defined parameter expansions. The most notable is the "Second Lever Range," which is activated by pressing the SHIFT modifier in conjunction with moving the lever. Depending on the server's configuration, this shifts the lever's mapping to either a \-100% to \+100% range (allowing seamless transition into reverse playback) or a high-speed \-200% to \+200% range for rapid searching3.  
Furthermore, the system accommodates High Frame Rate (HFR) Super Motion cameras. Because HFR cameras capture at multiples of standard frame rates (e.g., 3x or 4x), playing their footage at a 100% system speed results in slow motion. To output true real-time speed for these formats, the lever incorporates software-defined "flat steps" or detents. For SD Super Motion, this step occurs at 33% of the lever's travel; for HD Super Motion, the detent is located at 50%1. These detents allow the operator to instantly locate the real-time playback speed by feel.

### **Play-on-Move and Dead Zones**

A critical ergonomic feature is the "Lever Engage Mode" (frequently set to "Direct"). If the video is paused and the operator nudges the lever forward from the absolute 0% position, the system instantly initiates playback at a speed matching the analog percentage of the lever's physical angle. Conversely, pulling the lever back to the absolute zero stop issues an instantaneous hard pause10.  
To translate this to a DIY microcontroller, firmware must implement a small "dead zone" (typically 1–2%) near the 0% position. Analog potentiometers and even high-resolution digital encoders generate microscopic jitter. Without a dead zone, this noise would cause a paused frame to stutter or accidentally trigger playback. The microcontroller logic must dictate that if the delta of the lever's movement exceeds the dead zone threshold, a ReplayPlay command is fired, followed immediately by continuous SetRateSlowMotion updates.

### **Calibration Protocols and AS5600 Integration**

Because hardware components drift over time, the EVS system relies on manual calibration to set the absolute boundaries of the lever. This is not an automatic power-on sweep; it is initiated manually via the Operational Setup Menu (accessed by pressing SHIFT \+ MENU, then selecting F4 for lever controls). The routine requires the operator to move the lever to the physical minimum and maximum stops, registering the raw analog values as 0% and 100%5. Failure to calibrate can result in an inability to reach true 0% (preventing pausing) or maxing out below 100%.  
For a DIY hardware build, replacing a wear-prone analog potentiometer with an AS5600 12-bit contactless magnetic encoder is the optimal engineering choice. The AS5600 reads the absolute angular position of a diametrically magnetized N35-N52 magnet suspended 0.5 to 3mm above the silicon18. To emulate EVS calibration, the microcontroller should not simply read the RAW\_ANGLE (register 0x0C). Instead, the physical endpoints of the lever's 60-degree arc should be burned into the AS5600's ZPOS (Zero Position) and MPOS (Maximum Position) registers over I2C. This constrains the sensor's full 0–4095 digital output strictly to the mechanical travel of the T-bar, maximizing resolution. The firmware then queries the ANGLE register (0x0E), which benefits from the chip's built-in hysteresis and Automatic Gain Control (AGC), filtering out the jitter that plagues standard potentiometers7.

### **Mechanical Feel and Hardware Execution**

The mechanical feel of the EVS lever is defined by smooth, uniform friction. It does not utilize a spring-return mechanism; it must hold its position perfectly when released, allowing the operator to set a specific slow-motion speed (e.g., 42%) and remove their hand.  
Operators can dynamically alter the mechanical resolution of this friction arc using the PGM Speed/Var Max settings3. If an operator knows a particular replay sequence should never exceed 75% speed, they can configure the Var Max to 75%. This recalibrates the physical absolute maximum of the lever to equal 75% playback speed, effectively stretching the 0-75% speed range across the entire physical travel of the T-bar, allowing for incredibly granular, microscopic speed adjustments.

### **Table: Lever (T-Bar) Behavior Mapping**

| Feature | Classic EVS LSM Behavior | DIY vMix Translation (via AS5600 & API) |
| :---- | :---- | :---- |
| **Speed Range** | 0 to 100% (default linear curve). | Microcontroller maps AS5600 integer to a 0.0 to 1.0 float, sent via SetRateSlowMotion12. |
| **Reverse Play** | Shift+Lever expands range to \-100% / \+100%3. | Microcontroller detects localized SHIFT state, toggles ReplayChangeDirection and scales values. |
| **Play on Move** | Lever Engage Mode (Direct) initiates play from 0%10. | Firmware tracks AS5600 delta; crossing dead-zone threshold triggers ReplayPlay. |
| **Calibration** | F4 Operational Setup Menu bounds the min/max5. | Firmware calibrates physical endpoints into ZPOS/MPOS (0x01/0x02) registers over I2C7. |
| **Mechanical** | Friction hinge, holding position indefinitely. | DIY chassis requires a damped torque hinge to simulate fluid resistance without spring return. |

## **Part C: Jog Wheel and Operational Modes**

### **Jog Wheel Dynamics and Fast Jog Multipliers**

The LSM Jog dial is a high-resolution, absolute infinite-rotation optical or magnetic encoder designed for frame-accurate timeline scrubbing. In its standard operational mode, rotating the dial steps the video forward or backward frame-by-frame. The mechanical gearing and software mapping are calibrated so that a single complete physical revolution of the jog dial advances or rewinds the video by approximately 35 frames1.  
Unlike prosumer video editing hardware, the EVS jog wheel is not a shuttle ring (a spring-loaded concentric ring that dictates playback speed based on its deflection angle). It is strictly a positional encoder. To traverse massive amounts of recorded footage rapidly, the operator engages the FAST JOG modifier button. Pressing this multiplies the jog wheel's angular resolution by a configurable factor (ranging from 1x to 20x), with a standard industry default of 10x8.  
The jog dial is active at all times when the system is in a Play or Record state1. A critical operational dynamic occurs when the system is outputting a live feed: touching or moving the jog wheel instantly triggers a breakaway, kicking the system into a recorded buffer state (Search mode) and allowing the operator to immediately scrub backward in time to locate an event that just occurred on the live feed.

### **Core Operator Workflows**

The physical layout of the EVS is optimized to support tightly looped cognitive workflows. Replicating these sequences on a custom controller requires understanding the exact cadence of button presses:

* **(a) Mark IN/OUT and Save a Clip:** The operator observes an event on the live feed. They press MARK (or GOTO IN) to drop an In point into the timecode buffer. The video continues to roll; as the action concludes, they press OUT to establish the Out point. To commit this segment to memory, they strike an available, unlit F-key (e.g., F1). The F-key LED flashes green momentarily as the data is written, then resolves to solid green to indicate the clip is secured1.  
* **(b) Quick Replay from Live:** An unexpected event occurs on the live program feed (the LIVE key is illuminated). The operator instantly spins the jog wheel counter-clockwise. This immediately drops the system into Search mode, breaking away from the live feed. The operator scrubs back 5 seconds, locates the hit, and pushes the T-bar lever to 50%. The system immediately rolls the replay to the broadcast output at half-speed.  
* **(c) Camera Switching During Replay:** The EVS server natively records multiple synchronous camera angles. While a replay is actively rolling on CAM A, the operator can press CAM B. The server seamlessly cuts the video output to the identical timecode on Camera B without halting or interrupting the playback momentum.  
* **(d) Building and Playing a Playlist:** The operator presses the PLST key to enter Playlist Edit Mode. To build a sequence, they press the INSERT key followed by a rapid succession of saved F-keys (e.g., F1, F2, F3), dropping those clips sequentially into a timeline. Pressing PLAY rolls the compiled playlist to the output1.  
* **(e) PGM/PRV Modes and Second Channel Control:** In high-tier dual-output scenarios, the operator manages a Program (PGM) and Preview (PRV) monitor. They can cue up a clip on the PRV channel using the jog wheel. By pressing the PGM/PRV swap button, they push the cued clip to the live PGM output, freeing up the PRV channel to locate and cue the next angle while the first is rolling to air1.  
* **(f) Return to Live:** Once a replay sequence concludes, the operator strikes the LIVE button. The server instantly terminates buffer playback and snaps the output back to the real-time, end-to-end (E2E) camera feed1.

### **Table: Jog Behavior Analysis**

| Feature | Classic EVS LSM Behavior | DIY vMix Translation (via Rotary Encoder) |
| :---- | :---- | :---- |
| **Resolution** | \~35 frames per physical revolution1. | High-PPR (Pulses Per Revolution) encoder mapped to hardware interrupt pins. |
| **Action Mapping** | Frame-by-frame absolute scrubbing. | Microcontroller parses encoder ticks to fire ReplayJumpFrames (Value \= 1 or \-1)11. |
| **Fast Jog Mode** | Configurable 1x to 20x speed multiplier8. | A localized SHIFT state maps encoder ticks to fire ReplayJumpFrames (Value \= 10). |
| **Live Breakout** | Jogging during Live instantly enters Search mode. | Firmware detects jog pulse while in Live state, instantly triggering ReplayPlayPause to engage the buffer. |

### **Formulating the 15-Button Minimum Viable Controller**

Translating the expansive EVS console into a constrained DIY footprint of exactly 15 physical buttons (plus the lever and jog wheel) forces a severe prioritization of features. The design must sacrifice deep menu navigation, extensive clip-bank arrays, and complex playlist editing in favor of facilitating core, high-speed instant replay delivery.  
The essential 15-button matrix is prioritized as follows:

> 1. **CAM 1** (Explicit Angle Selection)  
> 2. **CAM 2** (Explicit Angle Selection)  
> 3. **CAM 3** (Explicit Angle Selection)  
> 4. **CAM 4** (Explicit Angle Selection)  
> 5. **MARK IN** (Set start of event timecode)  
> 6. **MARK OUT** (Set end of event timecode)  
> 7. **\-5 SECONDS** (Macro: jump back 5 seconds and set an IN point)  
> 8. **PLAY / PAUSE** (Primary transport toggle)  
> 9. **LIVE** (Return server output to real-time feed)  
> 10. **PREV EVENT** (Navigate up the event list)  
> 11. **NEXT EVENT** (Navigate down the event list)  
> 12. **TAKE PGM** (Instantly transition selected event/angle to output)  
> 13. **SWAP CAM** (Change the angle of the active replay)  
> 14. **SHIFT** (Hardware modifier to double the matrix logic)  
> 15. **UPDATE** (Commit modifications made to IN/OUT points)

*Design Justification:* This specific matrix guarantees that a solo operator can manage a standard 4-camera production, instantly create clips via the \-5 SEC macro, navigate the event bin, and execute precise playouts to the broadcast program feed without ever touching a mouse or keyboard. The inclusion of a localized SHIFT button, handled entirely by the custom microcontroller (e.g., an Arduino or Teensy), allows the hardware to dispatch alternate MIDI or HTTP API payloads. For example, pressing CAM 1 routes the angle to preview, but pressing SHIFT \+ CAM 1 could trigger the ReplayToggleSelectedEventCamera1 command to toggle that camera's inclusion in the final playlist.

### **ASCII Diagram: Proposed 15-Button Layout**

To effectively mimic the spatial ergonomics of the right-hand EVS transport cluster, the DIY chassis should anchor the jog wheel and lever at the bottom right. The 15 buttons are clustered in an arc, accessible by the thumb and fingers of the left and right hands resting in a natural, un-cramped posture.  
\+-------------------------------------------------------------+  
\| \| \| \[ CAM 1 \] \[ CAM 2 \] \[ MARK IN \] \[ MARK OUT\] \| \| \| \| \[ CAM 3 \] \[ CAM 4 \] \[ \-5 SEC \] \[ UPDATE \] \| \| \| \| \[ PREV \] \[ NEXT \] \[ SWAP CAM\] \[TAKE PGM \] \| \| \| \| \[ LEVER \] ( JOG )\| \| \[ SHIFT \] \[PLAY/PAUS\] \[ \| \] ( )\| \| \[ LIVE \] \[ v \] (\_\_\_\_\_)\| \| \| \+-------------------------------------------------------------+ *Industrial Design Notes:* The camera routing cluster (CAM 1-4) is grouped strictly on the left to preserve the left-hand operation established by the EVS matrix. The marking and transport controls are positioned adjacent to the lever and jog wheel. This allows the operator's right hand to maintain a grip on the T-bar while the thumb can extend to trigger an out-point or toggle playback. The SHIFT button is placed at the far bottom left to act as a pinky-actuated modifier, allowing chorded button presses across the entire board.

## **Part D: Translation to vMix Architecture**

### **Bridging EVS Logic with vMix API and Shortcuts**

The underlying architecture of vMix Replay operates on fundamentally different principles than the EVS SDTI/IP matrix. While EVS relies on writing media to absolute hardware memory registers (the F-keys), vMix utilizes a linear, software-based "Event List" paradigm. Replicating EVS workflows requires mapping the microcontroller's physical state changes to specific vMix TCP/HTTP API endpoints11.

* **Marking & Saving Integration:** vMix essentially combines the act of marking and saving into continuous, fluid actions. The API command ReplayMarkInRecordedNow jumps the playhead to the recorded buffer to allow the operator to establish an out point. Furthermore, the ReplayMarkInOut command (passing a value of 5\) instantly generates a 5-second retroactive clip without requiring distinct IN, OUT, and SAVE keystrokes21, streamlining the cognitive load.  
* **Lever Command Routing:** The microcontroller must capture the 12-bit absolute angle from the AS5600, normalize it to a 0.0 to 1.0 floating-point value, and push it to the vMix API via the endpoint: http\://\[IP\]:8088/api/?Function=SetRateSlowMotion\&Value=\[0.0-1.0\]12. Alternatively, this can be transmitted as a continuous MIDI Control Change (CC) message.  
* **Jog Wheel Emulation:** A standard digital rotary encoder must be mapped to the ReplayJumpFrames API command. Rotating the encoder clockwise sends Value=1; counter-clockwise sends Value=-1. When the hardware SHIFT state is active, the microcontroller modifies the payload to send Value=10, emulating the EVS FAST JOG function12.  
* **LED Feedback Loops (Activators):** To achieve the red/green binary illumination logic of the EVS, the DIY controller cannot operate in isolation. It must receive state data back from vMix. This is achieved using vMix Activators. Activators send MIDI note data back to the hardware when a specific state changes (e.g., lighting a button red when InputPlaying is true for the Replay input)13. The microcontroller firmware must be written to listen for these incoming MIDI notes and address the specific RGB LEDs underlying the 15x15mm switches.

### **Limitations and Workarounds**

While vMix is a highly capable software switcher, it cannot natively replicate every facet of the bespoke EVS hardware ecosystem.

> 1. **Networked Infrastructure:** vMix cannot replicate EVS's intricate XNet clip-pushing protocols, where clips are seamlessly transferred and modified across entirely separate server mainframes in real-time20.  
> 2. **Audio Routing:** Deeply granular audio track swapping on the fly (e.g., isolating a specific referee microphone track recorded on CAM C and binding it to the video of CAM A during a live replay) requires complex, external API scripting to achieve in vMix, whereas it is a native hardware matrix function on the EVS20.  
> 3. **Playlist Paradigm:** vMix handles Playlists differently. It plays sequentially down a pre-constructed Event List. It does not facilitate building a temporary, non-destructive timeline via an INSERT command from various unconnected memory banks in the same fluid manner as the EVS PLST workflow.  
> 4. **True PGM/PRV Rolling:** Replicating the dual-channel PGM/PRV synchronized rolling of EVS requires significant API trickery in vMix, relying heavily on the ReplaySwapChannels and ReplayPlayEventToOutput commands, as vMix does not treat its A/B replay channels as entirely autonomous SDI outputs in the same hardware sense23.

### **Table: EVS to vMix Function Mapping (15-Button Matrix)**

| Proposed Button | EVS Hardware Equivalent | vMix API / Shortcut Command | Operational Note & Translation Logic |
| :---- | :---- | :---- | :---- |
| **CAM 1** | CAM A | ReplayACamera1 | Routes Camera Angle 1 to the active preview/output channel11. |
| **CAM 2** | CAM B | ReplayACamera2 | Routes Camera Angle 2 to the active preview/output channel. |
| **CAM 3** | CAM C | ReplayACamera3 | Routes Camera Angle 3 to the active preview/output channel. |
| **CAM 4** | CAM D | ReplayACamera4 | Routes Camera Angle 4 to the active preview/output channel. |
| **MARK IN** | IN | ReplayMarkInRecordedNow | Jumps system into recorded mode and establishes an IN point11. |
| **MARK OUT** | OUT | ReplayMarkOut | Completes the current event and commits the timecode. |
| **\- 5 SEC** | (Custom Macro) | ReplayMarkInOut (Value \= 5\) | Instantly generates a 5-second clip; emulates common EVS operator macros21. |
| **PLAY/PAUS** | PLAY | ReplayPlayPause | Primary transport toggle; halts or resumes the playback buffer. |
| **LIVE** | LIVE | ReplayLive | Escapes the buffer and returns the system output to the real-time feed11. |
| **PREV** | F-Key / Scroll Up | ReplaySelectPreviousEvent | Navigates upward through the vMix Event List11. |
| **NEXT** | F-Key / Scroll Down | ReplaySelectNextEvent | Navigates downward through the vMix Event List. |
| **TAKE PGM** | PGM/PRV or TAKE | ReplayPlayEventToOutput | Instantly fires the selected event directly to the live broadcast output. |
| **SWAP CAM** | Swap | ReplaySwapChannels | Swaps the A/B playback channels; a necessary workaround for lacking true PGM/PRV routing. |
| **SHIFT** | SHIFT | *(Hardware Local Logic)* | Does not send a command to vMix; alters the payload of the other 14 buttons within the microcontroller firmware. |
| **UPDATE** | ENTER / CLEAR | ReplayUpdateEvent | Commits manual modifications made to IN/OUT points via the jog wheel. |

### **Source Matrix Integration**

The architectural specifications, mechanical tolerances, and ergonomic theories detailed in this report are synthesized directly from EVS operational documentation and broadcast engineering schematics. Key sources include the *Multicam LSM Operation Manual* (versions 10 through 14\) which establishes the Red/Green LED logic1, the 33%/50% super-motion detent programming, and the F4 Operational Setup menu calibration protocols1. The physical chassis weights (2.9 kg) and the evolution to the touchscreen interface are derived from the *LSM-VIA Installation and Configuration Manual* and XT-VIA technical references3.  
For the hardware fabrication of the custom T-Bar, the electrical engineering constraints of the AS5600 12-bit contactless magnetic encoder—specifically the requirement to write endpoints to the ZPOS/MPOS registers over I2C to bypass noise and utilize the ANGLE register (0x0E)—are standard implementational guidelines7. Finally, the translation of these physical inputs into network payloads relies on the official vMix Shortcut and TCP/HTTP API documentation, specifically targeting the Replay function subsets11.

#### **Citovaná díla**

> 1. EVS Multicam User Manual \| PDF \| Computer Keyboard \- Scribd, [https\://www\.scribd.com/document/190386618/EVS-Multicam-User-manual-7-00-44-English](https://www.scribd.com/document/190386618/EVS-Multicam-User-manual-7-00-44-English)  
> 2. Led Colors \- EVS Multicam LSM Operation Manual \[Page 18\], [https\://www\.manualslib.com/manual/1224276/Evs-Multicam-Lsm.html?page=18](https://www.manualslib.com/manual/1224276/Evs-Multicam-Lsm.html?page=18)  
> 3. EVS LSM User Manual Ver9 \| PDF \| Digital Technology \- Scribd, [https\://www\.scribd.com/document/246035404/EVS-LSM-User-Manual-Ver9](https://www.scribd.com/document/246035404/EVS-LSM-User-Manual-Ver9)  
> 4. MULTICAM \- Manuals.plus, [https\://manuals.plus/m/55ead8addc994ae2f8ea1c3d945a935025db006ef4939fa0bb7fa420849470e9](https://manuals.plus/m/55ead8addc994ae2f8ea1c3d945a935025db006ef4939fa0bb7fa420849470e9)  
> 5. EVS XT2+ Tech Ref Software Manual v10.03 PDF \- Scribd, [https\://www\.scribd.com/document/441270592/EVS-XT2-Tech-Ref-Software-Manual-v10-03-pdf](https://www.scribd.com/document/441270592/EVS-XT2-Tech-Ref-Software-Manual-v10-03-pdf)  
> 6. AS5600 Magnetic Rotary Encoder: Pinout, Wiring & Arduino Guide, [https\://www\.tinkered.ai/components/as5600](https://www.tinkered.ai/components/as5600)  
> 7. AS5600 Magnetic Encoder: Pinout, Features & Contactless Angle, [https\://www\.flywing-tech.com/blog/as5600-magnetic-encoder-pinout-features-contactless-angle-measurement/](https://www.flywing-tech.com/blog/as5600-magnetic-encoder-pinout-features-contactless-angle-measurement/)  
> 8. Configuration Manual \- XT3 12.05 \- AV Broadcast, [https\://www\.avbroadcast.fr/media/productfile/e/v/evs-xt3-manuel.pdf](https://www.avbroadcast.fr/media/productfile/e/v/evs-xt3-manuel.pdf)  
> 9. LSM-VIA Installation Guide 1.9 \| PDF \| Sudo \- Scribd, [https\://www\.scribd.com/document/879992891/LSM-Via-Installconfig-1-9-1](https://www.scribd.com/document/879992891/LSM-Via-Installconfig-1-9-1)  
> 10. XT3 Server Configuration Guide 11.02 \| PDF \| Web Application, [https\://www\.scribd.com/document/914539730/EVS-XT3-User-Manual-Version-11-02](https://www.scribd.com/document/914539730/EVS-XT3-User-Manual-Version-11-02)  
> 11. Shortcut Reference \- vMix User Guide, [https\://www\.vmix.com/help25/ShortcutReference.html](https://www.vmix.com/help25/ShortcutReference.html)  
> 12. Shortcut Function Reference \- vMix User Guide, [https\://www\.vmix.com/help25/ShortcutFunctionReference.html](https://www.vmix.com/help25/ShortcutFunctionReference.html)  
> 13. Activators \- MIDI Lights and Faders \- vMix User Guide, [https\://www\.vmix.com/help25/Activators.html](https://www.vmix.com/help25/Activators.html)  
> 14. Add/Edit Activator \- vMix, [https\://www\.vmix.com/help28/ActivatorsEdit.html](https://www.vmix.com/help28/ActivatorsEdit.html)  
> 15. EVS XT-VIA Server Manual 20.1 \| PDF \- Scribd, [https\://www\.scribd.com/document/893801136/XT-VIA-TechRef-20-1](https://www.scribd.com/document/893801136/XT-VIA-TechRef-20-1)  
> 16. Live replay and highlights system \- LSM-VIA \- EVS, [https\://evs.com/products/live-replays-storytelling/lsm-via](https://evs.com/products/live-replays-storytelling/lsm-via)  
> 17. EVS Nano Operation 12 05 B \| PDF \- Scribd, [https\://www\.scribd.com/document/272901420/EVS-Nano-Operation-12-05-B](https://www.scribd.com/document/272901420/EVS-Nano-Operation-12-05-B)  
> 18. AS5600 Magnetic Encoder: Absolute Position Sensing Explained, [https\://zbotic.in/as5600-magnetic-encoder-absolute-position-sensing-explained/](https://zbotic.in/as5600-magnetic-encoder-absolute-position-sensing-explained/)  
> 19. EVS Multicam LSM Operation Manual 14.02 \| PDF \- Scribd, [https\://www\.scribd.com/document/491929423/EVS-Multicam-LSM-Operation-manual-14-02](https://www.scribd.com/document/491929423/EVS-Multicam-LSM-Operation-manual-14-02)  
> 20. EVS Multicam LSM Operating Manual \- ManualsLib, [https\://www\.manualslib.com/manual/850166/Evs-Multicam-Lsm.html](https://www.manualslib.com/manual/850166/Evs-Multicam-Lsm.html)  
> 21. How to add shortcuts for the replay \-5 \-10 and \-20 buttons. \- vMix, [https\://www\.vmix.com/knowledgebase/article.aspx/243/how-to-add-shortcuts-for-the-replay-5-10-and-20-buttons](https://www.vmix.com/knowledgebase/article.aspx/243/how-to-add-shortcuts-for-the-replay-5-10-and-20-buttons)  
> 22. HTTP Web API \- vMix User Guide, [https\://www\.vmix.com/help25/DeveloperAPI.html](https://www.vmix.com/help25/DeveloperAPI.html)  
> 23. vMix User Guide, [https\://www\.vmix.com/help29/vMixUserGuide.pdf](https://www.vmix.com/help29/vMixUserGuide.pdf)  
> 24. Replay API \- vMix, [https\://www\.vmix.com/help30/ReplayAPI.html](https://www.vmix.com/help30/ReplayAPI.html)