#!/usr/bin/env bash

echo "=================================================="
echo "🚀 INITIATING CLEAN PIPER HARDWARE SUBSTRATE LAUNCH"
echo "=================================================="

# 1. Kill any hanging ROS wrappers or duplicate camera loops
echo "Stopping any duplicate software processes..."
killall -9 camera_node servo_node vision_tracking_node python3 python ros2 2>/dev/null

# 2. Reset the ROS background graph discovery daemon
echo "Flushing background ROS discovery daemons..."
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export RCUTILS_LOGGING_SEVERITY_THRESHOLD=ERROR
ros2 daemon stop 2>/dev/null

# 3. Forcefully reset the locked NVIDIA Argus camera pipeline
echo "Resetting hardware nvargus-daemon..."
sudo systemctl restart nvargus-daemon
sleep 1 # Give the hardware micro-service a moment to reallocate memory bounds

# 4. Initialize the local ROS workspace
echo "Sourcing workspace environment..."
source /opt/ros/humble/setup.bash
cd /home/steve/piper_ws || exit
source install/setup.bash

# 5. Launch the hardware nodes directly
echo "Launching camera and servo nodes cleanly on Domain 42..."
ros2 launch piper_brain piper_launch.py nodes:=camera,servo
