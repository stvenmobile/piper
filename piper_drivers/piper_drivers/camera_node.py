#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import cv2
import threading
import time
import os
from sensor_msgs.msg import Image, CompressedImage
from cv_bridge import CvBridge


class CameraStream:
    def __init__(self, src=0):  # Can be 0 or 1 dynamically
        self.src = src
        self.grabbed = False
        self.frame = None
        self.started = False
        self.read_lock = threading.Lock()

        print(f"INFO: Checking Arducam UVC Hardware via /dev/video{self.src}...")
        
        # Inject custom hardware baseline parameters before opening the capture handle
        os.system(f"v4l2-ctl --device=/dev/video{self.src} --set-ctrl=auto_exposure=3 > /dev/null 2>&1")
        os.system(f"v4l2-ctl --device=/dev/video{self.src} --set-ctrl=brightness=20 > /dev/null 2>&1")
        os.system(f"v4l2-ctl --device=/dev/video{self.src} --set-ctrl=contrast=20 > /dev/null 2>&1")
        os.system(f"v4l2-ctl --device=/dev/video{self.src} --set-ctrl=hue=40 > /dev/null 2>&1")
        os.system(f"v4l2-ctl --device=/dev/video{self.src} --set-ctrl=gamma=150 > /dev/null 2>&1")
        os.system(f"v4l2-ctl --device=/dev/video{self.src} --set-ctrl=gain=40 > /dev/null 2>&1")
        os.system(f"v4l2-ctl --device=/dev/video{self.src} --set-ctrl=power_line_frequency=2 > /dev/null 2>&1")
        os.system(f"v4l2-ctl --device=/dev/video{self.src} --set-ctrl=white_balance_automatic=1 > /dev/null 2>&1")
        os.system(f"v4l2-ctl --device=/dev/video{self.src} --set-ctrl=focus_absolute=208 > /dev/null 2>&1")

        time.sleep(0.5) # Allows the V4L2 hardware registers to settle safely
        
        self.stream = cv2.VideoCapture(self.src, cv2.CAP_V4L2)
        
        # Lock camera pipeline properties to the low-latency stream matrix
        self.stream.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'YUYV'))
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.stream.set(cv2.CAP_PROP_FPS, 30)

        if not self.stream.isOpened():
            return

        # Grab initial frame array validation signature
        self.grabbed, self.frame = self.stream.read()

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
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join()
        if self.stream.isOpened():
            self.stream.release()


class PiperCameraNode(Node):
    def __init__(self):
        super().__init__('piper_camera_node')
        self.get_logger().info("Initializing Piper Resilient Camera Node Layer...")

        self.pub_cam0 = self.create_publisher(Image, '/piper/camera0/image_raw', 10)
        self.compressed_image_pub = self.create_publisher(
            CompressedImage, 
            '/piper/camera0/image_raw/compressed', 
            10
        )

        self.bridge = CvBridge()
        self.cam0 = None

        # --- DYNAMIC AUTO-DETECTION PORT LOOP ---
        candidate_indexes = [0, 1]
        for idx in candidate_indexes:
            self.get_logger().info(f"Probing hardware bus: /dev/video{idx}...")
            attempt = CameraStream(idx)
            
            if attempt.stream.isOpened() and attempt.grabbed:
                self.cam0 = attempt
                self.get_logger().info(f"SUCCESS: Arducam locked and verified on /dev/video{idx}!")
                break
            else:
                self.get_logger().warn(f"Port /dev/video{idx} offline or non-responsive. Advancing probe matrix...")
                attempt.stop() # Clean up stale open resource handle immediately

        # Final Verification Guard
        if self.cam0 is None:
            self.get_logger().error("CRITICAL ERROR: No responsive video devices found across target profiles (/dev/video0, /dev/video1)!")
            raise RuntimeError("Hardware Bus Error: Camera completely missing or unbound.")

        time.sleep(1.0)
        self.cam0.start()

        # Broadcast timer: 30 FPS framing loop
        self.timer = self.create_timer(0.033, self._publish_frames)
        self.get_logger().info("Resilient Camera Node active and streaming at 30 FPS.")

    def _publish_frames(self):
        if self.cam0 is None:
            return
            
        success0, frame0 = self.cam0.read()
        if success0 and frame0 is not None:
            current_time = self.get_clock().now().to_msg()
            
            # 1. Handle Raw Data Stream
            try:
                msg0 = self.bridge.cv2_to_imgmsg(frame0, encoding="bgr8")
                msg0.header.stamp = current_time
                msg0.header.frame_id = "camera0_link"
                self.pub_cam0.publish(msg0)
            except Exception as e:
                self.get_logger().warn(f"Failed to serialize frame data matrix to ROS 2 Image msg: {e}")

            # 2. Handle Highly-Compressed JPEG Stream
            try:
                success, encoded_image = cv2.imencode('.jpg', frame0, [cv2.IMWRITE_JPEG_QUALITY, 90])
                if success:
                    comp_msg = CompressedImage()
                    comp_msg.header.stamp = current_time
                    comp_msg.header.frame_id = "camera0_link"
                    comp_msg.format = "jpeg"
                    comp_msg.data = encoded_image.tobytes()
                    self.compressed_image_pub.publish(comp_msg)
            except Exception as e:
                self.get_logger().warn(f"Failed to compress frame data matrix to ROS 2 CompressedImage msg: {e}")

    def destroy_node(self):
        self.get_logger().info("Stopping physical camera stream...")
        if self.cam0:
            self.cam0.stop()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    try:
        node = PiperCameraNode()
        rclpy.spin(node)
    except RuntimeError as e:
        print(f"Termination: {e}")
    except KeyboardInterrupt:
        pass
    finally:
        # Check if node was successfully created before invoking destruction logic
        if 'node' in locals():
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()