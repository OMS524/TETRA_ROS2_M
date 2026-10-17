#!/usr/bin/env python3
"""Check USB alias selection without accessing hardware or /etc."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    'tetra_usb_ports', Path(__file__).resolve().parents[1] / 'scripts/tetra_usb_ports.py')
ports = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ports)


def device(number, serial, path, interface='00'):
    return {'DEVNAME': f'/dev/ttyUSB{number}', 'ID_BUS': 'usb',
            'ID_VENDOR_ID': '067b', 'ID_MODEL_ID': '2303',
            'ID_SERIAL_SHORT': serial, 'ID_USB_INTERFACE_NUM': interface, 'ID_PATH': path}


class UsbAliases(unittest.TestCase):
    def setUp(self):
        self.devices = [device(0, 'MOTOR_001', 'pci-0000:00:14.0-usb-0:2.1:1.0'),
                        device(1, 'POWER_002', 'pci-0000:00:14.0-usb-0:2.2:1.0'),
                        device(2, 'LIDAR_003', 'pci-0000:00:14.0-usb-0:2.3:1.0')]
        self.roles = dict(zip(ports.ROLES, [d['DEVNAME'] for d in self.devices]))

    def test_unique_serials_and_usb_renumbering(self):
        rules = ports.render_rules(self.devices, self.roles, 'serial')
        self.assertEqual(rules.count('SYMLINK+='), 3)
        self.assertNotIn('ttyUSB', rules)
        self.assertIn('MODE="0660"', rules)
        self.assertNotIn('0777', rules)
        for d in self.devices:
            selector = ports.identity(d, 'serial')
            reconnected = dict(d, DEVNAME='/dev/ttyUSB9', ID_PATH='another-hub-port')
            self.assertTrue(ports.matches(reconnected, selector))

    def test_identical_adapters_with_duplicate_serials_are_rejected(self):
        self.devices[1]['ID_SERIAL_SHORT'] = self.devices[0]['ID_SERIAL_SHORT']
        with self.assertRaisesRegex(ports.ConfigurationError, '겹칩니다'):
            ports.render_rules(self.devices, self.roles, 'serial')

    def test_duplicate_serial_on_an_unassigned_adapter_is_rejected(self):
        self.devices.append(dict(self.devices[0], DEVNAME='/dev/ttyUSB8'))
        with self.assertRaises(ports.ConfigurationError):
            ports.render_rules(self.devices, self.roles, 'serial')

    def test_missing_serial_requires_explicit_path_mode(self):
        self.devices[0].pop('ID_SERIAL_SHORT')
        with self.assertRaisesRegex(ports.ConfigurationError, '고유 시리얼'):
            ports.render_rules(self.devices, self.roles, 'serial')
        rules = ports.render_rules(self.devices, self.roles, 'path')
        self.assertEqual(rules.count('ENV{ID_PATH}'), 3)
        selector = ports.identity(self.devices[0], 'path')
        self.assertFalse(ports.matches(dict(self.devices[0], ID_PATH='different-port'), selector))

    def test_duplicate_physical_paths_are_rejected(self):
        self.devices[1]['ID_PATH'] = self.devices[0]['ID_PATH']
        with self.assertRaises(ports.ConfigurationError):
            ports.render_rules(self.devices, self.roles, 'path')

    def test_same_device_cannot_control_two_roles(self):
        self.roles['interface'] = self.roles['motor']
        with self.assertRaisesRegex(ports.ConfigurationError, '동일한 장치'):
            ports.render_rules(self.devices, self.roles, 'serial')

    def test_missing_device_and_missing_role_are_rejected(self):
        with self.assertRaises(ports.ConfigurationError):
            ports.render_rules(self.devices[:2], self.roles, 'serial')
        del self.roles['interface']
        with self.assertRaises(ports.ConfigurationError):
            ports.render_rules(self.devices, self.roles, 'serial')

    def test_usb_interfaces_can_distinguish_same_serial(self):
        self.devices[1]['ID_SERIAL_SHORT'] = self.devices[0]['ID_SERIAL_SHORT']
        self.devices[1]['ID_USB_INTERFACE_NUM'] = '01'
        self.assertIn('ENV{ID_USB_INTERFACE_NUM}=="01"', ports.render_rules(self.devices, self.roles, 'serial'))

    def test_udev_metacharacters_are_rejected(self):
        for serial in ['*', 'a?b', 'abc"', 'a\\b', '%k', '$env{DEVNAME}', 'a\nb']:
            with self.subTest(serial=serial), self.assertRaises(ports.ConfigurationError):
                ports.identity(dict(self.devices[0], ID_SERIAL_SHORT=serial), 'serial')

    def test_legacy_alias_conflict_and_rule_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vendor, local = root / 'vendor', root / 'local'
            vendor.mkdir()
            local.mkdir()
            (vendor / 'tetra_motor.rules').write_text('SUBSYSTEM=="tty", SYMLINK+="tetra/motor"\n')
            self.assertEqual(len(ports.conflicting_rules((vendor, local))), 1)
            (local / 'tetra_motor.rules').symlink_to('/dev/null')
            (local / ports.RULE_NAME).write_text('SUBSYSTEM=="tty", SYMLINK+="tetra/motor"\n')
            self.assertEqual(ports.conflicting_rules((vendor, local)), [])


if __name__ == '__main__':
    unittest.main()
