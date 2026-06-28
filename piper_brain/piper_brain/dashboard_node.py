#!/usr/bin/env python3
import os
import sys
import time
import json
import logging
import subprocess
import threading
from flask import Flask, render_template, Response, request, jsonify

# Pure ROS 2 Resource Index Asset Package Locators
from ament_index_python.packages import get_package_share_directory

# ROS 2 & Vision Core Imports
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Vector3
from std_msgs.msg import String
import cv2
from cv_bridge import CvBridge

# ==========================================================================
# PURE ROS 2 PACKAGE SHARE RESOLUTION
# ==========================================================================
try:
    # Dynamically queries the active ament resource map tracker
    ros_share_root = get_package_share_directory('piper_brain')
    resolved_template_dir = os.path.join(ros_share_root, "templates")
    resolved_assets_dir = os.path.join(ros_share_root, "assets")
except Exception:
    # Local fallback for quick naked python test executions
    current_dir = os.path.dirname(os.path.abspath(__file__))
    resolved_template_dir = os.path.join(current_dir, "templates")
    resolved_assets_dir = os.path.join(current_dir, "assets")

# --- PATH SANITY CHECK DIAGNOSTIC LOOP ---
print("\n" + "="*60)
print(f"[PATH DIAGNOSIS] Target share directory root: {ros_share_root}")
print(f"[PATH DIAGNOSIS] Looking for templates at:    {resolved_template_dir}")
print(f"[PATH DIAGNOSIS] Does templates folder exist? {os.path.exists(resolved_template_dir)}")
if os.path.exists(resolved_template_dir):
    print(f"[PATH DIAGNOSIS] Found files inside folder:  {os.listdir(resolved_template_dir)}")
print("="*60 + "\n")

# ==========================================================================
# FLASK SERVER INITIALIZATION
# ==========================================================================
_app = Flask(
    __name__, 
    template_folder=resolved_template_dir, 
    static_folder=resolved_assets_dir, 
    static_url_path='/assets'
)

# ==========================================================================
# GLOBAL VARIABLE REGISTRATION
# ==========================================================================
_log = logging.getLogger('werkzeug')
_log.setLevel(logging.ERROR)
_latest_frame_jpeg = None

_system_state_snapshot = {
    "state": "SOLO", 
    "active_task": "System running autonomously. Conducting spatial research.",
    "objects": []
}

