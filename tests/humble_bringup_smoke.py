#!/usr/bin/env python3
"""Run DS4 bringup with a PTY motor emulator; no physical devices are opened."""
import argparse
import os
import math
from pathlib import Path
import signal
import subprocess
import tempfile
import time

from ds4_driver_smoke import Controller


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--domain-id', type=int, default=194)
    args = parser.parse_args()
    os.environ['ROS_DOMAIN_ID'] = str(args.domain_id)
    os.environ['ROS_LOCALHOST_ONLY'] = '1'
    if os.environ.get('ROS_DISTRO') != 'humble':
        raise RuntimeError('Source ROS 2 Humble and the built workspace first.')
    import rclpy
    from nav_msgs.msg import Odometry
    from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
    from tf2_msgs.msg import TFMessage

    work = Path(tempfile.mkdtemp(prefix='tetra-bringup-smoke-'))
    os.environ['ROS_LOG_DIR'] = str(work / 'ros_logs')
    rclpy.init()
    node = rclpy.create_node('test_ds4_bringup')
    rclpy.spin_once(node, timeout_sec=1.0)
    others = [name for name, _ in node.get_node_names_and_namespaces()
              if name != node.get_name()]
    if others:
        node.destroy_node()
        rclpy.shutdown()
        raise RuntimeError(f'DDS domain {args.domain_id} already occupied: {others}')
    received, laser_transforms, odom_transforms = [], [], []

    def receive_static(message):
        laser_transforms.extend(t for t in message.transforms if t.child_frame_id == 'laser')

    def receive_tf(message):
        odom_transforms.extend(t for t in message.transforms
                               if t.header.frame_id == 'odom' and t.child_frame_id == 'base_footprint')

    static_subscription = node.create_subscription(
        TFMessage, 'tf_static', receive_static,
        QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL))
    tf_subscription = node.create_subscription(TFMessage, 'tf', receive_tf, 100)
    # Reliable subscription ensures Cartographer / Nav2 can consume the raw motor stream.
    subscription = node.create_subscription(Odometry, 'odom', received.append, 10)
    controller = Controller()
    log = (work / 'launch.log').open('w')
    proc = subprocess.Popen([
        'ros2', 'launch', 'tetra_bringup', 'tetra_bringup.launch.py',
        f'motor_port:={controller.port}',
        'enable_lidar:=false', 'use_imu:=false', 'use_rviz:=false',
    ], stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.05)
            assert not controller.errors, controller.errors
            if proc.poll() is not None:
                raise RuntimeError('Bringup launch failed')
        assert received and odom_transforms, 'Missing direct motor /odom or odom TF'
        odom, transform = received[-1], odom_transforms[-1]
        assert odom.header.frame_id == 'odom' and odom.child_frame_id == 'base_footprint'
        assert abs(odom.pose.pose.position.x - 1.0) < 1e-6
        assert abs(odom.pose.pose.position.y - 2.0) < 1e-6
        assert abs(transform.transform.translation.x - 1.0) < 1e-6
        assert abs(transform.transform.translation.y - 2.0) < 1e-6
        assert abs(transform.transform.rotation.z - math.sqrt(0.5)) < 1e-6
        stamps = {(m.header.stamp.sec, m.header.stamp.nanosec) for m in received}
        assert any((t.header.stamp.sec, t.header.stamp.nanosec) in stamps for t in odom_transforms)
        names = {name for name, _ in node.get_node_names_and_namespaces()}
        assert 'tetra' in names and 'ekf_filter_node' not in names, names
        assert 'tetra_interface' not in names, 'Power-board driver should be disabled by default'
        assert node.count_publishers('/odometry/filtered') == 0, 'Unexpected EKF output'
        publishers = node.get_publishers_info_by_topic('/odom')
        assert len(publishers) == 1 and publishers[0].node_name == 'tetra'
        assert publishers[0].qos_profile.reliability == ReliabilityPolicy.RELIABLE
        print('PASS: bringup uses motor /odom and matching odom TF, reliable QoS, no EKF', flush=True)
        assert laser_transforms, 'No base_link -> laser static transform'
        transform = laser_transforms[-1]
        assert transform.header.frame_id == 'base_link'
        xyz = transform.transform.translation
        assert abs(xyz.x - 0.1372) < 1e-6 and abs(xyz.y) < 1e-6 and abs(xyz.z - 0.142) < 1e-6
        s, c = math.sin(3.14 / 2), math.cos(3.14 / 2)
        expected = (s*c, c*s, -s*s, c*c)
        q = transform.transform.rotation
        assert abs(sum(a*b for a, b in zip((q.x, q.y, q.z, q.w), expected))) > 1 - 1e-8
        print('PASS: live laser TF matches received DS4 mount (RPY 3.14, 3.14, 0)', flush=True)
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGINT)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
        controller.close()
        log.close()
        node.destroy_node()
        rclpy.shutdown()
        print(f'Launch log: {work / "launch.log"}', flush=True)


if __name__ == '__main__':
    main()
