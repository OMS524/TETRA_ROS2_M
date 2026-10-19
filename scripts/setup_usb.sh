#!/usr/bin/env bash
# Install: sudo ./scripts/setup_usb.sh   Inspect only: ./scripts/setup_usb.sh --check
set -euo pipefail

fail() { echo "오류: $*" >&2; exit 1; }

# 설치된 이 파일을 udev도 사용합니다. AC0(엔코더 조회)만 보내 모터보드를 판별합니다.
probe_motor() {
    [[ -c $1 ]] || return 1
    if fuser -s -- "$1" 2>/dev/null; then
        echo "$1 사용 중: bringup 등 시리얼 포트를 사용하는 프로그램을 종료하세요." >&2
        return 1
    fi
    /usr/bin/python3 - "$1" <<'PY'
import fcntl
import os
import re
import select
import sys
import termios
import time
from functools import reduce

fd = None
saved = None
exclusive = False
matched = False
try:
    fd = os.open(sys.argv[1], os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    fcntl.ioctl(fd, termios.TIOCEXCL)
    exclusive = True
    saved = termios.tcgetattr(fd)
    attrs = termios.tcgetattr(fd)
    attrs[:4] = [0, 0, termios.CS8 | termios.CREAD | termios.CLOCAL, 0]
    attrs[4] = attrs[5] = termios.B115200
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    termios.tcflush(fd, termios.TCIFLUSH)
    # STX + AC0 + ETX + XOR checksum. Servo/velocity commands are never sent.
    payload = b'AC0\x03'
    os.write(fd, b'\x02' + payload + bytes([reduce(int.__xor__, payload, 0)]))
    buffer = b''
    deadline = time.monotonic() + 0.8
    finished = False
    while not finished and time.monotonic() < deadline:
        if not select.select([fd], [], [], max(0, deadline - time.monotonic()))[0]:
            break
        data = os.read(fd, 256)
        if not data:
            break
        buffer += data
        while b'\x02' in buffer:
            buffer = buffer[buffer.index(b'\x02'):]
            if b'\x03' not in buffer[1:]:
                break
            end = buffer.index(b'\x03', 1)
            if len(buffer) < end + 2:
                break
            frame, buffer = buffer[:end + 2], buffer[end + 2:]
            if reduce(int.__xor__, frame[1:-1], 0) != frame[-1]:
                continue
            body = frame[1:-2]
            matched = (len(body) == 21 and body[:1] == b'0'
                       and all(re.fullmatch(rb' *[+-]?[0-9]+', field)
                               for field in (body[1:11], body[11:21])))
            finished = True
            break
except (OSError, termios.error):
    pass
finally:
    if fd is not None:
        try:
            if saved is not None:
                termios.tcsetattr(fd, termios.TCSANOW, saved)
            if exclusive:
                fcntl.ioctl(fd, termios.TIOCNXCL)
        except (OSError, termios.error):
            pass
        os.close(fd)
if matched:
    print('motor')
sys.exit(0 if matched else 1)
PY
}

if [[ ${1:-} == --probe ]]; then
    [[ $# -eq 2 && $2 =~ ^/dev/tty(USB|ACM)[0-9]+$ ]] || exit 1
    probe_motor "$2"
    exit $?
fi

check_only=false
case "${1:-}" in
    --check) check_only=true ;;
    '') ;;
    *) fail "사용법: sudo ./scripts/setup_usb.sh 또는 ./scripts/setup_usb.sh --check" ;;
esac
[[ $# -le 1 ]] || fail "인자가 너무 많습니다."
if [[ $EUID -ne 0 && $check_only == false ]]; then
    echo "sudo ./scripts/setup_usb.sh 로 실행하세요."
    exit 1
fi

command -v fuser >/dev/null || fail "fuser가 필요합니다. sudo apt install psmisc 로 설치하세요."
[[ -x /usr/bin/python3 ]] || fail "Ubuntu 기본 python3가 필요합니다."
motor_nodes=()
lidar_nodes=() lidar_serials=()
for device in /dev/ttyUSB* /dev/ttyACM*; do
    [[ -c "$device" ]] || continue
    info=$(udevadm info --query=property --name="$device") || fail "$device 조회 실패"
    vendor= product= serial=
    while IFS='=' read -r key value; do
        case "$key" in
            ID_VENDOR_ID) vendor=$value ;;
            ID_MODEL_ID) product=$value ;;
            ID_SERIAL_SHORT) serial=$value ;;
        esac
    done <<< "$info"
    case "$vendor:$product" in
        067b:2303) motor_nodes+=("$device") ;;
        10c4:ea60) lidar_nodes+=("$device"); lidar_serials+=("$serial") ;;
    esac
