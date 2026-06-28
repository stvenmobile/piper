from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # Your supervisor node stays active
        Node(
            package='piper_brain',
            executable='piper_brain_node',
            name='piper_brain_node',
            output='screen'
        ),
        # Replace the Flask dashboard with the native Foxglove Bridge
        Node(
            package='foxglove_bridge',
            executable='foxglove_bridge',
            name='foxglove_bridge',
            parameters=[{
                'port': 8765,
                'send_buffer_limit': 10000000 # High ceiling for raw video matrices
            }]
        )
    ])