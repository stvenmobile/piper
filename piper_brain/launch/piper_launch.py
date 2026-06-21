import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    # Updated launch argument parameter mapping
    video_arg = DeclareLaunchArgument(
        'video',
        default_value='true',
        description='Toggles active camera video streaming capture layers (true/false)'
    )

    camera_node = Node(
        package='piper_brain',
        executable='camera_node',
        name='piper_camera_node',
        output='screen'
    )

    servo_node = Node(
        package='piper_brain',
        executable='servo_node',
        name='piper_servo_node',
        output='screen'
    )

    vision_node = Node(
        package='piper_brain',
        executable='vision_tracking_node',
        name='piper_vision_tracking_node',
        output='screen',
        parameters=[{'video': LaunchConfiguration('video')}]
    )

    return LaunchDescription([
        video_arg,
        camera_node,
        servo_node,
        vision_node
    ])