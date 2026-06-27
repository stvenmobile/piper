from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # 1. Hardware CSI Camera Driver Node (Single Feed, Flipped)
        Node(
            package='piper_drivers',
            executable='camera_node',
            name='piper_camera_node',
            output='screen',
            emulate_tty=True
        ),
        
        # 2. Hardware Actuation Node (Servos/Kinematics)
        Node(
            package='piper_drivers',
            executable='servo_node',
            name='piper_servo_node',
            output='screen',
            emulate_tty=True
        ),

        # 3. Headless State Broker Helper Node
        Node(
            package='piper_drivers',
            executable='vision_tracking_node',
            name='piper_vision_tracking_node',
            output='screen',
            emulate_tty=True
        )
    ])
