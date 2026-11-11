# **Technical Analysis of Hardware Control Architectures for vMix Instant Replay: Imitating the EVS LSM Workflow**

## **Executive Summary**

* **Optimal Architecture Definition:** The most robust architecture for an EVS-style vMix replay controller is a microcontroller-based system (specifically the RP2040) functioning either as a direct Ethernet Transmission Control Protocol (TCP) client or a hybrid Universal Serial Bus (USB) Communications Device Class (CDC) serial device utilizing a lightweight host-PC companion application.  
* **API Selection:** Relying solely on vMix’s native Musical Instrument Digital Interface (MIDI) mapping introduces severe logic limitations for dynamic replay actions. Direct communication via the vMix TCP API (Port 8099\) allows the controller to dispatch exact, compound FUNCTION commands and handle asynchronous state feedback.  
* **Real-Time State Feedback:** While vMix version 29 introduced native activators for ReplayChannelA and ReplayLive, complex EVS-like feedback (clip timecode, exact playback speed, selected event metadata) requires continuous or event-driven polling of REPLAYXML and REPLAYEVENTSXMLTEXT via the TCP API.  
* **T-Bar Implementation:** Native MIDI mapping for T-bars fails to initiate playback when moved from a paused state due to how vMix evaluates shortcuts. Custom firmware must read the analog-to-digital converter (ADC), apply an Exponential Moving Average (EMA) filter, and transmit a compound TCP sequence (ReplayPlay followed by ReplaySetSpeed) to imitate the EVS LSM lever correctly.  
* **Jog/Shuttle Precision:** Microcontroller interrupts are insufficient for high-speed optical quadrature encoders, leading to missed pulses and sluggish scrubbing. The RP2040’s Programmable I/O (PIO) state machines must be utilized to track jog wheel movements entirely in hardware, ensuring frame-accurate scrubbing via ReplayJumpFrames.  
* **Protocol Framing:** The vMix TCP API utilizes a carriage-return/line-feed (\\r\\n) terminated text protocol. Controllers must parse length-prefixed binary/text payloads asynchronously, as vMix may push SUBSCRIBE ACTS or TALLY events at any moment.  
* **EVS vs. vMix Paradigm:** vMix operates on a dual-channel (A/B) unified timeline paradigm, which fundamentally differs from the EVS LSM multi-PGM and PGM/PRV playlist workflows. Custom firmware must bridge this gap by aggressively utilizing ReplayPlayEventsByID and ReplaySwapChannels shortcuts.  
* **Commercial Limitations:** Commercial solutions like the Switchblade RP400 rely on standard MIDI and often require third-party middleware (e.g., Central Control) to overcome vMix’s native shortcut limitations.  
* **The SKAARHOJ Paradigm:** SKAARHOJ panels bypass native limitations by utilizing their proprietary Raw Panel TCP protocol and a dedicated Blue Pill device core to talk directly to the vMix API.  
* **Microcontroller Superiority:** The Raspberry Pi RP2040 is superior for this application due to its PIO capabilities, dual-core architecture (separating the network/USB stack from UI polling), and robust TinyUSB support.  
* **Firmware Complexity:** Implementing a custom TCP client directly on the microcontroller via a W5500 physical layer (PHY) reduces PC-side software dependencies but vastly increases firmware complexity regarding Extensible Markup Language (XML) stream parsing and memory allocation.  
* **USB Composite Risks:** Attempting to build a USB composite device (MIDI \+ CDC \+ Custom HID) via TinyUSB on the RP2040 introduces known descriptor and endpoint conflicts in Windows 11 environments, necessitating careful driver and Errata 15 management.  
* **Analog Front-End Design:** Hall-effect sensors used for the T-bar must be heavily decoupled and filtered both in hardware and software to prevent ADC jitter from saturating the vMix network socket with microscopic speed updates.  
* **License Limitations:** Hardware controllers cannot unlock software limitations; vMix Pro or Max editions are strictly required to support the full eight-camera replay capability that an EVS operator would expect.  
* **Prototyping Imperative:** Before ordering printed circuit boards (PCBs), engineers must breadboard the quadrature PIO counter and the analog T-bar EMA filter to verify that the resulting TCP command stream yields visually smooth playback on the vMix output.

## **PART A: vMix Control Interfaces**

### **Comprehensive Analysis of External Control Vectors**

