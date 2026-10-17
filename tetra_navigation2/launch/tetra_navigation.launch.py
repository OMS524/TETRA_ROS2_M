"""Humble navigation for the TETRA M / RPLIDAR A2M12 profile."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution


def generate_launch_description():
    share = get_package_share_directory('tetra_navigation2')
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('map_name', default_value='office.yaml',
                              description='Map in the installed tetra_navigation2/maps directory'),
        DeclareLaunchArgument('map', default_value=PathJoinSubstitution([
            share, 'maps', LaunchConfiguration('map_name')]),
            description='Absolute path to your map YAML; overrides map_name'),
        DeclareLaunchArgument('params_file', default_value=os.path.join(
            share, 'params', 'navigation.yaml')),
        DeclareLaunchArgument('autostart', default_value='true'),
        DeclareLaunchArgument('use_composition', default_value='false'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(share, 'launch', 'bringup_launch.py')),
            launch_arguments={
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'map': LaunchConfiguration('map'),
                'params_file': LaunchConfiguration('params_file'),
                'autostart': LaunchConfiguration('autostart'),
                'use_composition': LaunchConfiguration('use_composition'),
            }.items()),
    ])
