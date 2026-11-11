# **Advanced Hardware Architecture for a USB-C Broadcast Replay Controller**

## **Executive Summary**

The engineering of a broadcast-grade replay controller necessitates a rigorous focus on component latency, tactile feedback, signaling integrity, and strict power constraints. Operating within a strict 500 mA, 5 V USB-C power budget while driving \~45 independent LED channels, processing high-resolution quadrature feedback, and maintaining reliable TCP communication over Ethernet demands a highly optimized and mathematically verified hardware architecture.  
Based on extensive component analysis and the specific manufacturing capabilities of the JLCPCB Surface Mount Technology (SMT) assembly ecosystem, this report establishes a comprehensive design methodology for the printed circuit board (PCB) assembly. The recommended architecture leverages the Raspberry Pi RP2040 microcontroller1 for its maturity and predictable silicon behavior, intentionally bypassing the newer RP2350 due to unresolved hardware errata affecting GPIO inputs3. Ethernet connectivity is managed by the WIZnet W5500 over an 80 MHz SPI bus5, terminating in a HanRun HR911105A integrated magnetic RJ45 jack6 to minimize electromagnetic interference (EMI).  
For the human-machine interface, two ISSI IS31FL3236A constant-current LED drivers manage the common-anode RGB switches7, actively avoiding the camera-flicker and banding issues inherent in matrix-multiplexed topologies. Switch states are acquired via a TCA9555 I2C I/O expander, utilizing hardware interrupts to eliminate polling overhead and preserve CPU cycles8. Both the replay lever and the jog wheel employ the MT6701 contactless magnetic angle sensor10, providing 14-bit absolute accuracy and high-resolution ABZ quadrature outputs, drastically outperforming traditional optical encoders and the slower AS560011. Power is regulated by a robust AMS1117-3.3 linear low-dropout (LDO) regulator13, with the design strictly adhering to JLCPCB "Basic" and "Promotional Extended" components wherever possible to minimize feeder loading fees14.

## **1\. Microcontroller Subsystem: RP2040 vs. RP2350 Architecture**

The selection of the primary microcontroller unit (MCU) dictates the foundational architecture, software stack, peripheral allocation, and routing topology of the entire controller board. While both the Raspberry Pi RP2040 and its successor, the RP2350, offer exceptional Programmable I/O (PIO) capabilities, their silicon maturity, layout requirements, and current hardware bugs differ significantly.

### **1.1 Architectural and Performance Comparison**

The RP2040 (LCSC C2040) is a mature, dual-core ARM Cortex-M0+ processor operating at 133 MHz, equipped with 264 KB of SRAM2. It has been heavily adopted across the industry and is widely available at JLCPCB as a "Basic" component, meaning it incurs no \$3.07 feeder loading fee during assembly14.  
Conversely, the RP2350 (LCSC C39843328 for the QFN-80 package) offers a significant performance leap, featuring a dual-core Cortex-M33 architecture with an optional Hazard3 RISC-V core execution mode at 150 MHz1. The RP2350 doubles the internal SRAM to 520 KB and introduces a hardware Floating-Point Unit (FPU) alongside DSP-oriented instructions2. Both microcontrollers lack internal non-volatile application flash memory, necessitating an external Quad-SPI (QSPI) flash chip for code execution17.

| Feature / Specification | RP2040 (C2040) | RP2350 (C39843328) |
| :---- | :---- | :---- |
| **CPU Architecture** | Dual Cortex-M0+ @ 133 MHz | Dual Cortex-M33 / Hazard3 RISC-V @ 150 MHz |
| **Internal SRAM** | 264 KB | 520 KB |
| **Hardware FPU/DSP** | None (Software accelerated) | Single-precision FPU, DSP extensions |
| **Programmable I/O (PIO)** | 2 blocks, 8 state machines | 3 blocks, 12 state machines |
| **Advanced Security** | Basic | TrustZone, Secure Boot, OTP, TRNG |
| **JLCPCB Classification** | Basic (Highly Stocked, No Fee) | Extended (Subject to stock and \$3.07 fee) |
| **Silicon Maturity & Risk** | Fully patched, mature ecosystem | Susceptible to E9 GPIO Latching Erratum |

### **1.2 The E9 Erratum and Hardware Implications**

Despite the RP2350's superior computational headroom, early silicon revisions (including the A2 stepping) exhibit a critical hardware flaw documented as Erratum E93. This erratum involves increased leakage current when Bank 0 GPIO pads are enabled as digital inputs. The internal pull-down resistors (approximately 50 k$\Omega$) are too weak to overcome this leakage current, causing the pad voltage to artificially latch at approximately 2.0 V to 2.2 V4.  
For a broadcast controller reading numerous high-impedance switches, limit sensors, and external interrupts, reliable input states are mandatory. The E9 erratum forces hardware designers to either implement aggressive software workarounds—such as continuously toggling the GPIO input enable (IE) bit, temporarily disabling interrupts, and halting FreeRTOS task switching during every digital read—or to populate external physical pull-down resistors of 8.2 k$\Omega$ or lower on every affected input pin4.  
If the RP2350 were selected for this design, adding external pull-down resistors for the \~20 switch inputs and encoder channels would significantly increase the Bill of Materials (BOM) count, consume valuable PCB real estate, and inflate assembly costs.

### **1.3 External QSPI Flash and Support Circuitry**

Both MCUs execute code in place (XIP) via an external QSPI flash memory. The Winbond W25Q128JVSIQ (LCSC C97521) is an optimal choice, providing 128 Mbit (16 MB) of storage and supporting up to 133 MHz clock speeds25. To ensure stable boot sequences, a 10 k$\Omega$ pull-up resistor is required on the QSPI\_SS pin to prevent the MCU from dropping into USB mass storage bootloader mode erratically21.  
Timing accuracy for USB communication and PIO state machines relies on an external 12 MHz crystal oscillator (3225 package format, with 12 pF to 18 pF load capacitance)26.

### **1.4 Power Supply Topologies (LDO vs. Internal Regulators)**

The power supply architecture differs fundamentally between the two chips. The RP2040 features a built-in linear regulator that accepts 3.3 V and outputs the 1.1 V required for the internal digital core (DVDD)21. The RP2350, however, features a more complex five-pin internal switched-mode/linear regulator subsystem that requires specific external componentry, or alternatively, entirely bypassing it in favor of an external 1.1 V buck converter21.

### **1.5 Recommendation for Late 2026**

For a commercial design entering manufacturing in late 2026, the **RP2040 is the unequivocally recommended MCU**. The broadcast controller's processing requirements—primarily TCP offloading to the W5500, I2C polling, and PIO-based ABZ quadrature tracking—do not require Cortex-M33 DSP instructions or 520 KB of RAM. The RP2040 is a JLCPCB Basic part, guarantees predictable silicon behavior, avoids the BOM-bloat associated with the E9 erratum, and utilizes highly documented KiCad hardware minimal design references17.

## **2\. Ethernet Subsystem: WIZnet W5500 Integration**

Broadcast replay systems typically interface with software (such as vMix) or hardware switchers via local area networks. Reliable, low-latency TCP communication is mandatory. Relying on an MCU to handle software TCP/IP stacks (like lwIP) often introduces unpredictable latency spikes under heavy packet loads.

### **2.1 W5500 Architecture and SPI Direct Memory Access**

The WIZnet W5500 (LCSC C32843) is a hardwired TCP/IP embedded Ethernet controller that provides internet connection to embedded systems by utilizing a highly efficient Serial Peripheral Interface (SPI)27. It encapsulates the entire OSI model transport and network layers in silicon, supporting TCP, UDP, IPv4, ICMP, ARP, IGMP, and PPPoE27. It includes 32 KB of internal static RAM allocated for TX/RX buffering and supports up to 8 independent hardware sockets simultaneously27.  
Offloading the TCP/IP stack to the W5500 frees the RP2040 from managing packet fragmentation, ARP resolution, and TCP handshakes30. The SPI interface on the W5500 supports theoretical clock speeds up to 80 MHz5. To achieve minimal latency on TCP port 8099 (the standard communication port for vMix and similar broadcast APIs), the RP2040 should communicate with the W5500 using Direct Memory Access (DMA) over the SPI bus. Utilizing the RP2040's PIO state machines to drive the SPI interface further eliminates CPU bottlenecking during large packet transfers31.

### **2.2 RJ45 Magjack Integration**

Instead of routing discrete Ethernet transformers—which consume excessive PCB real estate and demand rigorous EMI shielding techniques—an integrated RJ45 magjack is highly recommended. The HanRun HR911105A (LCSC C12074) integrates the 1:1 isolation transformers, common-mode chokes, and link/activity LEDs required for 10/100Base-TX Ethernet directly into the connector housing6.

| Component Category | Recommended Part | LCSC Number | JLCPCB Classification | Estimated Function / Benefit |
| :---- | :---- | :---- | :---- | :---- |
| **Ethernet Controller** | WIZnet W5500 | C32843 | Extended | Hardwired TCP/IP, 32KB Buffer, 80MHz SPI |
| **Integrated Magjack** | HanRun HR911105A | C12074 | Extended | Built-in isolation magnetics, saves PCB space |
| **Clock Source** | 25.000 MHz Crystal | C521599 (varies) | Basic | Required for W5500 PHY PLL timing |
| **Termination Resistors** | 49.9 ![][image1] 1% Resistors | Generic 0603/0402 | Basic | RX/TX pair impedance matching |

### **2.3 PCB Layout Guidelines and 100-Ohm Differential Impedance**

