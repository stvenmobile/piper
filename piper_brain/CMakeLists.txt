cmake_minimum_required(VERSION 3.8)
project(piper_brain)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclpy REQUIRED)
find_package(piper_interfaces REQUIRED)

# This macro automatically packages your entire python tree cleanly!
ament_python_install_package(${PROJECT_NAME})

# Install Python source files and asset directories
install(DIRECTORY
  piper_brain/assets
  DESTINATION lib/${PROJECT_NAME}/piper_brain
)

# Install launch files explicitly from the package source root
install(DIRECTORY
  "${CMAKE_CURRENT_SOURCE_DIR}/launch"
  DESTINATION share/${PROJECT_NAME}
)

# Install the core brain node script
install(PROGRAMS
  piper_brain/piper_brain_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME piper_brain_node
)

# Install the new camera node script
install(PROGRAMS
  piper_brain/camera_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME camera_node
)

# Install the servo hardware actuator node script
install(PROGRAMS
  piper_brain/servo_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME servo_node
)

# Install the vision tracking node script
install(PROGRAMS
  piper_brain/vision_tracking_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME vision_tracking_node
)

ament_package()