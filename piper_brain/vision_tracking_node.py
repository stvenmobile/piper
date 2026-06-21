#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import cv2
from cv_bridge import CvBridge
import face_recognition
import numpy as np
import os

class PiperVisionTrackingNode(Node):

    def __init__(self):
        super().__init__('piper_vision_tracking_node')
        self.get_logger().info("Initializing Piper Unified Dashboard & Tracking Node...")

        # Declare the 'video' parameter (Default to True)
        self.declare_parameter('video', True)
        self.enable_video = self.get_parameter('video').get_parameter_value().bool_value

        # Initialize ROS2 to OpenCV bridge
        self.bridge = CvBridge()

        # Operational State (Mirroring README configuration definitions)
        self.state = "ALONE" 
        self.active_task = "Conducting Spatial Research: Mapping Matrix Deltas"

        # Biometric Cache
        self.known_face_encodings = []
        self.known_face_names = []
        self._load_known_collaborators()

        self.frame_count = 0
        self.process_every_n_frames = 5 
        self.cached_face_locations = []
        self.cached_face_names = []

        # Only subscribe to the camera feed if video rendering processing is requested
        if self.enable_video:
            self.subscription = self.create_subscription(
                Image,
                '/piper/camera0/image_raw',
                self._image_callback,
                10)
            self.get_logger().info("Video tracking active. Subscribed to camera channel.")
        else:
            # If headless video, use a background timer to keep the text UI responsive
            self.ui_timer = self.create_timer(0.1, self._render_headless_ui_loop)
            self.get_logger().info("Operating in UI-Only Mode (Video Stream Disabled).")

    def _load_known_collaborators(self):
        """Dynamically loads all reference face profiles from assets/faces/."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        faces_dir = os.path.join(current_dir, 'assets', 'faces')
        if not os.path.exists(faces_dir):
            return
        valid_extensions = ('.jpg', '.jpeg', '.png')
        for filename in os.listdir(faces_dir):
            if filename.lower().endswith(valid_extensions):
                image_path = os.path.join(faces_dir, filename)
                name = os.path.splitext(filename)[0].capitalize()
                try:
                    loaded_image = face_recognition.load_image_file(image_path)
                    encodings = face_recognition.face_encodings(loaded_image)
                    if encodings:
                        self.known_face_encodings.append(encodings[0])
                        self.known_face_names.append(name)
                except Exception as e:
                    self.get_logger().error(f"Error loading {filename}: {e}")

    def _draw_dashboard_chrome(self, base_canvas):
        """Draws the text information blocks, status inputs, and command structures."""
        # Create an expanded workspace canvas block to append status text below the main canvas
        h, w, c = base_canvas.shape
        ui_panel = np.zeros((200, w, 3), dtype=np.uint8)
        
        # Draw border lines separating the visual layers
        cv2.line(ui_panel, (0, 0), (w, 0), (0, 255, 0), 2)
        
        # Inject Core State Metadata Text Fields
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(ui_panel, f"COGNITIVE STATE: {self.state}", (20, 40), font, 0.7, (0, 255, 0), 2)
        cv2.putText(ui_panel, f"ACTIVE TASK: {self.active_task}", (20, 80), font, 0.6, (255, 255, 255), 1)
        
        # Input Box Overlay Placeholder
        cv2.rectangle(ui_panel, (20, 120), (w - 20, 170), (50, 50, 50), -1)
        cv2.rectangle(ui_panel, (20, 120), (w - 20, 170), (0, 255, 0), 1)
        cv2.putText(ui_panel, "INSTRUCTION COMMAND INPUT: [Awaiting OpenCode Pipeline Bridging...]", (35, 152), font, 0.5, (150, 150, 150), 1)
        
        # Combine the visual tracking window with the control console panel
        return np.vstack((base_canvas, ui_panel))

    def _image_callback(self, msg):
        self.frame_count += 1
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            return

        small_frame = cv2.resize(cv_image, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        if self.frame_count % self.process_every_n_frames == 0:
            self.cached_face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, self.cached_face_locations)

            self.cached_face_names = []
            steve_found = False

            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.6)
                name = "Unknown"
                if True in matches:
                    name = self.known_face_names[matches.index(True)]
                    if name == "Steve":
                        steve_found = True
                self.cached_face_names.append(name)

            if steve_found:
                if self.state != "ENGAGED":
                    self.state = "ENGAGED"
                    self.active_task = "Collaborator Verified. Monitoring OpenCode Task Request Queue."
            else:
                if self.state != "ALONE":
                    self.state = "ALONE"
                    self.active_task = "Conducting Spatial Research: Mapping Matrix Deltas"

        for (top, right, bottom, left), name in zip(self.cached_face_locations, self.cached_face_names):
            top *= 4; right *= 4; bottom *= 4; left *= 4
            cv2.rectangle(cv_image, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.rectangle(cv_image, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
            cv2.putText(cv_image, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 0, 0), 1)

        # Build and present the combined control dashboard
        complete_dashboard = self._draw_dashboard_chrome(cv_image)
        cv2.imshow("Piper Master Control Console", complete_dashboard)
        cv2.waitKey(1)

    def _render_headless_ui_loop(self):
        """Generates a text-only system terminal matrix if video processing is disabled."""
        # Create a clean slate 640x480 dark panel canvas profile
        canvas = np.zeros((200, 640, 3), dtype=np.uint8)
        complete_dashboard = self._draw_dashboard_chrome(canvas)
        cv2.imshow("Piper Master Control Console", complete_dashboard)
        cv2.waitKey(1)


def main(args=None):
    rclpy.init(args=args)
    node = PiperVisionTrackingNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()