The vMix live production software ecosystem exposes a multifaceted array of vectors for external hardware and software control. Designing a broadcast-grade hardware controller requires a granular understanding of these interfaces, specifically regarding their latency characteristics, bidirectional feedback capabilities, processing overhead, and licensing restrictions.  
The **HTTP Web API** operates inherently over port 8088 and processes incoming requests formatted as standard Uniform Resource Locators (URLs) containing query strings1. While this interface boasts universal compatibility across nearly all programming languages and platforms, it relies on standard HTTP request-response lifecycles. This introduces intolerable transmission latency and overhead for high-frequency, continuous control inputs, such as those generated by a rapidly spinning jog wheel or a smoothly transitioning T-bar. Furthermore, the HTTP API is entirely stateless; it requires aggressive polling by the external controller to obtain system feedback, which concurrently taxes the network stack of the controller and the CPU of the vMix host machine1.  
The **TCP API**, designated to operate on port 8099, resolves the latency and overhead bottlenecks of the HTTP API by establishing and maintaining a persistent, raw socket connection1. This protocol is engineered specifically for embedded devices and custom controllers, boasting the lowest processing overhead while supporting asynchronous, bidirectional feedback. It allows devices to subscribe to real-time events, such as TALLY and ACTS (activators), making it the overwhelmingly superior choice for an EVS-style hardware controller1. It requires no auxiliary software running on the vMix PC, though enhanced security settings may necessitate authorization or local-network restriction within the vMix Web Controller settings5.  
**MIDI (Musical Instrument Digital Interface)** provides native, ultra-low latency input mapping and supports MIDI output to illuminate LEDs or move motorized faders via the vMix Activator subsystem7. However, vMix restricts MIDI input strictly to its predefined Shortcut evaluation engine. This creates a severe limitation for complex logic; a single MIDI Control Change (CC) message cannot conditionally trigger different macros based on the controller's internal state without convoluted workarounds. MIDI requires a direct USB connection to the vMix host, limiting physical deployment distances compared to Ethernet7.  
**X-Keys** devices, manufactured by P.I. Engineering, utilize native USB Human Interface Device (HID) protocols that are deeply integrated directly into the vMix source code9. X-Keys controllers support bidirectional LED control identically to MIDI and provide specialized configurations within vMix (such as the "JogWheel" type in the shortcut menu)11. Despite this tight integration, X-Keys solutions remain strictly bound to the operational limitations of the vMix Shortcut engine8.  
**Gamepads and Joysticks**, utilizing XInput or DirectInput libraries (e.g., Xbox controllers), are natively supported, primarily for Pan-Tilt-Zoom (PTZ) camera control and basic shortcut triggering12. They offer zero bidirectional feedback capabilities and are categorically unsuited for professional broadcast environments due to the total absence of visual state indicators (LEDs).  
**Scripting** is a powerful internal feature supported exclusively in vMix 4K, Pro, and Max editions13. It utilizes VB.NET code executed locally on the host machine. Scripts can be triggered via hardware controllers and allow for the execution of complex, conditional logic arrays that native shortcuts cannot achieve. However, scripts execute on the vMix host CPU and are processed in a sequential queue, making them highly unsuitable for real-time, continuous data streams like an analog T-bar position13.  
Third-party middleware applications, such as **Bitfocus Companion** or **Central Control**, function by abstracting the vMix TCP API15. Companion, for instance, utilizes a dedicated Studiocoast module that parses the massive vMix XML payload into discrete JSON variables, exposing them for complex logical evaluation and integration with Elgato Stream Deck hardware17. While powerful, these solutions mandate that middleware be running continuously on a host PC, introducing another potential point of failure during a live broadcast19.  
Regarding licensing limitations, custom hardware cannot bypass the restrictions imposed by the user's vMix tier. vMix Basic HD supports limited shortcuts and entirely lacks scripting6. Instant Replay functionality itself is strictly tiered: vMix HD supports one-channel replay, vMix 4K supports four-channel, and vMix Pro/Max supports up to eight-channel replay, which is the baseline requirement for an operator accustomed to a standard EVS LSM environment6.

### **TCP API Protocol Framing and Communication Architecture**

The vMix TCP API is structurally designed as a highly simplified text command-and-response architecture, intentionally eschewing fixed-length binary structures to ensure seamless compatibility with basic terminal interfaces and embedded microcontrollers1. Communication relies strictly on UTF-8 encoded strings terminated by a carriage-return/line-feed sequence (\\r\\n)1.  
Client requests must follow the format of \<command\> \<parameters\>\\r\\n. Responses from the vMix server follow a highly precise framing format: \<command\> \<status/length\> \[response\]\\r\\n. The status parameter is strictly limited to three distinct values: OK (indicating success), ER (indicating an error, followed by an error string), or an integer representing the exact byte length of the ensuing binary or multiline text payload1.  
An example session invoking a standard replay shortcut demonstrates this simplicity: FUNCTION ReplayPlay Channel=A\\r\\n Response: FUNCTION OK ReplayPlay\\r\\n1  
To construct a bi-directional controller with real-time feedback, the embedded device must subscribe to asynchronous events. The client dispatches SUBSCRIBE ACTS\\r\\n and SUBSCRIBE TALLY\\r\\n1. Once subscribed, the vMix host will actively push state changes over the socket without waiting for a polling request. A TALLY event response appears as TALLY OK 012100...\\r\\n, where the continuous numeric string represents the tally state (0=off, 1=program, 2=preview) padded sequentially to match the total number of inputs loaded into the vMix session1.  
Activator events (ACTS) are pushed in a slightly more verbose format: ACTS OK \<ActivatorName\> \<InputNumber\> \<Value\>\\r\\n. For example, ACTS OK Input 1 1\\r\\n indicates that the activator logic for Input 1 has transitioned to a positive (illuminated) state1. The return values are consistently mathematically mapped between 0 and 1; boolean states resolve strictly to 0 or 1, whereas continuous values (such as audio fader volumes) are represented as 32-bit floating-point numbers1.  
When extracting complex state data via Extensible Markup Language (XML) parsing, the TCP framing dynamically changes based on the specific request. A standard XML\\r\\n request yields a length-prefixed response to accommodate the massive data structure, which can easily exceed several megabytes in a large production1: XML 37\\r\\n \<vmix\>\<version\>27.0.0.76\</version\>\</vmix\>\\r\\n1  
To prevent an embedded microcontroller with limited Random Access Memory (RAM) from stalling while attempting to buffer and parse the entire XML document, the TCP API provides highly targeted XPath query commands: XMLTEXT and REPLAYXMLTEXT. If the data targeted by the XPath query is a single line, a standard OK response is returned directly: REPLAYXMLTEXT replay/@channelMode\\r\\n Response: REPLAYXMLTEXT OK AB\\r\\n23.  
However, if the XPath query returns multiline text, the protocol reverts to the length-prefixed binary format1. Because vMix events are entirely asynchronous, the microcontroller firmware must maintain a non-blocking ring buffer. A custom TCP client may receive a massive TALLY update exactly halfway between transmitting a FUNCTION command and receiving its OK response; failure to parse these interleaved packets will result in immediate firmware crashing or buffer overruns1.

### **Acquiring Real-Time Feedback for LED State Indications**

