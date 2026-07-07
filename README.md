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