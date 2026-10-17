"""SLAMTEC A2M12: 256000 baud, /scan, laser frame."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('lidar_port', default_value='/dev/tetra/lidar'),
        DeclareLaunchArgument('lidar_baudrate', default_value='256000'),
        DeclareLaunchArgument('lidar_inverted', default_value='false'),
        DeclareLaunchArgument('lidar_scan_mode', default_value='Sensitivity'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        Node(package='sllidar_ros2', executable='sllidar_node', name='sllidar_node',
             output='screen', parameters=[{
                 'use_sim_time': ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool),
                 'channel_type': 'serial',
                 'serial_port': LaunchConfiguration('lidar_port'),
                 'serial_baudrate': ParameterValue(LaunchConfiguration('lidar_baudrate'), value_type=int),
                 'frame_id': 'laser',
                 'inverted': ParameterValue(LaunchConfiguration('lidar_inverted'), value_type=bool),
                 'angle_compensate': True,
                 'scan_mode': LaunchConfiguration('lidar_scan_mode'),
             }]),
    ])
