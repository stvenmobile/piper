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
    resolved_tasks_dir = os.path.join(workspace_root, "tasks")
else:
    resolved_template_dir = os.path.join(current_script_dir, "templates")
    resolved_assets_dir = os.path.join(current_script_dir, "assets")
    resolved_tasks_dir = os.path.join(current_script_dir, "tasks")

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

# ==========================================================================
# FILE SYSTEM MEMORY LOCATORS (UM790 BRAIN CORE)
# ==========================================================================
TASK_LEDGER_PATH = os.path.join(resolved_tasks_dir, "current_tasks.md")
DB_PATH = os.path.join(resolved_assets_dir, "piper_memory.db")

_last_known_objects = set()
_pending_state = "SOLO"
_state_transition_time = 0.0
_current_pan = 90.0
_current_tilt = 70.0
_global_node_instance = None
_latest_sketch_filename = None
_latest_hermes_status = "[SYSTEM] Standing by for Hermes task streaming..."

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
        "latest_sketch": _latest_sketch_filename,
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
    
    # 1. HERMES ROUTE: Direct hand-off to background file-layer execution
    if user_raw_text.lower().startswith("hermes:"):
        clean_task = user_raw_text[7:].strip()
        try:
            with open(TASK_LEDGER_PATH, "a") as f:
                f.write(f"\n- [ ] **Task via Dashboard ({time.strftime('%Y-%m-%d %H:%M')})**: {clean_task}\n")
            
            return jsonify({"response": "📋 System task logged directly to current_tasks.md. Hermes is deploying background routines."})
        except Exception as e:
            return jsonify({"response": f"❌ Failed to notify Hermes: {str(e)}"})

    # 2. PIPER ROUTE: On-demand foreground assistant execution
    else:
        try:
            response_msg = f"Acknowledged. I am processing your request regarding: '{user_raw_text}'"
            return jsonify({"response": response_msg})
        except Exception as e:
            return jsonify({"response": f"⚠️ Piper Interactivity Error: {str(e)}"})

# --- HERMES INTERACTIVE GATEWAY ENDPOINTS ---
@_app.route("/api/hermes/status", methods=["GET"])
def get_hermes_status():
    log_path = os.path.expanduser("~/piper_ws/hermes_runtime.log")
    if not os.path.exists(log_path):
        return jsonify({"status": "[SYSTEM] Log file pipeline initializing..."})
    
    try:
        # Read the last 40 lines dynamically from the filesystem log
        with open(log_path, "r") as f:
            lines = f.readlines()
        tail_lines = lines[-40:]
        
        # Convert newlines to HTML break tags for the terminal view wrapper
        formatted_log = "<br>".join([line.rstrip() for line in tail_lines])
        return jsonify({"status": formatted_log})
    except Exception as e:
        return jsonify({"status": f"[ERROR] Failed to read runtime stream: {str(e)}"})

@_app.route("/api/hermes/approve", methods=["POST"])
def approve_hermes_task():
    global _global_node_instance
    if _global_node_instance:
        msg = String()
        msg.data = "approve"
        _global_node_instance.approval_pub.publish(msg)
        return jsonify({"status": "success", "message": "Approval sent down the pipe."})
    return jsonify({"status": "error", "message": "ROS graph unavailable."})

@_app.route("/api/hermes/deny", methods=["POST"])
def deny_hermes_task():
    global _global_node_instance
    if _global_node_instance:
        msg = String()
        msg.data = "deny"
        _global_node_instance.approval_pub.publish(msg)
        return jsonify({"status": "success", "message": "Denial sent. Staging cleared."})
    return jsonify({"status": "error", "message": "ROS graph unavailable."})

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

        # Communications Infrastructure Mapping
        self.img_sub = self.create_subscription(CompressedImage, '/piper/camera0/image_raw/compressed', self._image_callback, 10)
        self.object_sub = self.create_subscription(String, '/piper/perception/tracked_objects_json', self._object_callback, 10)
        self.servo_pub = self.create_publisher(Vector3, '/piper/neck/set_position', 10)
            
        # Hermes Interactive Gateway Communication Channels
        self.status_sub = self.create_subscription(String, '/hermes/status_stream', self._hermes_status_callback, 10)
        self.approval_pub = self.create_publisher(String, '/hermes/human_approval', 10)

        # Threaded Polling Routines
        threading.Thread(target=self._sketchbook_filesystem_watcher, daemon=True).start()
        threading.Thread(target=self._send_initial_homing_pulse, daemon=True).start()
        
        # Trigger single-shot automatic matrix mapping 10.0 seconds post-initialization
        self.matrix_scan_timer = self.create_timer(10.0, self._trigger_initial_matrix_scan)

    def _send_initial_homing_pulse(self):
        time.sleep(1.5)
        cmd = Vector3()
        cmd.x = _current_pan; cmd.y = _current_tilt; cmd.z = 1.0
        self.servo_pub.publish(cmd)

    def _trigger_initial_matrix_scan(self):
        self.matrix_scan_timer.cancel()
        self.get_logger().info("🌐 Commencing background World Model Matrix generation sequence...")
        threading.Thread(target=self.execute_spatial_scan, daemon=True).start()

    def _hermes_status_callback(self, msg):
        global _latest_hermes_status
        _latest_hermes_status = msg.data

    def _sketchbook_filesystem_watcher(self):
        """Asynchronously polls the sketchbook folder to map the newest sketch file string to the UI."""
        global _latest_sketch_filename
        sketch_dir = os.path.join(resolved_assets_dir, "sketchbook")
        
        while True:
            try:
                if os.path.exists(sketch_dir):
                    files = [f for f in os.listdir(sketch_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                    if files:
                        files.sort(key=lambda x: os.path.getmtime(os.path.join(sketch_dir, x)), reverse=True)
                        with self.data_lock:
                            _latest_sketch_filename = files[0]
            except Exception as e:
                print(f"[WATCHER ERROR] Directory indexing failure: {e}")
            time.sleep(2.5)

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
            time.sleep(2.0)
            
            with self.data_lock:
                current_seen = list(_system_state_snapshot.get("objects", []))
                formatted_seen = [item.upper() for item in current_seen]
                _system_state_snapshot["matrix_report"][wp['id']] = formatted_seen if formatted_seen else ["CLEAR"]

        with self.data_lock:
            _current_pan = home_p; _current_tilt = home_t
        cmd = Vector3()
        cmd.x = home_p; cmd.y = home_t; cmd.z = 1.0
        self.servo_pub.publish(cmd)
        self.get_logger().info("🌐 Spatial scanning sequence concluded. Matrix map generated successfully.")

    def _parse_object_payload(self, raw_string_data):
        global _system_state_snapshot, _last_known_objects
        try:
            telemetry_data = json.loads(raw_string_data)
            
            if isinstance(telemetry_data, list):
                detected_objects = telemetry_data
            elif isinstance(telemetry_data, dict):
                detected_objects = telemetry_data.get("objects", [])
            else:
                detected_objects = []
                
            cleaned_labels = []; processed_objects_for_db = []; current_frame_objects = set()
            label_parser = re.compile(r"([a-zA-Z0-9_\s\-]+)(?:\s*\((\d+)%\))?")

            for obj in detected_objects:
                raw_label = obj.get("label", "unknown")
                match = label_parser.match(raw_label)
                if match:
                    clean_label = match.group(1).strip().lower()
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