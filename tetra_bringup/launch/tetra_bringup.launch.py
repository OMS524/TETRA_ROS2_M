"""Ubuntu 22.04 / Humble bringup: TETRA DS4-M with RPLIDAR A2M12."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    def option(name):
        return IfCondition(LaunchConfiguration(name))

    def include(package, filename, condition=None, arguments=None):
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
                FindPackageShare(package), 'launch', filename])),
            condition=condition, launch_arguments=(arguments or {}).items())

    defaults = {
        'use_sim_time': 'false',
        'enable_base': 'true',
        'enable_interface': 'false',
        'enable_lidar': 'true',
        'use_rviz': 'true',
        'rviz_config': PathJoinSubstitution([
            FindPackageShare('tetra_bringup'), 'rviz', 'tetra_bringup.rviz']),
        'use_imu': 'false',
        'enable_joy': 'false',
        'enable_service': 'false',
        'enable_web': 'false',
        'enable_usb_camera': 'false',
        'enable_apriltag': 'false',
        'enable_cyglidar': 'false',
        'enable_realsense': 'false',
        'enable_virtual_wall': 'false',
        'motor_port': '/dev/tetra/motor',
        'interface_port': '/dev/tetra/interface',
        'imu_port': '/dev/IMU',
        'lidar_port': '/dev/tetra/lidar',
        'lidar_baudrate': '256000',
        'lidar_scan_mode': 'Sensitivity',
        'lidar_inverted': 'false',
        'lidar_x': '0.1372', 'lidar_y': '0.0', 'lidar_z': '0.142',
        'lidar_roll': '3.14', 'lidar_pitch': '3.14', 'lidar_yaw': '0.0',
    }
    args = [DeclareLaunchArgument(name, default_value=value)
            for name, value in defaults.items()]
    clock = {'use_sim_time': ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool)}
    nodes = [
        Node(package='tetra', executable='tetra', output='screen',
             condition=option('enable_base'), parameters=[clock, {
                 'm_bEKF_option': False, 'serial_port': LaunchConfiguration('motor_port')}]),
        Node(package='tetra_interface', executable='tetra_interface', output='screen',
             condition=option('enable_interface'), parameters=[clock, {
                 'm_bConveyor_option': False, 'm_bUltrasonic_option': False,
                 'serial_port': LaunchConfiguration('interface_port')}]),
        Node(package='iahrs_driver', executable='iahrs_driver', output='screen',
             condition=option('use_imu'), parameters=[clock, {
                 'm_bSingle_TF_option': False, 'serial_port': LaunchConfiguration('imu_port')}]),
        Node(package='joy', executable='joy_node', output='screen',
             condition=option('enable_joy'), parameters=[clock, {'deadzone': 0.05}]),
        Node(package='rviz2', executable='rviz2', output='screen',
             condition=option('use_rviz'), parameters=[clock],
             arguments=['-d', LaunchConfiguration('rviz_config')]),
        Node(package='tetra_service', executable='tetra_service', output='screen',
             condition=option('enable_service'), parameters=[clock, {'m_dHome_ID': 0}]),
        Node(package='rosbridge_server', executable='rosbridge_websocket',
             condition=option('enable_web'), parameters=[{'port': 9090, 'max_message_size': 10000000}]),
        Node(package='rosapi', executable='rosapi_node', condition=option('enable_web')),
        Node(package='web_video_server', executable='web_video_server',
             condition=option('enable_web'), parameters=[{'quality': 1}]),
    ]
    # Motor driver owns /odom and odom -> base_footprint; no EKF is launched.
    nodes.extend([
        include('tetra_description', 'tetra_description.launch.py', arguments={
            name: LaunchConfiguration(name) for name in (
                'use_sim_time', 'lidar_x', 'lidar_y', 'lidar_z',
                'lidar_roll', 'lidar_pitch', 'lidar_yaw')}),
        include('tetra_bringup', 'sllidar_a2m12.launch.py', option('enable_lidar'), {
            name: LaunchConfiguration(name) for name in (
                'lidar_port', 'lidar_baudrate', 'lidar_scan_mode', 'lidar_inverted', 'use_sim_time')}),
        include('usb_cam', 'camera.launch.py', option('enable_usb_camera')),
        include('apriltag_ros', 'apriltag_detection.launch.py', option('enable_apriltag')),
        include('cyglidar_d1_ros2', 'cyglidar.launch.py', option('enable_cyglidar')),
        include('realsense2_camera', 'rs_launch.py', option('enable_realsense')),
        include('virtual_wall', 'virtual_wall.launch.py', option('enable_virtual_wall')),
    ])
    return LaunchDescription(args + nodes)
