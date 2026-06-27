#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
from ultralytics import YOLO
import json
import time

class PiperVisionTrackingNode(Node):
    def __init__(self):
        super().__init__('piper_vision_tracking_node')
        self.bridge = CvBridge()
        
        # Initialize YOLOv8 Nano model (Uses GPU/TensorRT internally via PyTorch)
        self.get_logger().info("Loading YOLO network layers onto GPU...")
        self.model = YOLO('yolov8n.pt') 
        
        # Core Subscription to local CSI/USB GStreamer pipeline
        self.subscription = self.create_subscription(
            Image,
            '/piper/camera0/image_raw',
            self._image_callback,
            10)
            
        # Coordinated World-Model Topic output (Unified JSON Stream)
        self.object_pub = self.create_publisher(String, '/piper/perception/tracked_objects', 10)
        self.get_logger().info("Headless State Broker Active. Multi-Object JSON pipeline online.")

    def _image_callback(self, msg):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f"CvBridge conversion failed: {e}")
            return

        # Run model inference. verbose=False keeps our launch logs clean.
        results = self.model(cv_image, verbose=False)
        
        # Extract image dimensions to calculate bounding box midpoints
        img_h, img_w, _ = cv_image.shape
        
        tracked_objects = []
        current_epoch = time.time()

        # Parse frame detections
        for result in results:
            boxes = result.boxes
            for box in boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                
                # Filter out low-confidence noise reflections
                if confidence > 0.40:
                    label = self.model.names[class_id]
                    xyxy = box.xyxy[0].tolist()  # [xmin, ymin, xmax, ymax]
                    
                    # Calculate tracking center offset relative to the camera focal center
                    # Useful for driving physical pan/tilt servo nodes down the line
                    box_center_x = (xyxy[0] + xyxy[2]) / 2.0
                    box_center_y = (xyxy[1] + xyxy[3]) / 2.0
                    delta_x = int(box_center_x - (img_w / 2.0))
                    delta_y = int(box_center_y - (img_h / 2.0))
                    
                    # Construct structural dictionary object entry
                    obj_data = {
                        "class_id": class_id,
                        "label": label,
                        "confidence": round(confidence, 2),
                        "bbox": [int(v) for v in xyxy],
                        "center_delta": [delta_x, delta_y],
                        "identity": "UNKNOWN"  # To be hydrated by workstation biometrics later
                    }
                    tracked_objects.append(obj_data)

        # Assemble the unified payload frame
        payload = {
            "timestamp": current_epoch,
            "frame_width": img_w,
            "frame_height": img_h,
            "object_count": len(tracked_objects),
            "objects": tracked_objects
        }

        # Convert to string and publish over DDS network topology
        msg_out = String()
        msg_out.data = str(json.dumps(payload))
        self.object_pub.publish(msg_out)

        # Print a quick scannable summary line to terminal logs
        if len(tracked_objects) > 0:
            labels_seen = [obj["label"] for obj in tracked_objects]
            self.get_logger().info(f"Perception Frame Matrix: Spotted {labels_seen}")

def main(args=None):
    rclpy.init(args=args)
    node = PiperVisionTrackingNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()