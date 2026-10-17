# TETRA DS4-M description

기본 모델은 AIRO-lab/tetra_pkg의 실물 DS4 모델입니다. 하부·상부 본체, 구동 바퀴 2개,
후방 캐스터 2개를 포함하며 `meshes/ds4_m/`의 STL만 로드합니다.
[원본 출처와 파일 대응](meshes/ds4_m/README.md)을 참고하세요.

```bash
ros2 launch tetra_description tetra_description.launch.py
```

`lidar_x/y/z`와 `lidar_roll/pitch/yaw`로 A2M12 장착 위치를 지정합니다.
단위는 m / rad이며 `base_link` 기준입니다. 기본 위치 `(0.1372, 0, 0.142)`와
회전 `(3.14, 3.14, 0)`은 직접 받은 선배 파일의 `laser_joint`와 같습니다.
A2M12의 실제 브래킷을 새로 측정한 값은 아닙니다.

`urdf/tetra.xacro`가 기본 진입점이고 `base.urdf.xacro`가 DS4 본체·바퀴를 정의합니다.
기존 카메라 노드와의 호환을 위해 `camera` 프레임 이름은 유지했습니다.
`base_footprint`의 시각화 직사각형은 Nav2의 DS4 영역(x -0.490~0.240, y ±0.260 m)과 같습니다.

상위 `meshes/`에 남은 DS5-M 파일과 `urdf/tetra_bak.xacro`는 기본 실행에서 사용하지 않습니다.
설치·빌드·주행 명령과 검증 방법은 [루트 README](../README.md)를 참고하세요.
