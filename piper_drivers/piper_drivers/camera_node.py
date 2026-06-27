#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import cv2
import threading
import time
import os
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class CameraStream:
    def __init__(self, src=1):  # Mounted securely at /dev/video1
        self.src = src
        self.grabbed = False
        self.frame = None
        self.started = False
        self.read_lock = threading.Lock()

        print(f"INFO: Mounting Arducam UVC Hardware via /dev/video{self.src}...")
        
        # Inject custom hardware baseline parameters before opening the capture handle
        # This prevents streaming thread locks from ignoring our runtime values
        os.system(f"v4l2-ctl --device=/dev/video{self.src} --set-ctrl=auto_exposure=3")
        os.system(f"v4l2-ctl --device=/dev/video{self.src} --set-ctrl=brightness=20")
        os.system(f"v4l2-ctl --device=/dev/video{self.src} --set-ctrl=contrast=20")
        os.system(f"v4l2-ctl --device=/dev/video{self.src} --set-ctrl=hue=40")
        os.system(f"v4l2-ctl --device=/dev/video{self.src} --set-ctrl=gamma=150")
        os.system(f"v4l2-ctl --device=/dev/video{self.src} --set-ctrl=gain=40")
        os.system(f"v4l2-ctl --device=/dev/video{self.src} --set-ctrl=power_line_frequency=2")
        os.system(f"v4l2-ctl --device=/dev/video{self.src} --set-ctrl=white_balance_automatic=1")
        os.system(f"v4l2-ctl --device=/dev/video{self.src} --set-ctrl=focus_absolute=208")

        self.stream = cv2.VideoCapture(self.src, cv2.CAP_V4L2)
        
        # Lock camera pipeline properties to the low-latency stream matrix
        self.stream.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'YUYV'))
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.stream.set(cv2.CAP_PROP_FPS, 30)

        if not self.stream.isOpened():
            print(f"CRITICAL ERROR: System could not open USB camera index {self.src}!")
            return

        # Grab initial frame array validation signature
        self.grabbed, self.frame = self.stream.read()
        if not self.grabbed:
            print(f"WARN: Arducam connected, but failed to grab first frame array context.")

    def start(self):
        if not self.stream.isOpened():
            print(f"ERROR: Cannot start thread. Camera {self.src} stream is closed.")
            return self
        self.started = True
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()
        return self

    def update(self):
        while self.started:
            try:
                grabbed, frame = self.stream.read()
                if not grabbed or frame is None or frame.size == 0:
                    time.sleep(0.005)
                    continue
                
                with self.read_lock:
                    self.grabbed = grabbed
                    self.frame = frame
                    
            except Exception as e:
                print(f"WARN: Dropped corrupt USB frame packet sequence: {e}")
                time.sleep(0.005)
                continue
            
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
        self.get_logger().info("Initializing Piper Resilient Camera Node Layer...")

        self.pub_cam0 = self.create_publisher(Image, '/piper/camera0/image_raw', 10)
        self.bridge = CvBridge()

        self.get_logger().info("Starting Camera 1 setup...")
        self.cam0 = CameraStream(1)
        time.sleep(2.0)
        self.cam0.start()

        # Broadcast timer: 30 FPS framing loop
        self.timer = self.create_timer(0.033, self._publish_frames)
        self.get_logger().info("Single Camera Node actively broadcasting at 30 FPS.")

    def _publish_frames(self):
        success0, frame0 = self.cam0.read()
        if success0 and frame0 is not None:
            try:
                msg0 = self.bridge.cv2_to_imgmsg(frame0, encoding="bgr8")
                msg0.header.stamp = self.get_clock().now().to_msg()
                msg0.header.frame_id = "camera0_link"
                self.pub_cam0.publish(msg0)
            except Exception as e:
                self.get_logger().warn(f"Failed to serialize frame data matrix to ROS 2 Image msg: {e}")

    def destroy_node(self):
        self.get_logger().info("Stopping physical camera stream...")
        self.cam0.stop()
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
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()