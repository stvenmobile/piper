from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # 1. Physical CSI Camera Driver Node (Modified for Single-Stream/Hardware Flip)
        Node(
            package='piper_brain',
            executable='camera_node',
            name='piper_camera_node',
            output='screen',
            emulate_tty=True
        ),
        
        # 2. AI Vision Processing Layer (Running Headless on Jetson)
        Node(
            package='piper_brain',
            executable='vision_tracking_node',
            name='piper_vision_tracking_node',
            output='screen',
            emulate_tty=True,
            parameters=[{'video': False}] # <--- Disables local cv2.imshow windows
        )
    ])