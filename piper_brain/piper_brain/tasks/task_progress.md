# Piper ROS2 Workspace README

## Introduction

Piper is an advanced robotics platform designed to facilitate the development and deployment of autonomous systems using ROS 2. This document provides a comprehensive overview of setting up, running, and interacting with Piper through its Jazzy architecture.

## Setup Instructions

To set up your Piper ROS2 workspace, follow these steps:

1. **Install ROS 2**: Ensure you have ROS 2 installed on your system. You can download it from the [official ROS 2 website](https://docs.ros.org/en/foxy/Installation.html).

2. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-repo/piper_ws.git
   cd piper_ws
   ```

3. **Install Dependencies**:
   ```bash
   sudo apt-get update
   sudo apt-get install ros-foxy-rclpy ros-foxy-pip
   pip3 install -r requirements.txt
   ```

4. **Build the Workspace**:
   ```bash
   colcon build --packages-select piper_brain piper_sensor
   source install/setup.bash
   ```

## Usage Examples

### Initializing and Running Piper

To initialize and run Piper, execute the following commands:

```bash
ros2 launch piper_ws piper_launch.py
```

This will start both the `piper_brain_node` and `sensor_node`.

### Interacting with Piper through rclpy

Here’s how you can interact with Piper using rclpy:

1. **Import Necessary Modules**:
   ```python
   import rclpy
   from piper_brain.srv import BrainService
   ```

2. **Create a Node and Call the Service**:
   ```python
   def main(args=None):
       rclpy.init(args=args)
       node = rclpy.create_node('piper_client')
       client = node.create_client(BrainService, 'brain_service')

       while not client.wait_for_service(timeout_sec=1.0):
           node.get_logger().info('service not available, waiting again...')

       request = BrainService.Request()
       response = client.call_async(request)
       rclpy.spin_until_future_complete(node, response)

       node.get_logger().info(f'Response: {response.result()}')
       node.destroy_node()
       rclpy.shutdown()

   if __name__ == '__main__':
       main()
   ```

## Technical Details

### Node Class Structures and Message Types

Piper utilizes proper ROS 2 node class structures and correct message type imports. For example, the `piper_brain_node` uses the following structure:

```python
from rclpy.node import Node
from piper_brain.srv import BrainService

class PiperBrainNode(Node):
    def __init__(self):
        super().__init__('piper_brain')
        self.service = self.create_service(BrainService, 'brain_service', self.handle_request)

    def handle_request(self, request, response):
        # Handle the service request
        return response
```

### Libraries and Packages

Piper's development relies on several crucial libraries and packages:
- `rclpy`: ROS 2 Client Library for Python.
- `sensor_msgs`: Standard message types for sensor data.

These dependencies ensure that Piper can effectively interact with various sensors and perform autonomous tasks.

## Conclusion

This README provides a detailed guide to setting up, running, and interacting with Piper using its Jazzy architecture. By following the instructions and examples provided, you should be able to leverage Piper's capabilities for your robotics projects.

For further enhancements and user feedback, please refer to the [Piper Brain Task Progress](src/piper_brain/piper_brain/tasks/task_progress.md) document.