The physical layer (PHY) layout between the W5500 and the HR911105A is the most critical routing task on the board to ensure packet integrity. The Ethernet standard specifies a 100 ![][image1] differential impedance for the transmit (TX) and receive (RX) pairs33.

* **Routing Topology:** The differential pairs (TXP/TXN and RXP/RXN) must be routed symmetrically, edge-coupled, and strictly length-matched35. Any mismatch in trace length introduces phase shifts that degrade the differential signal into common-mode noise. Acute routing angles (less than 135 degrees) must be avoided to prevent signal reflection35.  
* **Reference Plane:** A solid, uninterrupted ground plane must exist directly beneath the entire length of the differential pairs on the adjacent internal or bottom layer to provide a predictable, low-impedance return path35.  
* **Clearance and Crosstalk:** Maintain a clearance of at least three times the inter-pair spacing (the "3W rule")—ideally 5X—between the Ethernet pairs and any high-speed digital lines (e.g., the SPI bus or QSPI traces) to prevent capacitive coupling and crosstalk35.  
* **Center Tap Filtering:** The W5500 PHY requires specific termination passive networks. The center tap of the RJ45 magnetics must be decoupled to ground via a 0.1 ![][image2]F capacitor, and the TX/RX pairs require 49.9 ![][image1] (1% tolerance) pull-up resistors to the 3.3 V analog supply rail (AVDD) to dissipate common-mode noise37.  
* **Clock Isolation:** The 25 MHz crystal required to drive the W5500's internal phase-locked loop (PLL) must be placed as close to the XTAL pins as possible. A dedicated ground guard ring should surround the crystal circuitry to prevent the 25 MHz fundamental frequency and its harmonics from coupling into the sensitive analog PHY traces38.

## **3\. Broadcast Tactile Interface: LED Driving Topology**

A replay controller relies heavily on visual feedback; buttons must illuminate brightly to indicate active cameras, recording states, and transition readiness. Driving \~15 SPDT push buttons featuring common-anode RGB LEDs results in \~45 discrete LED channels. The 5 V, 500 mA power budget strictly governs the driving topology and efficiency requirements.

### **3.1 Multiplexing vs. Constant-Current Direct Drive**

Traditional approaches to driving high-channel-count LEDs involve matrix multiplexing (e.g., IS31FL3731, IS31FL3741) or simple shift registers combined with current-limiting resistors (e.g., 74HC595). However, broadcast environments involve high-framerate, rolling-shutter cameras under studio lighting. Matrix multiplexing inherently relies on scanning rows and columns sequentially; if this scanning frequency beats against a broadcast camera's shutter speed or refresh rate, severe dark banding or flickering will be visible on the video feed.  
Furthermore, relying on simple shift registers with series resistors (or a PCA9685 paired with 45 external discrete transistors) results in massive BOM bloat, exorbitant assembly costs, and uneven brightness. Forward voltage (![][image3]) variations across different LED color batches mean that fixed resistors will yield unpredictable luminous intensity.  
A direct-drive, constant-current PWM topology is essential. Every LED cathode must be driven by a dedicated, unmultiplexed current sink operating at a high PWM frequency.

### **3.2 Component Comparison: LED Drivers**

| Driver IC | Topology | Channels | Interface | PWM Frequency / Resolution | Viability for Broadcast |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **IS31FL3731/3741** | Matrix Multiplexed | 144 / 351 | I2C | Variable / 8-bit | **Poor:** Causes camera banding/flicker. |
| **74HC595 \+ Resistors** | Direct Voltage | 8 | SPI | Bit-banged MCU | **Poor:** 100% CPU usage, uneven brightness. |
| **PCA9685 \+ Transistors** | Direct Voltage | 16 | I2C | 1.5 kHz / 12-bit | **Poor:** Requires 45 external MOSFETs. |
| **TLC5947 / TLC5955** | Direct Constant Current | 24 / 48 | SPI | High / 12-bit to 16-bit | **Moderate:** High cost, often low stock at JLCPCB. |
| **IS31FL3236A** | Direct Constant Current | 36 | I2C | 22 kHz / 8-bit | **Excellent:** No flicker, minimal passives. |

### **3.3 The IS31FL3236A Architecture**

The ISSI IS31FL3236A (LCSC C246443) is the optimal choice for this architecture. It provides 36 independent constant-current channels, each with 8-bit (256-step) independent PWM duty-cycle control7. Most critically, the PWM frequency can be hard-set to 22 kHz, placing it well outside the audible spectrum (preventing ceramic capacitor "singing") and completely eliminating camera flicker, regardless of the camera's shutter angle7.  
To support 45 channels, two IS31FL3236A ICs are required in parallel (yielding a total capacity of 72 channels)7. Both ICs share the same I2C bus. The 7-bit I2C slave address is hardware-configured via the AD pin. Connecting the AD pin of IC1 to GND configures it to address 0x78, and connecting the AD pin of IC2 to VCC configures it to 0x7E7.

### **3.4 Thermal Dissipation and Efficiency Calculations**

Power dissipation within the LED driver is a direct function of the voltage drop across the internal constant-current sinks. The RGB LEDs possess differing forward voltages based on semiconductor bandgaps:

* Red LEDs: ![][image4]  
* Green/Blue LEDs: ![][image5]

Given that the common anodes are tied directly to the 5.0 V USB VBUS supply (to avoid overloading the 3.3 V LDO), the driver IC must sink the remaining voltage internally to maintain constant current:

* Red Voltage Drop: ![][image6]  
* Green/Blue Voltage Drop: ![][image7]

Assuming a conservative design target of 10 mA per color channel (which yields excellent brightness for modern LEDs without blinding the operator), the thermal power dissipation (![][image8]) per IC can be estimated. Assuming the 45 LEDs are split evenly (22 channels on IC1, 23 on IC2), IC1 will drive approximately 7 Red, 7 Green, and 8 Blue channels. ![][image9] ![][image10] Total ![][image11] per driver IC41.  
The QFN-44 (5x5 mm) package utilizes a large exposed thermal pad. To safely dissipate \~0.5 W and maintain junction temperatures well below the 125 °C absolute maximum, the PCB layout must feature a solid copper ground pour directly beneath the IC. This pad must be stitched with a 3x3 grid of thermal vias connecting the top layer to the internal and bottom ground planes, creating a highly efficient thermal exhaust path42.  
The global output current ceiling is established via a single external resistor (![][image12]) on pin 40\. According to the datasheet formula ![][image13], selecting an ![][image12] of 7.6 k$\Omega$ sets the maximum possible per-channel current to a safe 10 mA, ensuring that software bugs cannot accidentally command 38 mA and melt the plastic button housings40.

## **4\. Switch Acquisition and Debounce Strategy**

Reading 15 SPDT push buttons (utilizing the Common and Normally Open terminals), alongside auxiliary switches on the T-bar lever and jog wheel, requires tracking approximately 18 to 20 digital inputs.

### **4.1 Topology Comparison: GPIO, Matrix, and Expanders**

> 1. **Direct GPIO:** Connecting 20 switches directly to the RP2040 requires 20 pins. This exhausts the RP2040's GPIO budget, leaving insufficient pins for the QSPI flash, Ethernet SPI bus, I2C buses, and PIO encoder reading.  
> 2. **Diode Matrix:** A matrix reduces pin count (e.g., a 4x5 matrix requires only 9 pins) but demands 20 individual switching diodes (e.g., 1N4148W) to prevent ghosting when multiple buttons are pressed simultaneously44. This significantly inflates the BOM line items and JLCPCB assembly costs, while still requiring the CPU to continuously scan the matrix45.  
> 3. **Shift Registers:** The 74HC165 (LCSC C80696) is highly affordable and categorized as a Basic part46. However, shift registers lack interrupt capabilities. They require continuous CPU polling over SPI or bit-banging, wasting RP2040 cycles and introducing variable input latency.  
> 4. **I/O Expander:** I2C I/O expanders like the MCP23017 or TCA9555 offer 16 bits of remote I/O with dedicated hardware interrupt outputs8.

| Input Topology | Pin Count Required | CPU Overhead | Hardware Interrupt | JLCPCB Assembly Impact |
| :---- | :---- | :---- | :---- | :---- |
| **Direct GPIO** | 20 | Low | Yes | None (uses native MCU) |
| **Diode Matrix** | 9 | High (Constant scanning) | No | High (Adds 20 diodes to BOM) |
| **74HC165 Shift Register** | 4 (SPI) | High (Constant polling) | No | Low (Basic Part) |
| **TCA9555 I/O Expander** | 2 (I2C) \+ 1 (INT) | Very Low (Event-driven) | Yes | Moderate (Extended Part) |

### **4.2 The TCA9555 Interrupt Architecture**

The TCA9555 (LCSC C140277) is the superior architectural choice. By utilizing two TCA9555 ICs on the same I2C bus, 32 inputs are secured. The critical advantage of the TCA9555 is its hardware interrupt (INT) pin. The IC automatically drives the INT pin low whenever any input state changes across its ports8.  
Consequently, the RP2040 can remain completely idle regarding switch polling. It only initiates an I2C read when the hardware interrupt triggers, ensuring sub-millisecond reaction times to button presses—a strict necessity for a live broadcast controller triggering rapid video cuts9.  
Mechanical switches inherently exhibit contact bounce, which can last between 5 ms and 20 ms. While hardware RC filters (e.g., a 10 k$\Omega$ pull-up and a 100 nF capacitor to ground) provide perfect analog debouncing, they add 40 passive components to the BOM. A more efficient approach utilizes robust software debouncing algorithms within the RP2040 firmware, utilizing a non-blocking delayed-on/off state machine that filters any transitions faster than 15 ms49.

