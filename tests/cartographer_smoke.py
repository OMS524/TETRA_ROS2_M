#!/usr/bin/env python3
"""Check the installed Cartographer config with synthetic /odom, TF and scans."""
import argparse
import math
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--domain-id', type=int, default=200)
    parser.add_argument('--configuration-directory', help='Optional Lua include directory for extracted dependencies')
    args = parser.parse_args()
    os.environ['ROS_DOMAIN_ID'] = str(args.domain_id)
    os.environ['ROS_LOCALHOST_ONLY'] = '1'
    if os.environ.get('ROS_DISTRO') != 'humble':
        raise RuntimeError('Source Humble and the built workspace first.')
    import rclpy
    from geometry_msgs.msg import TransformStamped
    from nav_msgs.msg import Odometry, OccupancyGrid
    from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy
    from sensor_msgs.msg import LaserScan
    from tf2_msgs.msg import TFMessage
    from tf2_ros import StaticTransformBroadcaster, TransformBroadcaster

    work = Path(tempfile.mkdtemp(prefix='tetra-cartographer-smoke-'))
    os.environ['ROS_LOG_DIR'] = str(work / 'ros_logs')
    rclpy.init()
    node = rclpy.create_node('test_cartographer')
    rclpy.spin_once(node, timeout_sec=1)
    others = [name for name, _ in node.get_node_names_and_namespaces() if name != node.get_name()]
    if others:
        node.destroy_node()
        rclpy.shutdown()
        raise RuntimeError(f'DDS domain {args.domain_id} already occupied: {others}')
    static = StaticTransformBroadcaster(node)
    dynamic = TransformBroadcaster(node)
    laser_tf = TransformStamped()
    laser_tf.header.frame_id = 'base_footprint'
    laser_tf.child_frame_id = 'laser'
    laser_tf.transform.translation.z = 0.2
    laser_tf.transform.rotation.w = 1.0
    laser_tf.header.stamp = node.get_clock().now().to_msg()
    static.sendTransform(laser_tf)
    odom_tf = TransformStamped()
    odom_tf.header.frame_id = 'odom'
    odom_tf.child_frame_id = 'base_footprint'
    odom_tf.transform.rotation.w = 1.0
    odom = Odometry()
    odom.header.frame_id = 'odom'
    odom.child_frame_id = 'base_footprint'
    odom.pose.pose.orientation.w = 1.0
    scan = LaserScan()
    scan.header.frame_id = 'laser'
    scan.angle_min = -math.pi
    scan.angle_increment = 2 * math.pi / 360
    scan.angle_max = scan.angle_min + 359 * scan.angle_increment
    scan.range_min, scan.range_max = 0.12, 13.5
    scan.scan_time = 0.1
    scan.time_increment = 0.1 / 360
    # A rectangular virtual room, with the robot stationary at the origin.
    scan.ranges = [min(3 / max(abs(math.cos(scan.angle_min + i * scan.angle_increment)), 1e-6),
                       2 / max(abs(math.sin(scan.angle_min + i * scan.angle_increment)), 1e-6))
                   for i in range(360)]
    odom_pub = node.create_publisher(Odometry, 'odom', 10)
    scan_pub = node.create_publisher(LaserScan, 'scan', qos_profile_sensor_data)
    maps, map_transforms = [], []
    map_sub = node.create_subscription(
        OccupancyGrid, 'map', maps.append,
        QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))

    def receive_tf(message):
        map_transforms.extend(t for t in message.transforms
                              if t.header.frame_id == 'map' and t.child_frame_id == 'odom')

    tf_sub = node.create_subscription(TFMessage, 'tf', receive_tf, 100)

    def publish():
        stamp = node.get_clock().now().to_msg()
        odom_tf.header.stamp = stamp
        odom.header.stamp = stamp
        scan.header.stamp = stamp
        dynamic.sendTransform(odom_tf)
        odom_pub.publish(odom)
        scan_pub.publish(scan)

    timer = node.create_timer(0.1, publish)
    log = (work / 'launch.log').open('w')
    command = ['ros2', 'launch', 'tetra_cartographer', 'cartographer.launch.py', 'use_rviz:=false']
    if args.configuration_directory:
        command.append('cartographer_config_dir:=' + args.configuration_directory)
    proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.05)
            if proc.poll() is not None:
                raise RuntimeError(f'Cartographer launch exited: {proc.returncode}')
            if maps and map_transforms and any(value >= 0 for value in maps[-1].data):
                break
        assert maps and any(value >= 0 for value in maps[-1].data), 'No occupancy map from synthetic scans'
        assert map_transforms, 'No Cartographer map -> odom TF'
        assert maps[-1].header.frame_id == 'map' and abs(maps[-1].info.resolution - 0.05) < 1e-6
        assert any(info.node_name == 'cartographer_node'
                   for info in node.get_subscriptions_info_by_topic('/odom')), 'Cartographer is not using motor /odom'
        assert node.count_subscribers('/odometry/filtered') == 0
        print('PASS: Cartographer loads senior Lua config, consumes /odom and publishes map + map->odom TF', flush=True)
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGINT)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
        log.close()
        node.destroy_node()
        rclpy.shutdown()
        print(f'Launch log: {work / "launch.log"}', flush=True)


if __name__ == '__main__':
    main()
