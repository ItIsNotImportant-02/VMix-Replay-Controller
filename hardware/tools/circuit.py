"""vMix Replay Controller main board: netlist description.

Run gen.py to turn this into KiCad schematic files. Pin assignment and design
notes are in hardware/DESIGN.md; keep both in sync.
"""
from schgen import Part

# --- footprints -------------------------------------------------------------
R0603 = "Resistor_SMD:R_0603_1608Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
L0805 = "Inductor_SMD:L_0805_2012Metric"
LED0603 = "LED_SMD:LED_0603_1608Metric"
TP = "TestPoint:TestPoint_Pad_D1.5mm"

# --- LCSC numbers (JLCPCB). "?" = still to be verified before ordering -------
LCSC_R = {"10k": "C25804", "1k": "C21190", "5.1k": "C23186", "100k": "C25803", "2.2k": "C4190",
          "4.7k": "C23162", "27R": "?", "33R": "?", "49.9R 1%": "?", "12.4k 1%": "?", "3.9k 1%": "?",
          "1M": "?", "10R": "?"}
LCSC_C = {"100nF": "C14663", "1uF": "C15849", "10uF": "C15850", "4.7uF": "?", "10nF": "?", "22nF": "?",
          "6.8nF": "?", "15pF": "?", "27pF": "?"}

_n = {"R": 0, "C": 0}


def R(ref, value, a, b, fp=R0603):
    return Part(ref, "Device:R", value.split(" ")[0], fp, pins={"1": a, "2": b},
                lcsc=LCSC_R.get(value, "?"), fields={"Tolerance": "1%" if "1%" in value else "5%"} if True else None)


def C(ref, value, a, b="GND", fp=None):
    if fp is None:
        fp = C0805 if value in ("10uF", "22uF") else C0603
    return Part(ref, "Device:C", value, fp, pins={"1": a, "2": b}, lcsc=LCSC_C.get(value, "?"))


def TPt(ref, net):
    return Part(ref, "Connector:TestPoint", net, TP, pins={"1": net}, in_bom=False)


# ---------------------------------------------------------------------------
# Buttons: name, TCA9555 (chip, port pin), LED driver channels
# Order matters: the first 11 go to the left/centre LED driver U6, the rest to U7 (see LED_MAP).
PB26 = ["MENU", "SHIFT", "CAM_A", "CAM_B", "CAM_C", "CAM_D", "PLST", "BROWSE", "IN", "OUT", "TAKE",
        "CLEAR", "ENTER", "PLAY", "LAST_CUE", "MARK", "RECORD", "PRV_CTL"]
U6_BUTTONS = 11
FKEYS = ["F%d" % i for i in range(1, 11)]

TCA_PORTS = ["P00", "P01", "P02", "P03", "P04", "P05", "P06", "P07",
             "P10", "P11", "P12", "P13", "P14", "P15", "P16", "P17"]
# U8 (0x20): left/centre buttons + F1-F5 ; U9 (0x21): right buttons + F6-F10, 4 spare
BTN_INPUTS = PB26[:U6_BUTTONS] + FKEYS[:5] + PB26[U6_BUTTONS:] + FKEYS[5:]
TCA_MAP = {}
for i, name in enumerate(BTN_INPUTS):
    TCA_MAP[name] = ("U8", TCA_PORTS[i]) if i < 16 else ("U9", TCA_PORTS[i - 16])
SPARE_EXP = [("U9", p) for p in TCA_PORTS[12:]]

# LED channels: U6 (0x3C) OUT1-33 = first 11 PB26 (R,G,B) ; U7 (0x3F) OUT1-21 = other 7 PB26, OUT22-31 = F1-F10
LED_MAP = {}
for i, name in enumerate(PB26):
    chip, base = ("U6", 3 * i) if i < U6_BUTTONS else ("U7", 3 * (i - U6_BUTTONS))
    for k, col in enumerate("RGB"):
        LED_MAP["LED_%s_%s" % (name, col)] = (chip, base + k + 1)
for i, name in enumerate(FKEYS):
    LED_MAP["LED_%s" % name] = ("U7", 3 * (len(PB26) - U6_BUTTONS) + 1 + i)


