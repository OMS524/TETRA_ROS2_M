#!/usr/bin/env python3
"""Exercise the built DS4-M driver using a new PTY, never a physical device.

Checks ASCII commands, mm / 0.1-degree odometry, body-frame twist, yaw wrap,
emergency stop and fault shutdown. Uses an unoccupied local DDS domain 195.
"""
import math
import os
from pathlib import Path
import select
import signal
import subprocess
import tempfile
import threading
import time


def checksum(data):
    result = 0
    for byte in data:
        result ^= byte
    return result


class Controller:
    def __init__(self):
        self.master, self.slave = os.openpty()
        self.port = os.ttyname(self.slave)
        assert self.port.startswith('/dev/pts/')
        self.commands = []
        self.errors = []
        self.pose = [1000, 2000, 900]
        self.step = [0, 0, 0]
        self.emergency = False
        self.fault = False
        self.stop = threading.Event()
        self.worker = threading.Thread(target=self.run, daemon=True)
        self.worker.start()

    def reply(self, body):
        payload = body + b'\x03'
        os.write(self.master, b'\x02' + payload + bytes([checksum(payload)]))

    def run(self):
        buffer = b''
        try:
            while not self.stop.is_set():
                if not select.select([self.master], [], [], 0.1)[0]:
                    continue
                buffer += os.read(self.master, 1024)
                while b'\x03' in buffer:
                    end = buffer.index(b'\x03')
                    if len(buffer) < end + 2:
                        break
                    frame, buffer = buffer[:end + 2], buffer[end + 2:]
                    assert frame[0] == 2, f'Non-ASCII frame: {frame!r}'
                    assert checksum(frame[1:-1]) == frame[-1], 'Bad command checksum'
                    command = frame[1:-2].decode('ascii')
                    self.commands.append(command)
                    if command == 'AC1':
                        self.pose = [value + step for value, step in zip(self.pose, self.step)]
                        self.pose[2] = (self.pose[2] + 1800) % 3600 - 1800
                        self.reply(('0' + ''.join(f'{value:010d}' for value in self.pose)).encode())
                    elif command == 'AA':
                        error = '2' if self.fault else ('1' if self.emergency else '0')
                        self.reply(f'00{error}0{error}00{int(self.emergency)}'.encode())
                    else:
                        assert command.startswith(('BE', 'DB', 'CG', 'XB', 'XD', 'CZ', 'CX')), command
                        self.reply(b'0')
        except Exception as exc:
            self.errors.append(repr(exc))

    def close(self):
        self.stop.set()
        self.worker.join(timeout=2)
        os.close(self.master)
        os.close(self.slave)


