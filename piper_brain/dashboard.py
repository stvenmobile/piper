# ==============================================================================
# Component:  jetson_nx_mind
# Module:     dashboard.py
# Version:    3.5.2 (Clean Reference Build - Restored)
# Purpose:    Flask web micro-service network infrastructure. Direct-spawns
#             OpenCode developer agents via decoupled OS subprocess pipelines.
# ==============================================================================

import os
import sys
import time
import logging
import subprocess
from flask import Flask, render_template, Response, request, jsonify

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
sys.path.append(CURRENT_DIR)
sys.path.append(PARENT_DIR)

_log = logging.getLogger('werkzeug')
_log.setLevel(logging.ERROR)

_app = Flask(__name__, template_folder="templates")

_latest_frame_jpeg = None
_system_state_snapshot = {}
TASK_LEDGER_PATH = os.path.expanduser("~/piper/jetson_nx_mind/task_requests.md")

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
    global _system_state_snapshot
    return jsonify(_system_state_snapshot)

@_app.route("/api/command", methods=["POST"])
def handle_incoming_command():
    """Intercepts web console inputs, logs tasks to the filesystem, and instantly

    spawns a decoupled OpenCode sub-process worker shell.
    """
    data = request.json or {}
    user_raw_text = data.get("command", "").strip()
    
    if not user_raw_text:
        return jsonify({"response": "Empty directive matrix bypassed by parser core."})
    
    print(f"\n[DASHBOARD INGEST] Received web console directive: '{user_raw_text}'")
    
    action_keywords = ["task", "run", "write", "build", "map", "test", "calibrate", "execute", "gather", "process"]
    is_task_declaration = any(kw in user_raw_text.lower() for kw in action_keywords)
    
    if is_task_declaration:
        try:
            # 1. Log the requirement immediately to disk storage
            with open(TASK_LEDGER_PATH, "a") as f:
                f.write(f"\n- [ ] **Task via Dashboard Console ({time.strftime('%Y-%m-%d %H:%M')})**: {user_raw_text}\n")
            os.utime(TASK_LEDGER_PATH, None)
            
            # 2. DECOUPLED BACKGROUND PROCESS INITIALIZATION
            print("[SYSTEM LOG] Launching autonomous OpenCode sub-process shell...")
            
            cmd_args = ["opencode", "run", f"Please process the task requested by Steve: {user_raw_text}"]
            
            subprocess.Popen(
                cmd_args,
                stdout=sys.stdout,  
                stderr=sys.stderr,
                preexec_fn=os.setpgrp 
            )
            
            response_msg = "Task parsed and appended. OpenCode background sub-process successfully invoked!"
        except Exception as e:
            response_msg = f"Failed to successfully delegate background task execution. Error: {str(e)}"
    else:
        response_msg = f"Directive acknowledged: '{user_raw_text}'"

    return jsonify({"response": response_msg})

def run_dashboard_server(host="0.0.0.0", port=5000):
    _app.run(host=host, port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    run_dashboard_server()