from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # 1. Cognitive Priority Queue Core & Action Server
        Node(
            package='piper_brain',
            executable='piper_brain_node',
            name='piper_brain_node',
            output='screen',
            emulate_tty=True
        ),
        
        # 2. Workstation Flask Web Interface & Local Biometrics Node
        Node(
            package='piper_brain',
            executable='dashboard_node',
            name='um790_dashboard_node',
            output='screen',
            emulate_tty=True
        )
    ])
