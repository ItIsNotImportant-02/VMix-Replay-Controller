# Přiřazení pinů (generováno z tools/circuit.py, needitovat ručně)

## RP2040 GPIO

| GPIO | Síť |
|---|---|
| GP0 | `UART_TX` |
| GP1 | `UART_RX` |
| GP2 | `JOG_A` |
| GP3 | `JOG_B` |
| GP4 | `JOG_Z` |
| GP5 | `JOG_MODE` |
| GP6 | `I2C_SDA` |
| GP7 | `I2C_SCL` |
| GP8 | `LED_SDB` |
| GP9 | `BTN_INT` |
| GP10 | `GP10` |
| GP11 | `GP11` |
| GP12 | `LEV_DO` |
| GP13 | `LEV_CSN` |
| GP14 | `LEV_CLK` |
| GP15 | `LEV_MODE` |
| GP16 | `ETH_MISO` |
| GP17 | `ETH_CS` |
| GP18 | `ETH_SCK` |
| GP19 | `ETH_MOSI` |
| GP20 | `ETH_RST` |
| GP21 | `ETH_INT` |
| GP22 | `GP22` |
| GP23 | `GP23` |
| GP24 | `GP24` |
| GP25 | `STATUS_LED` |
| GP26 | `LEV_OUT` |
| GP27 | `JOG_OUT` |
| GP28 | `GP28` |
| GP29 | `VSENSE_5V` |

## Tlačítka → TCA9555

| Tlačítko | Expandér | Port |
|---|---|---|
| MENU | U8 (0x20) | P00 |
| SHIFT | U8 (0x20) | P01 |
| CLEAR | U8 (0x20) | P02 |
| ENTER | U8 (0x20) | P03 |
| CAM_A | U8 (0x20) | P04 |
| CAM_B | U8 (0x20) | P05 |
| CAM_C | U8 (0x20) | P06 |
| CAM_D | U8 (0x20) | P07 |
| PLST | U8 (0x20) | P10 |
| BROWSE | U8 (0x20) | P11 |
| IN | U8 (0x20) | P12 |
| OUT | U8 (0x20) | P13 |
| TAKE | U8 (0x20) | P14 |
| PLAY | U8 (0x20) | P15 |
| LAST_CUE | U8 (0x20) | P16 |
| MARK | U8 (0x20) | P17 |
| RECORD | U9 (0x21) | P00 |
| PRV_CTL | U9 (0x21) | P01 |
| F1 | U9 (0x21) | P02 |
| F2 | U9 (0x21) | P03 |
| F3 | U9 (0x21) | P04 |
| F4 | U9 (0x21) | P05 |
| F5 | U9 (0x21) | P06 |
| F6 | U9 (0x21) | P07 |
| F7 | U9 (0x21) | P10 |
| F8 | U9 (0x21) | P11 |
| F9 | U9 (0x21) | P12 |
| F10 | U9 (0x21) | P13 |
| (volné, na J3) | U9 (0x21) | P14 |
| (volné, na J3) | U9 (0x21) | P15 |
| (volné, na J3) | U9 (0x21) | P16 |
| (volné, na J3) | U9 (0x21) | P17 |

## LED → IS31FL3236A

| LED | Budič | Kanál |
|---|---|---|
| MENU_R | U6 (0x3C) | OUT1 |
| MENU_G | U6 (0x3C) | OUT2 |
| MENU_B | U6 (0x3C) | OUT3 |
| SHIFT_R | U6 (0x3C) | OUT4 |
| SHIFT_G | U6 (0x3C) | OUT5 |
| SHIFT_B | U6 (0x3C) | OUT6 |
| CLEAR_R | U6 (0x3C) | OUT7 |
| CLEAR_G | U6 (0x3C) | OUT8 |
| CLEAR_B | U6 (0x3C) | OUT9 |
| ENTER_R | U6 (0x3C) | OUT10 |
| ENTER_G | U6 (0x3C) | OUT11 |
| ENTER_B | U6 (0x3C) | OUT12 |
| CAM_A_R | U6 (0x3C) | OUT13 |
| CAM_A_G | U6 (0x3C) | OUT14 |
| CAM_A_B | U6 (0x3C) | OUT15 |
| CAM_B_R | U6 (0x3C) | OUT16 |
| CAM_B_G | U6 (0x3C) | OUT17 |
| CAM_B_B | U6 (0x3C) | OUT18 |
| CAM_C_R | U6 (0x3C) | OUT19 |
| CAM_C_G | U6 (0x3C) | OUT20 |
| CAM_C_B | U6 (0x3C) | OUT21 |
| CAM_D_R | U6 (0x3C) | OUT22 |
| CAM_D_G | U6 (0x3C) | OUT23 |
| CAM_D_B | U6 (0x3C) | OUT24 |
| PLST_R | U6 (0x3C) | OUT25 |
| PLST_G | U6 (0x3C) | OUT26 |
| PLST_B | U6 (0x3C) | OUT27 |
| BROWSE_R | U6 (0x3C) | OUT28 |
| BROWSE_G | U6 (0x3C) | OUT29 |
| BROWSE_B | U6 (0x3C) | OUT30 |
| IN_R | U6 (0x3C) | OUT31 |
| IN_G | U6 (0x3C) | OUT32 |
| IN_B | U6 (0x3C) | OUT33 |
| OUT_R | U6 (0x3C) | OUT34 |
| OUT_G | U6 (0x3C) | OUT35 |
| OUT_B | U6 (0x3C) | OUT36 |
| TAKE_R | U7 (0x3F) | OUT1 |
| TAKE_G | U7 (0x3F) | OUT2 |
| TAKE_B | U7 (0x3F) | OUT3 |
| PLAY_R | U7 (0x3F) | OUT4 |
| PLAY_G | U7 (0x3F) | OUT5 |
| PLAY_B | U7 (0x3F) | OUT6 |
| LAST_CUE_R | U7 (0x3F) | OUT7 |
| LAST_CUE_G | U7 (0x3F) | OUT8 |
| LAST_CUE_B | U7 (0x3F) | OUT9 |
| MARK_R | U7 (0x3F) | OUT10 |
| MARK_G | U7 (0x3F) | OUT11 |
| MARK_B | U7 (0x3F) | OUT12 |
| RECORD_R | U7 (0x3F) | OUT13 |
| RECORD_G | U7 (0x3F) | OUT14 |
| RECORD_B | U7 (0x3F) | OUT15 |
| PRV_CTL_R | U7 (0x3F) | OUT16 |
| PRV_CTL_G | U7 (0x3F) | OUT17 |
| PRV_CTL_B | U7 (0x3F) | OUT18 |
| F1 | U7 (0x3F) | OUT19 |
| F2 | U7 (0x3F) | OUT20 |
| F3 | U7 (0x3F) | OUT21 |
| F4 | U7 (0x3F) | OUT22 |
| F5 | U7 (0x3F) | OUT23 |
| F6 | U7 (0x3F) | OUT24 |
| F7 | U7 (0x3F) | OUT25 |
| F8 | U7 (0x3F) | OUT26 |
| F9 | U7 (0x3F) | OUT27 |
| F10 | U7 (0x3F) | OUT28 |
