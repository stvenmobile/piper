cmake_minimum_required(VERSION 3.8)
project(piper_drivers)

# Find standard ROS 2 Humble dependencies
find_package(ament_cmake REQUIRED)
find_package(rclpy REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)

# ==========================================================================
# INSTALLATION AND REGISTRATION TIER (Python Nodes & Executables)
# ==========================================================================

# Install peripheral driver nodes and edge vision processing layers
install(PROGRAMS
  piper_drivers/camera_node.py
  piper_drivers/servo_node.py
  piper_drivers/vision_tracking_node.py
  DESTINATION lib/${PROJECT_NAME}
)

# Rename the installed binaries cleanly to match standard 'ros2 run' calls
# This maps the .py source files to clean execution handles
install(PROGRAMS
  piper_drivers/camera_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME camera_node
)

install(PROGRAMS
  piper_drivers/servo_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME servo_node
)

install(PROGRAMS
  piper_drivers/vision_tracking_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME vision_tracking_node
)

# Install the vision tracking node script
install(PROGRAMS
  piper_drivers/vision_tracking_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME vision_tracking_node
)

# ==========================================================================
# ASSET & CONFIGURATION REGISTRATION TIER
# ==========================================================================

# Install the native Python launch files into the share space
install(DIRECTORY
  launch
  DESTINATION share/${PROJECT_NAME}
)

# Export local python modules (e.g., servo_controller.py) to Python's path layout
ament_package()