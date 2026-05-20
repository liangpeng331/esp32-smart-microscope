# CMake 板级配置 — Waveshare ESP32-P4-WIFI6-Touch-LCD-4B
#
# ESP32-P4 需要 ESP-IDF v5.2+ (或 v5.3 LTS)
# MicroPython 需要 esp32p4 目标支持 (mpy-cross + 固件)

# ---- ESP-IDF 目标芯片 ----
set(IDF_TARGET esp32p4)

# ---- 串口烧录参数 ----
set(ESPTOOL_FLASH_SIZE      16MB)
set(ESPTOOL_FLASH_FREQ      80m)
set(ESPTOOL_FLASH_MODE      qio)

# ---- 固件分区表 (16MB Flash) ----
# 使用自定义分区表，为 LVGL 静态资源、摄像头帧缓冲和 MicroPython 文件系统提供空间
set(PARTITION_TABLE_CSV "${CMAKE_CURRENT_LIST_DIR}/partitions.csv")

# ---- 组件依赖 ----
set(MICROPY_COMPONENTS
    driver
    esp_lcd
    esp_lcd_touch
    esp_lcd_touch_gt911
    esp_camera
    esp_sr
    sdmmc
    fatfs
    esp_wifi_remote       # ESP32-C6 WiFi 协处理器
)

# ---- SDKCONFIG 覆盖 ----
# 开启 PSRAM、摄像头、WiFi 协处理、I2S 等
set(SDKCONFIG_DEFAULTS
    "${CMAKE_CURRENT_LIST_DIR}/sdkconfig.defaults"
    "${MICROPY_BOARD_DIR}/sdkconfig.defaults"
)

# ---- LVGL 库路径 (本地构建) ----
# 若 MicroPython 固件未内嵌 lvgl，从外部引入
if(EXISTS "${CMAKE_CURRENT_LIST_DIR}/lvgl")
    list(APPEND EXTRA_COMPONENT_DIRS "${CMAKE_CURRENT_LIST_DIR}/lvgl")
endif()

# ---- 编译优化 ----
set(CMAKE_C_FLAGS_RELEASE "${CMAKE_C_FLAGS_RELEASE} -Os -ffunction-sections -fdata-sections")
set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -Os")
