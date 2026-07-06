from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # 🧠 1. Core Brain Supervisor Node
        Node(
            package='piper_brain',
            executable='piper_brain_node',
            name='piper_brain_node',
            output='screen',
            emulate_tty=True
        ),
        
        # 📊 2. Web Dashboard Node
        Node(
            package='piper_brain',
            executable='dashboard_node', 
            name='um790_dashboard_node',
            output='screen',
            emulate_tty=True
        ),

        # 🎨 3. Autonomous Drawing Node
        Node(
            package='piper_brain',
            executable='autonomous_drawing',
            name='piper_autonomous_drawing',
            output='screen',
            emulate_tty=True
        ),

        # 🛡️ 4. Hermes Mind Task Supervisor Node
        Node(
            package='hermes_mind',
            executable='task_supervisor',
            name='hermes_task_supervisor',
            output='screen',
            emulate_tty=True
        )
    ])