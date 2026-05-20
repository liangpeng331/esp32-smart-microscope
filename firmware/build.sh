#!/usr/bin/env bash
# ============================================================
# ESP32-P4 MicroPython 固件一键编译脚本
#
# 用法:
#   ./build.sh setup      — 初始化工具链和依赖（首次使用）
#   ./build.sh build       — 编译固件
#   ./build.sh flash      — 编译并烧录到开发板
#   ./build.sh clean      — 清理编译产物
#   ./build.sh monitor    — 串口监视器 (115200 baud)
#   ./build.sh all        — setup → build → flash → monitor
#
# 环境要求:
#   - macOS 14+ / Ubuntu 22.04+
#   - Python 3.10+
#   - pip, cmake, ninja, git, dfu-util
# ============================================================

set -euo pipefail

# ---- 配置 ----
BOARD="ESP32_P4_WAVESHARE_4B"
BOARD_DIR="$(cd "$(dirname "$0")" && pwd)/boards/${BOARD}"
MPY_DIR="${HOME}/micropython"
IDF_DIR="${HOME}/esp/esp-idf"
IDF_VERSION="v5.3.2"

# ESP-IDF 工具链路径覆盖 (按需修改)
export IDF_TOOLS_PATH="${HOME}/.espressif"

# 串口设备 (自动检测或手动指定)
if [[ "$(uname)" == "Darwin" ]]; then
    PORT="${MICROPY_PORT:-$(ls /dev/cu.usbmodem* 2>/dev/null | head -1)}"
else
    PORT="${MICROPY_PORT:-$(ls /dev/ttyUSB* 2>/dev/null | head -1)}"
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ---- 依赖检查 ----

check_prereqs() {
    info "检查系统依赖..."

    command -v python3 >/dev/null 2>&1 || err "需要 python3 (>= 3.10)"
    command -v pip3    >/dev/null 2>&1 || err "需要 pip3"
    command -v cmake   >/dev/null 2>&1 || err "需要 cmake"
    command -v ninja   >/dev/null 2>&1 || err "需要 ninja"
    command -v git     >/dev/null 2>&1 || err "需要 git"

    ok "系统依赖检查通过"
}

# ---- ESP-IDF ----

setup_idf() {
    if [ -d "${IDF_DIR}" ]; then
        info "ESP-IDF 已存在: ${IDF_DIR}"
        return 0
    fi

    info "克隆 ESP-IDF ${IDF_VERSION} ..."
    mkdir -p "$(dirname "${IDF_DIR}")"
    git clone --depth 1 --branch "${IDF_VERSION}" \
        https://github.com/espressif/esp-idf.git "${IDF_DIR}" \
        || err "ESP-IDF 克隆失败"

    info "安装 ESP-IDF 工具链 (这一步较久，约 10-30 分钟)..."
    cd "${IDF_DIR}"
    ./install.sh esp32p4 || err "ESP-IDF 安装失败"

    ok "ESP-IDF ${IDF_VERSION} 安装完成"
}

# ---- MicroPython ----

setup_micropython() {
    if [ -d "${MPY_DIR}" ]; then
        info "MicroPython 源码已存在: ${MPY_DIR}"
        cd "${MPY_DIR}"
        git pull --ff-only 2>/dev/null || true
        return 0
    fi

    info "克隆 MicroPython ..."
    git clone --depth 1 https://github.com/micropython/micropython.git "${MPY_DIR}" \
        || err "MicroPython 克隆失败"

    info "构建 mpy-cross ..."
    cd "${MPY_DIR}/mpy-cross"
    make -j"$(nproc 2>/dev/null || sysctl -n hw.ncpu)" \
        || err "mpy-cross 构建失败"

    info "初始化子模块 (esp32, lvgl 等) ..."
    cd "${MPY_DIR}"
    git submodule update --init --depth 1 lib/berkeley-db-1xx
    git submodule update --init --depth 1 lib/esp-idf-components

    ok "MicroPython 源码准备完成"
}

