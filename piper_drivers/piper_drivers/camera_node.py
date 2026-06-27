#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import cv2
import threading
import time
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

class CameraStream:
    def __init__(self, src=0):
        self.src = src
        # Single camera pipeline optimized with your hardware vertical flip parameters
        gst_pipeline = (
            f"nvarguscamerasrc sensor-id={self.src} ! "
            "video/x-raw(memory:NVMM), width=1920, height=1080, format=NV12, framerate=30/1 ! "
            "nvvidconv flip-method=2 ! "
            "video/x-raw, width=1280, height=720, format=BGRx ! "
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
            time.sleep(0.033)  # Balanced loop cadence for 30fps

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
        self.get_logger().info("Initializing Piper Single Camera Node...")

        # Mapped exclusively to Camera 0 raw output channel
        self.pub_cam0 = self.create_publisher(Image, '/piper/camera0/image_raw', 10)
        self.bridge = CvBridge()

        self.get_logger().info("Starting Camera 0 setup...")
        self.cam0 = CameraStream(0)
        time.sleep(2.0)
        self.cam0.start()

        # Broadcast timer: 30 FPS framing loop
        self.timer = self.create_timer(0.033, self._publish_frames)
        self.get_logger().info("Single Camera Node actively broadcasting at 30 FPS.")

    def _publish_frames(self):
        success0, frame0 = self.cam0.read()
        if success0 and frame0 is not None:
            msg0 = self.bridge.cv2_to_imgmsg(frame0, encoding="bgr8")
            msg0.header.stamp = self.get_clock().now().to_msg()
            msg0.header.frame_id = "camera0_link"
            self.pub_cam0.publish(msg0)

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
        rclpy.shutdown()

if __name__ == '__main__':
    main()