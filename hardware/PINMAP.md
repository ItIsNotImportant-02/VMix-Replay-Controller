# Přiřazení pinů (generováno z tools/circuit.py, needitovat ručně)

## RP2040 GPIO

| GPIO | Síť |
|---|---|
| GP0 | `UART_TX` |
| GP1 | `UART_RX` |
| GP2 | `GP2` |
| GP3 | `GP3` |
| GP4 | `GP4` |
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
| GP22 | `JOG_DO` |
| GP23 | `JOG_CLK` |
| GP24 | `JOG_CSN` |
| GP25 | `STATUS_LED` |
| GP26 | `LEV_OUT` |
| GP27 | `JOG_OUT` |
| GP28 | `GP28` |
| GP29 | `VSENSE_5V` |

## Tlačítka → TCA9555

| Tlačítko | Expandér | Port |
|---|---|---|
| BROWSE | U8 (0x20) | P05 |
| CAM_A | U8 (0x20) | P04 |
| CAM_B | U8 (0x20) | P03 |
| CAM_C | U8 (0x20) | P00 |
| CAM_D | U9 (0x21) | P13 |
| CLEAR | U9 (0x21) | P03 |
| ENTER | U9 (0x21) | P01 |
| F1 | U8 (0x20) | P02 |
| F10 | U9 (0x21) | P17 |
| F2 | U8 (0x20) | P17 |
| F3 | U8 (0x20) | P16 |
| F4 | U9 (0x21) | P11 |
| F5 | U9 (0x21) | P10 |
| F6 | U9 (0x21) | P07 |
| F7 | U9 (0x21) | P06 |
| F8 | U9 (0x21) | P04 |
| F9 | U9 (0x21) | P02 |
| IN | U8 (0x20) | P12 |
| LAST_CUE | U9 (0x21) | P00 |
| MARK | U9 (0x21) | P15 |
| MENU | U8 (0x20) | P01 |
| OUT | U8 (0x20) | P13 |
| PLAY | U9 (0x21) | P05 |
| PLST | U8 (0x20) | P15 |
| PRV_CTL | U9 (0x21) | P14 |
| RECORD | U9 (0x21) | P16 |
| SHIFT | U9 (0x21) | P12 |
| TAKE | U8 (0x20) | P14 |
| (volné, na J3) | U8 (0x20) | P06 |
| (volné, na J3) | U8 (0x20) | P07 |
| (volné, na J3) | U8 (0x20) | P10 |
| (volné, na J3) | U8 (0x20) | P11 |

## LED → IS31FL3236A

| LED | Budič | Kanál |
|---|---|---|
| F7 | U6 (0x3C) | OUT1 |
| CLEAR_R | U6 (0x3C) | OUT2 |
| CLEAR_G | U6 (0x3C) | OUT3 |
| CLEAR_B | U6 (0x3C) | OUT4 |
| F6 | U6 (0x3C) | OUT5 |
| F5 | U6 (0x3C) | OUT6 |
| SHIFT_G | U6 (0x3C) | OUT7 |
| SHIFT_R | U6 (0x3C) | OUT8 |
| SHIFT_B | U6 (0x3C) | OUT9 |
| F4 | U6 (0x3C) | OUT10 |
| MENU_G | U6 (0x3C) | OUT11 |
| MENU_B | U6 (0x3C) | OUT12 |
| MENU_R | U6 (0x3C) | OUT13 |
| F3 | U6 (0x3C) | OUT14 |
| F2 | U6 (0x3C) | OUT15 |
| F1 | U6 (0x3C) | OUT16 |
| CAM_A_B | U6 (0x3C) | OUT18 |
| CAM_A_G | U6 (0x3C) | OUT19 |
| CAM_A_R | U6 (0x3C) | OUT20 |
| CAM_B_B | U6 (0x3C) | OUT21 |
| CAM_B_G | U6 (0x3C) | OUT22 |
| CAM_B_R | U6 (0x3C) | OUT23 |
| CAM_C_G | U6 (0x3C) | OUT24 |
| CAM_C_B | U6 (0x3C) | OUT25 |
| CAM_C_R | U6 (0x3C) | OUT26 |
| CAM_D_B | U6 (0x3C) | OUT27 |
| CAM_D_G | U6 (0x3C) | OUT28 |
| CAM_D_R | U6 (0x3C) | OUT29 |
| PLST_B | U6 (0x3C) | OUT30 |
| PLST_G | U6 (0x3C) | OUT31 |
| PLST_R | U6 (0x3C) | OUT32 |
| BROWSE_B | U6 (0x3C) | OUT33 |
| BROWSE_G | U6 (0x3C) | OUT34 |
| BROWSE_R | U6 (0x3C) | OUT35 |
| F8 | U6 (0x3C) | OUT36 |
| TAKE_B | U7 (0x3F) | OUT1 |
| TAKE_G | U7 (0x3F) | OUT2 |
| TAKE_R | U7 (0x3F) | OUT3 |
| PRV_CTL_R | U7 (0x3F) | OUT4 |
| PRV_CTL_G | U7 (0x3F) | OUT5 |
| PRV_CTL_B | U7 (0x3F) | OUT6 |
| MARK_R | U7 (0x3F) | OUT7 |
| MARK_G | U7 (0x3F) | OUT8 |
| MARK_B | U7 (0x3F) | OUT9 |
| F10 | U7 (0x3F) | OUT10 |
| ENTER_R | U7 (0x3F) | OUT11 |
| ENTER_G | U7 (0x3F) | OUT12 |
| ENTER_B | U7 (0x3F) | OUT13 |
| F9 | U7 (0x3F) | OUT14 |
| LAST_CUE_R | U7 (0x3F) | OUT15 |
| LAST_CUE_G | U7 (0x3F) | OUT16 |
| LAST_CUE_B | U7 (0x3F) | OUT17 |
| RECORD_R | U7 (0x3F) | OUT18 |
| RECORD_G | U7 (0x3F) | OUT19 |
| RECORD_B | U7 (0x3F) | OUT20 |
| PLAY_G | U7 (0x3F) | OUT21 |
| PLAY_R | U7 (0x3F) | OUT22 |
| PLAY_B | U7 (0x3F) | OUT23 |
| IN_B | U7 (0x3F) | OUT31 |
| IN_G | U7 (0x3F) | OUT32 |
| IN_R | U7 (0x3F) | OUT33 |
| OUT_B | U7 (0x3F) | OUT34 |
| OUT_G | U7 (0x3F) | OUT35 |
| OUT_R | U7 (0x3F) | OUT36 |
