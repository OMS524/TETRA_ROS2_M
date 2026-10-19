# TETRA DS4-M bringup — Humble

`tetra_bringup.launch.py`는 모터, SLAMTEC A2M12, DS4 모델과 RViz2를 실행합니다.
RViz에는 Grid, RobotModel, LaserScan만 표시하며, Fixed Frame은 `odom`입니다.
전원보드는 기본 비활성이며, 포트 등록 후 `enable_interface:=true`로 추가합니다.
모터 드라이버가 `/odom`과 `odom -> base_footprint` TF를 직접 발행합니다. EKF는 실행하지 않습니다.
`params/ekf*.yaml`은 참고용으로 남아 있으며 현재 launch에서 읽지 않습니다.

```bash
ros2 launch tetra_bringup tetra_bringup.launch.py
# RViz 없이 실행
ros2 launch tetra_bringup tetra_bringup.launch.py use_rviz:=false
# 라이다만 실행
ros2 launch tetra_bringup sllidar_a2m12.launch.py
```

| 인자 | 기본값 | 역할 |
|---|---|---|
| `motor_port` | `/dev/tetra/motor` | 모터 제어 보드 |
| `interface_port` | `/dev/tetra/interface` | 전원·입출력 보드 |
| `lidar_port` | `/dev/tetra/lidar` | A2M12 |
| `enable_base`, `enable_lidar` | true | 모터·라이다 실행 여부 |
| `enable_interface` | false | 전원·입출력 보드 실행 여부 |
| `use_rviz` | true | bringup과 같은 ROS 환경에서 RViz2 실행 |
| `rviz_config` | 패키지의 `rviz/tetra_bringup.rviz` | RViz 표시 설정 |
| `use_imu` | false | IAHRS 드라이버 실행만 제어; odom 융합 없음 |
| `enable_service`, `enable_joy`, `enable_web` | false | 제조사 부가 기능 |
| `use_sim_time` | false | 실기 시간 사용 |

라이다는 저장소 안에 클론한 `sllidar_ros2`의 `sllidar_node`를 사용합니다.
A2M12 기본값은 256000 baud, `laser` frame, `Sensitivity`, angle_compensate=true, inverted=false입니다.

의존성 설치, 빌드, USB 별칭 등록과 전체 인자는 [상위 README](../README.md)를 따르세요.
