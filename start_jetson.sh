#!/bin/bash
source /opt/ros/humble/setup.bash
source /home/steve/piper_ws/install/setup.bash

# 🐍 Activate the local virtual environment for proper dependency isolation
if [ -f "/home/steve/piper_ws/.venv/bin/activate" ]; then
    source /home/steve/piper_ws/.venv/bin/activate
fi

# 🔇 Muzzle RMW/rcutils type-hash state-overwrite noise
export RCUTILS_CONSOLE_OUTPUT_FORMAT="[{severity}] [{name}]: {message}"
export RCUTILS_LOGGING_SEVERITY_THRESHOLD=INFO

# 🔇 Suppress Jetson.GPIO carrier warnings and PyTorch driver complaints
export PYTHONWARNINGS="ignore::UserWarning"

ros2 launch piper_drivers piper_hardware_launch.py 

