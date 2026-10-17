"""DS4-M description with configurable lidar extrinsics (metres / radians)."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    mount = {'lidar_x': '0.1372', 'lidar_y': '0.0', 'lidar_z': '0.142',
             'lidar_roll': '3.14', 'lidar_pitch': '3.14', 'lidar_yaw': '0.0'}
    args = [DeclareLaunchArgument('use_sim_time', default_value='false')]
    command = ['xacro ', PathJoinSubstitution([
        FindPackageShare('tetra_description'), 'urdf', 'tetra.xacro'])]
    for name, default in mount.items():
        args.append(DeclareLaunchArgument(name, default_value=default))
        command.extend([' ', name, ':=', LaunchConfiguration(name)])
    return LaunchDescription(args + [
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             output='screen', parameters=[{
                 'use_sim_time': ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool),
                 'robot_description': ParameterValue(Command(command), value_type=str),
             }]),
    ])
