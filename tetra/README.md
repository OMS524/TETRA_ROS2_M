# 🤖 Tetra

## 📖 개요
Tetra 패키지는 Tetra 로봇의 기본 제어 기능을 제공합니다. 이 패키지는 로봇의 이동 및 센서 데이터를 처리합니다.

## 의존성
- ament_cmake
- rclcpp
- std_msgs
- geometry_msgs
- nav_msgs
- sensor_msgs
- tf2
- tf2_ros
- interfaces

## 설치 방법
1. ROS2 워크스페이스를 설정합니다.
2. `tetra` 디렉토리를 `src` 폴더에 복사합니다.
3. 워크스페이스 루트에서 다음 명령어를 실행합니다:
   ```bash
   colcon build --packages-select tetra
   ```

## 주요 파일 설명
### include/
- **`rs232_common.h`**: RS232 통신의 공통 헤더 파일.
- **`rs232.h`**: RS232 통신 관련 함수 정의.

### src/
- **`drive_module.c`**: 로봇의 구동 모듈 구현.
- **`dssp_rs232_drive_module.c`**: RS232 기반 구동 모듈 구현.
- **`tetra.cpp`**: ROS2 노드의 메인 파일로, 로봇의 동작을 제어합니다. 주요 기능:
  - `/cmd_vel` 토픽을 구독하여 로봇의 속도를 제어.
  - `/odom` 토픽을 퍼블리시하여 로봇의 위치와 자세 정보를 제공합니다.
  - 다양한 서비스(`ParameterRead`, `ParameterWrite`, `SetMoveMode` 등)를 통해 로봇의 설정 및 동작을 제어.

### launch/
- **`tetra_launch.xml`**: XML 형식의 Launch 파일.
- **`tetra.launch.py`**: Python 형식의 Launch 파일로, ROS2 노드를 실행합니다.

## 주요 토픽 및 서비스
### 퍼블리시 토픽
- **`/odom`** (타입: `nav_msgs/msg/Odometry`): 로봇의 위치와 자세 정보를 제공합니다.
- **`/bumper_data`** (타입: `std_msgs/msg/Int32`): 범퍼 상태를 퍼블리시합니다.
- **`/emg_state`** (타입: `std_msgs/msg/Int32`): 비상 정지 상태를 퍼블리시합니다.
- **`/left_error_code`** (타입: `std_msgs/msg/Int32`): 왼쪽 모터의 오류 코드를 퍼블리시합니다.
- **`/right_error_code`** (타입: `std_msgs/msg/Int32`): 오른쪽 모터의 오류 코드를 퍼블리시합니다.

### 구독 토픽
- **`/cmd_vel_nav`** (타입: `geometry_msgs/msg/Twist`): 내비게이션 명령을 수신하여 로봇의 속도를 제어합니다.
- **`/cmd_vel_nav2`** (타입: `geometry_msgs/msg/Twist`): 보조 내비게이션 명령을 수신합니다.
- **`/cmd_vel`** (타입: `geometry_msgs/msg/Twist`): 키보드 등 수동 속도 명령을 수신합니다.
- **`/accel_vel`** (타입: `std_msgs/msg/Int32`): 가속도 데이터를 수신합니다.
- **`/pose_reset`** (타입: `std_msgs/msg/Int32`): 로봇의 위치를 초기화합니다.
- **`/servo_on`** (타입: `std_msgs/msg/Int32`): 서보 모터를 활성화합니다.
- **`/power_status`** (타입: `std_msgs/msg/Int32`): 전원 상태를 수신합니다.
- **`/joy`** (타입: `sensor_msgs/msg/Joy`): 조이스틱 입력을 수신합니다.

### 서비스
- **`param_read_cmd`** (타입: `interfaces/srv/ParameterRead`): 로봇의 매개변수를 읽습니다.
- **`param_write_cmd`** (타입: `interfaces/srv/ParameterWrite`): 로봇의 매개변수를 설정합니다.
- **`mode_change_cmd`** (타입: `interfaces/srv/SetMoveMode`): 로봇의 이동 모드를 변경합니다.
- **`linear_position_move`** (타입: `interfaces/srv/LinearPositionMove`): 선형 위치 이동 명령을 실행합니다.
- **`angular_position_move`** (타입: `interfaces/srv/AngularPositionMove`): 각도 위치 이동 명령을 실행합니다.
- **`servo`** (타입: `interfaces/srv/Servo`): 서보 모터를 On/Off 제어합니다.

## 사용 방법 예시
1. Launch 파일 실행:
   ```bash
   ros2 launch tetra tetra.launch.py
   ```
2. `/cmd_vel` 토픽을 퍼블리시하여 로봇의 속도를 제어합니다:
   ```bash
   ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.1}}"
   ```
3. `/param_read_cmd` 서비스를 호출하여 매개변수를 읽습니다:
   ```bash
   ros2 service call /param_read_cmd interfaces/srv/ParameterRead "{num: 1}"
   ```
