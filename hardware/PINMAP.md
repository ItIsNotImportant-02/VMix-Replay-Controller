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
| BROWSE | U8 (0x20) | P10 |
| CAM_A | U9 (0x21) | P14 |
| CAM_B | U9 (0x21) | P15 |
| CAM_C | U9 (0x21) | P16 |
| CAM_D | U9 (0x21) | P17 |
| CLEAR | U9 (0x21) | P07 |
| ENTER | U9 (0x21) | P06 |
| F1 | U9 (0x21) | P13 |
| F10 | U9 (0x21) | P03 |
| F2 | U9 (0x21) | P12 |
| F3 | U9 (0x21) | P11 |
| F4 | U8 (0x20) | P01 |
| F5 | U8 (0x20) | P00 |
| F6 | U8 (0x20) | P17 |
| F7 | U8 (0x20) | P16 |
| F8 | U9 (0x21) | P05 |
| F9 | U9 (0x21) | P04 |
| IN | U8 (0x20) | P11 |
| LAST_CUE | U9 (0x21) | P01 |
| MARK | U9 (0x21) | P02 |
| MENU | U9 (0x21) | P10 |
| OUT | U8 (0x20) | P12 |
| PLAY | U9 (0x21) | P00 |
| PLST | U8 (0x20) | P03 |
| PRV_CTL | U8 (0x20) | P14 |
| RECORD | U8 (0x20) | P15 |
| SHIFT | U8 (0x20) | P02 |
| TAKE | U8 (0x20) | P13 |
| (volné, na J3) | U8 (0x20) | P04 |
| (volné, na J3) | U8 (0x20) | P05 |
| (volné, na J3) | U8 (0x20) | P06 |
| (volné, na J3) | U8 (0x20) | P07 |

## LED → IS31FL3236A

| LED | Budič | Kanál |
|---|---|---|
| PLST_G | U6 (0x3C) | OUT1 |
| CAM_D_G | U6 (0x3C) | OUT2 |
| CAM_D_R | U6 (0x3C) | OUT3 |
| CAM_D_B | U6 (0x3C) | OUT4 |
| BROWSE_G | U6 (0x3C) | OUT5 |
| BROWSE_R | U6 (0x3C) | OUT6 |
| BROWSE_B | U6 (0x3C) | OUT7 |
| F3 | U6 (0x3C) | OUT8 |
| SHIFT_G | U6 (0x3C) | OUT9 |
| SHIFT_R | U6 (0x3C) | OUT10 |
| SHIFT_B | U6 (0x3C) | OUT11 |
| CAM_C_G | U6 (0x3C) | OUT12 |
| CAM_C_R | U6 (0x3C) | OUT13 |
| CAM_C_B | U6 (0x3C) | OUT14 |
| F2 | U6 (0x3C) | OUT15 |
| MENU_G | U6 (0x3C) | OUT16 |
| MENU_R | U6 (0x3C) | OUT17 |
| MENU_B | U6 (0x3C) | OUT18 |
| F1 | U6 (0x3C) | OUT19 |
| CAM_B_G | U6 (0x3C) | OUT20 |
| CAM_B_R | U6 (0x3C) | OUT21 |
| CAM_B_B | U6 (0x3C) | OUT22 |
| CAM_A_R | U6 (0x3C) | OUT23 |
| CAM_A_B | U6 (0x3C) | OUT24 |
| CAM_A_G | U6 (0x3C) | OUT25 |
| IN_B | U6 (0x3C) | OUT26 |
| IN_R | U6 (0x3C) | OUT27 |
| IN_G | U6 (0x3C) | OUT28 |
| OUT_B | U6 (0x3C) | OUT29 |
| OUT_G | U6 (0x3C) | OUT30 |
| OUT_R | U6 (0x3C) | OUT31 |
| TAKE_B | U6 (0x3C) | OUT32 |
| TAKE_G | U6 (0x3C) | OUT33 |
| TAKE_R | U6 (0x3C) | OUT34 |
| PLST_B | U6 (0x3C) | OUT35 |
| PLST_R | U6 (0x3C) | OUT36 |
| PRV_CTL_B | U7 (0x3F) | OUT2 |
| PRV_CTL_R | U7 (0x3F) | OUT3 |
| PRV_CTL_G | U7 (0x3F) | OUT4 |
| MARK_R | U7 (0x3F) | OUT5 |
| MARK_G | U7 (0x3F) | OUT6 |
| MARK_B | U7 (0x3F) | OUT7 |
| F10 | U7 (0x3F) | OUT8 |
| ENTER_R | U7 (0x3F) | OUT9 |
| ENTER_G | U7 (0x3F) | OUT10 |
| ENTER_B | U7 (0x3F) | OUT11 |
| F9 | U7 (0x3F) | OUT12 |
| LAST_CUE_R | U7 (0x3F) | OUT13 |
| LAST_CUE_G | U7 (0x3F) | OUT14 |
| LAST_CUE_B | U7 (0x3F) | OUT15 |
| CLEAR_R | U7 (0x3F) | OUT16 |
| CLEAR_G | U7 (0x3F) | OUT17 |
| CLEAR_B | U7 (0x3F) | OUT18 |
| F8 | U7 (0x3F) | OUT19 |
| F7 | U7 (0x3F) | OUT20 |
| PLAY_G | U7 (0x3F) | OUT21 |
| PLAY_R | U7 (0x3F) | OUT22 |
| PLAY_B | U7 (0x3F) | OUT23 |
| RECORD_G | U7 (0x3F) | OUT24 |
| RECORD_R | U7 (0x3F) | OUT25 |
| RECORD_B | U7 (0x3F) | OUT26 |
| F6 | U7 (0x3F) | OUT27 |
| F5 | U7 (0x3F) | OUT28 |
| F4 | U7 (0x3F) | OUT29 |
