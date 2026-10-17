#!/usr/bin/env python3
"""Check the installed DS4 model, mesh bounds and navigation collision areas."""
import ast
import hashlib
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import numpy as np
import yaml
from ament_index_python.packages import get_package_share_directory


def main():
    description = Path(get_package_share_directory('tetra_description'))
    nav = Path(get_package_share_directory('tetra_navigation2'))
    model = ET.fromstring(subprocess.check_output(['xacro', str(description / 'urdf/tetra.xacro')]))
    links = {link.attrib['name']: link for link in model.findall('link')}
    assert {'base_link', 'base_footprint', 'base_Upperlink',
            'l_rear_caster_wheel', 'r_rear_caster_wheel'} <= links.keys()
    parents = {joint.find('child').attrib['link']: joint for joint in model.findall('joint')}

    def translation(link):
        if link == 'base_footprint':
            return np.zeros(3)
        joint = parents[link]
        origin = joint.find('origin')
        # All mesh-bearing joints in the DS4 real-robot model are fixed, unrotated.
        assert joint.attrib['type'] == 'fixed'
        assert np.allclose(np.fromstring(origin.attrib.get('rpy', '0 0 0'), sep=' '), 0)
        return np.fromstring(origin.attrib['xyz'], sep=' ') + translation(joint.find('parent').attrib['link'])

    mesh_dir = description / 'meshes/ds4_m'
    for line in (mesh_dir / 'SHA256SUMS').read_text().splitlines():
        digest, filename = line.split()
        assert hashlib.sha256((mesh_dir / filename).read_bytes()).hexdigest() == digest
    bounds = []
    mesh_count = 0
    for name, link in links.items():
        for visual in link.findall('visual'):
            mesh = visual.find('geometry/mesh')
            if mesh is None:
                continue
            uri = mesh.attrib['filename']
            prefix = 'package://tetra_description/'
            assert uri.startswith(prefix + 'meshes/ds4_m/'), f'Non-DS4 asset loaded: {uri}'
            data = (description / uri[len(prefix):]).read_bytes()
            triangles = np.frombuffer(data[84:], dtype=np.dtype([
                ('normal', '<f4', (3,)), ('vertices', '<f4', (3, 3)), ('attribute', '<u2')]))
            points = triangles['vertices'].reshape(-1, 3) * np.fromstring(mesh.attrib['scale'], sep=' ')
            origin = visual.find('origin')
            if origin is not None:
                assert np.allclose(np.fromstring(origin.attrib.get('rpy', '0 0 0'), sep=' '), 0)
                points += np.fromstring(origin.attrib['xyz'], sep=' ')
            points += translation(name)
            bounds.extend([points.min(axis=0), points.max(axis=0)])
            mesh_count += 1
    assert mesh_count == 8, 'Expected two body meshes, two drive wheels and two caster assemblies'
    bounds = np.array(bounds)
    low, high = bounds.min(axis=0), bounds.max(axis=0)
    config = yaml.safe_load((nav / 'params/navigation.yaml').read_text())
    footprints = [np.array(ast.literal_eval(config[key][key]['ros__parameters']['footprint']))
                  for key in ('local_costmap', 'global_costmap')]
    assert np.allclose(footprints[0], footprints[1]), 'Local/global footprints disagree'
    footprint = footprints[0]
    # Bounding rectangles are used here; every mesh must fit the navigation area.
    assert np.all(low[:2] >= footprint.min(axis=0) - 1e-6), (low, footprint)
    assert np.all(high[:2] <= footprint.max(axis=0) + 1e-6), (high, footprint)
    monitor = config['collision_monitor']['ros__parameters']
    previous = footprint
    for name in monitor['polygons']:
        polygon = np.array(monitor[name]['points']).reshape(-1, 2)
        assert np.all(previous.min(axis=0) > polygon.min(axis=0)), name
        assert np.all(previous.max(axis=0) < polygon.max(axis=0)), name
        previous = polygon
    print(f'PASS: DS4 assets and two rear casters; mesh bounds {low[:2]} .. {high[:2]} m')
    print('PASS: matching costmap footprints contain the model; stop/slowdown areas enclose them')


if __name__ == '__main__':
    main()
