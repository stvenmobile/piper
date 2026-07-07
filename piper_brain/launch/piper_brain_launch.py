from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # Supervisor node
        Node(
            package='piper_brain',
            executable='piper_brain_node',
            name='piper_brain_node',
            output='screen'
        ),
        # Dashboard gateway node
        Node(
            package='piper_brain',
            executable='dashboard_node', 
            name='um790_dashboard_node',
            output='screen'
        ),
        # Hermes task supervisor node
        Node(
            package='hermes_mind',
            executable='task_supervisor',
            name='hermes_supervisor',
            output='screen'
        ),
        # The Autonomous Drawing Node for quick sketches
        Node(
            package='piper_brain',
            executable='autonomous_drawing', # Assumes 'autonomous_drawing' is set in your piper_brain setup.py
            name='autonomous_drawing',
            output='screen'
        )
    ])