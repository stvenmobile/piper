#!/usr/bin/env python3
import os
import sys
import time
import logging
import subprocess
import threading
from flask import Flask, render_template, Response, request, jsonify

# ROS 2 & Vision Imports
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import cv2
from cv_bridge import CvBridge
import face_recognition

# Flask Setup
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_log = logging.getLogger('werkzeug')
_log.setLevel(logging.ERROR)
_app = Flask(__name__, template_folder=os.path.join(CURRENT_DIR, "templates"))

# Global Frames & System State Cache
_latest_frame_jpeg = None
_system_state_snapshot = {"state": "ALONE", "active_task": "Awaiting Stream..."}
TASK_LEDGER_PATH = os.path.expanduser("~/piper/jetson_nx_mind/task_requests.md")

# Ensure asset directories exist for local biometric matching
FACES_DIR = os.path.join(CURRENT_DIR, 'assets', 'faces')

# --------------------------------------------------------------------------
# FLASK WEB ROUTING TIER
# --------------------------------------------------------------------------
@_app.route("/")
def index():
    return render_template("index.html")

@_app.route("/video_feed")
def video_feed():
    def _generate_stream():
        global _latest_frame_jpeg
        while True:
            if _latest_frame_jpeg is not None:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + _latest_frame_jpeg + b"\r\n")
            time.sleep(0.04)  # ~25 FPS delivery
    return Response(_generate_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")

@_app.route("/api/state", methods=["GET"])
def get_state():
    return jsonify(_system_state_snapshot)

@_app.route("/api/command", methods=["POST"])
def handle_incoming_command():
    data = request.json or {}
    user_raw_text = data.get("command", "").strip()
    
    if not user_raw_text:
        return jsonify({"response": "Empty directive matrix bypassed by parser core."})
    
    print(f"\n[DASHBOARD INGEST] Received web console directive: '{user_raw_text}'")
    
    action_keywords = ["task", "run", "write", "build", "map", "test", "calibrate", "execute", "gather", "process"]
    is_task_declaration = any(kw in user_raw_text.lower() for kw in action_keywords)
    
    if is_task_declaration:
        try:
            os.makedirs(os.path.dirname(TASK_LEDGER_PATH), exist_ok=True)
            with open(TASK_LEDGER_PATH, "a") as f:
                f.write(f"\n- [ ] **Task via Dashboard Console ({time.strftime('%Y-%m-%d %H:%M')})**: {user_raw_text}\n")
            
            print("[SYSTEM LOG] Launching autonomous OpenCode sub-process shell...")
            cmd_args = ["opencode", "run", f"Please process the task requested by Steve: {user_raw_text}"]
            
            subprocess.Popen(cmd_args, stdout=sys.stdout, stderr=sys.stderr, preexec_fn=os.setpgrp)
            response_msg = "Task parsed and appended. OpenCode background sub-process successfully invoked!"
        except Exception as e:
            response_msg = f"Failed to delegate background task execution. Error: {str(e)}"
    else:
        response_msg = f"Directive acknowledged: '{user_raw_text}'"

    return jsonify({"response": response_msg})


# --------------------------------------------------------------------------
# ROS 2 PROCESSING NODE TIER (With Local Workstation Face Recognition)
# --------------------------------------------------------------------------
class UM790DashboardNode(Node):
    def __init__(self):
        super().__init__('um790_dashboard_node')
        self.bridge = CvBridge()
        
        # Biometric reference caches
        self.known_face_encodings = []
        self.known_face_names = []
        self._load_known_collaborators()
        
        self.frame_count = 0
        self.process_every_n_frames = 5  # Offload heavy facial loops
        self.cached_face_locations = []
        self.cached_face_names = []

        # Subscribe to cross-machine video stream
        self.subscription = self.create_subscription(
            Image,
            '/piper/camera0/image_raw',
            self._image_callback,
            10)
        self.get_logger().info("UM790 Dashboard Backend active, processing streams over CycloneDDS.")

    def _load_known_collaborators(self):
        """Dynamically loads profile images saved locally on the workstation."""
        if not os.path.exists(FACES_DIR):
            return
        for filename in os.listdir(FACES_DIR):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                path = os.path.join(FACES_DIR, filename)
                name = os.path.splitext(filename)[0].capitalize()
                try:
                    img = face_recognition.load_image_file(path)
                    encodings = face_recognition.face_encodings(img)
                    if encodings:
                        self.known_face_encodings.append(encodings[0])
                        self.known_face_names.append(name)
                except Exception as e:
                    self.get_logger().error(f"Error loading face profile {filename}: {e}")

    def _image_callback(self, msg):
        global _latest_frame_jpeg, _system_state_snapshot
        self.frame_count += 1
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception:
            return

        # Heavy AI Facial Inference (Executed cleanly on your UM790 Pro CPU cores)
        if self.frame_count % self.process_every_n_frames == 0:
            small_frame = cv2.resize(cv_image, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
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
            
            # Update global state definitions exported to the web UI
            if steve_found:
                _system_state_snapshot["state"] = "ENGAGED"
                _system_state_snapshot["active_task"] = "Collaborator Verified. Monitoring OpenCode Queue."
            else:
                _system_state_snapshot["state"] = "ALONE"
                _system_state_snapshot["active_task"] = "Conducting Spatial Research: Mapping Matrix Deltas"

        # Overlay face tracking boxes onto visual stream frame
        for (top, right, bottom, left), name in zip(self.cached_face_locations, self.cached_face_names):
            top *= 4; right *= 4; bottom *= 4; left *= 4
            cv2.rectangle(cv_image, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(cv_image, name, (left + 6, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Compress to JPEG for high performance Flask streaming browser injection
        ret, jpeg = cv2.imencode('.jpg', cv_image)
        if ret:
            _latest_frame_jpeg = jpeg.tobytes()


def run_ros_loop():
    rclpy.init()
    node = UM790DashboardNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    # Spin up ROS2 stream subscriber in its own independent background thread
    ros_thread = threading.Thread(target=run_ros_loop, daemon=True)
    ros_thread.start()
    
    # Run Flask infrastructure server directly on local loopback port
    _app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