## **5\. Precision Lever Angle Sensing (T-Bar)**

Broadcast replay controllers utilize a heavily damped lever (often referred to as a T-bar) to control playback speed (e.g., from 0% to 100% slow motion). Historically, these relied on high-end carbon track potentiometers, which inevitably degrade over time due to mechanical friction. Contactless magnetic Hall-effect sensors provide infinite mechanical life and superior linearity.

### **5.1 Magnetic Sensor Comparison**

The two dominant market options for absolute magnetic angle sensing are the AMS AS5600 (LCSC C499458)11 and the MagnTek MT6701 (LCSC C3003196)50.

| Specification | AS5600 | MT6701 |
| :---- | :---- | :---- |
| **Technology** | Standard Hall-Effect | Differential Hall-Effect |
| **Resolution** | 12-bit (4,096 steps) | 14-bit (16,384 steps) |
| **Digital Interfaces** | I2C, PWM | I2C, SSI, ABZ Quadrature, PWM |
| **System Latency** | \~1.5 ms (I2C bound) | \< 5 ![][image2]s (Analog/SSI bound) |
| **Maximum Speed** | Limited | 55,000 RPM |
| **JLCPCB Cost (Est.)** | \~\$1.20 | \~\$0.76 |

While the AS5600 is ubiquitous in hobbyist applications, its 12-bit resolution and high I2C latency make it unsuitable for smooth, broadcast-grade interpolation11. Furthermore, multiple AS5600s share the exact same hardcoded I2C address, requiring hardware multiplexers if more than one is used on a bus52.  
The MT6701 calculates the absolute angle by utilizing two interleaved Wheatstone bridges mapped to an internal DSP unit, achieving a sub-5 ![][image2]s propagation delay12.

### **5.2 Sensor Mechanical Implementation**

For the T-bar lever, the MT6701 should be read over its high-speed SPI/SSI interface to guarantee minimal latency. The mechanical integration requires a diametrically magnetized disc magnet (commonly 6 mm diameter ![][image14] 2.5 mm thickness) mounted directly to the pivot shaft of the lever53.  
The MT6701 IC is placed on the PCB directly beneath the axis of the magnet. The air gap between the magnet face and the IC surface must be strictly maintained between 0.5 mm and 2.0 mm. This ensures the magnetic flux linkage remains within the operational window, avoiding sensor saturation (if too close) or low Signal-to-Noise Ratio resulting in angle jitter (if too far)53. Careful 3D CAD mechanical modeling of the controller chassis is required to ensure the enclosure naturally enforces this tolerance.

## **6\. Broadcast Jog Wheel Encoding**

The jog wheel is utilized to scrub through individual video frames backward and forward. A premium broadcast jog wheel must feel dense, possess high rotational inertia, and rotate infinitely without mechanical detents or friction.

### **6.1 Avoiding Optical Encoders**

Inexpensive optical encoders (e.g., 100–600 PPR models from AliExpress) rely on mechanical bearings and slotted acrylic discs. They are highly susceptible to dust ingress and internal friction, ruining the tactile feel over time. Premium optical encoders used in professional gear are excessively expensive, bulky, and difficult to source reliably through automated PCBA channels.

### **6.2 MT6701 ABZ Quadrature Configuration**

The MT6701 provides a brilliant architectural alternative by operating as a high-resolution, contactless incremental encoder12. When configured in ABZ mode, the MT6701 outputs standard incremental quadrature signals (Channel A and Channel B, 90 degrees out of phase, plus a Zero index pulse)12.  
The IC can be permanently programmed via its internal EEPROM to output up to 1024 Pulses Per Revolution (PPR)12. When firmware decodes all four edges (rising and falling on both A and B) of these signals, this yields exactly 4096 discrete steps per 360-degree rotation. The RP2040's unique PIO hardware state machines can effortlessly decode these quadrature signals in the background with absolute zero CPU overhead, storing the accumulated steps in a register for the main core to read at its leisure56.  
The mechanical design requires a heavy aluminum or weighted plastic knob attached to a metal shaft, supported by dual sealed ABEC-rated ball bearings within the chassis. A diametric magnet is affixed to the bottom of the shaft, hovering over a second MT6701 on the PCB. This topology guarantees flawless, friction-free tracking, enabling operators to achieve frame-accurate jogging without any mechanical wear to the sensor itself.

## **7\. USB-C Power Delivery and Signal Integrity**

The entire system is powered and programmed via a single USB-C interface. Because the device does not contain a battery and operates well under the baseline 5 V / 500 mA (2.5 W) USB limit, complex USB Power Delivery (USB-PD) negotiation chips (like the FUSB302) are unnecessary. A standard legacy 5 V / 3 A Type-C resistor implementation is completely sufficient.

### **7.1 USB-C Connector and Host Enumeration**

The Korean Hroparts TYPE-C-31-M-12 (LCSC C165948) is a 16-pin hybrid connector featuring SMT pads for electrical connections and THT tabs for physical shield mounting, providing excellent mechanical rigidity against cable torque. It is classified as a "Promotional Extended" part at JLCPCB, meaning it bypasses the \$3.07 feeder loading fee, minimizing assembly costs15.  
To ensure a standard USB host (such as a PC or a modern Type-C charger) provides 5 V on the VBUS pins, the CC1 and CC2 pins on the connector must each be independently pulled to GND via their own 5.1 k$\Omega$ (1%) resistor. Tying them together with a single resistor violates the USB specification and will cause the device to fail to power on when used with active "e-marked" cables.

### **7.2 ESD Protection and Overcurrent Safeguards**

Broadcast environments are highly prone to static electricity due to extensive cabling, carpets, and rapid movement. The STMicroelectronics USBLC6-2SC6 (LCSC C7519) transient voltage suppressor (TVS) diode array provides IEC 61000-4-2 Level 4 protection (15 kV air discharge, 8 kV contact discharge)59. Its ultra-low parasitic capacitance (3.5 pF max) ensures the USB 2.0 Full-Speed D+/D- data lines suffer no signal degradation or edge-rate distortion59. A 500 mA PTC resettable polyfuse must be placed in series with VBUS to protect the host PC from catastrophic failure in the event of an onboard short circuit.

### **7.3 Power Regulation (LDO vs. Buck)**

The RP2040, W5500, I/O expanders, and MT6701 sensors all require a 3.3 V logic supply. A linear low-dropout (LDO) regulator is preferred over a switching buck converter due to its lower cost, smaller footprint, and complete absence of high-frequency switching noise that could pollute the Ethernet PHY.  
The AMS1117-3.3 (LCSC C6186) is a heavily stocked Basic part capable of supplying 800 mA13. A current budget analysis yields the following estimates:

* **W5500 PHY/MAC:** \~130 mA (during 100 Mbps full-duplex transmission)  
* **RP2040 Core:** \~25 mA  
* **Flash \+ Sensors \+ Logic:** \~20 mA  
* **Total 3.3 V Load:** \~175 mA

The thermal dissipation within the LDO is calculated as ![][image15]. ![][image16]. The SOT-223 package of the AMS1117 possesses a thermal resistance (![][image17]) of \~60 °C/W on a standard PCB layout. A 0.3 W dissipation results in a mere 18 °C temperature rise above ambient, which is extremely safe and well within thermal limits13.

### **7.4 LED PWM Noise Filtering and OLED Integration**

The 45 LED channels operate directly from the 5 V VBUS rail to reduce thermal load on the LDO. The IS31FL3236A drivers will aggressively switch up to 450 mA of instantaneous current at 22 kHz. This rapid di/dt switching will create severe voltage ripples on the VBUS rail. To prevent this noise from backfeeding into the USB host or disrupting the 3.3 V logic LDO, the 5 V feed to the LED anodes must be isolated using an LC Pi-filter or a heavy ferrite bead (e.g., 600 ![][image1] at 100 MHz) paired with localized bulk decoupling capacitors (10 ![][image2]F to 47 ![][image2]F) placed physically close to the LED drivers.  
For timecode and status display, an optional OLED screen utilizing an SSD1306 controller can be integrated. These modules communicate over I2C and require only 4 pins (3.3 V, GND, SDA, SCL). They can easily share the primary I2C bus with the TCA9555 expanders and LED drivers, provided the trace capacitance remains within the I2C specification limit of 400 pF.

## **8\. JLCPCB Assembly Cost Estimation and BOM**

Optimizing a design for JLCPCB's ecosystem requires deeply understanding their automated assembly fee structure. In 2026, JLCPCB charges an \$8.18 setup fee for Economic PCBA, plus a \$1.53 stencil fee19.  
The critical variable in prototype runs is the "Feeder Loading Fee." Every unique "Extended" component incurs a \$3.07 fee because the tape-and-reel must be manually loaded onto the Yamaha Pick-and-Place machines by an operator14. "Basic" and "Promotional Extended" parts are permanently pre-loaded in the machines and incur no loading fee15.  
Economic PCBA only permits single-sided assembly58. All SMT components (MCU, ICs, passives) must be placed on the top layer. Through-Hole (THT) components (such as the RJ45 jack, USB-C shield pins, and the 15 push buttons) can be soldered manually by JLCPCB, which incurs a flat \$3.58 hand-soldering labor fee per order, plus a small per-joint fee19.

### **8.1 Preliminary Bill of Materials (BOM)**

The following table outlines the core integrated circuits and critical connectors required for the architecture, cross-referenced with LCSC part numbers, JLCPCB classification, and estimated unit pricing for a small prototype run.