def build(prj):
    # ======================================================================
    s = prj.sheet("Power and USB", "power.kicad_sch", "Napájení a USB-C")
    s.note("USB-C 5 V (bez PD, 2x 5,1k na CC). Polyswitch omezuje proud, LED jas omezí firmware na < 500 mA celkem.\n"
           "+5V_LED napájí anody tlačítek a budiče IS31FL3236A (OUTx nesmí přesáhnout VCC+0,3 V, proto VCC = 5 V).")
    s.add(Part("J1", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
               pins={"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "A4": "VBUS", "A9": "VBUS", "B4": "VBUS",
                     "B9": "VBUS", "A5": "USB_CC1", "B5": "USB_CC2", "A6": "USB_CONN_DP", "B6": "USB_CONN_DP",
                     "A7": "USB_CONN_DM", "B7": "USB_CONN_DM", "A8": None, "B8": None, "S1": "GND"},
               lcsc="C165948", mpn="TYPE-C-31-M-12"))
    s.add(R("R1", "5.1k", "USB_CC1", "GND"))
    s.add(R("R2", "5.1k", "USB_CC2", "GND"))
    s.add(Part("U1", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
               pins={"1": "USB_CONN_DP", "6": "USB_CONN_DP", "3": "USB_CONN_DM", "4": "USB_CONN_DM",
                     "5": "VBUS", "2": "GND"}, lcsc="C7519"))
    s.add(R("R3", "27R", "USB_CONN_DP", "USB_DP"))
    s.add(R("R4", "27R", "USB_CONN_DM", "USB_DM"))
    s.add(Part("F1", "Device:Polyfuse", "0.75A", "Fuse:Fuse_1206_3216Metric", pins={"1": "VBUS", "2": "+5V"},
               lcsc="C2830242", mpn="JK-nSMD075/6V", desc="PTC resettable fuse, 0.75 A hold, 1206"))
    s.add(Part("D1", "Device:D", "SMF5.0A", "Diode_SMD:D_SOD-123F", pins={"1": "+5V", "2": "GND"}, lcsc="C2857263",
               desc="TVS 5 V unidirectional"))
    s.add(C("C1", "10uF", "+5V"))
    s.add(C("C2", "100nF", "+5V"))
    s.add(Part("FB1", "Device:FerriteBead_Small", "600R@100MHz 2A", "Inductor_SMD:L_1206_3216Metric",
               pins={"1": "+5V", "2": "+5V_LED"}, lcsc="C840591", mpn="MH3261-601Y",
               desc="Bourns, 2 A, DCR 100 mOhm (C1017 má jen 500 mA a 300 mOhm, na proud LED nestačí)"))
    s.add(C("C3", "10uF", "+5V_LED"))
    s.add(C("C4", "10uF", "+5V_LED"))
    s.add(C("C5", "100nF", "+5V_LED"))
    # LDL1117S33R has the same pinout as AMS1117 (1 GND, 2 VOUT + tab, 3 VIN)
    s.add(Part("U2", "Regulator_Linear:AMS1117-3.3", "LDL1117S33R", "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
               pins={"VI": "+5V", "GND": "GND", "VO": "+3V3"}, lcsc="C435835", mpn="LDL1117S33R",
               desc="LDO 3.3 V 1.2 A, low dropout (ST LDL1117), Cout >= 4.7 uF"))
    s.add(C("C6", "10uF", "+3V3"))
    s.add(C("C7", "100nF", "+3V3"))
    s.add(R("R5", "1k", "+3V3", "PWR_LED_A"))
    s.add(Part("D2", "Device:LED", "green", LED0603, pins={"A": "PWR_LED_A", "K": "GND"}, lcsc="?"))
    s.add(R("R6", "10k", "+5V", "VSENSE_5V"))
    s.add(R("R7", "10k", "VSENSE_5V", "GND"))
    s.add(C("C8", "100nF", "VSENSE_5V"))
    for i, net in enumerate(["VBUS", "+5V", "+5V_LED", "+3V3", "+1V1", "GND", "GND"]):
        s.add(TPt("TP%d" % (i + 1), net))
    for net in ["VBUS", "+5V", "+5V_LED", "GND"]:
        prj.flag(net, s.name)

    # ======================================================================
    s = prj.sheet("MCU", "mcu.kicad_sch", "RP2040, flash, krystal, debug")
    s.note("GPIO: viz hardware/DESIGN.md. SPI0 = W5500 (jako W5500-EVB-Pico), I2C1 = LED budiče + expandéry,\n"
           "SPI1 = páka (MT6701 SSI), GP2/GP3 = jog A/B pro PIO kvadraturní dekodér.")
    gp = {0: "UART_TX", 1: "UART_RX", 2: "JOG_A", 3: "JOG_B", 4: "JOG_Z", 5: "JOG_MODE", 6: "I2C_SDA",
          7: "I2C_SCL", 8: "LED_SDB", 9: "BTN_INT", 10: "GP10", 11: "GP11", 12: "LEV_DO", 13: "LEV_CSN",
          14: "LEV_CLK", 15: "LEV_MODE", 16: "ETH_MISO", 17: "ETH_CS", 18: "ETH_SCK", 19: "ETH_MOSI",
          20: "ETH_RST", 21: "ETH_INT", 22: "GP22", 23: "GP23", 24: "GP24", 25: "STATUS_LED",
          26: "LEV_OUT", 27: "JOG_OUT", 28: "GP28", 29: "VSENSE_5V"}
    pins = {"IOVDD": "+3V3", "ADC_AVDD": "+3V3", "VREG_VIN": "+3V3", "USB_VDD": "+3V3", "VREG_VOUT": "+1V1",
            "DVDD": "+1V1", "GND": "GND", "TESTEN": "GND", "XIN": "XIN", "XOUT": "XOUT", "SWCLK": "SWCLK",
            "SWDIO": "SWDIO", "RUN": "RUN", "USB_DM": "USB_DM", "USB_DP": "USB_DP", "QSPI_SD0": "QSPI_SD0",
            "QSPI_SD1": "QSPI_SD1", "QSPI_SD2": "QSPI_SD2", "QSPI_SD3": "QSPI_SD3", "QSPI_SCLK": "QSPI_SCLK",
            "~{QSPI_SS}": "QSPI_SS"}
    for g, net in gp.items():
        pins["GPIO%d" % g if g < 26 else "GPIO%d/ADC%d" % (g, g - 26)] = net
    s.add(Part("U3", "MCU_RaspberryPi:RP2040", "RP2040", "Package_DFN_QFN:QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm",
               pins=pins, lcsc="C2040"))
    n = 10
    for i in range(6):
        s.add(C("C%d" % n, "100nF", "+3V3")); n += 1          # IOVDD x6
    s.add(C("C%d" % n, "100nF", "+3V3")); n += 1              # ADC_AVDD
    s.add(C("C%d" % n, "100nF", "+3V3")); n += 1              # USB_VDD
    s.add(C("C%d" % n, "1uF", "+3V3")); n += 1                # VREG_VIN
    s.add(C("C%d" % n, "1uF", "+1V1")); n += 1                # VREG_VOUT
    s.add(C("C%d" % n, "100nF", "+1V1")); n += 1              # DVDD
    s.add(C("C%d" % n, "100nF", "+1V1")); n += 1              # DVDD
    s.add(C("C%d" % n, "10uF", "+3V3")); n += 1               # bulk
    s.add(Part("Y1", "Device:Crystal_GND24", "12MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
               pins={"1": "XIN", "3": "XTAL_OUT", "2": "GND", "4": "GND"}, lcsc="C20625731", mpn="ABM8-272-T3",
               desc="12 MHz, CL 10 pF, ESR 50R, +-30 ppm; krystal doporučený v Hardware design with RP2040"))
    s.add(R("R10", "1k", "XOUT", "XTAL_OUT"))
    s.add(C("C%d" % n, "15pF", "XIN")); n += 1      # CL 10 pF: 15/2 + ~3 pF parazitní = 10,5 pF (C0G)
    s.add(C("C%d" % n, "15pF", "XTAL_OUT")); n += 1
    s.add(Part("U4", "Memory_Flash:W25Q128JVS", "W25Q128JVSIQ", "Package_SO:SOIC-8_5.3x5.3mm_P1.27mm",
               pins={"1": "QSPI_SS", "2": "QSPI_SD1", "3": "QSPI_SD2", "4": "GND", "5": "QSPI_SD0",
                     "6": "QSPI_SCLK", "7": "QSPI_SD3", "8": "+3V3"}, lcsc="C97521"))
    s.add(C("C%d" % n, "100nF", "+3V3")); n += 1
    s.add(R("R11", "1k", "QSPI_SS", "BOOTSEL"))
    s.add(Part("SW1", "Switch:SW_Push", "BOOTSEL", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A",
               pins={"1": "BOOTSEL", "2": "GND"}, lcsc="C318884"))
    s.add(R("R12", "10k", "+3V3", "RUN"))
    s.add(Part("SW2", "Switch:SW_Push", "RESET", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A",
               pins={"1": "RUN", "2": "GND"}, lcsc="C318884"))
    s.add(R("R13", "220R", "STATUS_LED", "STATUS_LED_A"))   # modrá Vf ~2,9 V -> ~2 mA
    s.add(Part("D3", "Device:LED", "blue", LED0603, pins={"A": "STATUS_LED_A", "K": "GND"}, lcsc="?"))
    s.add(Part("J2", "Connector_Generic:Conn_01x07", "DEBUG", "Connector_PinHeader_2.54mm:PinHeader_1x07_P2.54mm_Vertical",
               pins={"1": "+3V3", "2": "SWCLK", "3": "SWDIO", "4": "GND", "5": "RUN", "6": "UART_TX", "7": "UART_RX"},
               in_bom=False, desc="SWD + UART debug header (osadit ručně jen při ladění)"))
    exp = {"1": "+5V", "2": "+3V3", "3": "GND", "4": "GND", "5": "GP10", "6": "GP11", "7": "GP22", "8": "GP23",
           "9": "GP24", "10": "GP28", "15": "I2C_SDA", "16": "I2C_SCL"}
    for k, (chip, port) in enumerate(SPARE_EXP):
        exp[str(11 + k)] = "EXP_%s" % port
    s.add(Part("J3", "Connector_Generic:Conn_02x08_Odd_Even", "EXPANSION",
               "Connector_PinHeader_2.54mm:PinHeader_2x08_P2.54mm_Vertical", pins=exp, in_bom=False,
               desc="Rezervní GPIO, I2C a volné vstupy expandéru"))
    prj.flag("+1V1", s.name) if False else None

    # ======================================================================
    s = prj.sheet("Ethernet", "ethernet.kicad_sch", "W5500 + RJ45 HR911105A")
    s.note("Analogová část podle referenčního zapojení WIZnet W5500 (33R série, 49,9R terminace, 6,8nF na RX).")
    s.add(Part("U5", "Interface_Ethernet:W5500", "W5500", "Package_QFP:LQFP-48_7x7mm_P0.5mm",
               pins={"AVDD": "+3V3A", "AGND": "GND", "VDD": "+3V3", "GND": "GND", "TXN": "W_TXN", "TXP": "W_TXP",
                     "RXN": "W_RXN", "RXP": "W_RXP", "EXRES1": "W_EXRES", "VBG": None, "TOCAP": "W_TOCAP",
                     "1V2O": "W_1V2O", "RSVD": "GND", "SPDLED": None, "LINKLED": "W_LINKLED", "DUPLED": None,
                     "ACTLED": "W_ACTLED", "XI/CLKIN": "W_XI", "XO": "W_XO", "~{SCS}": "ETH_CS", "SCLK": "ETH_SCK",
                     "MISO": "ETH_MISO", "MOSI": "ETH_MOSI", "~{INT}": "ETH_INT", "~{RST}": "ETH_RST",
                     "PMODE0": "+3V3", "PMODE1": "+3V3", "PMODE2": "+3V3"}, lcsc="C32843"))
    s.add(Part("FB2", "Device:FerriteBead_Small", "600R@100MHz", L0805, pins={"1": "+3V3", "2": "+3V3A"}, lcsc="C1017"))
    n = 40
    s.add(C("C%d" % n, "10uF", "+3V3A")); n += 1
    for i in range(6):
        s.add(C("C%d" % n, "100nF", "+3V3A")); n += 1
    s.add(C("C%d" % n, "100nF", "+3V3")); n += 1
    s.add(C("C%d" % n, "4.7uF", "W_TOCAP")); n += 1
    s.add(C("C%d" % n, "10nF", "W_1V2O")); n += 1
    s.add(R("R20", "12.4k 1%", "W_EXRES", "GND"))
    s.add(Part("Y2", "Device:Crystal_GND24", "25MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
               pins={"1": "W_XI", "3": "W_XO", "2": "GND", "4": "GND"}, lcsc="C9006", mpn="X322525MOB4SI (CL 12 pF)"))
    s.add(C("C%d" % n, "15pF", "W_XI")); n += 1    # CL 12 pF crystal
    s.add(C("C%d" % n, "15pF", "W_XO")); n += 1
    s.add(R("R21", "1M", "W_XI", "W_XO"))
    s.add(R("R22", "10k", "+3V3", "ETH_INT"))
    s.add(R("R23", "10k", "+3V3", "ETH_RST"))
    # TX
    s.add(R("R24", "33R", "W_TXP", "ETH_TDP"))
    s.add(R("R25", "33R", "W_TXN", "ETH_TDN"))
    s.add(R("R26", "49.9R 1%", "ETH_TDP", "+3V3A"))
    s.add(R("R27", "49.9R 1%", "ETH_TDN", "+3V3A"))
    s.add(R("R28", "10R", "+3V3A", "ETH_TCT"))
    s.add(C("C%d" % n, "22nF", "ETH_TCT")); n += 1
    # RX
    s.add(R("R29", "33R", "W_RXP", "ETH_RXP_T"))
    s.add(R("R30", "33R", "W_RXN", "ETH_RXN_T"))
    s.add(R("R31", "49.9R 1%", "ETH_RXP_T", "ETH_RCT"))
    s.add(R("R32", "49.9R 1%", "ETH_RXN_T", "ETH_RCT"))
    s.add(C("C%d" % n, "6.8nF", "ETH_RXP_T", "ETH_RDP")); n += 1
    s.add(C("C%d" % n, "6.8nF", "ETH_RXN_T", "ETH_RDN")); n += 1
    s.add(C("C%d" % n, "10nF", "ETH_RCT")); n += 1
    # LEDs
    # LED anody 12 a 9 na +3V3, katody 11 a 10 přes 330R do W5500 (aktivní v nule, max. 8 mA)
    s.add(R("R33", "330R", "W_LINKLED", "ETH_LINK_K"))
    s.add(R("R34", "330R", "W_ACTLED", "ETH_ACT_K"))
    s.add(Part("J4", "Connector:RJ45_Hanrun_HR911105A_Horizontal", "HR911105A", "Connector_RJ:RJ45_Hanrun_HR911105A_Horizontal",
               pins={"1": "ETH_TDP", "2": "ETH_TDN", "3": "ETH_RDP", "4": "ETH_TCT", "5": "ETH_RCT", "6": "ETH_RDN",
                     "8": "GND", "9": "+3V3", "10": "ETH_ACT_K", "11": "ETH_LINK_K", "12": "+3V3", "SH": "GND"},
               lcsc="C12074"))
    prj.flag("+3V3A", s.name)

    # ======================================================================
    s = prj.sheet("LED drivers", "leds.kicad_sch", "2x IS31FL3236A")
    s.note("I_MAX = 58,5 x 1,3 V / R_EXT = 19,5 mA pro R_EXT 3,9k. Jas a celkový odběr omezuje firmware.\n"
           "U6 adresa 0x3C (AD=GND), U7 0x3F (AD=VCC). SDB stažený do nuly: LED po startu zhasnuté.")
    for chip, ad in (("U6", "GND"), ("U7", "+5V_LED")):
        pins = {"VCC": "+5V_LED", "GND": "GND", "EP": "GND", "SDA": "I2C_SDA", "SCL": "I2C_SCL",
                "~{SDB}": "LED_SDB", "AD": ad, "R_EXT": "%s_REXT" % chip}
        for k in range(1, 37):
            pins["OUT%d" % k] = None
        for net, (c, ch) in LED_MAP.items():
            if c == chip:
                pins["OUT%d" % ch] = net
        s.add(Part(chip, "vrc:IS31FL3236A-QFN44", "IS31FL3236A", "vrc:QFN-44-1EP_5x5mm_P0.4mm",
                   pins=pins, lcsc="C246443", mpn="IS31FL3236A-QFLS2-TR"))
    s.add(R("R40", "3.9k 1%", "U6_REXT", "GND"))
    s.add(R("R41", "3.9k 1%", "U7_REXT", "GND"))
    n = 60
    for i in range(2):
        s.add(C("C%d" % n, "1uF", "+5V_LED")); n += 1
        s.add(C("C%d" % n, "100nF", "+5V_LED")); n += 1
    s.add(R("R42", "100k", "LED_SDB", "GND"))
    s.add(R("R43", "2.2k", "+3V3", "I2C_SDA"))
    s.add(R("R44", "2.2k", "+3V3", "I2C_SCL"))
    for i, net in enumerate(["I2C_SDA", "I2C_SCL", "LED_SDB", "BTN_INT"]):
        s.add(TPt("TP%d" % (10 + i), net))

    # ======================================================================
    s = prj.sheet("Buttons", "buttons.kicad_sch", "Tlačítka PB26 RGB a TS5")
    s.note("Tlačítka se pájí ručně. Spínač: COM = GND, NO = vstup expandéru (interní pull-up 100k).\n"
           "LED: společná anoda na +5V_LED, katody na kanály IS31FL3236A.")
    for i, name in enumerate(PB26):
        s.add(Part("SW%d" % (10 + i), "vrc:PB26-13M-RGB", name, "vrc:PB26-13M-RGB",
                   pins={"1": "GND", "2": "BTN_%s" % name, "3": None, "A": "+5V_LED",
                         "R": "LED_%s_R" % name, "G": "LED_%s_G" % name, "B": "LED_%s_B" % name},
                   mpn="PB26-13M-B-WT-RGB-N", in_bom=False, fields={"Assembly": "ruční pájení"}))
    for i, name in enumerate(FKEYS):
        s.add(Part("SW%d" % (30 + i), "vrc:TS5-LED", name, "vrc:TS5-9.2mm-LED",
                   pins={"1": "GND", "2": "GND", "3": "BTN_%s" % name, "4": "BTN_%s" % name,
                         "6": "+5V_LED", "5": "LED_%s" % name},
                   mpn="TS5 yellow", in_bom=False, fields={"Assembly": "ruční pájení"}))

    s = prj.sheet("Inputs", "inputs.kicad_sch", "2x TCA9555 expandér")
    s.note("U8 adresa 0x20, U9 0x21. INT (open drain) společný, pull-up R50.")
    for chip, a0 in (("U8", "GND"), ("U9", "+3V3")):
        pins = {"VCC": "+3V3", "GND": "GND", "EPAD": "GND", "SCL": "I2C_SCL", "SDA": "I2C_SDA",
                "~{INT}": "BTN_INT", "A0": a0, "A1": "GND", "A2": "GND"}
        for name, (c, port) in TCA_MAP.items():
            if c == chip:
                pins[port] = "BTN_%s" % name
        for c, port in SPARE_EXP:
            if c == chip:
                pins[port] = "EXP_%s" % port
        s.add(Part(chip, "Interface_Expansion:TCA9555RTWR", "TCA9555RTWR",
                   "Package_DFN_QFN:Texas_RTW_WQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm", pins=pins, lcsc="C140277"))
    s.add(C("C70", "100nF", "+3V3"))
    s.add(C("C71", "100nF", "+3V3"))
    s.add(R("R50", "10k", "+3V3", "BTN_INT"))

    # ======================================================================
    s = prj.sheet("Sensors", "sensors.kicad_sch", "Konektory páky a jogu (MT6701)")
    s.note("Stejný 8pin konektor pro obě senzorové destičky s MT6701 (SOP-8):\n"
           "1 +3V3, 2 GND, 3 MODE, 4 P6 = A/SDA/DO, 5 P7 = B/SCL/CLK, 6 P8 = Z/CSN, 7 OUT (analog/PWM), 8 GND.\n"
           "MODE řídí MCU: přepíná ABZ a I2C/SSI (programování EEPROM, čtení úhlu). OUT jde do ADC jako záloha.")
    n = 80
    rn = 60
    for pre, ref, nets in (("LEV", "J5", ("LEV_MODE", "LEV_DO", "LEV_CLK", "LEV_CSN", "LEV_OUT")),
                           ("JOG", "J6", ("JOG_MODE", "JOG_A", "JOG_B", "JOG_Z", "JOG_OUT"))):
        mode, p6, p7, p8, out = nets
        s.add(Part(ref, "Connector_Generic_MountingPin:Conn_01x08_MountingPin", "LEVER" if pre == "LEV" else "JOG",
                   "Connector_JST:JST_PH_S8B-PH-SM4-TB_1x08-1MP_P2.00mm_Horizontal",
                   pins={"1": "+3V3", "2": "GND", "3": pre + "_C_MODE", "4": pre + "_C_P6", "5": pre + "_C_P7",
                         "6": pre + "_C_P8", "7": pre + "_C_OUT", "8": "GND", "MP": "GND"}, lcsc="C265121",
                   mpn="S8B-PH-SM4-TB"))
        for net, cn in ((mode, "_C_MODE"), (p6, "_C_P6"), (p7, "_C_P7"), (p8, "_C_P8")):
            s.add(R("R%d" % rn, "33R", net, pre + cn)); rn += 1
        for cn in ("_C_P6", "_C_P7", "_C_P8"):
            s.add(R("R%d" % rn, "10k", "+3V3", pre + cn)); rn += 1
        s.add(R("R%d" % rn, "1k", pre + "_C_OUT", out)); rn += 1
        s.add(C("C%d" % n, "10nF", out)); n += 1
        s.add(C("C%d" % n, "1uF", "+3V3")); n += 1
