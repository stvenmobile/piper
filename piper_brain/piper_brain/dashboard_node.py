#!/usr/bin/env python3
import os
import sys
import time
import json
import logging
import sqlite3
import subprocess
import threading
import re
from flask import Flask, render_template, Response, request, jsonify

# Pure ROS 2 Index Package Locators
from ament_index_python.packages import get_package_share_directory
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from geometry_msgs.msg import Vector3
from std_msgs.msg import String

# ==========================================================================
# PATH RESOLUTION CORE
# ==========================================================================
current_script_dir = os.path.dirname(os.path.abspath(__file__))
if "install/" in current_script_dir:
    workspace_root = os.path.abspath(os.path.join(current_script_dir, "../../../../src/piper_brain/piper_brain"))
    resolved_template_dir = os.path.join(workspace_root, "templates")
    resolved_assets_dir = os.path.join(workspace_root, "assets")
else:
    resolved_template_dir = os.path.join(current_script_dir, "templates")
    resolved_assets_dir = os.path.join(current_script_dir, "assets")

# ==========================================================================
# FLASK SERVER CONTEXT
# ==========================================================================
_app = Flask(__name__, template_folder=resolved_template_dir, static_folder=resolved_assets_dir, static_url_path='/assets')
_log = logging.getLogger('werkzeug')
_log.setLevel(logging.ERROR)
_latest_frame_jpeg = None

# Base layout tracking metrics
_system_state_snapshot = {
    "state": "SOLO", 
    "active_task": "System running autonomously. Conducting spatial research.",
    "objects": [],
    "matrix_report": {
        "P1_Top_Left": [],
        "P2_Top_Right": [],
        "P3_Bottom_Right": [],
        "P4_Bottom_Left": []
    }
}

TASK_LEDGER_PATH = os.path.expanduser("~/piper/jetson_nx_mind/task_requests.md")
DB_PATH = os.path.expanduser("~/piper/jetson_nx_mind/piper_memory.db")

_last_known_objects = set()
_pending_state = "SOLO"
_state_transition_time = 0.0
_current_pan = 90.0
_current_tilt = 70.0
_global_node_instance = None

# ==========================================================================
# SQLITE PERSISTENCE INITIALIZATION
# ==========================================================================
def init_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detected_objects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            label TEXT NOT NULL,
            confidence REAL NOT NULL,
            xmin REAL,
            ymin REAL,
            xmax REAL,
            ymax REAL,
            center_x REAL,
            center_y REAL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_objects_timestamp ON detected_objects(timestamp)")
    conn.commit()
    conn.close()

init_database()

def log_detection_to_db(timestamp, label, confidence, bbox=None, centroid=None):
    try:
        xmin, ymin, xmax, ymax = bbox if bbox else (None, None, None, None)
        cx, cy = centroid if centroid else (None, None)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO detected_objects (timestamp, label, confidence, xmin, ymin, xmax, ymax, center_x, center_y)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, label, confidence, xmin, ymin, xmax, ymax, cx, cy))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DATABASE ERROR] Failed to write telemetry record: {e}")

