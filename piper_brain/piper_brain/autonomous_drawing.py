#!/usr/bin/env python3
import sys
import os
import time
import random
import numpy as np
import cv2
from datetime import datetime

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from sensor_msgs.msg import CompressedImage
from geometry_msgs.msg import Vector3

# DNA Path Injection for local imports targeting the UM790 brain location
sys.path.append('/home/steve/piper_ws/src/piper_brain/piper_brain')
from sketcher import PiperSketcher

class AutonomousDrawingNode(Node):
    def __init__(self):
        super().__init__('autonomous_drawing')
        
        # Use a Reentrant Callback Group to allow concurrent execution of timers and subscriptions
        self.callback_group = ReentrantCallbackGroup()
        
        # Publishers & Subscribers
        self.sub = self.create_subscription(
            CompressedImage, 
            '/piper/camera0/image_raw/compressed', 
            self.image_callback, 
            10,
            callback_group=self.callback_group
        )
        self.servo_pub = self.create_publisher(Vector3, '/piper/neck/set_position', 10)
        
        # 10-minute loop (600.0 seconds) for scheduled execution
        self.timer = self.create_timer(600.0, self.execute_autonomous_loop, callback_group=self.callback_group)
        
        self.get_logger().info('🎨 Autonomous Drawing Node Initialized on UM790. 10-Minute loop active.')
        
        # Cache tracks
        self.latest_frame = None
        
        # Explicitly bind the startup timer to an attribute so it can be destroyed
        self._startup_timer = self.create_timer(3.0, self.trigger_initial_pass, callback_group=self.callback_group)

    def image_callback(self, msg):
        # Muzzled: Heartbeat pulse logs removed to prevent terminal spam
        self.latest_frame = msg

    def trigger_initial_pass(self):
        if self._startup_timer:
            self._startup_timer.cancel()
            self._startup_timer = None
        self.get_logger().info('🏁 Initial startup single-shot pass triggered.')
        self.execute_autonomous_loop()

    def maintain_storage_ceiling(self):
        """ Scans the sketchbook folder and maintains a maximum threshold of the 50 latest files """
        sketchbox_dir = '/home/steve/piper_ws/src/piper_brain/piper_brain/assets/sketchbook'
        if not os.path.exists(sketchbox_dir):
            self.get_logger().warn(f'⚠️ Directory missing: {sketchbox_dir}')
            return
            
        try:
            # Gather all sketches
            files = [os.path.join(sketchbox_dir, f) for f in os.listdir(sketchbox_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            
            # If overhead exceeds ceiling, sort by modification epoch and prune old files
            if len(files) > 50:
                files.sort(key=os.path.getmtime)  # Oldest first
                prune_count = len(files) - 50
                
                self.get_logger().info(f'🧹 Storage maintenance required. Pruning {prune_count} older assets...')
                for i in range(prune_count):
                    os.remove(files[i])
                self.get_logger().info('✅ Asset pruning complete. Under 50 image limit.')
        except Exception as e:
            self.get_logger().error(f'⚠️ Failed to execute asset ceiling cleanup loop: {str(e)}')

    def execute_autonomous_loop(self):
        self.get_logger().info('🚀 [LOOP TRACE] Beginning scheduled sketch execution pass...')
        
        # 1. Vector3 look-around commands (Pan: 45 to 135, Tilt: 50 to 90)
        pan = random.uniform(45.0, 135.0)
        tilt = random.uniform(50.0, 90.0)
        
        cmd = Vector3()
        cmd.x = pan
        cmd.y = tilt
        cmd.z = 1.0
        self.servo_pub.publish(cmd)
        self.get_logger().info(f'🎥 Neck adjusted to Pan: {pan:.2f}, Tilt: {tilt:.2f}. Settling motor for 2 seconds...')
        
        # Settling delay for motion blur minimization
        time.sleep(2.0)
        
        if self.latest_frame is None:
            self.get_logger().error('⚠️ [CRITICAL] No image buffer received yet from camera topic! Skipping loop execution pass.')
            return
            
        try:
            img_array = np.frombuffer(self.latest_frame.data, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if frame is None:
                self.get_logger().error('❌ [LOOP TRACE] OpenCV failed to decode the buffer into a standard matrix format.')
                return
                
            # Create a clean, human-readable file signature template
            human_timestamp = datetime.now().strftime("%Y%m%d_%H_%M_%S")
            filename_template = f"sketch_{human_timestamp}.jpg"
            
            sketcher = PiperSketcher()
            self.get_logger().info('[LOOP TRACE] Passing frame matrix to PiperSketcher logic core...')
            
            # Pass our custom human-readable file layout signature directly to the sketch core
            filename = sketcher.sketch_from_frame(frame, description=filename_template)
            self.get_logger().info(f'🎨 Sketch rendering complete: {filename}')
            
            # Run storage cleanup step immediately following a successful save
            self.maintain_storage_ceiling()
            
        except Exception as e:
            self.get_logger().error(f'❌ Skill engine execution failed: {str(e)}')

def main(args=None):
    rclpy.init(args=args)
    node = AutonomousDrawingNode()
    
    # Use a MultiThreadedExecutor to process callbacks across a thread pool
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()