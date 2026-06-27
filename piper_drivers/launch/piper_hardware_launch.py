import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import RegisterEventHandler
from launch.event_handlers import OnProcessStart

def generate_launch_description():
    
    # 1. Camera Node Driver Layer
    camera_node = Node(
        package='piper_drivers',
        executable='camera_node',
        name='piper_camera_node',
        output='screen',
        emulate_tty=True
    )
    
    # 2. Servo Node Actuator Layer
    servo_node = Node(
        package='piper_drivers',
        executable='servo_node',
        name='piper_servo_node',
        output='screen',
        emulate_tty=True
    )
    
    # 3. Edge Vision Tracking Node Layer
    vision_tracking_node = Node(
        package='piper_drivers',
        executable='vision_tracking_node',
        name='piper_vision_tracking_node',
        output='screen',
        emulate_tty=True
    )
    
    # 4. Sequential Event Handler:
    # This prevents the GStreamer race condition by waiting for the camera_node
    # to register its process ID before initializing the YOLO network layers.
    delay_vision_tracker = RegisterEventHandler(
        event_handler=OnProcessStart(
            target_action=camera_node,
            on_start=[vision_tracking_node]
        )
    )

    # Return the coordinated launch schedule
    return LaunchDescription([
        camera_node,
        servo_node,
        delay_vision_tracker
    ])