# ---- 板级文件链接 ----

link_board() {
    info "链接板级定义文件..."

    local target="${MPY_DIR}/ports/esp32/boards/${BOARD}"

    if [ -L "${target}" ] || [ -d "${target}" ]; then
        warn "板级目录已存在，跳过链接"
        return 0
    fi

    ln -sf "${BOARD_DIR}" "${target}"
    ok "板级定义已链接: ${target}"
}

# ---- 编译固件 ----

build_firmware() {
    info "开始编译 MicroPython 固件 (目标: ${BOARD})..."

    # 激活 ESP-IDF 环境
    source "${IDF_DIR}/export.sh" 2>/dev/null

    cd "${MPY_DIR}/ports/esp32"

    # 清理旧的 esp-idf 组件缓存
    rm -rf build-${BOARD} 2>/dev/null || true

    # 构建
    make BOARD="${BOARD}" -j"$(nproc 2>/dev/null || sysctl -n hw.ncpu)" \
        || err "编译失败 — 请检查上面的错误输出"

    # 验证产物
    local fw="${MPY_DIR}/ports/esp32/build-${BOARD}/micropython.bin"
    if [ -f "${fw}" ]; then
        local size=$(du -h "${fw}" | cut -f1)
        ok "固件编译成功: ${fw} (${size})"
    else
        err "固件文件未生成，编译可能未完成"
    fi
}

# ---- 烧录 ----

flash_firmware() {
    if [ -z "${PORT}" ]; then
        warn "未检测到串口设备"
        warn "请手动指定: MICROPY_PORT=/dev/cu.usbmodemXXX ./build.sh flash"
        return 1
    fi

    info "烧录到: ${PORT} ..."

    source "${IDF_DIR}/export.sh" 2>/dev/null

    cd "${MPY_DIR}/ports/esp32"

    # 先擦除整个 Flash
    info "擦除 Flash..."
    python3 -m esptool --chip esp32p4 --port "${PORT}" erase_flash \
        || warn "擦除失败，尝试继续..."

    # 写入固件
    info "写入固件..."
    make BOARD="${BOARD}" PORT="${PORT}" deploy \
        || err "烧录失败 — 请检查串口连接和权限"

    ok "烧录完成"
}

# ---- 串口监视器 ----

monitor() {
    if [ -z "${PORT}" ]; then
        err "未检测到串口，无法启动监视器"
    fi

    info "启动串口监视器 (115200 baud, 按 Ctrl+A 然后 K 退出)..."
    info "端口: ${PORT}"

    if command -v screen >/dev/null 2>&1; then
        screen "${PORT}" 115200
    elif command -v picocom >/dev/null 2>&1; then
        picocom -b 115200 "${PORT}"
    else
        python3 -m serial.tools.miniterm "${PORT}" 115200
    fi
}

# ---- 清理 ----

clean() {
    info "清理编译产物..."
    cd "${MPY_DIR}/ports/esp32"
    make BOARD="${BOARD}" clean
    ok "清理完成"
}

# ---- 主线 ----

main() {
    local cmd="${1:-build}"

    case "${cmd}" in
        setup)
            check_prereqs
            setup_idf
            setup_micropython
            link_board
            ok "环境初始化完成"
            info "下一步: ./build.sh build"
            ;;
        build)
            check_prereqs
            setup_idf >/dev/null 2>&1
            setup_micropython >/dev/null 2>&1
            link_board
            build_firmware
            ;;
        flash)
            check_prereqs
            build_firmware
            flash_firmware
            ;;
        clean)
            clean
            ;;
        monitor)
            monitor
            ;;
        all)
            check_prereqs
            setup_idf
            setup_micropython
            link_board
            build_firmware
            flash_firmware
            monitor
            ;;
        *)
            echo "用法: $0 {setup|build|flash|clean|monitor|all}"
            exit 1
            ;;
    esac
}

main "$@"
