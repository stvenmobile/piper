#!/bin/bash
source /opt/ros/humble/setup.bash
source /home/steve/piper_ws/install/setup.bash

# 🐍 Activate the local virtual environment for proper dependency isolation
if [ -f "/home/steve/piper_ws/.venv/bin/activate" ]; then
    source /home/steve/piper_ws/.venv/bin/activate
fi

ros2 launch piper_drivers piper_hardware_launch.py