done
[[ ${#lidar_nodes[@]} -eq 1 ]] || fail "CP2102 라이다(10c4:ea60)가 ${#lidar_nodes[@]}개입니다. 라이다 한 대를 연결하세요. 규칙은 변경하지 않았습니다."
lidar_node=${lidar_nodes[0]}
lidar_serial=${lidar_serials[0]}
[[ $lidar_serial =~ ^[A-Za-z0-9_.:+-]+$ ]] || fail "라이다의 고유 시리얼을 확인할 수 없습니다. 규칙은 변경하지 않았습니다."

# 실행 중인 드라이버와 동시에 시리얼 포트를 열지 않습니다.
for device in "${motor_nodes[@]}"; do
    if fuser -s -- "$device" 2>/dev/null; then
        fail "$device 사용 중입니다. bringup을 종료한 뒤 다시 실행하세요. 규칙은 변경하지 않았습니다."
    fi
done
motor_node=
for device in "${motor_nodes[@]}"; do
    if probe_motor "$device" >/dev/null; then
        [[ -z $motor_node ]] || fail "모터보드 응답이 여러 개입니다. 로봇 한 대만 연결하세요. 규칙은 변경하지 않았습니다."
        motor_node=$device
    fi
done
[[ -n $motor_node ]] || fail "모터 엔코더 응답을 받지 못했습니다. 로봇 전원과 USB 연결을 확인하세요. 규칙은 변경하지 않았습니다."

helper=/usr/local/libexec/tetra-usb
motor_rule="ACTION==\"change\", SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"067b\", ATTRS{idProduct}==\"2303\", IMPORT{db}=\"TETRA_ROLE\"
ACTION==\"add\", SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"067b\", ATTRS{idProduct}==\"2303\", PROGRAM==\"$helper --probe /dev/%k\", RESULT==\"motor\", ENV{TETRA_ROLE}=\"motor\"
SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"067b\", ATTRS{idProduct}==\"2303\", ENV{TETRA_ROLE}==\"motor\", GROUP:=\"dialout\", MODE:=\"0660\", SYMLINK+=\"tetra/motor\""
lidar_rule="SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"10c4\", ATTRS{idProduct}==\"ea60\", ATTRS{serial}==\"$lidar_serial\", GROUP:=\"dialout\", MODE:=\"0660\", SYMLINK+=\"tetra/lidar\""
echo "모터(엔코더 응답 확인): $motor_node"
echo "라이다: $lidar_node, 시리얼: $lidar_serial"
if $check_only; then
    printf '%s\n%s\n' "$motor_rule" "$lidar_rule"
    echo "연결값 확인 완료. 설치하려면 sudo ./scripts/setup_usb.sh 로 실행하세요."
    exit 0
fi

mkdir -p /etc/udev/rules.d
install -d -m 0755 /usr/local/libexec
install -o root -g root -m 0755 "$(readlink -f "$0")" "$helper"
printf '%s\n' "$motor_rule" > /etc/udev/rules.d/tetra_motor.rules
printf '%s\n' "$lidar_rule" > /etc/udev/rules.d/tetra_lidar.rules
if [[ -n "${SUDO_USER:-}" ]]; then
    usermod -aG dialout "$SUDO_USER"
fi
udevadm control --reload-rules
for device in "${motor_nodes[@]}" "$lidar_node"; do
    udevadm trigger --action=add --subsystem-match=tty --sysname-match="${device##*/}"
done
udevadm settle --timeout=10

for role in motor lidar; do
    alias_path="/dev/tetra/$role"
    expected="$motor_node"
    [[ $role != lidar ]] || expected="$lidar_node"
    [[ -L $alias_path && -c $alias_path && $(readlink -f "$alias_path") == "$expected" ]] || fail "$alias_path 연결 확인에 실패했습니다. USB 연결을 확인하고 다시 실행하세요."
done
echo "USB 이름 고정 완료: /dev/tetra/motor, /dev/tetra/lidar"
ls -l /dev/tetra/motor /dev/tetra/lidar
echo "이제 PC USB 포트나 허브 소켓을 바꿔 꽂아도 모터를 자동 판별합니다."
echo "새 노트북에서는 최초 한 번, 라이다 교체 시에는 이 스크립트를 다시 실행하세요."
echo "dialout에 처음 추가됐다면 다시 로그인하세요."