# --------------------------------------------------------------------------
# FLASK WEB ENDPOINTS
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
                yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + _latest_frame_jpeg + b"\r\n")
            time.sleep(0.04)
    return Response(_generate_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")

@_app.route("/api/state", methods=["GET"])
def get_state():
    global _system_state_snapshot
    payload = {
        "state": _system_state_snapshot["state"],
        "active_task": _system_state_snapshot["active_task"],
        "objects": _system_state_snapshot["objects"],
        "matrix_report": _system_state_snapshot["matrix_report"],
        "boxes": []
    }
    raw_cache = _system_state_snapshot.get("raw_boxes_cache", [])
    for label, confidence, bbox, centroid in raw_cache:
        if bbox and None not in bbox:
            payload["boxes"].append({
                "label": label, "confidence": int(confidence * 100),
                "xmin": bbox[0], "ymin": bbox[1], "xmax": bbox[2], "ymax": bbox[3]
            })
    return jsonify(payload)

@_app.route("/api/history", methods=["GET"])
def get_detection_history():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT label, MAX(timestamp) as last_seen, COUNT(*) as occurrence_count, MAX(confidence) as last_conf
            FROM detected_objects GROUP BY label ORDER BY last_seen DESC LIMIT 15
        """)
        rows = cursor.fetchall()
        conn.close()
        
        history_list = []
        for row in rows:
            local_time_str = time.strftime('%H:%M:%S', time.localtime(row[1]))
            raw_conf = row[3] if row[3] is not None else 1.0
            history_list.append({"label": row[0], "last_seen": local_time_str, "count": row[2], "confidence": int(raw_conf * 100)})
        return jsonify({"history": history_list})
    except Exception as e:
        return jsonify({"history": [], "error": str(e)})

@_app.route("/api/jog", methods=["POST"])
def manual_jog_servo():
    global _current_pan, _current_tilt, _global_node_instance
    data = request.json or {}
    direction = data.get("direction", "").lower()
    step = float(data.get("step", 5.0))

    if direction == "left": _current_pan += step
    elif direction == "right": _current_pan -= step
    elif direction == "up": _current_tilt -= step    
    elif direction == "down": _current_tilt += step  
    
    _current_pan = max(0.0, min(180.0, _current_pan))
    _current_tilt = max(0.0, min(180.0, _current_tilt))

    if _global_node_instance:
        jog_cmd = Vector3()
        jog_cmd.x = _current_pan
        jog_cmd.y = _current_tilt
        jog_cmd.z = 1.0
        _global_node_instance.servo_pub.publish(jog_cmd)
        return jsonify({"status": "success", "pan": _current_pan, "tilt": _current_tilt})
    return jsonify({"status": "error", "message": "ROS instance mapping unavailable."})

@_app.route("/api/command", methods=["POST"])
def handle_incoming_command():
    global _global_node_instance
    data = request.json or {}
    user_raw_text = data.get("command", "").strip()
    if not user_raw_text:
        return jsonify({"response": "Empty matrix bypassed."})
    
    if "scan" in user_raw_text.lower():
        if _global_node_instance:
            threading.Thread(target=_global_node_instance.execute_spatial_scan, daemon=True).start()
            return jsonify({"response": "Scan matrix engaged. Watch the Active World Model panel load raw waypoints..."})
        return jsonify({"response": "ROS node offline. Scan command dropped."})
        
    action_keywords = ["task", "run", "write", "build", "map", "test", "execute", "gather"]
    if any(kw in user_raw_text.lower() for kw in action_keywords):
        try:
            os.makedirs(os.path.dirname(TASK_LEDGER_PATH), exist_ok=True)
            with open(TASK_LEDGER_PATH, "a") as f:
                f.write(f"\n- [ ] **Task via Dashboard Console ({time.strftime('%Y-%m-%d %H:%M')})**: {user_raw_text}\n")
            cmd_args = ["opencode", "run", f"Please process the task requested by Steve: {user_raw_text}"]
            subprocess.Popen(cmd_args, stdout=sys.stdout, stderr=sys.stderr, preexec_fn=os.setpgrp)
            response_msg = "Task logged. OpenCode script runtime active."
        except Exception as e:
            response_msg = f"Delegation error: {str(e)}"
    else:
        response_msg = f"Directive acknowledged: '{user_raw_text}'"
    return jsonify({"response": response_msg})

# --------------------------------------------------------------------------
# ROS 2 CORE INTERFACE NODE
# --------------------------------------------------------------------------
class UM790DashboardNode(Node):
    def __init__(self):
        super().__init__('um790_dashboard_node')
        global _global_node_instance
        _global_node_instance = self
        self.data_lock = threading.Lock()
        self.first_frame_received = False

        self.img_sub = self.create_subscription(CompressedImage, '/piper/camera0/image_raw/compressed', self._image_callback, 10)
        self.object_sub = self.create_subscription(String, '/piper/perception/tracked_objects_json', self._object_callback, 10)
        self.servo_pub = self.create_publisher(Vector3, '/piper/neck/set_position', 10)
            
        threading.Thread(target=self._send_initial_homing_pulse, daemon=True).start()

    def _send_initial_homing_pulse(self):
        time.sleep(1.5)
        cmd = Vector3()
        cmd.x = _current_pan; cmd.y = _current_tilt; cmd.z = 1.0
        self.servo_pub.publish(cmd)

    def _image_callback(self, msg):
        global _latest_frame_jpeg
        _latest_frame_jpeg = msg.data.tobytes()

    def _object_callback(self, msg):
        self._parse_object_payload(msg.data)

    def execute_spatial_scan(self):
        global _current_pan, _current_tilt, _system_state_snapshot
        with self.data_lock:
            home_p = _current_pan
            home_t = _current_tilt
            
        waypoints = [
            {"id": "P1_Top_Left",     "p": home_p + 20.0, "t": home_t + 10.0},
            {"id": "P2_Top_Right",    "p": home_p - 20.0, "t": home_t + 10.0},
            {"id": "P3_Bottom_Right", "p": home_p - 20.0, "t": home_t - 10.0},
            {"id": "P4_Bottom_Left",  "p": home_p + 20.0, "t": home_t - 10.0}
        ]
        
        for wp in waypoints:
            wp["p"] = max(0.0, min(180.0, wp["p"]))
            wp["t"] = max(0.0, min(180.0, wp["t"]))
            
            with self.data_lock:
                _current_pan = wp['p']; _current_tilt = wp['t']
            
            cmd = Vector3()
            cmd.x = wp['p']; cmd.y = wp['t']; cmd.z = 1.0
            self.servo_pub.publish(cmd)
            time.sleep(1.5)
            
            with self.data_lock:
                current_seen = list(_system_state_snapshot.get("objects", []))
                _system_state_snapshot["matrix_report"][wp['id']] = current_seen

        with self.data_lock:
            _current_pan = home_p; _current_tilt = home_t
        cmd = Vector3()
        cmd.x = home_p; cmd.y = home_t; cmd.z = 1.0
        self.servo_pub.publish(cmd)

    def _parse_object_payload(self, raw_string_data):
        global _system_state_snapshot, _last_known_objects
        try:
            telemetry_data = json.loads(raw_string_data)
            detected_objects = telemetry_data.get("objects", [])
            cleaned_labels = []; processed_objects_for_db = []; current_frame_objects = set()
            label_parser = re.compile(r"([a-zA-Z0-9_\s\-]+)(?:\s*\((\d+)%\))?")

            for obj in detected_objects:
                raw_label = obj.get("label", "unknown")
                match = label_parser.match(raw_label)
                if match:
                    clean_label = match.group(1).strip()
                    pct = match.group(2)
                    confidence = float(pct) / 100.0 if pct else float(obj.get("confidence", 1.0))
                else:
                    clean_label = raw_label; confidence = float(obj.get("confidence", 1.0))

                cleaned_labels.append(clean_label)
                current_frame_objects.add(clean_label)
                
                xmin = obj.get("xmin"); ymin = obj.get("ymin"); xmax = obj.get("xmax"); ymax = obj.get("ymax")
                cx = (xmin + xmax) / 2.0 if None not in (xmin, xmax) else None
                cy = (ymin + ymax) / 2.0 if None not in (ymin, ymax) else None
                
                processed_objects_for_db.append((clean_label, confidence, (xmin, ymin, xmax, ymax), (cx, cy)))

            unique_labels = list(set(cleaned_labels))

            new_items = current_frame_objects - _last_known_objects
            lost_items = _last_known_objects - current_frame_objects
            for item in new_items: self.get_logger().info(f"[LOG] Object Entered -> {item.upper()}")
            for item in lost_items: self.get_logger().info(f"[LOG] Object Exited -> {item.upper()}")
            _last_known_objects = current_frame_objects

            with self.data_lock:
                _system_state_snapshot["objects"] = unique_labels
                _system_state_snapshot["raw_boxes_cache"] = processed_objects_for_db
                _system_state_snapshot["state"] = "TEAMING" if "person" in unique_labels else "SOLO"
                _system_state_snapshot["active_task"] = "Collaborator tracked via Edge YOLO arrays." if "person" in unique_labels else "System running autonomously."

            for label, conf, bbox, centroid in processed_objects_for_db:
                log_detection_to_db(time.time(), label, conf, bbox, centroid)
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
    threading.Thread(target=run_ros_loop, daemon=True).start()
    _app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)