Replicating the tactile and visual precision of an EVS LSM remote necessitates precise, real-time LED feedback detailing which replay camera is currently selected, the exact playback state, the current lever speed, Mark IN/OUT timecode statuses, and the active A/B channel delegation.  
Historically, vMix architectures did not expose specific replay states via the Activator subsystem, forcing operators to visually monitor the graphical user interface to confirm their camera selections24. However, iterative updates (culminating in version 29\) introduced dedicated replay activators specifically requested by the broadcast community: ReplayLive, ReplayChannelAB, ReplayChannelA, ReplayChannelB, and ReplayQuadMode6. By sending the SUBSCRIBE ACTS TCP command, a hardware controller will receive an instantaneous boolean push notification whenever the operator toggles between Live and Recorded modes or changes the active channel delegation, allowing the corresponding physical LEDs to instantly illuminate1.  
Despite these critical additions, severe architectural gaps remain. State data regarding which specific camera angle (1 through 8\) is selected, the current playback speed multiplier (0.0 to 1.0), whether a specific event is actively playing or paused, and the exact timecode of Mark IN/OUT points are entirely omitted from the ACTS event stream23.  
To obtain this mission-critical state data, a custom controller must actively poll the vMix XML tree. The TCP API offers dedicated endpoints for this exact purpose: REPLAYXML and REPLAYEVENTSXML23. Utilizing the REPLAYEVENTSXMLTEXT XPATH command, the controller can query specific, highly granular attributes, such as REPLAYEVENTSXMLTEXT events/list\[1\]/@name to retrieve the active playlist string23.  
This polled data must be managed with extreme care to avoid saturating the microcontroller's network stack. An optimal firmware architecture will subscribe to ACTS for instant, event-driven boolean LED toggles (e.g., illuminating the LIVE button) while simultaneously utilizing a timed, non-blocking loop (e.g., executing at 10 Hz) to poll REPLAYXMLTEXT for continuous variable data. This polled data is then used to update an onboard OLED timecode display or illuminate the active camera angle button based on parsing the \<timecode\> and \<camera\> nodes nested within the replay XML payload2.

## **PART B: vMix Replay Architecture and Workflow**

### **Exhaustive vMix Replay Shortcut Function Reference**

The vMix Shortcut engine serves as the absolute primary conduit for executing replay control. All parameters accept standard URL-encoded strings via the TCP FUNCTION call. Certain commands target specific replay channels; if the channel parameter is omitted, the command defaults to the currently selected channel in the graphical user interface27.

| Function Name | Description & Parameters |
| :---- | :---- |
| **ReplayACamera1...8** | Instantly selects the specified camera angle for Replay Channel A. Parameters: None.28 |
| **ReplayBCamera1...8** | Instantly selects the specified camera angle for Replay Channel B. Parameters: None.28 |
| **ReplayCamera1...8** | Selects the camera angle for the currently active/delegated channel. Parameters: None.28 |
| **ReplayChangeDirection** | Toggles the timeline playback between forward and reverse states. Parameters: Channel (A, B, Current).28 |
| **ReplayChangeSpeed** | Adjusts playback speed relative to the current speed. Parameters: Value (Speed), Channel.28 |
| **ReplayFastForward / Backward** | Initiates high-speed playback (typically 1-30x). Parameters: Value (Speed multiplier), Channel.28 |
| **ReplayJumpFrames** | Scrubs the playhead forward or backward. Primarily used by hardware jog wheels. Parameters: Value (Frames, positive or negative), Channel.10 |
| **ReplayJumpFramesFastOn/Off** | Modifies the global ReplayJumpFrames behavior to jump by 1 second instead of 1 frame. Parameters: Channel.28 |
| **ReplayJumpToNow** | Jumps the recorded playhead instantly to the live timecode. Parameters: Channel.28 |
| **ReplayLive / Recorded** | Hard switches the output between Live passthrough and Recorded timeline playback. Parameters: None.28 |
| **ReplayLiveToggle** | Toggles between Live and Recorded states. Parameters: None.28 |
| **ReplayPlay / Pause** | Initiates playback or forcibly pauses the timeline. Parameters: Channel.28 |
| **ReplayPlayBackward / Forward** | Forces playback to initiate in a specific temporal direction. Parameters: Channel.28 |
| **ReplayPlayNext / Previous** | Skips the playhead to adjacent events in the active bin. Parameters: Channel.28 |
| **ReplayPlayPause** | Toggles the current playback state. Parameters: Channel.28 |
| **ReplaySetSpeed** | Sets absolute playback speed. This is the crucial command for T-bars. Parameters: Value (0-1 float), Channel.28 |
| **ReplayMarkIn / Out** | Drops an IN or OUT point at the exact current playhead position. Parameters: None.28 |
| **ReplayMarkInOut** | Creates an event based on a retroactive time block from the playhead. Parameters: Value (Seconds).28 |
| **ReplayMarkInOutLive** | Creates an event using a retroactive block from the live timecode, regardless of playhead. Parameters: Value (Seconds).28 |
| **ReplayMarkInOutLiveFuture** | Creates an event spanning into the future from the live timecode. Parameters: Value (Seconds).28 |
| **ReplayMoveSelectedIn/OutPoint** | Trims an existing event relative to its current marker. Parameters: Value (Frames), Channel.28 |
| **ReplayUpdateSelectedIn/OutPoint** | Trims the event exactly to the current playhead position. Parameters: Channel.28 |
| **ReplayCopy/Duplicate/DeleteEvent** | Modifies the event list targeting either LastEvent or SelectedEvent. Parameters: Channel (for Delete/Duplicate), Value (Event List 0-19 for Copy).28 |
| **ReplayExportLastEvent** | Initiates a render of the event to physical disk. Parameters: Value (Folder path), Channel.28 |
| **ReplayMoveLast/SelectedEvent** | Shifts an event to a completely different playlist bin. Parameters: Value (Event List 0-19).28 |
| **ReplayPlayAllEvents** | Plays a continuous highlight reel of the active list. Parameters: Channel.28 |
| **ReplayPlayEvent** | Forces playback of a specific event ID. Parameters: Value (Event Number 0-1000), Channel.28 |
| **ReplaySelectNext/PrevEvent** | Navigates the event list sequentially. Parameters: Channel.28 |
| **ReplayToggleLastEventCamera1..8** | Enables or disables specific multi-angles within a saved event. Parameters: None.28 |
| **ReplaySetLastEventText** | Injects metadata/tags into the XML tree for the event. Parameters: Value (Text).28 |
| **ReplaySetTimecode** | Jumps playhead to a specific absolute time. Format yyyy-MM-ddTHH:mm:ss.fff. Parameters: Value, Channel.28 |
| **ReplaySwapChannels** | Swaps Channel A and B delegations and state. Parameters: None.28 |

### **The Engineering Challenges of the T-Bar Lever and Jog Wheel**

