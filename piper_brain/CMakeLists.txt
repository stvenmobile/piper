cmake_minimum_required(VERSION 3.8)
project(piper_brain)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclpy REQUIRED)
find_package(piper_interfaces REQUIRED)

# Automatically packages the python tree cleanly
ament_python_install_package(${PROJECT_NAME})

# Install runtime asset directories (face profiles, web templates)
install(DIRECTORY
  piper_brain/assets
  piper_brain/templates
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

# Install the workstation UI dashboard node script
install(PROGRAMS
  piper_brain/dashboard_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME dashboard_node
)

ament_package()