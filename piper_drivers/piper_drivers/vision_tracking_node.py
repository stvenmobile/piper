#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import String
import cv2
import json
from cv_bridge import CvBridge
from ultralytics import YOLO

class PiperVisionTrackingNode(Node):
    def __init__(self):
        super().__init__('piper_vision_tracking_node')
        self.bridge = CvBridge()
        
        # Initialize YOLOv8 Nano model (Highly optimized for edge devices)
        self.get_logger().info("Loading YOLO network layers onto GPU...")
        self.model = YOLO('yolov8n.pt') 
        
        # Subscription shifted to CompressedImage channel to protect network bandwidth
        self.subscription = self.create_subscription(
            CompressedImage,
            '/piper/camera0/image_raw/compressed',
            self._image_callback,
            10)
            
        # Unified structured JSON telemetry topic for dashboard and brain tracking
        self.perception_pub = self.create_publisher(String, '/piper/perception/tracked_objects_json', 10)
        self.get_logger().info("Vision Tracking Node active with strict >=60% confidence filter.")

    def _image_callback(self, msg):
        try:
            # Decode compressed JPEG matrix to OpenCV format natively
            cv_image = self.bridge.compressed_imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f"Compressed CvBridge decoding failed: {e}")
            return

        # Run local GPU-accelerated inference
        results = self.model(cv_image, verbose=False)
        
        tracked_objects = []
        
        # Fetch the master names dictionary from the model configuration
        names_dict = self.model.names
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                
                # ENFORCE THRESHOLD: Strict 60% filter limit
                if confidence >= 0.60:
                    xyxy = box.xyxy[0].tolist()  # [xmin, ymin, xmax, ymax]
                    label = names_dict.get(class_id, f"unknown_{class_id}")
                    
                    # Construct individual object coordinate telemetry map
                    obj_data = {
                        "class_id": class_id,
                        "label": label.capitalize(),
                        "confidence": round(confidence, 2),
                        "xmin": int(xyxy[0]),
                        "ymin": int(xyxy[1]),
                        "xmax": int(xyxy[2]),
                        "ymax": int(xyxy[3])
                    }
                    tracked_objects.append(obj_data)

        # Serialize complete frame snapshot array into a single JSON payload
        payload = String()
        payload.data = json.dumps(tracked_objects)
        self.perception_pub.publish(payload)

        # Log active targets to console for edge telemetry checking
        # if tracked_objects:
        #    self.get_logger().info(f"Broadcasting tracking matrix: {[obj['label'] for obj in tracked_objects]}")

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