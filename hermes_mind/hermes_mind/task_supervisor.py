import os
import sys
import time
import json
import threading
import requests
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import logging
from datetime import datetime

class HermesSupervisorNode(Node):
    def __init__(self):
        super().__init__('hermes_supervisor')
        
        self.workspace_root = "/home/steve/piper_ws/src/piper_brain/piper_brain"
        self.ledger_path = os.path.join(self.workspace_root, "tasks/current_tasks.md")
        self.progress_path = os.path.join(self.workspace_root, "tasks/task_progress.md")
        
        # HITL Thread Synchronizers
        self.approval_lock = threading.Lock()
        self.pending_execution_payload = None
        self.pending_target_filepath = None
        self.latest_approval_granted = False

        # Communications Matrix
        self.status_pub = self.create_publisher(String, '/hermes/status_stream', 10)
        self.approval_sub = self.create_subscription(String, '/hermes/human_approval', self._approval_callback, 10)
        
        log_file_path = "/home/steve/piper_ws/hermes_runtime.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(log_file_path),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

        # File Watcher Loop Execution
        threading.Thread(target=self._file_watcher_loop, daemon=True).start()
        self.logger.info("🛡️ Hermes Supervisor Active with HITL Manager-Worker Pipeline.")
        self.ledger_already_clean = False #  Tracks completion state to avoid log spamming


    def _approval_callback(self, msg):
        action = msg.data.lower()
        with self.approval_lock:
            if action == "approve":
                self.latest_approval_granted = True
            elif action == "deny":
                self.pending_execution_payload = None
                self.pending_target_filepath = None
                self.latest_approval_granted = False

    def _publish_to_dashboard(self, status_text):
        msg = String()
        msg.data = status_text
        self.status_pub.publish(msg)

    def _file_watcher_loop(self):
        last_mtime = 0.0
        while rclpy.ok():
            if os.path.exists(self.ledger_path):
                current_mtime = os.path.getmtime(self.ledger_path)
                if current_mtime > last_mtime:
                    last_mtime = current_mtime
                    self.evaluate_next_steps()
            time.sleep(2.0)

    def query_local_llm(self, model_name, system_prompt, user_prompt):
        """ Helper to handle direct Ollama JSON REST requests """
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": model_name,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {"temperature": 0.2}
        }
        try:
            response = requests.post(url, json=payload, timeout=90.0)
            if response.status_code == 200:
                return response.json().get("response", "")
        except Exception as e:
            self.logger.error(f"Ollama connection dropped to model {model_name}: {e}")
        return ""

    def evaluate_next_steps(self):
        with open(self.ledger_path, 'r') as f:
            ledger_content = f.read()

        # Check if there are any active, unchecked tasks remaining
        if "- [ ]" in ledger_content:
            # We found open requirements, reset the completion flag
            self.ledger_already_clean = False
            
            self.logger.info("🚀 Active task identified. Engaging Hermes Orchestrator...")
            self._publish_to_dashboard("[HERMES] 🧠 Mapping out project requirements architecture...")
            
            # ------------------------------------------------------------------
            # STAGE 1: HERMES REASONING BLUEPRINT
            # ------------------------------------------------------------------
            hermes_system = (
                "You are Hermes, the autonomous Project Manager for a ROS 2 robot named Piper. "
                "Your job is to read the task ledger and decide exactly which file needs modification "
                "and write a high-level technical pseudo-code blueprint of the changes required. "
                "You MUST specify the target file path clearly on the very first line of your response as: "
                "TARGET_FILE: /path/to/file.py"
            )
            
            hermes_blueprint = self.query_local_llm("hermes3", hermes_system, ledger_content)
            
            # Parse target filename from the blueprint
            target_file = None
            first_line = hermes_blueprint.strip().split('\n')[0]
            if "TARGET_FILE:" in first_line:
                target_file = first_line.replace("TARGET_FILE:", "").strip()
            
            # Fallback lookup context for Task-03 if parsing slipped or file path is omitted
            if not target_file or not os.path.exists(target_file):
                target_file = os.path.join(self.workspace_root, "autonomous_drawing.py")

            self.logger.info(f"📋 Hermes selected target: {target_file}. Invoking Qwen-Coder...")
            self._publish_to_dashboard(f"[HERMES] 🤖 Handing blueprint over to Qwen-Coder for complete file refactoring...")

            # ------------------------------------------------------------------
            # STAGE 2: QWEN CODER FULL-FILE RENDERING
            # ------------------------------------------------------------------
            with open(target_file, 'r') as f:
                original_source_code = f.read()

            qwen_system = (
                "You are an expert ROS 2 software engineer. You write complete, valid, working python code files. "
                "You are given an existing python file and an architectural blueprint specifying modifications. "
                "Output the entire modified python file from scratch. DO NOT use placeholders like '# ... rest of code ...'. "
                "Include all imports, methods, loops, and setup declarations intact so it can overwrite the destination file directly. "
                "Output ONLY the raw code inside standard ```python ``` markdown wrapper blocks."
            )
            
            qwen_user_prompt = (
                f"### ARCHITECTURAL BLUEPRINT:\n{hermes_blueprint}\n\n"
                f"### ORIGINAL SOURCE CODE:\n{original_source_code}"
            )
            
            final_code_payload = self.query_local_llm("qwen2.5-coder", qwen_system, qwen_user_prompt)

            # Stage for Human Review
            self.stage_for_human_approval(final_code_payload, target_file)

        else:
            # ✨ Gated Celebration: Only execute if we haven't already reported it clean!
            if not getattr(self, 'ledger_already_clean', False):
                completion_message = "🎉 [SYSTEM] All tasks in the current ledger have been successfully executed! Piper is fully nominal and standing by."
                
                self.logger.info("✅ Ledger audit complete: Zero unfulfilled tasks remaining.")
                self._publish_to_dashboard(completion_message)
                
                # Lock the gate so the next file-watcher iteration skips logging this
                self.ledger_already_clean = True

    def stage_for_human_approval(self, proposal_text, target_file):
        with self.approval_lock:
            self.pending_execution_payload = proposal_text
            self.pending_target_filepath = target_file
            self.latest_approval_granted = False

        self.logger.info("🛑 Complete refactoring block staged. Awaiting dashboard interaction...")
        
        # Write to md file for persistence
        with open(self.progress_path, 'w') as f:
            f.write(proposal_text)

        # ✨ THE FIX: Explicitly broadcast the code proposal right into the dashboard text stream!
        dashboard_display = (
            f"============================================================\n"
            f"🤖 QWEN-CODER GENERATED PROPOSAL FOR: {os.path.basename(target_file)}\n"
            f"============================================================\n"
            f"{proposal_text}\n"
            f"============================================================\n"
            f"🛑 Awaiting verification. Click [APPROVE EXECUTION] to apply."
        )
        self._publish_to_dashboard(dashboard_display)

        while rclpy.ok():
            with self.approval_lock:
                if self.latest_approval_granted:
                    self.execute_approved_code()
                    return
                if self.pending_execution_payload is None:
                    self.logger.info("🛑 Code changes safely aborted by operator.")
                    self._publish_to_dashboard("[SYSTEM] Staged block aborted. Standing by...")
                    return
            time.sleep(1.0)

    def execute_approved_code(self):
        """ Executed ONLY when operator clicks Approve on the dashboard gateway """
        try:
            # Strip markdown code wrapper markers if Qwen wrapped them
            clean_code = self.pending_execution_payload
            if "```python" in clean_code:
                clean_code = clean_code.split("```python")[1].split("```")[0]
            elif "```" in clean_code:
                clean_code = clean_code.split("```")[1].split("```")[0]
                
            clean_code = clean_code.strip()

            # Overwrite the destination file cleanly
            with open(self.pending_target_filepath, 'w') as f:
                f.write(clean_code)

            self.logger.info(f"✨ File update sequence successful: {self.pending_target_filepath}")
            self._publish_to_dashboard(f"[SUCCESS] Core logic updated dynamically: {os.path.basename(self.pending_target_filepath)}")
        except Exception as e:
            self.logger.error(f"❌ Failed to write approved modifications to target: {e}")
            self._publish_to_dashboard(f"[CRITICAL ERROR] Commit failed: {str(e)}")
            
        with self.approval_lock:
            self.pending_execution_payload = None
            self.pending_target_filepath = None
            self.latest_approval_granted = False

def main(args=None):
    rclpy.init(args=args)
    node = HermesSupervisorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()