Replicating the tactile precision and instantaneous software response of an EVS lever and jog dial requires overcoming significant logical hurdles inherent within the vMix shortcut evaluation ecosystem.  
**The Lever (T-Bar) Conundrum:** In an EVS LSM workflow, pushing the lever physically off the zero-detent instantly initiates video playback at a proportional slow-motion speed31. If a custom controller is mapped to vMix natively via MIDI, moving the physical T-bar triggers the ReplaySetSpeed function based on a 0-127 MIDI Control Change (CC) absolute value11. However, a severe architectural limitation exists: if the replay channel is currently paused, moving the T-bar changes the internal speed multiplier variable within vMix but **does not initiate playback**29.  
The broadcast community has exhaustively documented that attempting to map a secondary shortcut (such as ReplayPlay) to the exact same MIDI T-bar axis fails entirely. This failure occurs because the secondary shortcut either only fires upon reaching a highly specific numeric threshold, or relies on an unpredictable software evaluation order that drops velocity 0-triggers29.  
The only optimal solution requires the custom hardware to bypass vMix's internal MIDI mapping matrix entirely. The microcontroller firmware must sample the T-bar's analog voltage (ADC), mathematically map it to a floating-point value between 0.00 and 1.00, and manage a local state machine28. If the sampled speed is greater than 0, and the prior state registered as paused, the microcontroller must immediately transmit a compound TCP sequence: FUNCTION ReplayPlay\\r\\n followed instantaneously by FUNCTION ReplaySetSpeed Value=X\\r\\n28.  
**The Jog Wheel Conundrum:** Achieving frame-accurate scrubbing requires the integration of high-resolution optical quadrature encoders33. Native vMix MIDI maps jog wheels using relative increment/decrement signals (e.g., Note On 0x01 for rotating right, 0x7F for rotating left) assigned to the ReplayJumpFrames function with the JogWheel advanced setting enabled within the vMix UI10.  
Microcontrollers utilizing standard interrupt service routines (ISRs) to count these quadrature pulses will inevitably lose steps when the wheel is spun rapidly by a frantic operator. This missed-pulse phenomenon results in sluggish, disjointed, or inaccurate scrubbing on the vMix output35. Furthermore, transmitting individual TCP ReplayJumpFrames Value=1 commands for every single microscopic encoder tick will catastrophically saturate both the microcontroller's network buffer and the vMix API listener28.  
The definitive solution dictates that the hardware must utilize hardware-accelerated counting. Specifically, the Programmable I/O (PIO) state machines present on the RP2040 microcontroller must be leveraged to track quadrature edges autonomously, without requiring active CPU intervention35. A timed execution loop (e.g., running at 30 Hz) within the main firmware thread should read the accumulated delta from the PIO, clear the hardware counter, and dispatch a single, consolidated TCP command: FUNCTION ReplayJumpFrames Value=\<delta\>\\r\\n28.

### **Conceptual Paradigm Mapping: EVS LSM vs. vMix Architecture**

To design an intuitive controller for veteran EVS operators, an engineer must map EVS operational terminology and logic to vMix equivalents, explicitly acknowledging and bridging the architectural gaps in firmware.

| EVS LSM Concept | vMix Replay Equivalent | Architectural Gaps & Firmware Workarounds |
| :---- | :---- | :---- |
| **PGM/PRV Mode** | Channel A and Channel B | EVS utilizes hard-patched physical SDI outputs for separate Program and Preview monitors31. vMix maps Replay Channels A and B as internal, switchable software inputs41. A custom controller must utilize the ReplaySwapChannels TCP command to imitate the physical EVS flip28. |
| **Multi-PGM Mode** | ReplayMultiView / Routing | EVS allows completely independent, disjointed control of distinct physical outputs simultaneously40. vMix inherently forces both A and B channels into a single unified session timeline41. True Multi-PGM workflows require running entirely separate vMix instances. |
| **Live / Rec Train** | Live / Recorded Modes | Activating ReplayLive passes through the live camera input directly to the output buffer6. The custom controller should directly map the physical EVS "LIVE" button to this function28. |
| **IN / OUT / TAKE** | ReplayMarkIn, ReplayMarkOut | Directly maps to standard vMix functions30. EVS operators frequently utilize retroactive blocks; the firmware can map a button to ReplayMarkInOut Value=10 for an instant, predefined 10-second Take28. |
| **Cam A/B/C/D...** | ReplayACamera1..8 | EVS seamlessly swaps camera angles on the physical output port31. vMix supports up to 8 synchronous angles41. The firmware must map the controller's camera row buttons to dispatch ReplayCameraX28. |
| **Playlist / Bank** | Event Lists 1-20 | EVS organizes clips hierarchically (Banks, Pages). vMix utilizes 20 flat Event Lists6. A numpad on the controller can utilize ReplayMoveSelectedEvent to forcibly categorize clips into these bins28. |
| **Browse / Search** | ReplaySelectNextEvent | EVS features deep, metadata-driven searching via a secondary VGA monitor31. vMix is highly restricted to mouse/keyboard interactions in the UI for deep searching; the controller can only scroll the currently active list28. |
| **Lever / T-Bar** | ReplaySetSpeed | Requires complex custom firmware logic (described in detail above) to accurately mimic the EVS play-on-move functionality28. |
| **Jog / Shuttle** | ReplayJumpFrames | The outer shuttle ring can be mapped to continuous fast-forward/rewind32, while the inner jog wheel maps precisely to frame-jumps11. |

## **PART C: Existing Controllers and Prior Art**

### **The SKAARHOJ Architecture**

SKAARHOJ controllers, such as the Time Spin V1B, currently dominate the premium tier of vMix external hardware control45. These devices operate on the proprietary Blue Pill processing platform running a custom skaarOS Linux environment45.  
SKAARHOJ panels do not rely on a host PC intermediary to broker communication. They communicate directly over the Ethernet network using a proprietary TCP implementation called the Raw Panel Protocol, operating on port 992347. This protocol acts as a backbone, allowing the panels to act as highly intelligent servers or clients. For vMix integration specifically, SKAARHOJ utilizes either direct TCP API commands formatted by an internal "Device Core," or relies on a legacy proxy application (vMix Bridge/Proxy) running on the host machine to translate inputs50.  
Through this robust interface, SKAARHOJ exposes all 8 camera angles, maps jog/shuttle interactions to precision encoders, supports discrete clip/timeline modes, and fetches dynamic OLED labeling directly from the vMix XML stream53. Because SKAARHOJ entirely governs the logic on the powerful Blue Pill processor, they can successfully imitate the EVS lever logic by interpreting analog T-bar moves and dispatching the requisite compound TCP commands directly to vMix, bypassing MIDI entirely53.