TASK_LEDGER_PATH = os.path.expanduser("~/piper/jetson_nx_mind/task_requests.md")


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
            time.sleep(0.04)
    return Response(_generate_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")

@_app.route("/api/state", methods=["GET"])
def get_state():
    return jsonify(_system_state_snapshot)

@_app.route("/api/command", methods=["POST"])
def handle_incoming_command():
    data = request.json or {}
    user_raw_text = data.get("command", "").strip()
    if not user_raw_text:
        return jsonify({"response": "Empty matrix bypassed."})
    
    print(f"\n[DASHBOARD INGEST] Received directive: '{user_raw_text}'")
    action_keywords = ["task", "run", "write", "build", "map", "test", "calibrate", "execute", "gather", "process"]
    if any(kw in user_raw_text.lower() for kw in action_keywords):
        try:
            os.makedirs(os.path.dirname(TASK_LEDGER_PATH), exist_ok=True)
            with open(TASK_LEDGER_PATH, "a") as f:
                f.write(f"\n- [ ] **Task via Dashboard Console ({time.strftime('%Y-%m-%d %H:%M')})**: {user_raw_text}\n")
            cmd_args = ["opencode", "run", f"Please process the task requested by Steve: {user_raw_text}"]
            subprocess.Popen(cmd_args, stdout=sys.stdout, stderr=sys.stderr, preexec_fn=os.setpgrp)
            response_msg = "Task appended. Background sub-process successfully invoked!"
        except Exception as e:
            response_msg = f"Failed to delegate task. Error: {str(e)}"
    else:
        response_msg = f"Directive acknowledged: '{user_raw_text}'"
    return jsonify({"response": response_msg})


# --------------------------------------------------------------------------
# ROS 2 PROCESSING NODE TIER
# --------------------------------------------------------------------------
class UM790DashboardNode(Node):
    def __init__(self):
        super().__init__('um790_dashboard_node')
        self.bridge = CvBridge()
        self.frame_count = 0
        self.first_frame_received = False
        
        self.data_lock = threading.Lock()

        # 1. High-speed video stream pass-through subscriber
        self.img_sub = self.create_subscription(
            Image,
            '/piper/camera0/image_raw',
            self._image_callback,
            10)
            
        # 2. Jetson Edge YOLO telemetry subscriber
        self.object_sub = self.create_subscription(
            String,
            '/piper/perception/tracked_objects',
            self._object_callback,
            10)
            
        # 3. Servo Command Publisher
        self.servo_pub = self.create_publisher(
            Vector3,
            '/piper/neck/set_position',
            10)
            
        # --- AUTOMATIC INITIALIZATION SERVO CENTERING ---
        self.init_centering_thread = threading.Thread(target=self._send_initial_homing_pulse, daemon=True)
        self.init_centering_thread.start()
            
        # FIXED: Variable updated to match definition at the top of the script
        self.get_logger().info(f"UM790 Dashboard Engine Active. Target Path: {resolved_template_dir}")

    def _send_initial_homing_pulse(self):
        time.sleep(1.5)
        try:
            home_cmd = Vector3()
            home_cmd.x = 90.0
            home_cmd.y = 70.0
            home_cmd.z = 1.0  
            self.servo_pub.publish(home_cmd)
            self.get_logger().info("[HARDWARE HOME] Absolute center position vector (90.0, 70.0) transmitted.")
        except Exception as e:
            self.get_logger().error(f"Failed to transmit startup homing cycle updates: {e}")

    def _image_callback(self, msg):
        global _latest_frame_jpeg
        if not self.first_frame_received:
            self.get_logger().info(f"[STREAM LIVE] Processing continuous camera frames... Format: '{msg.encoding}'")
            self.first_frame_received = True
            
        self.frame_count += 1
        try:
            raw_mat = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
            if msg.encoding.lower() in ['yuyv', 'yuv422', 'yuy2']:
                cv_image = cv2.cvtColor(raw_mat, cv2.COLOR_YUV2BGR_YUY2)
            else:
                cv_image = cv2.cvtColor(raw_mat, cv2.COLOR_RGB2BGR) if 'rgb' in msg.encoding.lower() else raw_mat
        except Exception:
            return

        if cv_image is None or cv_image.size == 0:
            return

        # Direct, unblocked compression right to the Flask buffer array
        ret, jpeg = cv2.imencode('.jpg', cv_image)
        if ret:
            _latest_frame_jpeg = jpeg.tobytes()

    def _object_callback(self, msg):
        """Processes live object lists from the Jetson's YOLO node asynchronously."""
        worker = threading.Thread(target=self._parse_object_payload, args=(msg.data,), daemon=True)
        worker.start()

    def _parse_object_payload(self, raw_string_data):
        global _system_state_snapshot
        try:
            telemetry_data = json.loads(raw_string_data)
            detected_objects = telemetry_data.get("objects", [])
            current_labels = [obj.get("label", "unknown") for obj in detected_objects]
            unique_labels = list(set(current_labels))
            
            with self.data_lock:
                _system_state_snapshot["objects"] = unique_labels
                previous_state = _system_state_snapshot["state"]
                
                if "person" in unique_labels:
                    new_state = "TEAMING"
                    new_task = "Collaborator tracked via Edge YOLO arrays. Ready for console tasking."
                else:
                    new_state = "SOLO"
                    new_task = "System running autonomously. Conducting spatial research."

                if previous_state != new_state:
                    self.get_logger().info(f"[EDGE YOLO TRANSITION] '{previous_state}' -> '{new_state}'")

                _system_state_snapshot["state"] = new_state
                _system_state_snapshot["active_task"] = new_task
        except Exception:
            pass


def run_ros_loop():
    rclpy.init()
    node = UM790DashboardNode()
    try:
        executor = rclpy.executors.MultiThreadedExecutor()
        executor.add_node(node)
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    ros_thread = threading.Thread(target=run_ros_loop, daemon=True)
    ros_thread.start()
    _app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)