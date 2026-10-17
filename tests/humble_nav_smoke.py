#!/usr/bin/env python3
"""Hardware-free Humble integration check, with a dedicated local DDS domain.

Source the built workspace, then run:
    python3 tests/humble_nav_smoke.py
    python3 tests/humble_nav_smoke.py --composition
Never starts the TETRA driver or opens a serial port.
"""
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
    parser.add_argument('--composition', action='store_true')
    parser.add_argument('--domain-id', type=int, default=193)
    args = parser.parse_args()
    os.environ['ROS_DOMAIN_ID'] = str(args.domain_id)
    os.environ['ROS_LOCALHOST_ONLY'] = '1'
    if os.environ.get('ROS_DISTRO') != 'humble':
        raise RuntimeError('Source ROS 2 Humble and the built workspace first.')

    import rclpy
    from action_msgs.msg import GoalStatus
    from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, TransformStamped, Twist
    from lifecycle_msgs.srv import GetState
    from nav2_msgs.action import FollowPath
    from nav_msgs.msg import Odometry
    from rcl_interfaces.srv import GetParameters
    from rclpy.action import ActionClient
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import LaserScan
    from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster

    work = Path(tempfile.mkdtemp(prefix='tetra-humble-smoke-'))
    # An empty 20x20 metre map, generated locally just for lifecycle validation.
    (work / 'map.pgm').write_bytes(b'P5\n400 400\n255\n' + bytes([254]) * 160000)
    (work / 'map.yaml').write_text(
        'image: map.pgm\nresolution: 0.05\norigin: [-10.0, -10.0, 0.0]\n'
        'negate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.25\n')
    rclpy.init()
    node = rclpy.create_node('tetra_humble_smoke')
    # Fail if the chosen domain already contains other nodes, before sending commands.
    rclpy.spin_once(node, timeout_sec=1.0)
    others = [name for name, _ in node.get_node_names_and_namespaces()
              if name not in ('tetra_humble_smoke', '_ros2cli_daemon_0')]
    if others:
        node.destroy_node()
        rclpy.shutdown()
        raise RuntimeError(f'DDS domain {args.domain_id} is occupied: {others}')
    static_tf = StaticTransformBroadcaster(node)
    transforms = []
    for parent, child in [('odom', 'base_footprint'), ('base_footprint', 'laser')]:
        transform = TransformStamped()
        transform.header.stamp = node.get_clock().now().to_msg()
        transform.header.frame_id = parent
        transform.child_frame_id = child
        transform.transform.rotation.w = 1.0
        transforms.append(transform)
    static_tf.sendTransform(transforms)
    scan_pub = node.create_publisher(LaserScan, 'scan', qos_profile_sensor_data)
    odom_pub = node.create_publisher(Odometry, 'odom', 10)
    command_pub = node.create_publisher(Twist, 'cmd_vel_raw', 10)
    initial_pose_pub = node.create_publisher(PoseWithCovarianceStamped, 'initialpose', 10)
    scan = LaserScan()
    scan.header.frame_id = 'laser'
    scan.angle_min = -math.pi
    scan.angle_increment = 2 * math.pi / 720
    scan.angle_max = scan.angle_min + 719 * scan.angle_increment
    scan.range_min, scan.range_max = 0.1, 12.0
    scan.scan_time = 0.1
    odom = Odometry()
    odom.header.frame_id = 'odom'
    odom.child_frame_id = 'base_footprint'
    odom.pose.pose.orientation.w = 1.0
    state = {'range': 4.0, 'command': 0.0, 'angular_command': 0.0,
             'output': None, 'angular_output': None, 'received': 0.0,
             'inject_command': False, 'dwb_commands': 0,
             'localized': False, 'initial_sent': 0.0}

    def receive(message):
        assert -0.2001 <= message.linear.x <= 0.3001, 'Nav2 linear speed limit exceeded'
        assert abs(message.angular.z) <= 1.0001, 'Nav2 angular speed limit exceeded'
        state['output'] = message.linear.x
        state['angular_output'] = message.angular.z
        state['received'] = time.monotonic()

    subscription = node.create_subscription(Twist, 'cmd_vel_nav2', receive, 10)
    def localized(message):
        state['localized'] = True
    localization_subscription = node.create_subscription(
        PoseWithCovarianceStamped, 'amcl_pose', localized, 10)


    def receive_raw(message):
        # Test commands are disabled during the FollowPath action, so these
        # velocities must have been computed by the live controller.
        if not state['inject_command'] and message.linear.x > 0.05:
            assert message.linear.x <= 0.3601, 'DWB linear maximum exceeded'
            assert abs(message.angular.z) <= 2.5001, 'DWB angular maximum exceeded'
            state['dwb_commands'] += 1

    raw_subscription = node.create_subscription(Twist, 'cmd_vel_raw', receive_raw, 10)
    follow_client = ActionClient(node, FollowPath, 'follow_path')
    parameter_client = node.create_client(GetParameters, 'controller_server/get_parameters')

    def publish():
        stamp = node.get_clock().now().to_msg()
        scan.header.stamp = stamp
        scan.ranges = [state['range']] * 720
        odom.header.stamp = stamp
        scan_pub.publish(scan)
        odom_pub.publish(odom)
        # Match real operation: AMCL now waits for RViz's initial pose instead
        # of automatically assuming that the robot starts at map origin.
        if 'amcl' in active and not state['localized'] and time.monotonic() - state['initial_sent'] > 1:
            initial = PoseWithCovarianceStamped()
            initial.header.frame_id = 'map'
            initial.header.stamp = stamp
            initial.pose.pose.orientation.w = 1.0
            initial.pose.covariance[0] = initial.pose.covariance[7] = 0.25
            initial.pose.covariance[35] = 0.0685
            initial_pose_pub.publish(initial)
            state['initial_sent'] = time.monotonic()
        command = Twist()
        command.linear.x = state['command']
        command.angular.z = state['angular_command']
        if state['inject_command']:
            command_pub.publish(command)

    timer = node.create_timer(0.05, publish)
    log = (work / 'launch.log').open('w')
    proc = subprocess.Popen([
        'ros2', 'launch', 'tetra_navigation2', 'tetra_navigation.launch.py',
        f'map:={work / "map.yaml"}',
        'use_composition:=' + str(args.composition).lower(),
    ], stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    names = ['map_server', 'amcl', 'controller_server', 'smoother_server',
             'planner_server', 'behavior_server', 'velocity_smoother',
             'collision_monitor', 'bt_navigator', 'waypoint_follower']
    clients = {name: node.create_client(GetState, f'{name}/get_state') for name in names}
    active = set()
    pending = {}

    def spin_until(predicate, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.05)
            if proc.poll() is not None:
                raise RuntimeError(f'Nav2 launch exited with {proc.returncode}')
            if predicate():
                return True
        return False

    def all_active():
        for name, client in clients.items():
            if name in active:
                continue
            future = pending.get(name)
            if future is not None and future.done():
                if future.result().current_state.id == 3:
                    active.add(name)
                del pending[name]
            elif future is None and client.service_is_ready():
                pending[name] = client.call_async(GetState.Request())
        return len(active) == len(names)

    try:
        assert spin_until(all_active, 45), f'Nodes not active: {sorted(set(names) - active)}'
        assert state['localized'], 'AMCL did not initialize from initialpose'
        print('PASS: all 10 Nav2 nodes active with motor /odom and explicit AMCL initial pose', flush=True)
        # Both custom BT XMLs must be loaded, exposing both navigation actions.
        assert spin_until(lambda: len([name for name, _ in node.get_service_names_and_types()
                                     if name in ('/navigate_to_pose/_action/send_goal',
                                                 '/navigate_through_poses/_action/send_goal')]) == 2, 5)
        print('PASS: NavigateToPose and NavigateThroughPoses action servers', flush=True)
        assert spin_until(parameter_client.service_is_ready, 5), 'Controller parameter service unavailable'
        request = GetParameters.Request()
        request.names = ['FollowPath.plugin', 'general_goal_checker.stateful', 'FollowPath.critics',
                         'general_goal_checker.xy_goal_tolerance',
                         'general_goal_checker.yaw_goal_tolerance', 'odom_topic']
        parameters = parameter_client.call_async(request)
        assert spin_until(parameters.done, 5), 'Controller parameter query timed out'
        values = parameters.result().values
        assert len(values) == len(request.names), 'Controller parameters unavailable'
        assert values[0].string_value == 'dwb_core::DWBLocalPlanner', 'DWB plugin not selected'
        assert values[1].type == 1 and values[1].bool_value, 'Goal checker stateful must be boolean true'
        assert list(values[2].string_array_value) == [
            'RotateToGoal', 'Oscillation', 'BaseObstacle', 'GoalAlign',
            'PathAlign', 'PathDist', 'GoalDist'], 'Unexpected DWB critics'
        assert values[3].double_value == 0.25 and values[4].double_value == 0.25
        assert values[5].string_value == '/odom', 'Controller must use motor /odom'

        # Exercise actual trajectory generation, not only injected cmd_vel.
        # The fixed virtual robot stays at the origin, so cancel after receiving
        # commands, before the progress checker expects physical displacement.
        assert spin_until(follow_client.server_is_ready, 5), 'FollowPath action unavailable'
        goal = FollowPath.Goal()
        goal.controller_id = 'FollowPath'
        goal.goal_checker_id = 'general_goal_checker'
        goal.path.header.frame_id = 'odom'
        goal.path.header.stamp = node.get_clock().now().to_msg()
        for index in range(41):
            pose = PoseStamped()
            pose.header = goal.path.header
            pose.pose.position.x = index * 0.05
            pose.pose.orientation.w = 1.0
            goal.path.poses.append(pose)
        sent = follow_client.send_goal_async(goal)
        assert spin_until(sent.done, 5), 'FollowPath goal request timed out'
        handle = sent.result()
        assert handle.accepted, 'FollowPath goal rejected'
        result = handle.get_result_async()
        assert spin_until(lambda: state['dwb_commands'] >= 5 and
                          state['output'] is not None and state['output'] > 0.05, 8), \
            'DWB did not produce velocity through the command chain'
        assert not result.done(), 'FollowPath stopped unexpectedly'
        cancelled = handle.cancel_goal_async()
        assert spin_until(cancelled.done, 5) and cancelled.result().return_code == 0
        assert spin_until(result.done, 5) and result.result().status == GoalStatus.STATUS_CANCELED
        assert spin_until(lambda: abs(state['output']) < 1e-6, 5), 'Cancellation did not stop velocity'
        print('PASS: live DWB plugin / critics, FollowPath velocity generation and cancellation', flush=True)

        state['inject_command'] = True
        state['command'] = 0.2
        assert spin_until(lambda: state['output'] is not None and state['output'] > 0.05, 8), 'Clear scan did not pass velocity'
        print('PASS: controller input -> smoother -> collision monitor -> cmd_vel_nav2', flush=True)
        state['range'] = 0.8  # Outside the stop polygon, inside the forward slowdown polygon.
        changed_at = time.monotonic()
        assert spin_until(lambda: state['received'] > changed_at + 0.3 and
                          abs(state['output'] - 0.08) < 0.005, 5), 'Slowdown did not scale velocity to 40%'
        print('PASS: slowdown polygon scales velocity to 40%', flush=True)
        state['range'] = 0.25
        changed_at = time.monotonic()
        assert spin_until(lambda: state['received'] > changed_at + 0.3 and
                          abs(state['output']) < 1e-6, 5), 'Near obstacle did not stop velocity'
        print('PASS: near obstacle produces zero velocity', flush=True)
        state['range'] = 4.0
        assert spin_until(lambda: state['output'] > 0.05, 5), 'Clear scan did not restore velocity'
        print('PASS: clearing obstacle restores velocity', flush=True)

        # Over-limit inputs must be capped along the complete Nav2 command chain.
        state['command'] = 1.0
        assert spin_until(lambda: abs(state['output'] - 0.3) < 0.01, 5), 'Forward cap not applied'
        state['command'] = -1.0
        assert spin_until(lambda: abs(state['output'] + 0.2) < 0.01, 5), 'Reverse cap not applied'
        state['command'] = 0.0
        for angular in (2.0, -2.0):
            state['angular_command'] = angular
            target = math.copysign(1.0, angular)
            assert spin_until(lambda: abs(state['angular_output'] - target) < 0.01, 5), 'Turn cap not applied'
        print('PASS: Nav2 limits forward 0.3 m/s, reverse 0.2 m/s, rotation +/-1.0 rad/s', flush=True)
    finally:
        state['command'] = 0.0
        state['angular_command'] = 0.0
        publish()
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
