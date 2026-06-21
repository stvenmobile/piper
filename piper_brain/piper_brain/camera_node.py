#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import cv2
import threading
import time
import numpy as np
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

class CameraStream:
    def __init__(self, src=0):
        self.src = src
        # Preserved your exact Orin NX hardware optimized GStreamer pipelines
        gst_pipeline = (
            f"nvarguscamerasrc sensor-id={self.src} ! "
            "video/x-raw(memory:NVMM), width=1280, height=720, format=NV12, framerate=60/1 ! "
            f"nvvidconv flip-method=2 ! "
            "video/x-raw, width=640, height=480, format=BGRx ! "
            "videoconvert ! "
            "video/x-raw, format=BGR ! "
            "appsink drop=true sync=false"
        )

        self.stream = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
        self.grabbed = False
        self.frame = None
        self.started = False
        self.read_lock = threading.Lock()

        if not self.stream.isOpened():
            print(f"ERROR: Camera {self.src} - GStreamer pipeline failed to open.")
        else:
            self.grabbed, self.frame = self.stream.read()
            if not self.grabbed:
                print(f"ERROR: Camera {self.src} opened but failed to grab first frame.")

    def start(self):
        self.started = True
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()
        return self

    def update(self):
        while self.started:
            grabbed, frame = self.stream.read()
            if not grabbed or frame is None:
                time.sleep(0.01)
                continue
            with self.read_lock:
                self.grabbed = grabbed
                self.frame = frame
            time.sleep(0.016)  # ~60fps matching cadence

    def read(self):
        if not self.stream.isOpened() or not self.grabbed or self.frame is None:
            return False, None
        with self.read_lock:
            frame = self.frame.copy()
        return self.grabbed, frame

    def stop(self):
        self.started = False
        if hasattr(self, 'thread'):
            self.thread.join()
        if self.stream.isOpened():
            self.stream.release()


class PiperCameraNode(Node):

    def __init__(self):
        super().__init__('piper_camera_node')
        self.get_logger().info("Initializing Piper Dual Camera Node...")

        # Initialize ROS2 Image Publishers
        self.pub_cam0 = self.create_publisher(Image, '/piper/camera0/image_raw', 10)
        self.pub_cam1 = self.create_publisher(Image, '/piper/camera1/image_raw', 10)
        self.bridge = CvBridge()

        # Staggered initialization preserved to protect nvargus-daemon
        self.get_logger().info("Starting Camera 0 setup...")
        self.cam0 = CameraStream(0)
        time.sleep(5.0)
        self.cam0.start()
        time.sleep(5.0)

        self.get_logger().info("Starting Camera 1 setup...")
        self.cam1 = CameraStream(1)
        time.sleep(5.0)
        self.cam1.start()
        time.sleep(5.0)

        # Broadcast timer: 30 FPS framing loop (0.033s interval)
        self.timer = self.create_timer(0.033, self._publish_frames)
        self.get_logger().info("Dual Camera Node actively broadcasting at 30 FPS.")

    def _publish_frames(self):
        # Process Camera 0
        success0, frame0 = self.cam0.read()
        if success0 and frame0 is not None:
            # Convert OpenCV BGR image matrix straight to standard ROS2 Image message
            msg0 = self.bridge.cv2_to_imgmsg(frame0, encoding="bgr8")
            msg0.header.stamp = self.get_clock().now().to_msg()
            msg0.header.frame_id = "camera0_link"
            self.pub_cam0.publish(msg0)

        # Process Camera 1
        success1, frame1 = self.cam1.read()
        if success1 and frame1 is not None:
            msg1 = self.bridge.cv2_to_imgmsg(frame1, encoding="bgr8")
            msg1.header.stamp = self.get_clock().now().to_msg()
            msg1.header.frame_id = "camera1_link"
            self.pub_cam1.publish(msg1)

    def destroy_node(self):
        self.get_logger().info("Stopping physical camera streams...")
        self.cam0.stop()
        self.cam1.stop()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = PiperCameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()