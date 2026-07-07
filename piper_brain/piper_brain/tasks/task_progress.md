```markdown
# Piper Project: Autonomous Dynamic World-Modeling

An agentic, visually-aware embodied AI leveraging a distributed, cross-platform ROS 2 network, edge vision acceleration (Jetson Orin NX), local heavy inference (UM790 Pro), and OpenCode orchestration to explore and define a dynamic world model based on real-time video streaming data.

## Introduction

Piper is an advanced autonomous system designed to explore and understand its environment through real-time video data. It utilizes a dual-node Jazzy architecture, leveraging ROS 2 for communication between nodes. Piper's capabilities include dynamic state management, edge computing, and high-level cognitive processing, all orchestrated by OpenCode.

## System Requirements

To run Piper, you will need the following dependencies:
- ROS 2 (specifically rclpy)
- Eclipse CycloneDDS
- NVIDIA Jetson Orin NX for hardware acceleration
- UM790 Pro workstation for cognitive processing
- Python 3.8 or later
- SQLite for session persistence

## Installation Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-repo/piper_ws.git
   ```

2. **Navigate to the workspace directory:**
   ```bash
   cd piper_ws
   ```

3. **Build the workspace:**
   ```bash
   colcon build --packages-select piper_brain piper_sensor piper_control
   ```

4. **Source the setup file:**
   ```bash
   source install/setup.bash
   ```

## Configuration

Piper can be configured through parameters and launch files located in the `config` directory. Common configurations include:
- Setting the camera resolution
- Adjusting inference thresholds
- Configuring logging levels

Example launch file (`launch/piper.launch.py`):
```python
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='piper_brain',
            executable='piper_brain_node',
            name='piper_brain',
            parameters=[{'camera_resolution': '1080p'}]
        ),
        Node(
            package='piper_sensor',
            executable='sensor_node',
            name='sensor_node'
        )
    ])
```

## Usage Examples

### Launching Nodes
To launch the Piper brain and sensor nodes, use:
```bash
ros2 launch piper_brain piper.launch.py
```

### Sending/Receiving Messages
To send a message to the Piper brain node using rclpy, you can create a Python script like `send_message.py`:
```python
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class MessageSender(Node):
    def __init__(self):
        super().__init__('message_sender')
        self.publisher_ = self.create_publisher(String, 'brain_command', 10)
        timer_period = 0.5  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)

    def timer_callback(self):
        msg = String()
        msg.data = 'Hello Piper!'
        self.publisher_.publish(msg)
        self.get_logger().info('Publishing: "%s"' % msg.data)

def main(args=None):
    rclpy.init(args=args)
    message_sender = MessageSender()

    rclpy.spin(message_sender)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    message_sender.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

### Running a Node
To run the `send_message.py` script, use:
```bash
python3 send_message.py
```

## Troubleshooting

- **ROS 2 Environment Not Found:** Ensure that you have sourced the setup file (`source install/setup.bash`) before running any ROS 2 commands.
- **Node Not Launching:** Check the terminal output for error messages and ensure all dependencies are installed correctly.
- **Message Not Received:** Verify that the publisher and subscriber nodes are running and subscribed to the correct topics.

For more information, refer to the [ROS 2 documentation](https://docs.ros.org/en/foxy/index.html).

## File Structure

The Piper ROS 2 workspace is organized as follows:
```
piper_ws/
├── src/
│   ├── piper_brain/
│   │   ├── CMakeLists.txt
│   │   ├── package.xml
│   │   └── src/
│   │       └── piper_brain_node.py
│   ├── piper_sensor/
│   │   ├── CMakeLists.txt
│   │   ├── package.xml
│   │   └── src/
│   │       └── sensor_node.py
│   └── piper_control/
│       ├── CMakeLists.txt
│       ├── package.xml
│       └── src/
│           └── control_node.py
├── config/
│   └── piper_brain_params.yaml
└── launch/
    └── piper.launch.py
```

## Conclusion

Piper is a powerful and flexible system designed to explore and understand its environment through real-time video data. By following the installation instructions, configuring parameters, and using provided examples, you can effectively leverage Piper's capabilities for your autonomous applications.

For further details and support, please visit our [GitHub repository](https://github.com/your-repo/piper_ws).
```