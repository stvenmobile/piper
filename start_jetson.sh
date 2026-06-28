#!/bin/bash
source /opt/ros/humble/setup.bash
source /home/steve/piper_ws/install/setup.bash
ros2 launch piper_drivers piper_hardware_launch.py