def main():
    os.environ['ROS_DOMAIN_ID'] = '195'
    os.environ['ROS_LOCALHOST_ONLY'] = '1'
    if os.environ.get('ROS_DISTRO') != 'humble':
        raise RuntimeError('Source ROS 2 Humble and the built workspace first.')
    from ament_index_python.packages import get_package_prefix
    import rclpy
    from geometry_msgs.msg import Twist
    from nav_msgs.msg import Odometry
    from rclpy.qos import qos_profile_sensor_data

    work = Path(tempfile.mkdtemp(prefix='tetra-ds4-driver-'))
    os.environ['ROS_LOG_DIR'] = str(work / 'ros_logs')
    rclpy.init()
    node = rclpy.create_node('test_ds4_driver')
    rclpy.spin_once(node, timeout_sec=1)
    others = [name for name, _ in node.get_node_names_and_namespaces() if name != node.get_name()]
    if others:
        node.destroy_node()
        rclpy.shutdown()
        raise RuntimeError(f'DDS domain 195 already occupied: {others}')
    received = []
    subscription = node.create_subscription(Odometry, 'odom', received.append, qos_profile_sensor_data)
    publisher = node.create_publisher(Twist, 'cmd_vel_nav2', 10)
    controller = Controller()
    binary = Path(get_package_prefix('tetra')) / 'lib/tetra/tetra'
    log = (work / 'driver.log').open('w')
    proc = subprocess.Popen([str(binary), '--ros-args', '-p', f'serial_port:={controller.port}',
                             '-p', 'm_bEKF_option:=true'],
                            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)

    def pump(seconds, angular=None, allow_exit=False):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if angular is not None:
                command = Twist()
                command.angular.z = angular
                publisher.publish(command)
            rclpy.spin_once(node, timeout_sec=0.02)
            assert not controller.errors, controller.errors
            if not allow_exit:
                assert proc.poll() is None, 'Driver exited; see log'

    try:
        pump(2)
        assert received, 'No /odom messages'
        odom = received[-1]
        assert abs(odom.pose.pose.position.x - 1.0) < 1e-6, 'mm to metre conversion failed'
        assert abs(odom.pose.pose.position.y - 2.0) < 1e-6
        assert abs(odom.pose.pose.orientation.z - math.sqrt(0.5)) < 1e-6
        assert abs(odom.twist.twist.linear.x) < 1e-6, 'Spurious initial speed'
        pump(0.5, angular=0.5)
        assert 'BE-109;109' in controller.commands, 'Wrong DS4-M wheel separation / ASCII velocity'
        controller.step = [0, 10, 0]  # Moving forward in body frame at yaw +90 degrees.
        pump(0.5, angular=0.0)
        assert all(0.1 < msg.twist.twist.linear.x < 1.0 for msg in received[-5:])
        assert all(abs(msg.twist.twist.linear.y) < 1e-5 for msg in received[-5:])
        controller.step = [0, 0, 0]
        pump(0.1)
        controller.pose = [1000, 2000, 1790]
        pump(0.3)
        first = len(received)
        controller.step = [0, 0, 2]
        pump(0.8)
        samples = received[first:]
        assert any(msg.pose.pose.orientation.z < -0.99 for msg in samples), 'No yaw wrap observed'
        assert all(0.0 < msg.twist.twist.angular.z < 1.0 for msg in samples[2:]), 'Yaw wrap spike'
        print('PASS: DS4 ASCII velocity, mm / angle units, body-frame twist and yaw wrap', flush=True)

        pump(0.2, angular=0.5)
        first = len(controller.commands)
        controller.emergency = True
        pump(0.5, angular=0.5)
        stopped = controller.commands[first:]
        assert 'DB00' in stopped, 'Emergency stop did not disable servo'
        assert all(cmd == 'BE0;0' for cmd in stopped[stopped.index('DB00'):] if cmd.startswith('BE'))
        # Drain commands already in DDS while the stop remains asserted.
        pump(0.3)
        first = len(controller.commands)
        controller.emergency = False
        pump(0.4)  # No new motion command after release.
        released = controller.commands[first:]
        assert 'DB11' in released, 'Servo not restored on healthy status'
        assert all(cmd == 'BE0;0' for cmd in released if cmd.startswith('BE')), 'Retained command resumed'
        controller.fault = True
        pump(0.5, allow_exit=True)
        assert proc.wait(timeout=3) == 1, 'Motor fault should terminate driver'
        assert controller.commands[-2:] == ['BE0;0', 'DB00'], 'Missing stop on shutdown'
        assert controller.commands.count('CG') == 1, 'Fault was repeatedly reset'
        print('PASS: emergency stop, release without stale command, motor-fault shutdown', flush=True)
        missing = subprocess.run([str(binary), '--ros-args', '-p', f'serial_port:={work / "missing-port"}'],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=5)
        assert missing.returncode != 0 and b'Port Open Error' in missing.stdout
        print('PASS: serial-open failure detected', flush=True)
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGINT)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=3)
        controller.close()
        (work / 'commands.log').write_text('\n'.join(controller.commands) + '\n')
        log.close()
        node.destroy_node()
        rclpy.shutdown()
        print(f'Driver log: {work / "driver.log"}', flush=True)


if __name__ == '__main__':
    main()
