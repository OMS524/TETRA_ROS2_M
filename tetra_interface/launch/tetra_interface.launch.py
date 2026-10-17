"""DS4-M power / I/O board with a configurable USB serial alias."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('interface_port', default_value='/dev/tetra/interface'),
        Node(package='tetra_interface', executable='tetra_interface', output='screen',
             parameters=[{
                 'serial_port': LaunchConfiguration('interface_port'),
                 'm_bConveyor_option': False,
                 'm_bUltrasonic_option': False,
             }]),
    ])