| Subsystem | Component Description | LCSC Part \# | Classification | Qty / Board | Unit Price (Est. \$) |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **MCU** | Raspberry Pi RP2040 (QFN-56) | C2040 | **Basic** | 1 | \$1.09 |
| **Flash** | Winbond 128 Mbit QSPI Flash | C97521 | Extended | 1 | \$0.93 |
| **Ethernet** | WIZnet W5500 TCP/IP MAC/PHY | C32843 | Extended | 1 | \$2.84 |
| **Magjack** | HanRun HR911105A RJ45 THT | C12074 | Extended | 1 | \$1.10 |
| **LED Driver** | ISSI IS31FL3236A (36-Channel) | C246443 | Extended | 2 | \$0.37 |
| **I/O Expander** | TI TCA9555 (16-bit I2C) | C140277 | Extended | 2 | \$0.45 |
| **Sensors** | MagnTek MT6701 (14-bit Hall) | C3003196 | Extended | 2 | \$0.76 |
| **USB-C** | Hroparts 16-pin Hybrid Receptacle | C165948 | **Promo Ext.** | 1 | \$0.17 |
| **ESD** | ST USBLC6-2SC6 TVS Array | C7519 | **Basic** | 1 | \$0.12 |
| **Power** | AMS1117-3.3 LDO (800 mA) | C6186 | **Basic** | 1 | \$0.08 |
| **Clocks** | 12 MHz & 25 MHz SMD Crystals | Varied | **Basic** | 2 | \~\$0.10 |

### **8.2 Assembly Cost Estimation (5 Boards)**

For a minimum order quantity of 5 prototype boards utilizing the Economic PCBA tier:

* **PCB Fabrication (FR4, 1.6mm):** \~\$2.00  
* **Economic Setup & Stencil:** \$9.7162  
* **Feeder Loading Fees:** 7 unique Extended parts ![][image14] \$3.07 \= \$21.49  
* **Component Costs (per board):** \~\$11.00 ![][image14] 5 \= \$55.00  
* **SMT Placement & THT Labor:** \~\$15.00  
* **Estimated Total (Excluding Shipping):** **\~\$103.20** for 5 fully assembled, ready-to-program prototype boards.

## **9\. Source List with URLs**

| Source ID | URL |
| :---- | :---- |
| 1 | https\://datasheet.lcsc.com/datasheet/pdf/7f40ef358423c77f721917b416e556f7.pdf |
| 4 | https\://news.sparkfun.com/11692 |
| 6 | https\://esp32.co.uk/rp2040-vs-rp2350-raspberry-pi-pico-vs-pico-2/ |
| 13 | https\://www\.lcsc.com/product-detail/C2040.html |
| 17 | https\://www\.lcsc.com/category/941.html |
| 18 | https\://www\.lcsc.com/product-detail/C39843328.html |
| 19 | https\://www\.lcsc.com/product-detail/C12074.html |
| 21 | https\://www\.lcsc.com/product-detail/C499458.html |
| 22 | https\://www\.lcsc.com/product-detail/C32843.html |
| 26 | https\://www\.lcsc.com/category/1599.html |
| 38 | https\://www\.lcsc.com/product-detail/C19711153.html |
| 40 | https\://www\.lcsc.com/product-detail/Position-Sensors\_Magn-Tek-MT6701CT-STD-R\_C3003196.html |
| 48 | https\://www\.lcsc.com/product-detail/C165948.html |
| 70 | https\://datasheet.lcsc.com/datasheet/pdf/7935197bddb8deeea95201ae83ce3777.pdf |
| 77 | https\://www\.lcsc.com/category/1155.html |
| 78 | https\://www\.lcsc.com/product-detail/Crystals\_TAITIEN-Elec-XXCCCLNANF-25-000000MHZ\_C521599.html |
| 79 | https\://www\.lcsc.com/product-detail/ESD-Protection-Devices\_STMicroelectronics-USBLC6-2SC6\_C7519.html |
| 81 | https\://forums.raspberrypi.com/viewtopic.php?t=375631 |
| 82 | https\://github.com/earlephilhower/arduino-pico/issues/2380 |
| 84 | https\://learn.adafruit.com/key-pad-matrix-scanning-in-circuitpython/raspberry-pi-rp2350-erratum-workarounds |
| 85 | https\://hackaday.com/2024/09/20/raspberry-pi-rp2350-e9-erratum-redefined-as-input-mode-leakage-current/ |
| 86 | https\://github.com/raspberrypi/pico-feedback/issues/401 |
| 90 | https\://productflo.io/error-index |
| 93 | https\://community.simplefoc.com/t/bldc-for-compact-cassette-like-mechanism-direct-drive/3806?page=2 |
| 99 | https\://docs.espressif.com/projects/esp-iot-solution/en/release-v2.0/esp-iot-solution-en-master.pdf |
| 112 | https\://www\.lcsc.com/category/980.html |
| 113 | https\://www\.lcsc.com/blog/ams1117-voltage-regulator-complete-guide/ |
| 114 | https\://www\.lcsc.com/category/1032.html |
| 115 | https\://www\.lcsc.com/product-detail/C97521.html |
| 117 | https\://www\.arduinolibraries.info/architectures/rp2040 |
| 126 | https\://jlcpcb.com/help/article/pcb-assembly-price |
| 127 | https\://jlcpcb.com/help/article/pcb-assembly-faqs |
| 128 | https\://www\.schemalyzer.com/en/blog/manufacturing/jlcpcb/jlcpcb-assembly-guide |
| 129 | https\://jlcpcb.com/blog/reduce-pcb-assembly-cost-prototype |
| 130 | https\://highway.hackclub.com/guides/JLC-cost-optimizing |
| 131 | https\://jlcpcb.com/parts/basic\_parts |
| 135 | https\://www\.lcsc.com/product-detail/C97521.html |
| 136 | https\://www\.lcsc.com/product-detail/NOR-FLASH\_Winbond-Elec-W25Q128JVSIQ\_C97521.html |
| 141 | https\://www\.ic-components.com/products/ISSI(Integrated-Silicon-Solution,Inc.)/IS31FL3236-TQLS2.jsp |
| 142 | https\://www\.ovaga.com/products/detail/is31lt3178-grls4-tr |
| 146 | https\://github.com/WIZnet-ioNIC/WIZnet-PICO-AWS-C |
| 147 | https\://www\.mouser.com/datasheet/3/939/1/W55RP20\_ds\_v100e.pdf |
| 148 | https\://www\.tme.eu/en/news/about-product/page/72258/building-iot-devices-with-wiznet-chips-and-modules/ |
| 149 | https\://docs.circuitpython.org/en/10.1.0/shared-bindings/rp2pio/ |
| 158 | https\://www\.mouser.com/datasheet/2/1534/IS31FL3237\_DS-3394770.pdf |
| 166 | https\://voltiq.ru/datasheets/MT6701.pdf |
| 167 | https\://community.simplefoc.com/t/mt6701-compatibility-question/5345 |
| 168 | https\://klipper.discourse.group/t/experiment-with-hall-effect-angle-sensors/1693 |
| 175 | https\://esphome.io/components/binary\_sensor/gpio/ |
| 177 | https\://gist.github.com/ericek111/91ee5ddaa1029dbb53ba204280b85547 |
| 183 | https\://esphome.io/components/binary\_sensor/ |
| 185 | https\://docs.wiznet.io/img/design\_guide/Wiznet%20Ethernet%20Design%20Guide\_ENG.pdf |
| 187 | https\://www\.reddit.com/r/PrintedCircuitBoard/comments/8hp0zl/w5500\_ethernet\_chip\_layout\_advicehelp/ |
| 188 | https\://manuals.plus/wiznet/w5100-ethernet-design-guide-manual |
| 190 | https\://electronics.stackexchange.com/questions/372956/w5500-ethernet-chip-layout-advice-help |
| 194 | https\://www\.lcsc.com/product-detail/C140277.html |
| 195 | https\://grafito.in/blog/retrofit-nema17-encoder-feedback/ |
| 198 | https\://www\.lumissil.com/assets/pdf/core/IS31FL3236A\_DS.pdf |
| 199 | https\://www\.lumissil.com/assets/pdf/support/app%20notes/AN-135%20IS31FL3236A%20WHITE%20GOOD%20APPLICATION.pdf |
| 202 | https\://www\.lcsc.com/product-detail/C246443.html |
| 208 | https\://jlcpcb.com/help/article/pcb-assembly-price |
| 210 | https\://techoverflow.net/2024/04/09/jlcpcb-pcba-assembly-price-overview/ |
| 212 | https\://www\.lcsc.com/product-detail/C466653.html |
| 213 | https\://pip.raspberrypi.com/documents/RP-008280-DS-hardware-design-with-rp2350.pdf |
| 216 | https\://esp32.co.uk/rp2040-vs-rp2350-raspberry-pi-pico-vs-pico-2/ |
| 220 | https\://github.com/WIZnet-ioNIC/WIZnet-PICO-C |

#### **Citovaná díla**