### **Commercial and Software Alternatives**

The **Switchblade RP400** is a dedicated, 4-channel vMix replay controller featuring 29 dual-color backlit keys, a smooth-action T-bar, and a jog wheel54. It communicates via USB, LAN, or RS-232, but fundamentally acts as a standard MIDI device to the vMix host54. While cost-effective (averaging \~\$695) compared to EVS hardware46, its core reliance on standard MIDI subjects it directly to the vMix T-bar evaluation bugs previously outlined11. Consequently, operators are often forced to integrate third-party software like Central Control to intercept the MIDI signals and translate them into TCP API commands to achieve true broadcast functionality29.  
**Bitfocus Companion**, utilizing the Elgato Stream Deck hardware, relies on the open-source Studiocoast vMix module to execute robust replay logic15. Companion constantly polls the vMix XML tree in the background and exposes states as programmable variables (e.g., replay\_quad\_view, output\_X\_omt)17. While unparalleled for dynamic button grids (marking IN/OUT, triggering specific playlists), Stream Decks fundamentally lack physical T-bars and jog wheels, rendering them highly inadequate as a primary EVS replacement18.  
**X-Keys** hardware (specifically the XK-60 and the XK-12 Jog & Shuttle) utilizes native USB HID integration, allowing for immediate plug-and-play mapping within vMix8. vMix provides a specific "JogWheel" type configuration in the MIDI settings precisely for interpreting X-Keys hardware encoders11. However, these devices feel distinctly like lightweight computer peripherals. They lack the physical heft, the Hall-effect precision, and the mechanical lever detents required by an EVS operator operating on muscle memory8.  
The **JLCooper SloMo Mini** is a highly professional, rugged RS-422 and USB controller featuring a heavy, optically-encoded jog wheel58. While extremely precise and directly supported by vMix's legacy controller options, its high price tag (approximately \~\$1,823) and legacy serial-based form factor make it significantly less adaptable to modern, highly customized, IP-based vMix routing setups46.

### **DIY and Open Source Prior Art**

A review of community projects on GitHub utilizing ESP32, STM32, and Arduino platforms reveals that most function simply as USB MIDI keyboards or basic HTTP request generators60. Most DIY replay controllers fail to accurately replicate the EVS operational feel due to three recurring engineering oversights:

> 1. Utilizing standard interrupt-based code for high-resolution quadrature encoders, leading to erratic, skipped jogging35.  
> 2. Relying on generic carbon potentiometers for the T-bar, resulting in analog-to-digital (ADC) jitter that constantly sends microscopic speed updates to vMix, destroying playback smoothness63.  
> 3. Connecting via simple MIDI HID, thereby hitting the vMix ReplayPlay shortcut limitation and failing to achieve the play-on-move lever logic29.

## **PART D: Recommendations for Custom Hardware**

### **Architecture Comparison and Recommendation**

For a custom Printed Circuit Board (PCB) utilizing an EVS-style physical layout, the following micro-architectures were evaluated against the criteria of latency, mechanical smoothness, LED feedback, operator simplicity, and firmware complexity:  
**A. USB MIDI Class-Compliant Device:**

* *Strengths:* Absolute simplicity. Zero host drivers required. Native vMix mapping integration.  
* *Limitations:* Highly susceptible to vMix’s internal logic flaws (specifically the T-bar play issue). It is exceedingly difficult to extract complex XML feedback for OLED displays or advanced RGB LED states through standard MIDI SysEx7.

**B. USB CDC (Serial) \+ PC Companion App:**

* *Strengths:* The microcontroller simply sends raw hardware states (e.g., TBAR: 512, JOG: \-4) over Serial. A lightweight Python or C\# application on the PC handles the intense XML polling, evaluates complex logic, and dispatches TCP API commands to vMix locally.  
* *Limitations:* Requires the operator to launch and actively manage secondary software on the host PC during high-stress live shows, introducing a point of software failure.

**C. Direct Ethernet (TCP API via PHY/W5500):**

* *Strengths:* Zero host PC software required. Direct, raw socket access to vMix. Identical to SKAARHOJ's robust network topology47.  
* *Limitations:* Drastically increases firmware complexity. Parsing massive, unbounded XML responses on a microcontroller with limited RAM requires meticulous chunking and stream-parsing algorithms to prevent heap fragmentation1.

**D. USB Composite Device (MIDI \+ CDC via TinyUSB):**

* *Strengths:* Appears as a standard MIDI device for simple button mapping, while simultaneously exposing a virtual COM port (CDC) for advanced bi-directional XML feedback and compound commands.  
* *Limitations:* Extremely complex USB descriptor configuration. There are heavily documented driver issues with CDC+UAC2/MIDI composite descriptors in Windows 11 environments, often resulting in silent enumeration failures64.

**Primary Recommendation:** Approach **B (USB CDC Serial \+ Companion App)** or a highly-optimized **Approach C (Direct Ethernet)** are the only viable engineering paths for achieving true EVS LSM workflow parity.  
If minimizing PC-side dependencies is the absolute paramount requirement, **Approach C** using an RP2040 paired with a W5500 Ethernet module is highly recommended. The custom firmware must open a TCP socket to port 8099, transmit SUBSCRIBE ACTS, and use highly targeted REPLAYXMLTEXT XPATH queries rather than attempting to buffer the entire REPLAYXML payload1.

### **Microcontroller Selection**

