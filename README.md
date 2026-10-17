# TETRA DS4-M — Ubuntu 22.04 / ROS 2 Humble

현재 작업본은 **TETRA DS4-M, Ubuntu 22.04 (Jammy), ROS 2 Humble, SLAMTEC RPLIDAR A2M12**를 대상으로 합니다.
제조사 Jazzy 저장소의 패키지 구성을 Humble로 이식하고, 본체·구동 통신·주행 치수는
AIRO-lab 선배님들의 DS4 소스에 맞췄습니다. 기본 실행 모델은 DS4-M입니다.

## 모델과 참고 소스

| 항목 | 현재 DS4-M 설정 |
|---|---|
| 본체 URDF / STL | `AIRO-lab/tetra_pkg`의 실물 DS4 모델, 상·하부 본체와 후방 캐스터 2개 |
| 구동 코드 휠 반지름 / 간격 | 0.1018 m / 0.4380 m |
| Nav2 본체 영역 | x: -0.490~0.240, y: ±0.260 m |
| 모터 통신 | 115200 baud, ASCII `BE` 속도 명령 / `AC1` 오도메트리 / `AA` 상태 조회 |
| 오도메트리 단위 | 위치 mm → m, 각도 0.1° → rad; 차체 좌표계 속도 계산 |
| 기본 전방 라이다 | RPLIDAR A2M12, `/scan`, `laser` 프레임 |
| 메시지 패키지 | 현재 워크스페이스의 `interfaces` 유지 (`tetra_msgs`로 교체하지 않음) |

참고한 스냅샷:

