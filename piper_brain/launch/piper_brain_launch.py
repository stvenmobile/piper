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
        # FIX: Change 'dashboard_node.py' to 'dashboard_node' to match your setup.py entry point!
        Node(
            package='piper_brain',
            executable='dashboard_node', 
            name='um790_dashboard_node',
            output='screen'
        )
    ])