The **Raspberry Pi RP2040** (or the recently released RP2350) is the definitive, uncompromised choice for this specific hardware application35.  
The primary justification is the **Programmable I/O (PIO)** subsystem. An EVS-grade jog wheel requires an optical quadrature encoder (often exceeding 200+ Pulses Per Revolution)33. At rapid spin rates, standard MCUs like the ESP32 or STM32 utilizing interrupt service routines (ISRs) will simply miss edges due to context-switching overhead35. The RP2040’s PIO state machines operate entirely independently of the CPU core, decoding quadrature signals in pure hardware flawlessly at megahertz speeds35.  
Furthermore, the RP2040 features native USB support backed by the highly robust TinyUSB stack66. TinyUSB allows for excellent CDC serial implementation66, which is critical if utilizing the host-PC architecture. It must be noted that Errata 15 on the RP2040 requires specific low-level workarounds within TinyUSB for bulk-in endpoints, which are gracefully handled in the most recent repository updates69.  
As an alternative, while the **ESP32-S3** possesses a hardware Pulse Counter (PCNT) capable of quadrature decoding34, its integrated WiFi stack introduces processing jitter, and its USB implementation is historically less stable for low-latency broadcast peripherals than the RP2040.

### **Risks and Breadboard Prototyping Priorities**

Before committing to a finalized PCB assembly via JLCPCB, the following high-risk engineering vectors must be thoroughly prototyped and validated on a breadboard:

> 1. **T-Bar ADC Jitter and Filtering:** An authentic EVS lever utilizes a high-precision Hall-effect sensor31. If connecting an analog linear Hall sensor (e.g., SS49E) to the RP2040's 12-bit ADC, inherent electrical noise will cause continuous state-change transmissions to vMix, saturating the TCP socket. The firmware engineer must implement and heavily tune an Exponential Moving Average (EMA) filter and a hard deadband (hysteresis) algorithm before finalizing the analog front-end layout63.  
> 2. **XML Polling Latency under Load:** If utilizing the Direct Ethernet architecture, establish a TCP connection to a heavily-loaded vMix session from the RP2040 and measure the exact latency of executing a REPLAYXMLTEXT query. The MCU must successfully handle the \\r\\n termination and extract the string payload without blocking the thread responsible for evaluating the jog wheel PIO.  
> 3. **The "Play-on-Move" Logic Validation:** Prototype a simple linear fader and verify that transmitting FUNCTION ReplayPlay followed instantly by FUNCTION ReplaySetSpeed Value=X over the TCP API flawlessly unpauses vMix and sets the correct speed without visual stuttering or frame dropping on the broadcast output28.

#### **Citovaná díla**