- [TETRA-ROBOT/TETRA_ROS2_M](https://github.com/TETRA-ROBOT/TETRA_ROS2_M): 이식 출발점인 제조사 Jazzy / DS5-M 소스.
- [AIRO-lab/tetra_pkg](https://github.com/AIRO-lab/tetra_pkg/tree/ecbf75fb82b6b6b5fa3d4fbf30733abb89db588c): DS4 실물 모델, ASCII 구동, Nav2 치수·Humble 구성.
- [AIRO-lab/tetra](https://github.com/AIRO-lab/tetra/tree/38ac7a2290a349b36e3fe238247f58a626df66c0): 동일 DS4 메시·구동 상수 교차 확인, 장치 경로·A2M12 사용 흔적 참고.
- [SLAMTEC sllidar_ros2](https://github.com/Slamtec/sllidar_ros2): 사용자가 클론한 `sllidar_ros2/`를 빌드해 사용. 확인한 커밋: `34300099fadfc772965962dec837bf436706188f`.

선행 저장소를 이 워크스페이스 안에 함께 clone하면 `tetra`, `tetra_description` 등 패키지 이름이 중복됩니다.
참고용 소스는 별도 경로에 두세요. 아래 빌드 명령은 `--base-paths src/TETRA_ROS2_M`으로 현재 수정본만 선택합니다. 모델은 Gazebo용으로 수정된 버전 대신 `tetra_pkg`의 실물용 URDF를 사용합니다.
메시 출처·해시는 [DS4-M 모델 기록](tetra_description/meshes/ds4_m/README.md)에 있습니다.
기본 Xacro는 `meshes/ds4_m/`의 메시만 사용하며, 상위 디렉터리의 DS5-M 메시와 `tetra_bak.xacro`는 실행에 사용하지 않습니다.
시각화 모델의 치수와 보정된 모터 상수는 각각 선행 소스 값을 유지했습니다.

## 설치와 빌드

[ROS 2 Humble 공식 설치 안내](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html)에 따라 Humble을 먼저 설치합니다.
다른 ROS 배포판을 source하지 않은 새 터미널에서 실행하세요.

```bash
cd ~/tetra_ws/src/TETRA_ROS2_M
bash scripts/install_humble_dependencies.sh

cd ~/tetra_ws
source /opt/ros/humble/setup.bash
colcon build --base-paths src/TETRA_ROS2_M --symlink-install --executor parallel --parallel-workers 4 --cmake-args -DBUILD_TESTING=OFF
source install/setup.bash
```

설치 스크립트는 Ubuntu 22.04 / Humble을 확인한 뒤 apt와 rosdep으로 빌드·실행 의존성을 설치합니다.
A2M12 드라이버는 이 저장소 안에 클론한 `sllidar_ros2/`를 함께 빌드합니다. `rplidar_ros`는 사용하지 않습니다. 센서 실행 여부와 별개로 전체 저장소를
빌드하려면 AprilTag, RealSense SDK 등 포함된 패키지의 의존성도 필요합니다.
`sudo` 암호는 본인 터미널에서 입력하세요. 다른 배포판에서 생성한 build/install을 재사용하지 마세요.

### USB 허브의 세 장치 등록

기본 포트는 아래 고정 별칭을 사용합니다. **코드를 빌드하는 것만으로 `/dev/tetra/*`가 생기지는 않습니다.**
실제 장치를 확인한 뒤 udev 규칙을 한 번 등록해야 합니다.

| 연결 대상 | 기본 포트 | launch 인자 |
|---|---|---|
| 모터 제어 보드 | `/dev/tetra/motor` | `motor_port` |
| 전원·입출력 보드 | `/dev/tetra/interface` | `interface_port` |
| A2M12 라이다 | `/dev/tetra/lidar` | `lidar_port` |

DS4 드라이버는 통신 포트 하나로 좌우 바퀴를 함께 제어합니다. 로봇에서 나온 두 케이블 중
어느 것이 모터 보드이고 어느 것이 전원·입출력 보드인지 커넥터 / 보드 라벨로 확인하세요.
두 번째 케이블을 확인 없이 `interface`로 지정하지 않습니다. 전원보드를 연결하지 않은 구성은
`enable_interface:=false`로 실행할 수 있습니다.

1. 로봇 노드를 종료한 상태에서 각 케이블을 구분하고 장치 정보를 조회합니다.

   ```bash
   cd ~/tetra_ws/src/TETRA_ROS2_M
   python3 scripts/tetra_usb_ports.py list
   ```

   도구는 `/dev/ttyUSB*`, `/dev/ttyACM*`의 고유 시리얼·USB 인터페이스·물리 경로·현재 별칭을 표시합니다.
   케이블을 한 개씩 연결하여 어느 장치가 나타나는지 확인한 뒤 세 개를 모두 연결합니다.
   USB 장치 번호순으로 역할을 정하지 않습니다. 조회 과정에서 시리얼 포트를 열거나 모터 명령을 보내지 않습니다.

2. 확인한 세 장치를 지정하여 규칙 파일을 만듭니다. 아래 `ttyUSB_MOTOR`, `ttyUSB_INTERFACE`,
   `ttyUSB_LIDAR`는 **자리표시자**이므로 1단계에서 확인한 실제 `/dev/ttyUSB숫자` 또는 기존 by-id 경로로 바꾸세요.

   ```bash
   python3 scripts/tetra_usb_ports.py generate \
     --motor /dev/ttyUSB_MOTOR \
     --interface /dev/ttyUSB_INTERFACE \
     --lidar /dev/ttyUSB_LIDAR \
     --output /tmp/99-tetra-usb.rules
   ```

   기본은 제조사·제품·고유 시리얼(가능하면 USB 인터페이스 번호 포함)로 구분합니다.
   고유 시리얼이 없거나 중복된다면 같은 명령에 `--match path`를 추가하여 물리 포트로 구분합니다.
   **path 방식은 케이블을 꽂는 허브 소켓과 허브를 연결하는 PC의 USB 포트를 유지해야 합니다.**
   serial 방식도 USB 변환기를 다른 로봇 보드로 옮기면 역할이 바뀌므로 케이블 라벨을 유지하세요.

   동일 장치에 두 역할을 지정하거나 식별값이 여러 장치와 일치하면 생성을 거부합니다.
   기존 선배 `initenv.sh`는 두 변환기를 제조사·제품 번호만으로 구분할 수 없어 그대로 실행하지 않습니다.
   기존 규칙과 별칭이 겹치면 도구가 파일 위치를 표시하므로, 해당 규칙을 백업하고 중복 항목을 정리하세요.
   생성기는 기존 출력 파일도 덮어쓰지 않습니다. 다시 생성할 때는 새 출력 파일명을 지정하세요.

3. 생성된 내용을 확인한 뒤 설치합니다.

   ```bash
   cat /tmp/99-tetra-usb.rules
   sudo install -m 0644 /tmp/99-tetra-usb.rules /etc/udev/rules.d/99-tetra-usb.rules
   sudo udevadm control --reload-rules
   sudo usermod -aG dialout "$USER"
   ```

   로봇 노드가 종료된 상태에서 USB 허브를 분리했다가 다시 연결하고 확인합니다.
   `dialout` 그룹을 처음 추가했다면 로그아웃 후 다시 로그인하세요.

   ```bash
   ls -l /dev/tetra/
   python3 scripts/tetra_usb_ports.py list
   ```

장치 권한은 `dialout` 그룹의 `0660`으로 설정합니다. 기본값은 통합 bringup, 단독 모터·전원보드
launch와 실행 파일, 단독 A2M12 launch에 동일하게 적용됩니다. 다른 경로가 필요하면 기존
`motor_port`, `interface_port`, `lidar_port` 인자 또는 드라이버의 `serial_port` 파라미터로 변경할 수 있습니다.


## 실행

각 터미널에서 먼저 환경을 적용합니다.

```bash
source /opt/ros/humble/setup.bash
source ~/tetra_ws/install/setup.bash
```

### 1. 라이다만 확인

```bash
ros2 launch tetra_bringup sllidar_a2m12.launch.py
# 별도 터미널
ros2 topic hz /scan
ros2 topic echo /scan --once --field header
```

A2M12 기본값은 256000 baud, `Sensitivity`, `angle_compensate=true`, `inverted=false`입니다.
장착 방향은 아래 `lidar_roll/pitch/yaw`로 설정하며, 스캔 순서의 반전인 `lidar_inverted`와 구분합니다.

### 2. 본체 + A2M12

```bash
ros2 launch tetra_bringup tetra_bringup.launch.py
```

기본 실행: 모터, 전원보드, A2M12, robot_state_publisher. **EKF는 실행하지 않습니다.**
모터 드라이버가 `/odom`과 `odom -> base_footprint` TF를 직접 발행하며, Nav2·Cartographer는
이 `/odom`을 사용합니다. Cartographer 등의 구독과 연결되도록 odom 발행 QoS는 reliable입니다.
IAHRS를 장착했다면 `use_imu:=true imu_port:=/dev/IMU`로 센서 드라이버를 켤 수 있지만, odom에 융합하지 않습니다.

| 인자 | 기본값 | 용도 |
|---|---|---|
| `motor_port` / `interface_port` / `lidar_port` | `/dev/tetra/motor` / `/dev/tetra/interface` / `/dev/tetra/lidar` | USB 장치 고정 별칭 |
| `enable_base`, `enable_interface`, `enable_lidar` | `true` | 본체·전원보드·라이다 실행 |
| `use_imu` | `false` | IAHRS 센서 드라이버만 실행; odom 융합 없음 |
| `enable_joy` | `false` | 제조사 조이스틱 입력 사용 |
| `enable_usb_camera`, `enable_apriltag` | `false` | 카메라와 태그 감지 각각 실행 |
| `enable_cyglidar`, `enable_realsense` | `false` | 추가 센서 실행 |
| `enable_service`, `enable_web`, `enable_virtual_wall` | `false` | 제조사 부가 기능 실행 |
| `lidar_x`, `lidar_y`, `lidar_z` | `0.1372`, `0`, `0.142` | **base_link 기준** 라이다 위치, m |
| `lidar_roll`, `lidar_pitch`, `lidar_yaw` | `3.14`, `3.14`, `0` | 직접 받은 선배 DS4-M의 라이다 회전, rad |

라이다 위치 `(0.1372, 0, 0.142)` m와 회전 `(3.14, 3.14, 0)` rad는 직접 받은
`/home/oms/tetra_ws/src/tetra/tetra_description/urdf/tetra_description.xacro`의 `laser_joint`와 같습니다.
회전은 수평 약 180°에 해당하며 `lidar_inverted`는 기존 `false`를 유지합니다.
실제 브래킷을 새로 측정한 값은 아니므로 RViz에서 로봇 앞 장애물이 앞쪽에 표시되는지 확인하세요.
카메라·보조 센서 TF도 선행 DS4 위치를 사용합니다. 장착된 센서가 다르면 실제 위치로 변경하세요.

### 3. SLAM과 지도 저장

본체 bringup을 유지하고 다른 터미널에서:

```bash
ros2 launch tetra_cartographer cartographer.launch.py
# 화면이 없는 환경: use_rviz:=false 추가
```

지도 저장:

```bash
mkdir -p ~/.ros/tetra/maps
ros2 run nav2_map_server map_saver_cli -f "$HOME/.ros/tetra/maps/my_map"
```

Cartographer가 `map -> odom` TF를 발행하므로 기존의 중복 static TF는 제거했습니다.
SLAM을 종료한 뒤 저장한 지도로 Nav2를 실행하세요. SLAM과 AMCL을 동시에 켜지 않습니다.

### 4. 내비게이션

```bash
ros2 launch tetra_navigation2 tetra_navigation.launch.py map:="$HOME/.ros/tetra/maps/my_map.yaml"
# 별도 터미널
ros2 launch tetra_navigation2 rviz_launch.py
```

**선배 AMCL 설정처럼 초기 위치를 자동으로 (0,0,0)에 두지 않습니다.**
RViz에서 실제 위치에 `2D Pose Estimate`를 지정한 뒤 목표를 지정합니다. 초기 위치 지정 전에는
`map -> odom` TF를 기다리는 메시지가 나올 수 있습니다.
기본 `office.yaml`은 제조사 예시 지도이므로 실제 공간에서는 새 지도를 사용하세요.
패키지에 설치된 지도는 `map_name:=office.yaml`, 외부 지도는 `map:=/절대경로/지도.yaml`로 지정합니다.
`use_composition:=true`도 지원합니다.

속도 연결은 다음과 같습니다 (모두 `geometry_msgs/msg/Twist`):

```text
Nav2 controller / behaviors -> /cmd_vel_raw
  -> velocity_smoother -> /cmd_vel_smoothed
  -> collision_monitor -> /cmd_vel_nav2 -> TETRA motor driver
```

현재 제어기는 **DWB (`dwb_core::DWBLocalPlanner`)**입니다.
직접 제공받은 `/home/oms/tetra_ws/src/tetra/tetra_nav2/param/tetra.yaml`의 DWB 설정,
progress checker, goal checker, 속도 임계값을 적용했습니다. 원본의 `stateful: Truez`는
잘못된 문자열이므로 `stateful: true`로 수정했습니다. 제어기·BT navigator·velocity smoother는
모터의 `odom_topic: /odom`을 직접 사용합니다.

- DWB 내부 상한: `max_vel_x / max_speed_xy = 0.36 m/s`, `max_vel_theta = 2.5 rad/s` (선배 값).
- 샘플 수: x/y/회전 `20 / 5 / 20`, 예측 시간 `1.7 s`; critic 7개와 가중치도 선배 값.
- 목표 도달 허용 오차: 거리 `0.25 m`, 방향 `0.25 rad`; 진행 검사: `10 s` 내 `0.5 m`.
- **최종 velocity_smoother 상한**: 전진 `0.3 m/s`, 후진 `0.2 m/s`, 회전 `±1.0 rad/s` (선배 값).
- DWB 자체는 `min_vel_x = 0`으로 전진 궤적을 선택합니다. 후진 `0.2 m/s`는 BackUp 같은 동작에도 적용되는 후처리 한도입니다.
- 이 제한은 위 Nav2 명령 경로에 적용됩니다. 별도 수동·조이스틱·도킹 입력의 제한을 대신하지 않습니다.

선배 설정과 동일하게 DWB 내부 상한과 최종 출력 상한이 서로 다릅니다. 현재 각가속도 후처리는
`±1.5 rad/s²`이며 선배의 `±3.2 rad/s²`보다 완만합니다. 차체 영역 등 남은 차이는
아래 비교에 정리했습니다. 실제 주행 특성은 제어기와 주변 설정을 함께 조정하여 확인해야 합니다.

모터가 충돌 감시 전 Nav2 명령을 직접 받던 연결을 분리했습니다.
제조사의 `/cmd_vel_nav` 도킹 입력, `/cmd_vel_manual` 수동 입력과 조이스틱은 별도 경로입니다.
기본 Nav2 costmap과 충돌 감시는 확인된 A2M12의 `/scan`만 사용합니다.
추가 카메라·보조 라이다·가상 벽 노드를 켜는 것만으로 costmap 관측원이 추가되지는 않습니다.
그 센서를 사용하려면 `params_file`로 전달할 설정의 관측원과 TF도 구성해야 합니다.

Humble에서는 Jazzy의 `velocity_polygon` 대신 고정 stop/slowdown polygon을 사용합니다.
DS4 본체를 포함하도록 stop 영역은 x [-0.57, 0.32], y ±0.32 m, slowdown 영역은 x [-0.65, 1.3], y ±0.37 m로 설정했습니다.
영역과 감속 비율은 `tetra_navigation2/params/navigation.yaml`에서 조정하세요.
초기 실기 확인은 바퀴를 띄우고 비상정지를 준비한 상태에서 포트·방향·오도메트리를 먼저 확인합니다.

## 변경 사항과 부가 기능

- DS4-M 상·하부 본체 메시, 후방 캐스터 2개, 센서 TF, Nav2 footprint 적용.
- DS5 바이너리 속도 교환을 DS4 ASCII 명령으로 변경. mm 오도메트리, 차체 좌표계 속도, ±π 각도 경계 처리.
- 시리얼 열기 실패와 ASCII 디코더 버퍼 종결 오류 수정. 통신·모터 오류 발생 시 정지 후 드라이버 종료.
- 비상정지 중 속도를 0으로 지우며, 정상 상태 복귀 시 이전 속도 명령을 재사용하지 않음. 모터 오류는 원인 확인 후 노드를 다시 실행.
- Humble Nav2의 BT 라이브러리 목록, `progress_checker_plugin`, planner/behavior 플러그인 식별자로 변경.
- 다중 목표 BT의 비활성화되어 있던 경로 계산 노드를 복원하고 두 BT XML을 설치·연결.
- 통합 launch의 패키지 경로, Humble `PushRosNamespace`, 소문자 bool 인자, 지도 경로 치환 수정.
- 기본 Nav2에서 별도 dock 설정이 없는 `opennav_docking` 서버 제거. 제조사 `tetra_service` 도킹 코드는 보존.
- 시리얼 포트 파라미터와 필수 파라미터 기본값 추가, 실제 데이터 저장 경로를 사용자 홈으로 변경.
- 누락된 CMake/manifest 의존성 보완. 벤더 드라이버의 기존 Humble 호환 분기는 유지.

전원보드 로그는 `~/.ros/tetra/log`에 저장하며 `log_directory`로 변경할 수 있습니다.
`tetra_service`의 위치·랜드마크·지도 경로 기본값은 `~/.ros/tetra/{locations,landmarks,maps}`이며,
각각 `location_directory`, `landmark_directory`, `map_directory` ROS 파라미터로 변경합니다.
기존 데이터를 사용하려면 해당 디렉터리로 옮기거나 기존 디렉터리를 파라미터로 지정하세요.

제조사 `tetra_service`의 GUI 기반 지도 저장/SLAM/내비게이션 시작 서비스는 원본에도 포함되지 않은
`mapsave.sh`, `mapping.sh`, `navigation.sh` 및 `gnome-terminal`에 의존합니다.
해당 기능을 쓸 때는 스크립트를 `script_directory`(기본 사용자 홈)에 별도로 준비해야 합니다.
위의 CLI 실행·지도 저장 명령은 그 외부 스크립트 없이 사용할 수 있습니다.
AprilTag 도킹은 카메라·태그·충전 스테이션 설치에 맞춘 실기 검증이 필요하여 기본 실행에서 꺼져 있습니다.

## 직접 제공받은 `tetra`와 현재 구성 비교

기준은 `/home/oms/tetra_ws/src/tetra`에 직접 받은 파일입니다. 해당 원본은 수정하지 않았습니다.

| 항목 | 현재 적용 상태 / 남은 차이 |
|---|---|
| 모델·구동 치수 | 선배 DS4-M STL 6개, 반경 0.1018 m·간격 0.438 m 동일 |
| 라이다 위치·방향 | xyz `(0.1372, 0, 0.142)`, RPY `(3.14, 3.14, 0)` 동일 |
| 모터 오도메트리 | 선배처럼 `/odom` 직접 사용, 모터가 odom TF 발행. EKF 실행 제거 |
| DWB | 평가 항목·가중치·샘플링·목표 허용 오차·진행 검사 동일; `Truez` 오타 수정 |
| AMCL | `tetra_nav2/param/tetra.yaml`의 **전체 AMCL 파라미터 동일** |
| local / global Costmap | **footprint를 제외한 전체 파라미터 동일**; local VoxelLayer, 5×5 m, 갱신/발행 5/2 Hz; global 1/1 Hz; inflation 둘 다 1.0 m / scaling 2.0 |
| Cartographer SLAM | 선배 `cartographer_2d.lua`의 **Lua 설정 동일**. 현재 `tetra_lds_2d.lua` 이름으로 제공, raw `/odom` 사용 |
| 라이다 드라이버 | 선배와 같은 `sllidar_ros2` / `sllidar_node`. 사용자가 새로 클론한 소스이므로 선배 복사본과 커밋까지 동일한 것은 아님 |
| A2M12 연결 설정 | 256000 baud, frame `laser`, inverted=false, angle_compensate=true 동일; `Sensitivity`를 Node에 실제 전달 |
| 장치 포트 | 모터 `/dev/tetra/motor` 동일. 전원·라이다는 선배 ttyUSB1/2 대신 `/dev/tetra/interface`, `/dev/tetra/lidar` |
| 속도 상한 | 전진 0.3·후진 0.2 m/s·회전 ±1 rad/s 동일; smoother 각가속도는 공식 값 ±1.5 rad/s² 유지 (선배 ±3.2) |
| velocity smoother | OPEN_LOOP 동일; odom_duration은 공식 값 0.1 s 유지 (선배 0.3 s) |
| 정지·감속 기능 | 선배에는 별도 collision monitor가 없음. 제조사 기능을 Humble용 고정 정지·감속 영역으로 유지 |
| 속도 토픽 | 선배 모터는 `/cmd_vel`; 현재 Nav2는 smoother·collision monitor를 거친 `/cmd_vel_nav2`, 수동은 `/cmd_vel_manual` |
| 기본 전원보드 실행 | 선배 본체 launch에는 미포함, 현재 포함. 미연결 시 `enable_interface:=false` |
| 시간·통신 처리 | 실기 시간 false, 선배 EKF 인자 이름 불일치 수정; 포트/응답 오류 확인 및 비상정지·모터 고장 처리 유지 |
| 부가 기능 | 제조사 서비스·센서 패키지 및 Humble용 BT 유지. 선배 음성·GUI·waypoint 앱은 이식하지 않음 |

**Costmap에서 footprint만 유지한 이유:** 선배 local 영역은 16×16 cm, global 영역은 47×44 cm이며
이식한 DS4 메시의 실제 외곽보다 작습니다. 그대로 줄이면 경로 계획에서 실제 차체 충돌을 놓치거나,
계획한 경로를 공식 collision monitor가 계속 막는 불일치가 생길 수 있습니다. 현재는 local/global 모두
x `[-0.490, 0.240]`, y `±0.260` m (73×52 cm)를 유지합니다. 정지·감속 영역도 이를 포함합니다.

AMCL은 자동 초기 위치를 제거한 선배 방식이며, RViz에서 초기 위치를 지정해야 합니다.
Cartographer의 범위 0.12~13.5 m, odometry sampling 1.0, 2D projection true,
constraint score 0.65 / global localization score 0.7 등도 선배 값으로 맞췄습니다.
글로벌 플래너는 둘 다 Navfn (`use_astar=false`), 경로 smoother는 SimpleSmoother입니다.
지도 파일·RViz·BT 자체는 현재 패키지 구성을 유지하며 실제 공간의 지도는 `map:=...`으로 지정합니다.

기능 출처: 제조사 원본에도 Nav2 `collision_monitor` 실행과 `velocity_polygon` 감속 설정이 있습니다.
현재는 Humble용 `PolygonStop` / `PolygonSlow`와 DS4 영역, 감속 비율 0.4, 올바른 속도 토픽 연결을 적용했습니다.
정지·감속 알고리즘 자체를 새로 작성한 것은 아닙니다.

### 현재 라이다 드라이버

`tetra_bringup/launch/sllidar_a2m12.launch.py`가 클론된 `sllidar_ros2` 패키지의
`sllidar_node`를 실행합니다. 통합 bringup도 같은 launch를 사용하며 `rplidar_ros` 의존성은 제거했습니다.
빌드 범위를 `src/TETRA_ROS2_M`으로 제한하면 옆의 선배 폴더에 있는 동명 패키지는 포함하지 않습니다.

클론된 upstream A2M12 launch 파일명에는 `.py` 앞 공백이 있고, `scan_mode`를 Node에 전달하지 않는
부분이 있어 이 프로젝트의 launch에서 필요한 값을 명시적으로 전달합니다. 클론한 원본은 수정하지 않았습니다.
포트 `/dev/tetra/lidar`, baud 256000, frame `laser`, `Sensitivity`, 각도 보정 true, inverted false를 사용합니다.

### Nav2를 불러오는 구조

[Navigation2의 humble 브랜치](https://github.com/ros-navigation/navigation2/tree/humble)는 Nav2의
소스 저장소입니다. 현재 작업 폴더에는 이 전체 저장소를 복제하지 않았으며, 로봇 전용 설정과 launch를 둡니다.
실행 시 ROS의 패키지 인덱스로 **로컬에 설치된 Nav2**를 찾아 노드·플러그인을 로드합니다.

```text
tetra_navigation2/launch/tetra_navigation.launch.py
  -> 이 패키지의 bringup / localization / navigation launch
  -> 설치된 nav2_controller, nav2_planner, nav2_amcl 등 실행
  -> controller_server가 dwb_core::DWBLocalPlanner 플러그인 로드
  -> tetra_navigation2/params/navigation.yaml로 로봇별 설정 적용
```

2026-10-16 확인한 이 PC의 `nav2_controller`, `dwb_core` 경로는 `/opt/ros/humble`이며,
설치된 `ros-humble-navigation2`, `ros-humble-nav2-bringup`, `ros-humble-dwb-core` 버전은 `1.1.20`입니다.
GitHub의 브랜치 HEAD를 매번 다운로드하거나 실행하는 방식이 아니므로 최신 브랜치와 설치 버전은 다를 수 있습니다.
환경을 source한 후 `ros2 pkg prefix nav2_controller`, `ros2 pkg prefix dwb_core`로 실제 선택된 경로를 확인할 수 있습니다.

## 검증

하드웨어 없는 Nav2 회귀 검사는 실제 모터나 시리얼 장치를 실행하지 않고,
별도 로컬 DDS 도메인(기본 193)에서 임시 지도·스캔·오도메트리를 생성합니다.

```bash
cd ~/tetra_ws/src/TETRA_ROS2_M
python3 tests/humble_nav_smoke.py
python3 tests/humble_nav_smoke.py --composition
python3 tests/humble_bringup_smoke.py
python3 tests/cartographer_smoke.py
python3 tests/ds4_model_check.py
python3 tests/ds4_driver_smoke.py
python3 tests/test_usb_ports.py
```

검사 항목: map_server/AMCL 포함 10개 노드 활성화, 두 navigation 액션 서버,
실제 DWB 플러그인·critic·목표 오차 조회, FollowPath 요청으로 속도 생성 및 취소 후 정지,
명시적 AMCL 초기 위치와 `/odom` 연결, 감속 영역에서 40% 출력, 근거리 정지 및 장애물 제거 후 재개,
제한보다 큰 명령 입력 시 전진 0.3 m/s·후진 0.2 m/s·회전 ±1.0 rad/s 상한 적용.
bringup 검사는 별도 도메인 194에서 새 PTY 가상 모터를 연결하여 모터의 `/odom`과 odom TF,
reliable QoS, EKF 미실행 및 실제 라이다 TF의 위치·회전 `(3.14, 3.14, 0)`을 확인합니다.
Cartographer 검사는 별도 도메인 200에서 가상 `/odom`·TF·스캔을 입력하고 지도와 `map -> odom` TF를 확인합니다.
DS4 모델 검사는 실제 STL 경계가 Nav2 footprint 안에 있고 정지·감속 영역이 이를 포함하는지 확인합니다.
DS4 드라이버 검사는 도메인 195의 새 가상 시리얼 포트(`/dev/pts/...`)로 ASCII 명령·단위 변환·각도 경계·비상정지·오류 종료를 확인합니다.
USB 규칙 검사는 장치 번호 변경·동일 변환기 중복·시리얼 부재·물리 포트 고정·기존 규칙 충돌을
가상 장치 정보로 확인하며 `/etc/udev`를 수정하지 않습니다.
이 검사는 실제 이동 정확도·하드웨어 통신·A2M12 실측 장착·제동거리를 검증하지 않습니다.

2026-10-16 로컬 검증 결과 (Ubuntu 22.04 / Humble):

- 이식 초기 전체 23개 패키지 빌드 성공. 이번 raw odom·sllidar 전환 후 변경 패키지 5개 (`tetra`, `tetra_bringup`, `tetra_navigation2`, `tetra_cartographer`, `sllidar_ros2`) 빌드 성공. 기존 벤더 C/C++ 경고는 남아 있음.
- 선배 AMCL 전체, Costmap의 footprint 외 전체 파라미터 및 Cartographer Lua 설정 일치 확인.
- Nav2 일반 실행(도메인 198)·컴포넌트 실행(199) 모두 통과. `/odom` 사용, 명시적 AMCL 초기 위치, DWB 경로 명령·취소, 40% 감속·정지·해제 및 속도 상한 확인.
- PTY 모터를 사용하는 bringup(201): 모터 `/odom` 및 동일 시각의 odom TF, reliable QoS, EKF 미실행, 선배 라이다 장착 TF 확인.
- Cartographer(203): 선배 Lua 로딩, `/odom` 입력, 지도 및 `map -> odom` TF 발행 확인.
- 클론한 `sllidar_node` 빌드·실행과 A2M12 파라미터 전달 확인. 존재하지 않는 임시 포트로 실행해 장치 접근 없이 연결 구성을 검사했으며 스캔 수신 검사는 아님.
- DS4 STL 해시·캐스터·모델 외곽과 Costmap·정지·감속 영역 포함 관계 재검사 통과.
- 앞선 가상 시리얼 DS4 ASCII·단위·각도 경계·비상정지·오류 종료 검사, USB 규칙 검사 10개 통과. 실물 USB 별칭 등록은 별도 필요.

시스템에 없던 공식 Humble 의존성은 `/tmp/tetra-humble-deps`에 압축 해제했고,
빌드 산출물은 `/tmp/tetra-humble-full`에 생성했습니다. Cartographer는 압축 해제된 패키지의
공통 Lua 파일과 설치된 TETRA Lua 파일을 임시 설정 디렉터리에 모아 검사했습니다.
**이는 시스템 apt 설치와 사용자 워크스페이스 재빌드를 대신하지 않습니다.**
실제 사용 환경에서는 앞의 의존성 설치 스크립트를 실행하고 `~/tetra_ws`에서 빌드하세요.
이전 Nav2 검사의 DDS 서비스 응답 타임아웃 이력이 있지만, 이번 도메인 198/199 검사는 모두 통과했습니다.
실기 시리얼 통신·A2M12 스캔·주행·도킹은 아직 검증하지 않았습니다.

## 📦 패키지 구성

### 1. 🏷️ apriltag_ros2 [🔗 상세 설명](./apriltag_ros2/README.md)
- **기능**: AprilTag 기반의 태그 감지 및 위치 추정.
- **주요 파일**:
  - 📄 `apriltag_detection.launch.py`: 태그 감지 실행을 위한 launch 파일.
  - 📂 `src/`: 태그 감지 및 위치 추정 관련 소스 코드.

### 2. 📡 cyglidar_d1-ROS2-v0.3.0 [🔗 상세 설명](./cyglidar_d1-ROS2-v0.3.0/README.md)
- **기능**: Cygbot D1 LiDAR 데이터 수집 및 처리.
- **주요 파일**:
  - 📄 `D1_Publisher.cpp`: LiDAR 데이터 퍼블리싱.
  - 🚀 `cyglidar.launch.py`: LiDAR 실행을 위한 launch 파일.

### 3. 📡 cyglidar_d2 [🔗 상세 설명](./cyglidar_d2/README.md)
- **기능**: Cygbot D2 LiDAR 데이터 수집 및 처리.
- **주요 파일**:
  - 📄 `main.cpp`: LiDAR 데이터 처리 메인 코드.
  - 🚀 `cyglidar.launch.py`: LiDAR 실행을 위한 launch 파일.

### 4. 🧭 iahrs_driver [🔗 상세 설명](./iahrs_driver/README.md)
- **기능**: IAHRS IMU 데이터 수집 및 퍼블리싱.
- **주요 파일**:
  - 📄 `iahrs_driver.cpp`: IMU 데이터 처리.
  - 🚀 `iahrs_driver.launch.py`: IMU 실행을 위한 launch 파일.

### 5. 🧩 interfaces [🔗 상세 설명](./interfaces/README.md)
- **기능**: ROS2 메시지 및 서비스 정의.
- **주요 파일**:
  - 📂 `msg/`: ROS2 메시지 정의.
  - 📂 `srv/`: ROS2 서비스 정의.

### 6. 🎥 realsense-ros [🔗 상세 설명](./realsense-ros/README.md)
- **기능**: Realsense D455 카메라 데이터 수집 및 처리.
- **주요 파일**:
  - 🚀 `rs_launch.py`: 카메라 실행을 위한 launch 파일.
  - 📂 `src/`: 카메라 데이터 처리 소스 코드.

### 7. 📡 sick_scan_xd-develop [🔗 상세 설명](./sick_scan_xd-develop/README.md)
- **기능**: SICK LiDAR 데이터 수집 및 처리.
- **주요 파일**:
  - ⚙️ `SickScan.cfg`: LiDAR 설정 파일.
  - 🚀 `launch/`: LiDAR 실행을 위한 launch 파일.

### 8. 🤖 tetra [🔗 상세 설명](./tetra/README.md)
- **기능**: Tetra 로봇의 기본 제어 기능 제공.
- **주요 파일**:
  - 📄 `tetra.cpp`: 로봇 제어 메인 코드.
  - 🚀 `tetra.launch.py`: 로봇 실행을 위한 launch 파일.

### 9. 🔧 tetra_bringup [🔗 상세 설명](./tetra_bringup/README.md)
- **기능**: Tetra 로봇의 초기화 및 설정.
- **주요 파일**:
  - 🚀 `tetra_bringup.launch.py`: 초기화 실행 파일.
  - 🚀 `sllidar_a2m12.launch.py`: A2M12 단독 실행. 기존 `params/ekf*.yaml`은 현재 실행에서 사용하지 않는 참고 파일.

### 10. 🗺️ tetra_cartographer [🔗 상세 설명](./tetra_cartographer/README.md)
- **기능**: SLAM 및 지도 생성.
- **주요 파일**:
  - 🚀 `cartographer.launch.py`: SLAM 실행 파일.
  - 🖼️ `tetra_cartographer.rviz`: RViz 설정 파일.

### 11. 🛠️ tetra_description [🔗 상세 설명](./tetra_description/README.md)
- **기능**: Tetra 로봇의 URDF 및 시뮬레이션 설정.
- **주요 파일**:
  - 📝 `tetra.xacro`: 로봇 URDF 파일.
  - 🚀 `tetra_description.launch.py`: 시뮬레이션 실행 파일.

### 12. 🔌 tetra_interface [🔗 상세 설명](./tetra_interface/README.md)
- **기능**: Tetra 로봇의 인터페이스 제어.
- **주요 파일**:
  - 📄 `tetra_interface.cpp`: 인터페이스 제어 코드.
  - 🚀 `tetra_interface.launch.py`: 실행 파일.

### 13. 🗺️ tetra_navigation2 [🔗 상세 설명](./tetra_navigation2/README.md)
- **기능**: 네비게이션 및 경로 계획.
- **주요 파일**:
  - 🚀 `navigation_launch.py`: 네비게이션 실행 파일.
  - 🖼️ `tetra_navigation2.rviz`: RViz 설정 파일.

### 14. 🛠️ tetra_service [🔗 상세 설명](./tetra_service/README.md)
- **기능**: Tetra 로봇의 서비스 관리.
- **주요 파일**:
  - 📄 `tetra_service.cpp`: 서비스 처리 코드.
  - 🚀 `tetra_service.launch.py`: 실행 파일.

### 15. 🎥 usb_cam-ros2 [🔗 상세 설명](./usb_cam-ros2/README.md)
- **기능**: USB 카메라 데이터 수집 및 처리.
- **주요 파일**:
  - 📄 `usb_cam_node.cpp`: 카메라 데이터 처리 코드.
  - 🚀 `camera.launch.py`: 실행 파일.

### 16. 🧱 virtual_wall [🔗 상세 설명](./virtual_wall/README.md)
- **기능**: 가상 벽 생성 및 관리.
- **주요 파일**:
  - 📄 `virtual_wall.cpp`: 가상 벽 처리 코드.
  - 🚀 `virtual_wall.launch.py`: 실행 파일.

