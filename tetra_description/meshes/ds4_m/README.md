# DS4-M mesh provenance

Copied without geometric changes from AIRO-lab/tetra_pkg, commit
`ecbf75fb82b6b6b5fa3d4fbf30733abb89db588c`, `tetra_description/meshes`.
The same mesh data also appears in AIRO-lab/tetra at commit
`38ac7a2290a349b36e3fe238247f58a626df66c0`.

The upstream manifest identifies `tetraDS4_description`, author Hyulimrobot,
license BSD; that manifest is preserved as `source_manifest.xml`.
`SHA256SUMS` records the original mesh data after filename normalization.

| Upstream filename | Installed filename |
|---|---|
| Platform Body_L.STL | platform_body_lower.stl |
| Platform Body_U.STL | platform_body_upper.stl |
| Wheel Drive Left.STL | wheel_drive_left.stl |
| Wheel Drive Right.STL | wheel_drive_right.stl |
| Caster Yoke.STL | caster_yoke.stl |
| Caster Wheel.STL | caster_wheel.stl |

`urdf/base.urdf.xacro` uses the real-robot DS4 description from `tetra_pkg`.
Its footprint visual was enlarged to match the reference Nav2 rectangle.
The main Xacro invokes the base macro with the required `xacro:` prefix.
Camera frame names stay compatible with this workspace, with DS4 transforms.
LiDAR placement is configurable for the user's A2M12 mount.

The meshes directly in the parent directory are unused upstream DS5-M assets.
The default description loads only meshes in this `ds4_m` directory.
