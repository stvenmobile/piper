#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String  # For broadcasting high-level state changes
import cv2
from cv_bridge import CvBridge
from ultralytics import YOLO

class PiperVisionTrackingNode(Node):
    def __init__(self):
        super().__init__('piper_vision_tracking_node')
        self.bridge = CvBridge()
        
        # Initialize YOLOv8 Nano model (Automatically downloads on first run)
        # 'yolov8n.pt' is highly optimized for edge devices
        self.get_logger().info("Loading YOLO network layers onto GPU...")
        self.model = YOLO('yolov8n.pt') 
        
        # Class 0 in the COCO dataset is 'person'
        self.TARGET_CLASS_ID = 0 
        
        # Subscription to raw GStreamer edge stream
        self.subscription = self.create_subscription(
            Image,
            '/piper/camera0/image_raw',
            self._image_callback,
            10)
            
        # Publisher to notify the brain loop when world model elements change
        self.state_pub = self.create_publisher(String, '/piper/vision/state', 10)
        self.get_logger().info("Vision Tracking Node fully initialized on Jetson Orin NX.")

    def _image_callback(self, msg):
        try:
            # Convert ROS 2 Image message to OpenCV format
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f"CvBridge conversion failed: {e}")
            return

        # Run inference via YOLO. verbose=False keeps our ROS logs clean.
        results = self.model(cv_image, verbose=False)
        
        person_detected = False
        
        # Parse detections
        for result in results:
            boxes = result.boxes
            for box in boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                
                # Check if the detected object is a person with a reasonable confidence threshold
                if class_id == self.TARGET_CLASS_ID and confidence > 0.5:
                    person_detected = True
                    
                    # Extract bounding box pixel coordinates: [xmin, ymin, xmax, ymax]
                    xyxy = box.xyxy[0].tolist()
                    self.get_logger().info(f"Person tracked in perception matrix! Coordinates: {xyxy}")
                    
                    # TODO: Calculate tracking offset deltas relative to image center
                    # to drive servo alignment loops tomorrow.

        # Broadcast world-model state transitions
        state_msg = String()
        state_msg.data = "ENGAGED" if person_detected else "ALONE"
        self.state_pub.publish(state_msg)

def main(args=None):
    rclpy.init(args=args)
    node = PiperVisionTrackingNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Vision tracking loop intercepted.")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()