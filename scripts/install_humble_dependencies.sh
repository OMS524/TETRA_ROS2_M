#!/usr/bin/env bash
# Run as your normal user; apt/rosdep will request sudo when needed.
set -eo pipefail
source /etc/os-release
if [[ "$ID" != ubuntu || "$VERSION_ID" != 22.04 ]]; then
  echo "This script targets Ubuntu 22.04 / ROS 2 Humble." >&2
  exit 1
fi
if [[ ! -f /opt/ros/humble/setup.bash ]]; then
  echo "Install ROS 2 Humble first: https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html" >&2
  exit 1
fi
if [[ -n "${ROS_DISTRO:-}" && "$ROS_DISTRO" != humble ]]; then
  echo "Open a fresh terminal without another ROS distribution sourced." >&2
  exit 1
fi
source /opt/ros/humble/setup.bash
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
sudo apt-get update
sudo apt-get install -y python3-rosdep python3-colcon-common-extensions
if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  sudo rosdep init
fi
rosdep update --rosdistro humble
rosdep install --from-paths "$repo_dir" --ignore-src --rosdistro humble \
  -t build -t buildtool -t build_export -t buildtool_export -t exec -y
