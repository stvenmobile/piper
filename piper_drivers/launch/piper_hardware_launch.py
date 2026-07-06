import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import TimerAction

def generate_launch_description():
    
    # 1. Camera Node Driver Layer
    camera_node = Node(
        package='piper_drivers',
        executable='camera_node',
        name='piper_camera_node',
        output='screen',
        emulate_tty=True
    )
    
    # ⏳ Hold the camera back for 5 seconds to let the servo sweep clear out
    delayed_camera_node = TimerAction(
        period=5.0,
        actions=[camera_node]
    )
    
    # 2. Servo Node Actuator Layer (Starts instantly)
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
    
    # ⏳ Hold the Vision Tracker back for 10 seconds total.
    # This guarantees the camera node has been streaming cleanly for 5 full seconds
    # before the GPU experiences a heavy power draw from loading YOLO layers.
    delayed_vision_tracker = TimerAction(
        period=10.0,
        actions=[vision_tracking_node]
    )


    # Return the coordinated launch schedule
    return LaunchDescription([
        servo_node,
        delayed_camera_node,
        delayed_vision_tracker
    ])