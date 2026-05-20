/*
 * Waveshare ESP32-P4-WIFI6-Touch-LCD-4B 板级配置
 *
 * 硬件特性:
 *   - ESP32-P4R16 (16MB PSRAM, 16MB Flash)
 *   - 4" 720×720 IPS LCD (MIPI DSI / RGB 接口)
 *   - GT911 电容触摸 (I2C 0x5D)
 *   - ESP32-C6 WiFi 6 协处理器
 *   - DVP 摄像头接口 (OV2640/OV5640)
 *   - microSD 卡槽 (SPI/MMC)
 *   - I2S MEMS 麦克风接口
 *   - USB Type-C 烧录/调试
 */

#ifndef MICROPY_HW_BOARD_NAME
#define MICROPY_HW_BOARD_NAME "ESP32-P4-WIFI6-Touch-LCD-4B"
#endif

#ifndef MICROPY_HW_MCU_NAME
#define MICROPY_HW_MCU_NAME       "ESP32-P4"
#endif

/* ---- Flash / PSRAM ---- */
#define MICROPY_HW_FLASH_SIZE      (16 * 1024 * 1024)
#define MICROPY_HW_PSRAM_SIZE      (16 * 1024 * 1024)

/* ---- 时钟 ---- */
#define MICROPY_HW_CLK_CPU_FREQ    (400000000)  /* 400 MHz */

/* ---- 显示屏 — ILI9881C 控制器 ---- */
/* MIPI DSI 或 SPI+RGB 接口，具体取决于 Waveshare 硬件版本          */
/* 若使用 RGB 接口，需要帧缓冲区和 DMA 传输，同时开启 LVGL 支持      */
#define MICROPY_HW_LCD_ENABLED     (1)
#define MICROPY_HW_LCD_WIDTH       (720)
#define MICROPY_HW_LCD_HEIGHT      (720)

/* ---- 触摸 — GT911 I2C ---- */
#define MICROPY_HW_TOUCH_ENABLED   (1)
#define MICROPY_HW_TOUCH_I2C_NUM   (0)
#define MICROPY_HW_TOUCH_I2C_ADDR  (0x5D)

/* ---- 摄像头 — DVP 接口 ---- */
#define MICROPY_HW_CAMERA_ENABLED  (1)

/* ---- SD 卡 — SDMMC ---- */
#define MICROPY_HW_SDCARD_ENABLED  (1)

/* ---- WiFi 协处理器 — ESP32-C6 (通过 SDIO/SPI) ---- */
#define MICROPY_HW_WIFI_ENABLED    (1)

/* ---- I2S 麦克风 ---- */
#define MICROPY_HW_I2S_ENABLED     (1)

/* ---- 蓝牙 — 禁用（显微镜不需要） ---- */
#define MICROPY_PY_BLUETOOTH       (0)
#define MICROPY_PY_BLUETOOTH_NIMBLE (0)

/* ---- ESP-NOW — 禁用（ESP32-P4 无原生 WiFi） ---- */
#define MICROPY_PY_ESPNOW          (0)

/* ---- USB 串口 ---- */
#define MICROPY_HW_USB_SERIAL_JTAG (1)