> 1. TCP API \- vMix, [https\://www\.vmix.com/help27/TCPAPI.html](https://www.vmix.com/help27/TCPAPI.html)  
> 2. Replay API \- vMix, [https\://www\.vmix.com/help30/ReplayAPI.html](https://www.vmix.com/help30/ReplayAPI.html)  
> 3. scoresight/docs/vmix.md at main \- GitHub, [https\://github.com/royshil/scoresight/blob/main/docs/vmix.md](https://github.com/royshil/scoresight/blob/main/docs/vmix.md)  
> 4. vMix User Guide, [https\://www\.vmix.com/help29/vMixUserGuide.pdf](https://www.vmix.com/help29/vMixUserGuide.pdf)  
> 5. Web Controller \- vMix, [https\://www\.vmix.com/help27/WebController.html](https://www.vmix.com/help27/WebController.html)  
> 6. Download vMix Live Video Production Software, [https\://www\.vmix.com/software/download.aspx](https://www.vmix.com/software/download.aspx)  
> 7. Activator Examples \- vMix, [https\://www\.vmix.com/help28/ActivatorExamples.html](https://www.vmix.com/help28/ActivatorExamples.html)  
> 8. Controller Options \- vMix User Guide, [https\://www\.vmix.com/help23/ControllerOptions.html](https://www.vmix.com/help23/ControllerOptions.html)  
> 9. Control Options \- vMix, [https\://www\.vmix.com/help29/ControlOptions.html](https://www.vmix.com/help29/ControlOptions.html)  
> 10. Controller Options \- vMix, [https\://www\.vmix.com/help28/ControllerOptions.html](https://www.vmix.com/help28/ControllerOptions.html)  
> 11. Advanced MIDI Shortcuts \- vMix, [https\://www\.vmix.com/help29/AdvancedMIDIShortcuts.html](https://www.vmix.com/help29/AdvancedMIDIShortcuts.html)  
> 12. PTZ control using shortcuts and joysticks \- vMix, [https\://www\.vmix.com/help27/PTZControlShortcuts.html](https://www.vmix.com/help27/PTZControlShortcuts.html)  
> 13. Switchblade Replay Systems, [https\://switchbladesystems.com/replay-systems/](https://switchbladesystems.com/replay-systems/)  
> 14. Web Controller \- vMix, [https\://www\.vmix.com/help28/WebSettings.html](https://www.vmix.com/help28/WebSettings.html)  
> 15. Studiocoast vMix module for Bitfocus Companion \- GitHub, [https\://github.com/bitfocus/companion-module-studiocoast-vmix](https://github.com/bitfocus/companion-module-studiocoast-vmix)  
> 16. StudioCoast vMix \- Central Control Wiki, [https\://wiki.centralcontrol.io/index.php?title=StudioCoast\_vMix](https://wiki.centralcontrol.io/index.php?title=StudioCoast_vMix)  
> 17. Releases · bitfocus/companion-module-studiocoast-vmix \- GitHub, [https\://github.com/bitfocus/companion-module-studiocoast-vmix/releases](https://github.com/bitfocus/companion-module-studiocoast-vmix/releases)  
> 18. \[BUG\] Search in Browse Actions does not follow sort order \#4155, [https\://github.com/bitfocus/companion/issues/4155](https://github.com/bitfocus/companion/issues/4155)  
> 19. vMix Companion Module- Page 3, [https\://forums.vmix.com/posts/t21290-vMix-Companion-Module/page3](https://forums.vmix.com/posts/t21290-vMix-Companion-Module/page3)  
> 20. companion/CHANGELOG.md at main · bitfocus/companion \- GitHub, [https\://github.com/bitfocus/companion/blob/main/CHANGELOG.md?fQuLL=cnbLiDbKLRJnXb](https://github.com/bitfocus/companion/blob/main/CHANGELOG.md?fQuLL=cnbLiDbKLRJnXb)  
> 21. System Requirements \- vMix, [https\://www\.vmix.com/help28/SystemRequirements.html](https://www.vmix.com/help28/SystemRequirements.html)  
> 22. vMix to EmberPlus Gateway. Control & Tally from vMix API ... \- GitHub, [https\://github.com/mattlamb99/vMix-EmberPlus](https://github.com/mattlamb99/vMix-EmberPlus)  
> 23. TCP API \- vMix, [https\://www\.vmix.com/help30/TCPAPI.html](https://www.vmix.com/help30/TCPAPI.html)  
> 24. ReplayToggleLastEventCamera1, 2, 3, 4 Activators \- vMix Forums, [https\://forums.vmix.com/posts/t31923-ReplayToggleLastEventCamera1--2--3--4-Activators](https://forums.vmix.com/posts/t31923-ReplayToggleLastEventCamera1--2--3--4-Activators)  
> 25. vMix 29 Preview Released\! \- vMix Forums, [https\://forums.vmix.com/posts/t33505-vMix-29-Preview-Released](https://forums.vmix.com/posts/t33505-vMix-29-Preview-Released)  
> 26. vMix 29 is available now\!, [https\://blog.vmix.com/vmix-29-is-available-now/](https://blog.vmix.com/vmix-29-is-available-now/)  
> 27. HTTP WEB API \- vMix, [https\://www\.vmix.com/help27/DeveloperAPI.html](https://www.vmix.com/help27/DeveloperAPI.html)  
> 28. [https\://www\.vmix.com/help27/ShortcutFunctionReference.html](https://www.vmix.com/help27/ShortcutFunctionReference.html)  
> 29. T-Bar roll replay with MIDI Controller does not work \- vMix Forums, [https\://forums.vmix.com/posts/t32283-T-Bar-roll-replay-with-MIDI-Controller-does-not-work](https://forums.vmix.com/posts/t32283-T-Bar-roll-replay-with-MIDI-Controller-does-not-work)  
> 30. Shortcut Function Reference \- vMix, [https\://www\.vmix.com/help28/ShortcutFunctionReference.html](https://www.vmix.com/help28/ShortcutFunctionReference.html)  
> 31. Live replay and highlights system \- LSM-VIA \- EVS, [https\://evs.com/products/live-replays-storytelling/lsm-via](https://evs.com/products/live-replays-storytelling/lsm-via)  
> 32. EVS Multicam LSM Operating Manual \- ManualsLib, [https\://www\.manualslib.com/manual/850166/Evs-Multicam-Lsm.html](https://www.manualslib.com/manual/850166/Evs-Multicam-Lsm.html)  
> 33. Esp32 or rp2040 precision encoder solution for high rpm \- Reddit, [https\://www\.reddit.com/r/embedded/comments/1lfgofe/esp32\_or\_rp2040\_precision\_encoder\_solution\_for/](https://www.reddit.com/r/embedded/comments/1lfgofe/esp32_or_rp2040_precision_encoder_solution_for/)  
> 34. Rudder Position Sensing to USB: Arduino Sensor Integration Guide, [https\://industrialmonitordirect.com/blogs/knowledgebase/rudder-position-sensing-to-usb-arduino-sensor-integration-guide](https://industrialmonitordirect.com/blogs/knowledgebase/rudder-position-sensing-to-usb-arduino-sensor-integration-guide)  
> 35. Optimize Arduino ISRs: Move Heavy Code Out of Interrupts, [https\://industrialmonitordirect.com/de/blogs/knowledgebase/arduino-isr-optimization-keep-interrupt-routines-minimal](https://industrialmonitordirect.com/de/blogs/knowledgebase/arduino-isr-optimization-keep-interrupt-routines-minimal)  
> 36. Optimize Arduino ISRs: Move Heavy Code Out of Interrupts \| IMD, [https\://industrialmonitordirect.com/blogs/knowledgebase/arduino-isr-optimization-keep-interrupt-routines-minimal](https://industrialmonitordirect.com/blogs/knowledgebase/arduino-isr-optimization-keep-interrupt-routines-minimal)  
> 37. Weekly Engineering Challenge: Can You Make a Robot Drive a, [https\://medium.com/@engasm89/weekly-engineering-challenge-can-you-make-a-robot-drive-a-square-and-come-back-to-where-it-started-f9025f6ff857](https://medium.com/@engasm89/weekly-engineering-challenge-can-you-make-a-robot-drive-a-square-and-come-back-to-where-it-started-f9025f6ff857)  
> 38. Read Motor Speed Better By Making The RP2040 PIO Do It, [https\://hackaday.com/2025/04/29/read-motor-speed-better-by-making-the-rp2040-pio-do-it/](https://hackaday.com/2025/04/29/read-motor-speed-better-by-making-the-rp2040-pio-do-it/)  
> 39. PICO RP2040 PIO Multi Encoder Solution \- Wokwi ESP32, STM32, [https\://wokwi.com/projects/401164763149178881](https://wokwi.com/projects/401164763149178881)  
> 40. 1/2/3 Pgm Modes (Press A Or Bfrom Main Menu); Secondary Menu, [https\://www\.manualslib.com/manual/850166/Evs-Multicam-Lsm.html?page=39](https://www.manualslib.com/manual/850166/Evs-Multicam-Lsm.html?page=39)  
> 41. Instant Replay \- vMix, [https\://www\.vmix.com/help27/InstantReplay1.html](https://www.vmix.com/help27/InstantReplay1.html)  
> 42. Settings \- vMix, [https\://www\.vmix.com/help28/ReplaySettings.html](https://www.vmix.com/help28/ReplaySettings.html)  
> 43. LSM-VIA Userman 1.1 \| PDF \| Command Line Interface \- Scribd, [https\://www\.scribd.com/document/688000897/LSM-VIA-userman-1-1-1](https://www.scribd.com/document/688000897/LSM-VIA-userman-1-1-1)  
> 44. Instant Replay \- vMix User Guide, [https\://www\.vmix.com/help24/InstantReplay1.html](https://www.vmix.com/help24/InstantReplay1.html)  
> 45. Time Spin \- User Manual \- skaarhoj, [https\://pid.skaarhoj.com/Manuals/SKAARHOJ\_manual-TIME-SPIN-V1B.pdf](https://pid.skaarhoj.com/Manuals/SKAARHOJ_manual-TIME-SPIN-V1B.pdf)  
> 46. Skaarhoj TIME-SPIN-V1B Time Spin Replay Controller \- Markertek, [https\://www\.markertek.com/product/ska-time-spinv1b/skaarhoj-time-spin-v1b-time-spin-replay-controller](https://www.markertek.com/product/ska-time-spinv1b/skaarhoj-time-spin-v1b-time-spin-replay-controller)  
> 47. TCP Device Core / UDP Device Core \- SKAARHOJ Wiki, [https\://wiki.skaarhoj.com/books/device-core-articles/page/tcp-device-core-udp-device-core](https://wiki.skaarhoj.com/books/device-core-articles/page/tcp-device-core-udp-device-core)  
> 48. rawpanel-lib/CLAUDE.md at master \- skaarhoj \- GitHub, [https\://github.com/SKAARHOJ/rawpanel-lib/blob/master/CLAUDE.md](https://github.com/SKAARHOJ/rawpanel-lib/blob/master/CLAUDE.md)  
> 49. skaarhoj device cores \- UniSketch TCP Client Overview \- Scribd, [https\://www\.scribd.com/document/453791805/DC-SKAARHOJ-RawPanel](https://www.scribd.com/document/453791805/DC-SKAARHOJ-RawPanel)  
> 50. vMix Proxy \| SKAARHOJ, [https\://www\.skaarhoj.com/vmix-proxy](https://www.skaarhoj.com/vmix-proxy)  
> 51. UniSketch \| SKAARHOJ, [https\://www\.skaarhoj.com/unisketch](https://www.skaarhoj.com/unisketch)  
> 52. Device: vMix \- GitHub, [https\://raw.githubusercontent.com/SKAARHOJ/Support/master/Manuals/DC\_vMix.pdf](https://raw.githubusercontent.com/SKAARHOJ/Support/master/Manuals/DC_vMix.pdf)  
> 53. vMix \- skaarhoj, [https\://www\.skaarhoj.com/integrations/vmix](https://www.skaarhoj.com/integrations/vmix)  
> 54. Switchblade Systems RP400 4-Channel vMix Replay Controller, [https\://www\.bhphotovideo.com/c/product/1846906-REG/switchblade\_systems\_swbs\_rp400\_rp400\_4\_channel\_vmix\_replay.html](https://www.bhphotovideo.com/c/product/1846906-REG/switchblade_systems_swbs_rp400_rp400_4_channel_vmix_replay.html)  
> 55. Switchblade RP400 \- 4-channel vMix Replay Controller with vMix Pro, [https\://usbroadcast.co/product/switchblade-rp400-4-channel-vmix-replay-controller-with-vmix-pro/](https://usbroadcast.co/product/switchblade-rp400-4-channel-vmix-replay-controller-with-vmix-pro/)  
> 56. Switchblade RP400 \- 4-channel vMix Replay Controller, [https\://magmaticmedia.com/products/switchblade-rp400-4-channel-vmix-replay-controller](https://magmaticmedia.com/products/switchblade-rp400-4-channel-vmix-replay-controller)  
> 57. Central Control Studio User Manual, [https\://centralcontrol.io/CentralControlManual.pdf](https://centralcontrol.io/CentralControlManual.pdf)  
> 58. Professional Control, Automation and Interfacing Products, [https\://jlcooper.com/\_brochures/\_Catalog/JLCooper\_Catalog.pdf](https://jlcooper.com/_brochures/_Catalog/JLCooper_Catalog.pdf)  
> 59. vMix User Guide, [https\://www\.vmix.com/help24/vMixUserGuide.pdf](https://www.vmix.com/help24/vMixUserGuide.pdf)  
> 60. trackawesomelist/content/2025/17/README.md at main \- GitHub, [https\://github.com/trackawesomelist/trackawesomelist/blob/main/content/2025/17/README.md](https://github.com/trackawesomelist/trackawesomelist/blob/main/content/2025/17/README.md)  
> 61. awesome-rainmana/README.md at master \- GitHub, [https\://github.com/rainmana/awesome-rainmana/blob/master/README.md](https://github.com/rainmana/awesome-rainmana/blob/master/README.md)  
> 62. eKuAI Link, [http\://eku.li/](http://eku.li/)  
> 63. How to get the best out of this forum \- IDE 1.x, [https\://forum.arduino.cc/t/how-to-get-the-best-out-of-this-forum/679966](https://forum.arduino.cc/t/how-to-get-the-best-out-of-this-forum/679966)  
> 64. tinyUSBv18 RP2040 on Windows 11 using UAC2 and CDC \#3215, [https\://github.com/hathach/tinyusb/discussions/3215](https://github.com/hathach/tinyusb/discussions/3215)  
> 65. Raspberry Pi Pico-series C/C++ SDK \| LaskaKit, [https\://www\.laskakit.cz/user/related\_files/raspberry-pi-pico-c-sdk.pdf](https://www.laskakit.cz/user/related_files/raspberry-pi-pico-c-sdk.pdf)  
> 66. Getting Started with Raspberry Pi Pico and TinyUSB. \- Medium, [https\://medium.com/cooking-with-raspberries/getting-started-with-raspberry-pi-pico-and-tinyusb-b45e0ab53783](https://medium.com/cooking-with-raspberries/getting-started-with-raspberry-pi-pico-and-tinyusb-b45e0ab53783)  
> 67. TinyUSB, [https\://docs.tinyusb.org/en/stable/](https://docs.tinyusb.org/en/stable/)  
> 68. Raspberry Pi Pico Arduino core, for all RP2040 and RP2350 boards, [https\://github.com/earlephilhower/arduino-pico](https://github.com/earlephilhower/arduino-pico)  
> 69. new-tinyusb/docs/info/changelog.rst at master \- GitHub, [https\://github.com/binhollc/new-tinyusb/blob/master/docs/info/changelog.rst](https://github.com/binhollc/new-tinyusb/blob/master/docs/info/changelog.rst)