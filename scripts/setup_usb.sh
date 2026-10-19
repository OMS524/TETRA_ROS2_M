#!/usr/bin/env bash
# Run once: sudo ./scripts/setup_usb.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "sudo ./scripts/setup_usb.sh 로 실행하세요."
    exit 1
fi

# 스크린샷의 두 PL2303은 모두 067b:2303이므로 ID_PATH로 구분합니다.
# 2026-10-19: AC0 엔코더 조회로 모터 보드임을 확인한 USB 포트입니다.
MOTOR_USB_PATH="pci-0000:05:00.4-usb-0:1.2:1.0"

echo "SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"067b\", ATTRS{idProduct}==\"2303\", ENV{ID_PATH}==\"$MOTOR_USB_PATH\", GROUP:=\"dialout\", MODE:=\"0660\", SYMLINK+=\"tetra/motor\"" > /etc/udev/rules.d/tetra_motor.rules
# 2026-10-19: 실제 연결된 CP2102의 시리얼을 udev에서 확인했습니다.
echo 'SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", ATTRS{serial}=="bb19f6f5d0252745bae134e7d8c48a83", GROUP:="dialout", MODE:="0660", SYMLINK+="tetra/lidar"' > /etc/udev/rules.d/tetra_lidar.rules

if [[ -n "${SUDO_USER:-}" ]]; then
    usermod -aG dialout "$SUDO_USER"
fi
udevadm control --reload-rules
udevadm trigger --action=change --subsystem-match=tty
udevadm settle --timeout=10

echo "USB 이름 고정 완료: /dev/tetra/motor, /dev/tetra/lidar"
echo "이후 재연결·재부팅 때 자동 적용됩니다. dialout에 처음 추가됐다면 다시 로그인하세요."
