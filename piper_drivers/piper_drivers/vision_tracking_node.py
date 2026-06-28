#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
from ultralytics import YOLO
import json
import sys
import argparse

class PiperVisionTrackingNode(Node):
    def __init__(self, verbose=False):
        super().__init__('piper_vision_tracking_node')
        self.bridge = CvBridge()
        self.verbose = verbose
        
        self.get_logger().info("Loading YOLO network layers onto GPU...")
        self.model = YOLO('yolov8n.pt') 
        
        self.subscription = self.create_subscription(
            Image,
            '/piper/camera0/image_raw',
            self._image_callback,
            10)
            
        # Standard ROS String topic - 100% immune to type-hash collisions
        self.json_pub = self.create_publisher(
            String, 
            '/piper/perception/tracked_objects_json', 
            10
        )
        self.get_logger().info("Headless State Broker Active. Universal JSON tracking stream online.")

    def _image_callback(self, msg):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f"CvBridge conversion failed: {e}")
            return

        results = self.model(cv_image, verbose=False)
        
        detection_list = []
        labels_seen = []

        for result in results:
            boxes = result.boxes
            for box in boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                
                if confidence > 0.40:
                    label = self.model.names[class_id]
                    xyxy = box.xyxy[0].tolist()
                    
                    labels_seen.append(label)

                    # Pack raw primitive dictionary coordinates
                    detection_list.append({
                        "label": f"{label} ({round(confidence * 100)}%)",
                        "xmin": float(xyxy[0]),
                        "ymin": float(xyxy[1]),
                        "xmax": float(xyxy[2]),
                        "ymax": float(xyxy[3])
                    })

        # Assemble and broadcast a completely universal JSON payload
        out_msg = String()
        out_msg.data = json.dumps({"objects": detection_list})
        self.json_pub.publish(out_msg)

        if self.verbose and len(labels_seen) > 0:
            self.get_logger().info(f"Perception Frame Matrix: Spotted {labels_seen}")


def main(args=None):
    parser = argparse.ArgumentParser(description="Piper Vision Tracking Runtime Engine")
    parser.add_argument('-V', '--verbose', action='store_true', help='Enable console logs')
    
    ros_args = rclpy.utilities.remove_ros_args(args=sys.argv)
    parsed_args, _ = parser.parse_known_args(ros_args[1:])

    rclpy.init(args=args)
    node = PiperVisionTrackingNode(verbose=parsed_args.verbose)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()