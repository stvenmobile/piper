from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # 1. AI Vision Processing Layer (Biometric face matching)
        Node(
            package='piper_brain',
            executable='vision_tracking_node',
            name='piper_vision_tracking_node',
            output='screen',
            emulate_tty=True
        ),
        
        # 2. Native PyQt6 Interactive Management Dashboard UI
        Node(
            package='piper_brain',
            executable='dashboard',
            name='piper_dashboard_node',
            output='screen',
            emulate_tty=True
        )
    ])