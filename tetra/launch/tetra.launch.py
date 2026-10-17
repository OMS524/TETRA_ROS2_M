from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('motor_port', default_value='/dev/tetra/motor'),
        DeclareLaunchArgument('use_ekf', default_value='false'),
        Node(package='tetra', executable='tetra', output='screen', parameters=[{
            'serial_port': LaunchConfiguration('motor_port'),
            'm_bEKF_option': ParameterValue(LaunchConfiguration('use_ekf'), value_type=bool),
        }]),
    ])