> 1. Seeed Studio XIAO RP2350 \- LCSC, [https\://datasheet.lcsc.com/datasheet/pdf/7f40ef358423c77f721917b416e556f7.pdf?productCode=C41882923](https://datasheet.lcsc.com/datasheet/pdf/7f40ef358423c77f721917b416e556f7.pdf?productCode=C41882923)  
> 2. A Technical Comparison of the RP2350 and RP2040 Chips, [https\://news.sparkfun.com/11692](https://news.sparkfun.com/11692)  
> 3. RP2350 Errata E9 \- Pull-down lock-up \- Raspberry Pi Forums, [https\://forums.raspberrypi.com/viewtopic.php?t=375631](https://forums.raspberrypi.com/viewtopic.php?t=375631)  
> 4. RP2350-E9 erratum: input pin can become latched at about \~2V, [https\://github.com/earlephilhower/arduino-pico/issues/2380](https://github.com/earlephilhower/arduino-pico/issues/2380)  
> 5. W55RP20 Datasheet \| Mouser, [https\://www\.mouser.com/datasheet/3/939/1/W55RP20\_ds\_v100e.pdf](https://www.mouser.com/datasheet/3/939/1/W55RP20_ds_v100e.pdf)  
> 6. HANRUN(Zhongshan HanRun Elec) HR911105A \- LCSC Electronics, [https\://www\.lcsc.com/product-detail/C12074.html](https://www.lcsc.com/product-detail/C12074.html)  
> 7. IS31FL3236A \- Lumissil Microsystems, [https\://www\.lumissil.com/assets/pdf/core/IS31FL3236A\_DS.pdf](https://www.lumissil.com/assets/pdf/core/IS31FL3236A_DS.pdf)  
> 8. UMW TCA9535/539/555 \- LCSC, [https\://datasheet.lcsc.com/datasheet/pdf/7935197bddb8deeea95201ae83ce3777.pdf?productCode=C42420609](https://datasheet.lcsc.com/datasheet/pdf/7935197bddb8deeea95201ae83ce3777.pdf?productCode=C42420609)  
> 9. GPIO Binary Sensor \- ESPHome \- Smart Home Made Simple, [https\://esphome.io/components/binary\_sensor/gpio/](https://esphome.io/components/binary_sensor/gpio/)  
> 10. MT6701CT-AKD-R \| Angle, Linear Position Measuring \| NOVOSENSE, [https\://www\.lcsc.com/product-detail/C19711153.html](https://www.lcsc.com/product-detail/C19711153.html)  
> 11. AS5600-ASOT \| Angle, Linear Position Measuring \| ams \- LCSC, [https\://www\.lcsc.com/product-detail/C499458.html](https://www.lcsc.com/product-detail/C499458.html)  
> 12. MT6701, [https\://voltiq.ru/datasheets/MT6701.pdf](https://voltiq.ru/datasheets/MT6701.pdf)  
> 13. AMS1117 Voltage Regulator Guide \- LCSC, [https\://www\.lcsc.com/blog/ams1117-voltage-regulator-complete-guide/](https://www.lcsc.com/blog/ams1117-voltage-regulator-complete-guide/)  
> 14. PCB Assembly FAQs \- JLCPCB, [https\://jlcpcb.com/help/article/pcb-assembly-faqs](https://jlcpcb.com/help/article/pcb-assembly-faqs)  
> 15. Basic Electronic Components for Fast PCB Assembly \- JLCPCB, [https\://jlcpcb.com/parts/basic\_parts](https://jlcpcb.com/parts/basic_parts)  
> 16. RP2040 \| Microcontrollers \| Raspberry Pi \- LCSC Electronics, [https\://www\.lcsc.com/product-detail/C2040.html](https://www.lcsc.com/product-detail/C2040.html)  
> 17. RP2040 vs RP2350: Is Raspberry Pi Pico 2 Worth It? (2026), [https\://esp32.co.uk/rp2040-vs-rp2350-raspberry-pi-pico-vs-pico-2/](https://esp32.co.uk/rp2040-vs-rp2350-raspberry-pi-pico-vs-pico-2/)  
> 18. Microcontrollers – Best Price, In Stock \| Embedded \- LCSC, [https\://www\.lcsc.com/category/941.html](https://www.lcsc.com/category/941.html)  
> 19. PCB Assembly Cost: What Does the Price Include? \- JLCPCB, [https\://jlcpcb.com/help/article/pcb-assembly-price](https://jlcpcb.com/help/article/pcb-assembly-price)  
> 20. Raspberry Pi RP2354B \- Microcontrollers \- LCSC Electronics, [https\://www\.lcsc.com/product-detail/C39843328.html](https://www.lcsc.com/product-detail/C39843328.html)  
> 21. Hardware design with RP2350 \| Raspberry Pi, [https\://pip.raspberrypi.com/documents/RP-008280-DS-hardware-design-with-rp2350.pdf](https://pip.raspberrypi.com/documents/RP-008280-DS-hardware-design-with-rp2350.pdf)  
> 22. Raspberry Pi RP2350-E9 Erratum Redefined As Input ... \- Hackaday, [https\://hackaday.com/2024/09/20/raspberry-pi-rp2350-e9-erratum-redefined-as-input-mode-leakage-current/](https://hackaday.com/2024/09/20/raspberry-pi-rp2350-e9-erratum-redefined-as-input-mode-leakage-current/)  
> 23. Raspberry Pi RP2350 E9 Erratum Workarounds \| Keypad and Matrix, [https\://learn.adafruit.com/key-pad-matrix-scanning-in-circuitpython/raspberry-pi-rp2350-erratum-workarounds](https://learn.adafruit.com/key-pad-matrix-scanning-in-circuitpython/raspberry-pi-rp2350-erratum-workarounds)  
> 24. RP2350-E9 Erratum: can get "stuck" at 2V state even without pulldown, [https\://github.com/raspberrypi/pico-feedback/issues/401](https://github.com/raspberrypi/pico-feedback/issues/401)  
> 25. W25Q128JVSIQ \| Memory \| Winbond \- LCSC Electronics, [https\://www\.lcsc.com/product-detail/C97521.html](https://www.lcsc.com/product-detail/C97521.html)  
> 26. Best Price, In Stock \| Crystals, Oscillators, Resonators \- LCSC, [https\://www\.lcsc.com/category/1155.html](https://www.lcsc.com/category/1155.html)  
> 27. W5500 \| Controllers \| WIZNET \- LCSC, [https\://www\.lcsc.com/product-detail/C32843.html](https://www.lcsc.com/product-detail/C32843.html)  
> 28. Controllers – Best Price, In Stock \| Interface \- LCSC Electronics, [https\://www\.lcsc.com/category/1599.html](https://www.lcsc.com/category/1599.html)  
> 29. WIZnet-PICO-C \- Ethernet Example for RP2040, RP2350 \- GitHub, [https\://github.com/WIZnet-ioNIC/WIZnet-PICO-C](https://github.com/WIZnet-ioNIC/WIZnet-PICO-C)  
> 30. Building IoT devices with WIZnet chips and modules \- Tme.eu, [https\://www\.tme.eu/en/news/about-product/page/72258/building-iot-devices-with-wiznet-chips-and-modules/](https://www.tme.eu/en/news/about-product/page/72258/building-iot-devices-with-wiznet-chips-and-modules/)  
> 31. GitHub \- WIZnet-ioNIC/WIZnet-PICO-AWS-C: AWS IoT SDK Example, [https\://github.com/WIZnet-ioNIC/WIZnet-PICO-AWS-C](https://github.com/WIZnet-ioNIC/WIZnet-PICO-AWS-C)  
> 32. rp2pio – Hardware interface to RP2 series' programmable IO (PIO, [https\://docs.circuitpython.org/en/10.1.0/shared-bindings/rp2pio/](https://docs.circuitpython.org/en/10.1.0/shared-bindings/rp2pio/)  
> 33. Wiznet Ethernet Design Guide\_ENG.pdf, [https\://docs.wiznet.io/img/design\_guide/Wiznet%20Ethernet%20Design%20Guide\_ENG.pdf](https://docs.wiznet.io/img/design_guide/Wiznet%20Ethernet%20Design%20Guide_ENG.pdf)  
> 34. Wiznet W5100 Ethernet Design Guide User Guide \- Manuals.plus, [https\://manuals.plus/wiznet/w5100-ethernet-design-guide-manual](https://manuals.plus/wiznet/w5100-ethernet-design-guide-manual)  
> 35. W5500 Ethernet Chip Layout Advice/Help : r/PrintedCircuitBoard, [https\://www\.reddit.com/r/PrintedCircuitBoard/comments/8hp0zl/w5500\_ethernet\_chip\_layout\_advicehelp/](https://www.reddit.com/r/PrintedCircuitBoard/comments/8hp0zl/w5500_ethernet_chip_layout_advicehelp/)  
> 36. W5500 Ethernet Chip Layout Advice/Help, [https\://electronics.stackexchange.com/questions/372956/w5500-ethernet-chip-layout-advice-help](https://electronics.stackexchange.com/questions/372956/w5500-ethernet-chip-layout-advice-help)  
> 37. Hardware Engineering Error Index \- ProductFlo.io, [https\://productflo.io/error-index](https://productflo.io/error-index)  
> 38. TAITIEN Elec XXCCCLNANF-25.000000MHZ \- LCSC Electronics, [https\://www\.lcsc.com/product-detail/Crystals\_TAITIEN-Elec-XXCCCLNANF-25-000000MHZ\_C521599.html](https://www.lcsc.com/product-detail/Crystals_TAITIEN-Elec-XXCCCLNANF-25-000000MHZ_C521599.html)  
> 39. ISSI IS31FL3236A-QFLS2-TR \- LED Drivers \- LCSC Electronics, [https\://www\.lcsc.com/product-detail/C246443.html](https://www.lcsc.com/product-detail/C246443.html)  
> 40. IS31FL3236A WHITE GOOD APPLICATION \- Lumissil, [https\://www\.lumissil.com/assets/pdf/support/app%20notes/AN-135%20IS31FL3236A%20WHITE%20GOOD%20APPLICATION.pdf](https://www.lumissil.com/assets/pdf/support/app%20notes/AN-135%20IS31FL3236A%20WHITE%20GOOD%20APPLICATION.pdf)  
> 41. IS31FL3237 \- Mouser Electronics, [https\://www\.mouser.com/datasheet/2/1534/IS31FL3237\_DS-3394770.pdf](https://www.mouser.com/datasheet/2/1534/IS31FL3237_DS-3394770.pdf)  
> 42. IS31FL3236-TQLS2 ISSI, Integrated Silicon Solution Inc \| IC, [https\://www\.ic-components.com/products/ISSI(Integrated-Silicon-Solution,Inc.)/IS31FL3236-TQLS2.jsp](https://www.ic-components.com/products/ISSI\(Integrated-Silicon-Solution,Inc.\)/IS31FL3236-TQLS2.jsp)  
> 43. IS31LT3178-GRLS4-TR \| Original stock,Price \- Ovaga Technologies, [https\://www\.ovaga.com/products/detail/is31lt3178-grls4-tr](https://www.ovaga.com/products/detail/is31lt3178-grls4-tr)  
> 44. High Diode 1N4148W \- LCSC Electronics, [https\://www\.lcsc.com/product-detail/C466653.html](https://www.lcsc.com/product-detail/C466653.html)  
> 45. JLCPCB Assembly: Complete Guide to PCB Assembly Service (2025), [https\://www\.schemalyzer.com/en/blog/manufacturing/jlcpcb/jlcpcb-assembly-guide](https://www.schemalyzer.com/en/blog/manufacturing/jlcpcb/jlcpcb-assembly-guide)  
> 46. Shift Registers – Best Price, In Stock \| Logic \- LCSC, [https\://www\.lcsc.com/category/980.html](https://www.lcsc.com/category/980.html)  
> 47. TCA9555RTWR \| I/O Expanders \| TI \- LCSC, [https\://www\.lcsc.com/product-detail/C140277.html](https://www.lcsc.com/product-detail/C140277.html)  
> 48. Firmware for the Chinese uSDR slim clone (longer body, small LCD, [https\://gist.github.com/ericek111/91ee5ddaa1029dbb53ba204280b85547](https://gist.github.com/ericek111/91ee5ddaa1029dbb53ba204280b85547)  
> 49. Binary Sensor Component \- ESPHome \- Smart Home Made Simple, [https\://esphome.io/components/binary\_sensor/](https://esphome.io/components/binary_sensor/)  
> 50. MT6701CT-STD-R \| Angle, Linear Position Measuring \| NOVOSENSE, [https\://www\.lcsc.com/product-detail/Position-Sensors\_Magn-Tek-MT6701CT-STD-R\_C3003196.html](https://www.lcsc.com/product-detail/Position-Sensors_Magn-Tek-MT6701CT-STD-R_C3003196.html)  
> 51. ESP-IoT-Solution User Guide \- Technical Documents, [https\://docs.espressif.com/projects/esp-iot-solution/en/release-v2.0/esp-iot-solution-en-master.pdf](https://docs.espressif.com/projects/esp-iot-solution/en/release-v2.0/esp-iot-solution-en-master.pdf)  
> 52. BLDC for Compact Cassette-like mechanism direct drive \- Page 2, [https\://community.simplefoc.com/t/bldc-for-compact-cassette-like-mechanism-direct-drive/3806?page=2](https://community.simplefoc.com/t/bldc-for-compact-cassette-like-mechanism-direct-drive/3806?page=2)  
> 53. How to Retrofit a Standard NEMA 17 Motor with Encoder Feedback, [https\://grafito.in/blog/retrofit-nema17-encoder-feedback/](https://grafito.in/blog/retrofit-nema17-encoder-feedback/)  
> 54. Experiment with hall effect angle sensors \- Klipper Discourse, [https\://klipper.discourse.group/t/experiment-with-hall-effect-angle-sensors/1693](https://klipper.discourse.group/t/experiment-with-hall-effect-angle-sensors/1693)  
> 55. MT6701 compatibility question \- SimpleFOC Community, [https\://community.simplefoc.com/t/mt6701-compatibility-question/5345](https://community.simplefoc.com/t/mt6701-compatibility-question/5345)  
> 56. Rp2040 \- Arduino Library List, [https\://www\.arduinolibraries.info/architectures/rp2040](https://www.arduinolibraries.info/architectures/rp2040)  
> 57. Korean Hroparts Elec TYPE-C-31-M-12 \- LCSC, [https\://www\.lcsc.com/product-detail/C165948.html](https://www.lcsc.com/product-detail/C165948.html)  
> 58. JLCPCB PCBA assembly price overview \- TechOverflow, [https\://techoverflow.net/2024/04/09/jlcpcb-pcba-assembly-price-overview/](https://techoverflow.net/2024/04/09/jlcpcb-pcba-assembly-price-overview/)  
> 59. st usblc6-2sc6 \- TVS Diodes \- LCSC Electronics, [https\://www\.lcsc.com/product-detail/ESD-Protection-Devices\_STMicroelectronics-USBLC6-2SC6\_C7519.html](https://www.lcsc.com/product-detail/ESD-Protection-Devices_STMicroelectronics-USBLC6-2SC6_C7519.html)  
> 60. Voltage Regulators \- Linear, Low Drop Out (LDO) Regulators, [https\://www\.lcsc.com/category/1032.html](https://www.lcsc.com/category/1032.html)  
> 61. JLCPCB Cost optimizing \- Highway: Custom Projects, [https\://highway.hackclub.com/guides/JLC-cost-optimizing](https://highway.hackclub.com/guides/JLC-cost-optimizing)  
> 62. How to Reduce Prototype PCB Assembly Cost (With Real Quotes), [https\://jlcpcb.com/blog/reduce-pcb-assembly-cost-prototype](https://jlcpcb.com/blog/reduce-pcb-assembly-cost-prototype)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAWCAYAAAAfD8YZAAABOElEQVR4Xp1SMUpDQRCdwSYQJU0Km6CITeqghXgBIeQEOYA38BYilpImhQewsBGvYRcbsbMTIohFMrMzu7M7+xeCD97u/PdmZvfP/wC7AL0QkYw8Q+K6plYK1C1qtHTGMXFJ/KCkB9rHhVtU2sMhcUNcEfcy/Un1aevMI5CEd28o7lD8a5O0EW2/IOaJmdU57DPRdIS+dmUa6hv+gOScmYSwr2JZXGMNknPljVh84I3sCjFnYJ5gocbMGwEIQwg+fuZibMwrF78VnsU3IMWjTC0wh/Z7r6nXixcZF8Rzjb8oaRIiTIf3QD8RsU+8FVlcHtK9CHBKfNY4YsbX1kaXkKZt7xwnyfwWM+Ex85hD/wtwwYYasflXWvgaPBmYm4lvE9ApQlvPJvQ/dBa7pp05BXbNTp4E9drGFoPkOr52HL9ZAAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAXCAYAAAA/ZK6/AAAA9UlEQVR4Xq2QPQ7CMAyFHcEAggsgMTFzDAZYGFi5AjsS5+AqVRcGJBZWJk6B2Bgpz3aaOm1UVRVPcup+/klsoo5ydSCyNPiJ1ARqqEtOXyXf2SbXPs/fFPXueZGUFbBjRMjdcTxKZmZycxwF/EUVFBVIONWYaEV6w1T+tNEIJzOOVfIzZHA4aHnZZGJ5KQ5caywTntgKd+CCnY3B/+K8GRS08W+d6a+UjUmauD2+Q7K3I3zRIK0DJHo7LeAmB9hSsW6Dk1+kX7YPbACe+5tzTVZNfMHWwrT4qY7f7/cfJlantoDg6epi2pANPWHn9q5J6fTNslg/HHUncedRdY4AAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABYAAAAWCAYAAADEtGw7AAABW0lEQVR4Xr2UIU8EMRCFXwWCQEIuJJxBYtAEQYJFIM5gEPArMCRYwm9An8diLqf4DwSFAHvhBAmKEJjZaXPTmW23ii952duZ19em7R5QIAwW/oG2OZOr4tatzJaPqSQ4oreSptkmvZN+lfjdssSqv6S8HdMvcgcZNKksgvumWzYnJpCBN/LqBtyTTvKS8yi4J/19SPBctyO8Xa/1oDKbkOA326C4BT3WbbFxms7Gwd+mcUa65R8pSJ6NsZF06gke/aPe++AtXNMFP2XAF/KTn4WAPW0wzEiXyBfTyzPENCZx4FPedrB3A+KtMoWYDyBb4Jao2CV91i0rriDBH6Rz01MRgW9JOg8W36gqhxDjAmFwJY+kC1vMiRn0GAcJ3nJND21Dtx0NcEYpx9fdTUgWb21nhOxDkqhCoCkXXB0Bp+j/T+kYPh4PDzkmPZCOdDHDFSpE7zXpBUP3l1p/F0k5YvRbr7IAAAAASUVORK5CYII=>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGAAAAAWCAYAAAA/45nkAAADpklEQVR4Xu2YT4hPURTHz0uKTIQipUSzIZGQMNlZSCxQFGXFbKwUymokW81CKY00K3+SjZQkyUJiYyMri5EoQoRCjPt9593fPfe8++57b36/1+/303zqNL97znnn3T/nnnvfECVUjvKp8khdmojZHJ3sbSdjTYmudyBIb/aqj+nKhHblpY2QNDOYWjFrOddioZHXRiaFoK35RM6O34ucqc3Otff4NvL7jnYU8boN5J77YWSuMwXBvHwj9wx+n/c8iK6zLUl9kry9kHPEQXdpgwD28ukq9+gUJ42MifYZ4j5eEroi9pI/nnlZeyka+SF4mr/EvgNSKRgycjcQpEXIhIlH0NPakHHRyHat7BShDlUA/b2qdD8zPSY0BnyG1Xsfmp688VVBRoizG0kb4pmR5VopCY13JXGn7msDcZl6pZWOULgA7DbLyL7sb4w0E4O4OJPmN/o8R1jHU318J9uxrld6JF+VXT6b2A87QYNnQ/pSBrLBTGiD4QPxS9sFcfAOe+b8okDcbPR3cpp884iRo86QcpO4/u5Qeslx4sVbq/SnUn1s8R3viH11ph+g4p1RCgL+Vro9Rs4qXXXcZB0zssUZUnDo4Z23uNlyXmN+P7GNmtj6HMvi8WyRlig9L0CS1vAydhO/RyRKCham6GwoBQEhFgzij2iHhoXtPFMr8250WysEOEztuyHfKRiilP3EzyNpYtgyFV6AePmStOYr6yx280dnrg8GLrPnnpFBZ84B+yHyF615wktjbzE7tSFApxYAuxT+m7P2CHEJmjIviAMuJp74R745B3xxAMYWSbKK/Ezf6ps9xgomOkWZ0ES8wfwjeQ25iV5RoNeHcxGrif1fZm2Uv+ALq2IzAx1A6YkFw0H1VSsjwB87zB66WLgJI1+MzLBOgrdaEcH0NVkg2qjhsUN4I4Un2t6C5K2qDJtMy4h3RFvw7YDrGOppEfY2Y6XKoaMPK4vdFU+JB3E4SdvJOt9N4KfFZ8pP2BXyy8smEqUpcTtmuOXB4Ape9wp5gdw8YEfUIJ/fNjMwwWVgQg9qZYRRrVDg2+C9kedU/i8BywPyE0GKHF0oUW6QP067KLjd1GE+ufhtg9qPQGVfkQDlp8p9uSkwmXrSpUiuGXmsdAA6lNrLxM+c8M1VSNcZpRU7oWm8LeMPMr+bItRyniYAtp3+YPtP6I/kwA0j9D+jPiUy6RFTN0B3hpL0/y2tjw/POE2jJPhQwUdH5P7fC8vQC32oxj/f5tZ8yNEO7AAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGAAAAAWCAYAAAA/45nkAAADlklEQVR4Xt2Yz8tNQRjHvzcUEUmRH4VSIpSE/FiykFigKMo/YGVBWb0lCxvpTSnZ2FHYSEkWoiQ2NlJi8VpQhAgL4jXf+5y5Z85z5szMuee+9973/dTTPfPMzDPPzDzz6wJDRUsrhoLh9GoSIAM3qOFT7bZKmsEwFE5MGFO7dxEadr5h9SYsMPLOyLgjTGu+IM/n98Jidn9xxms1ir7vzbOinEde75eRucXsEhyXH8jrmO/WhWIR3HDyKZ382Byfg1TYpzMcmB+z0092G7kln223VkB8vGMLBHhtZLuTfgupu8XRVfEPUnZOO1UekZ1G7mmln7wyB55Gzyi95TKkw7Upm+oZYxCfdzk6G3khloJlWjjs6Ka3dfG6ZARSjkHr47mRlVoZYw3E6AOdAdmmGCG9YKaRQ9lviGVa4YFBQZ/dsimDyAnzlfuZ6SSyq5kFKceVoGG8+fRR2CiNMqo0nyCNNoV22IY9c36j2u5drUiAUUe7KVvQqJG18tlZo38g9WdbRYAPkLI60o+gemVEoUE64XLAyNkebCMnUNxzCQ89bgW3lX6DkadKF2MJxH8u/26wUf1VZ1SwH1JeBwonpupsiKKXJU38ddI+uHXNKGj8DYei8hTytincCvxW/HBLuwKpy5tNAiXzj9Cu35qnMwLo8eIkfnbSHkrtFrB7oC1138iqPLsE84+h6MSgqRPFloNGxk2n6ww+4Sple9uy9AhkC+qalxCDiyADz6gIwbLcL0OTlNGeU+65bqTvcEsormpFIo8htlMHYjmk/DSdkcA6SN1XWZqHbzjEI1yDGNwE2XpCxnjz+K6VAVieK8weupy4MSPf4O/8e61Q0DdftD/M9OxLDEa87udNpB3CFhtMnMjiueVaDY2kw0mIMe5j7h1ZY28zVmLXNqIPK4tdFc8gnTiepTe6hTwsRt6+2z37oHJXwFaUXsgtnlt68giDpA6XkPvBFdGIzRBDHOAYHNCjWhngolZ0kOHjQfrRyAvE/xKw0Nf1TpqDSp2+OOhAYYssY/Wu8C+JOsxHXjeZqgXBvZ+GUg4jbj8pjyU/VR7Ug9sZ3xL02b4t3qBs/bqRJ07avvp9knaNLbbAVcOV0NW2E8dvqNaMp+FvaKrQy95x2ekHWz1qeVOrsKJJ3YmjqVd74P/PqGs6DjX1LIE+NNFLCu4ywb9aeVWzj4/JyySbCXIa8ujo3P9r9aFhmHdXqwv61hDwH2+H1u0ksiBOAAAAAElFTkSuQmCC>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMEAAAAWCAYAAAB5efgLAAAFhElEQVR4Xu2aT8hvQxjHn18o8i8WJOq914LETpSVEmWBDUVsZEOxU1dXKRsL1F1IlOjNQmJhY4GSfrFQbN1I1L0SRYhQ9xXXfN45z32f8/xmzpl5f+c957rOp6b3Pd8zc2bmeWbmmTPnJzImCy/kKM44MzMzs8O8dMzMzOye3awguynz/2G2zu7ZY9t1PP6xkD4N6ZqQzgxpI6T3Gr2E+0M63qSvQjqtdXeVb0Lakp0yP4f0UCuHyMfNPU3+/qAkbPOO1PXJ8pbslH3F3fNcJNEeO31dyLeNbvn9xP34v78/OAmbgO3bJ1JnF+vTp1XM1HOzeLvEa8vZIf3d3CP90L5dB4PdVkZ6v5Ujz0sh/WKur5dY/nSj5dC6MnaQ+0J63osjgGEvbP7HyWro80/kyIMtsIni7ZPjYol1/OFvGHShiuSsJp231sHaBb6W2OazjJaDsgfMNePrc3Od41aJdSydbvlLytrQCZPgCYkOu0usDbutScU08Cqn48jXnZaCPJRnsKf4XsoG3pDcITFKXWG0/RLbyQrdxS0S81mwINoNTk9xTGLeC/yNBv/sMblEYv3/GE0Xz5eNloIo7tt+TqNh2z7I58sr2KrPL0XQmdu9WMCDEhtHhywfNXofuvolVsoFEyyh7wWtmf6cxDaxylm6HKEclnQetKUXEzwiMW8q+rEipvQ95oRtiOy0za7ejzcaf7v4aZGOcJTd9GKCdyXmxQYebJLSq9ntJCCk0Tj2ZpZlo3fHkQihjLx+xX9S8hGil5KKM1CUiHie00smQS4P2p9eTKADLfUMVrtchJgK2kRb+7Yi5PnNixL1klX8csnnbWy1hscbmARvSnyxeFjidqDkneCopB22lKiXOE1DKiuwhcmxfs+GgX04bWRF6oI8uRUvZacUR2Q778JuMZkcqedOBX55QWKf9rVvJSEfY8WDjp9LPK025OBGYXIszfVaMBAPOo0KN53m6ZsE7CP7oFPktXtNtklsLU4WGIC0sc9VK5OgKVAzCTgVIa+dcGyT2HqWckhiNCtNNRH30pAOLKKPiW4+YqbomgSldtFtKrZQsJF/Hx0UDXUZx2/LQ0wC0Lr2N9e8MJe8SCrUU5oy/cnCIOFko6TcyiRoqHE2+PzHpOy0bWw0inMi2MUQk4DtMnmxhbJatsRLGWyIUZbSP5CXEvN4B6nuX5hz6DGYrn6rnevGD/SuVGOmO0P60Ysd0O4Y3tvUOBvsiyBRseQocQrOlWTfVkzMfU76POipRSMHByXHF9Em7qBgpc4qCG80xr+46Blw1yTQ0wE/2EtPhyxqzGvFHa+u170M/Q9ldfvSaSlHWjSiedD8aVOa2C4iImV43qbURUWo3Q49EIt18qjENtlVX485U322sG1KDXbKlbx7KvdILMP4OCL+MKXfp1n0mPJFp9Nw37l7Q7rSXGtZvy9jQh2ubJSufiSeOyUbIX3oRVl15DPSPhnRI04PWs2eHnhHKhlgY6Fb39eMpv63bcTrTEL7JZkV2/eDE0U03oFK4dla3+DH5zzQHnNuhOqoiO2AQkTwHYbvQnrbXOve7TKjlaDHYHbPNwX6ATCViHCK7oePmiVIncRHM+XuRqvlKYnlSj46jgEfvD5z2qZst3Fhx8mrUWud2pzRaFcb7aDEd61a+GrOs4gKg4LztsIffpOiv1G5rZ1lG35D86zTKPurxIn0hsSyN7ZylENZ+/Y/BerEVGJgKurY64wG/KwAHWepw/x3lBJ0qzF1VLTwswfaxFH6VvP/Ta0cO4vgPqdzjf5BSF9ILI8Na2G7zHPq9hlTkW5lWt0LxqpprHpOZmYb1DJbbGZGGWs2jFXPmJyKfTqlmR02JYNaf9CHVbJ23Ws/YFr+482f6WU6D/8Ljf6Vrct0G8oAAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,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>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABsAAAAWCAYAAAAxSueLAAABcUlEQVR4XqWUrU4EQQzHu5JwhBBwmAsOhUDwDBgUDoMDzxtAUDiCIcHxAjwA4jyPgCMBBMEiMEdL56PTdiazd79cN7Ptvx87s7cALoO41lBRV+w6fWRLmWY9vTRyUqihGYesyL8FWCzrEu0NbR7sI9yT/Qbf+1JP7OTEZkwWrAT/a/IsyQS44Ez5I+UgHs70NQ6Bix3pAFbZgJ5mklZjjD3jlYpNHN0VcKNzHWgWTVjRPDQLJMEux+Axx8p0XtuCNVYhb5O2H7TNLGVss37onKjwmQ4kcsUDtBtg/XGw+7Ar06SC+hAz4OQt5a9xi/aifPT0XS9Q3LJePtFOnNmpxp52StaARXrSkrIu6envoCH/vnbK5FNct8+LyPod8Hdhm+oM/HEwPIB988jWpcjhGtIuDHKIO1x/pTuQIbPdDr7mG/7Pq4CUPYPW4E5OP31e8SM9Fb4GqmK6Lf1PYLec7MIOVB20QXEkdXo0oxlbNOr/APW/TNERXoyoAAAAAElFTkSuQmCC>

[image9]: <data:image/png;base64,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>

[image10]: <data:image/png;base64,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>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHUAAAAWCAYAAAD+ZNNIAAAEaUlEQVR4Xu2YTahNURTH1w1FSCISg4cMmEhCpEgGDJhQhMGbMTBTlIzIhDJA+UgZSFKSMjEwuGUiBkpJYfDIR54QYfDkY//v2uuefdbZ+5x9znn3ulfvV4t3/3ufdc7Za6+19z5EY4yR0NBCfxP5OpHd+pXuvF72Lqxk9e7wr+7b35QdNW9/r+glpmd+n/zWXuCosVfG/lh7a3/DRqz2pt27dxmk5B1eGBuXahWK4/HB2BYtGuZR4h+2JN2c4Z6xkUbS/5uxU7btsbFfVocNG9to22YR95W2T1avhDjRTCLWn+uGHuKisc/O75XEzzze0WLYR3ydDuoyYw+VhvttU5oPGdfUs9i5FRpzcMPYfC2WYQqx86bShbybjy7FmaSRSbdY6d+NXSvhEH7ekz+oH41NVRoy97fSfFwm9rlTNxjeEbet1g3EmVyLzcTOt+oGw3SKDGr08DELja3XosfJIi0o9hI/GyamC8pf4TM7YNmZQf6gQhtUGoL6U2k+kG24fkjpeNM/5l9fMmHMkam1uEv+gQHHiNtQmgJkI5HDNGJ/WK8xkPj7ZqqHwG6LXk6efbLSm1aPebg9ptcOSipWElS++qnVH7R1omeUW35Tt5WkcMVNxEkkbS6HKFt5SuNzDOAY+hXdkCFm6BiUMr2J2UV8nw1Kv0r+0uTykvzP3mywjlmfxwTiyQWyQWXQR8YIhtLoK6chMDFxHQIpPCGMWqM9YdwguvuDSmCGuw/s2g/ikuQhPoqKw1qwwCF2re79ZbfY7uAhGFRifY7SNcg4BA3+Q0EFeveL00EOqaeV5EAgpWnItkm2SkWaaOyO/bsy4hRrUxGrjJ0k7r/d2gX7eyDp1lXqBBXv7i4roaAeoCR7cJRpBbZRLqPsZGhFdC0lmQ5BJgpAHJbbvyvTJHY4U+khTlN2ey8bjFjgQ15k2LxWK1N8mDe+nVHSKdsk9qOPL6L79gkA/XEmdfEFVTTt/5Et77FrX5O4P5aT+5T299q2zSXeEdfGnSUFtEYTN92tGgB8LNWixng4R3yuFNYQX3vG0QQcxPdrUYFy7gte0e4XvuUjixg+AuAaHPjxG0sTAox9gA89AfJA9qF/k7L+MJ5owx5CJ0xpcPaCM3YUWLQU6O/bfECPKRuh9QJBhY8jxOsXAp8XFGE2cT+dMV8pvYaBE8Tn0RAy8G6gUCr5PJodH+w5FmgxB/iG6YmKdVTacL9aDBI7illPAV7AN9AoG9B1tvjAOhwCw3aeOCD4PxbsXt0yLccmTA4BxwRoWINDrCD/eCCoB5WGz3q6fBeB5AmNE7LXN7bRXKJkZriGwcjjOPnLw1kq/4KjCSbDF+KNy3Xid1mX6pEcSxA4jaybUnalDMvg4wgm38HlOzm+35YFWYgvXT6QvVxZugxmk15PZffmmRDZesWE9Jp0yO3/DoLnrqfy3XXA0SoRikdI7wTV7lXtql7gFmVLNQznt96kf8e6n4gZ5Zg+MYyWnzGq09EY1Hde30Pn+Qtjri2VBM8OdwAAAABJRU5ErkJggg==>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADQAAAAWCAYAAACPHL/WAAACZklEQVR4Xs2Wu4vVUBDGvwMKiopgoYjb2AhWFmqh9TYqWLhbKGyxnc3WCpb6L2gjwooiYmUliFikt7DZ7VVEUStBLQQf82XmJCeTk9xX7nJ/MDfJN+fMmcl55AIjCJm78Zi+53wYOIuBw5UBB485BAuX1KItrBrN57bYB7F/Zp/s+WOiXdMOM7LD9VvyrYW6Zr61nchnqDH2Q5MunE5Ogr6A996xCHS9gAvQgnj1bEB9LyulK8oC8Rqa9D7vEP5AfbsbaraorDgwfWPUvrj5U46I/Rb7jo4oWTHLiJaVe0S7MeGssBgmz9ON9sO0E0m7LLkU2hqVtjob2XileBm5/RNw1/S9DV05KrYJ9T8Su29WmFYTsCq/P02/aNote34odsxa8jPxBRrnlfl5/8zuOWZNs57GU4H8/rlu+nnf2zgNn7yy7QXhHLTtLnvmnk2DUr+TPL+AtoncREcSOTgQj2XPm1IHTnkHCTpD20m/e3Z9WykNAmPxxJS3HvzLu4q6WPIX1YopB3iSyS/LAWjShdOJFqqHQw4uI84iYdFcun3EJbzkHY49qFZMWsV4Fa1DO19xOuyN0lg0+ZU6zbcuFvcIP86Ju8VK0D7Hs96S0rMMnaGJeIx6BuKS4zWd9kumb8n1K/QfQ8Tvn+d2ZX8uH88ZsRWxdxKvcD4P9w+t471MQBg/wCZ0j3keeAFcYgE37D4eDn0jcXaW6wZ9TYcj3T+Rs2JPqyfN4xD06E1hQRsdiSb7Z064YeN/vpYFXbIHrd1h549869D5jfExP5eebN09TNp+ZuKAUw48Zbc5MW02jX7tIP8BPeeJTAALjr0AAAAASUVORK5CYII=>

[image13]: <data:image/png;base64,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>

[image14]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAWCAYAAADJqhx8AAAAu0lEQVR4Xp2TTQ6FMAiEYe3CxCN4PO//li8RiqWFgk39Eo0OzPTHClDA7h6RV5SsJdMDJq2TsmWpmVk2LPA5GzNnphMnVTcvOi4veP4UstcXtMP96NKaQxv5gUK6Rimx+WjayzrgCcEWYs3gtmHMQpk7lpnkZp7FaFbqUjQg7k1V7PdBQsw2RYheRxZzMw1LSTAje8xntPOQNzpIEB+ktl/TgyRkyyy8FiGoszCIKzzmKKNqUW2O+1O+cgOSDRHg+pAWHgAAAABJRU5ErkJggg==>

[image15]: <data:image/png;base64,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>

[image16]: <data:image/png;base64,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>

[image17]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAWCAYAAAA4oUfxAAAB0klEQVR4Xq2Vvy8FQRDHZ4OCUNFIJOR1PI2oJEqdDp0/QCFRSMQfIHpR6l7nT1CJWoTqRaUgQqlSIPHMd/f2bmdu9+x7fJK5vf3u3Mzsj7sjSmK04Cjl4ibmFtOa6Nc/houB68DRGh5sGMqnKYixo+dsF2xDavRf0DvnmWHrsTjK7Ry3336gqV5Pjk+KEUJionagoT/vOzq47vdPFeGB7bkasCD5odL+nTYXgUSrgTZMKvnfZ0pVkCBYl1yiECw3tO28tDk+cZBELzlmXO15KnZKz6RVLPkN21lgX1RfDUFm3gNcUr77pE61xRWkVwPgLGyRK/aDbV0OC07YHrUYVtIx7t0Oi1shVxDaFF1+4FiLAeOEAg29215i6h2qL+89e2NWEhkABbeEIrljW6Ygdi2/sadZJJ+0K0E0G2iaKXLJUyyR+1hNU8LPS/iUIpnvv7FtFvcl6vkdtlcpCW6LFktvJxbJX7JBzgm2oMYcRgTAdyG133hFX9ieyB1YxJwQHs0gjagVnd2gj4Bqv60//g9HUqeeifv+Knk6VJ2LRbbyb6e4jgTBnq9psR9w+C7Z9tg+qf6f96cadlVoY4EGO40UVsf6ZDrmuDnyPQcjjJ+R6wfGA1Dk3TUpOwAAAABJRU5ErkJggg==>