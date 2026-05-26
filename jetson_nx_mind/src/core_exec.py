# ==============================================================================
# Component:  jetson_nx_mind
# Module:     core_exec.py
# Version:    3.0.0 (V3 Agentic - Audio Purge & OpenCode Prep)
# Purpose:    Acts as the main cognitive runtime commander. Coordinates the 
#             asynchronous visual worker and physical neck tracking. 
#             Logs environmental context to file system for OpenCode digestion.
# ==============================================================================

import os
import sys
import time
import json
import cv2
import threading
from datetime import datetime

from vision import VisionEngine
from neck import NeckEngine

class ExecutiveKernel:
    def __init__(self):
        self.stop_signal = threading.Event()
        self.task_gate = threading.Event()
        
        self.current_state = "ALONE" 
        self.active_user = None
        self.display_frame = None 
        self.lock = threading.Lock()
        
        self.base_dir = os.path.expanduser("~/piper/jetson_nx_mind")
        self.memory_dir = os.path.join(self.base_dir, "memory")
        self.journal_path = os.path.join(self.memory_dir, "journal.json")
        self.init_memory_store()
        
        self.neck = NeckEngine()
        self.threads = {}

    def init_memory_store(self):
        os.makedirs(self.memory_dir, exist_ok=True)
        if not os.path.exists(self.journal_path):
            with open(self.journal_path, "w") as f:
                json.dump({"boot_records": [], "interactions": []}, f, indent=4)

    def append_journal(self, context, message):
        with self.lock:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                with open(self.journal_path, "r") as f:
                    data = json.load(f)
                data["interactions"].append({"timestamp": timestamp, "context": context, "message": message})
                with open(self.journal_path, "w") as f:
                    json.dump(data, f, indent=4)
            except Exception: pass

    def evaluate_state_transitions(self, target_state, user_identity=None):
        if target_state == self.current_state and user_identity == self.active_user:
            return
        print(f"[STATE] Transitioning from {self.current_state} -> {target_state} (User: {user_identity})")
        
        # Log state changes so OpenCode has environmental awareness
        self.append_journal("State Transition", f"Shifted to {target_state}. Active entity: {user_identity}")
        
        self.current_state = target_state
        self.active_user = user_identity

        if target_state in ["ENGAGED", "CONVERSING", "PERCEIVING"]:
            self.task_gate.clear()
        else:
            self.task_gate.set()

    def _visual_worker(self):
        print("[EXECUTIVE] Spawning asynchronous visual tracking worker loop...")
        vision = VisionEngine()
        captured_frame = None
        
        absence_patience = 0
        PATIENCE_THRESHOLD = 2000  
        
        while not self.stop_signal.is_set():
            ret, frame = vision.yolo_driver.get_frame()
            if not ret:
                time.sleep(0.01)
                continue

            state, identity, metrics = vision.analyze_frame(frame)
            
            if metrics and metrics.get("box"):
                x, y, w, h = metrics["box"]
                color = (0, 255, 0) if identity != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                
                display_name = self.active_user if self.active_user else identity
                cv2.putText(frame, f"{display_name}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                
                frame_center_y = frame.shape[0] // 2
                face_center_y = y + (h // 2)
                centering_delta_y = face_center_y - frame_center_y
                
                self.neck.track_delta(metrics["centering_delta"], centering_delta_y)
                
            self.display_frame = frame

            # ==================================================================
            # V3 AGENTIC PERSISTENCE ROUTING
            # ==================================================================
            if state == "ALONE":
                absence_patience += 1
                if absence_patience > PATIENCE_THRESHOLD:
                    if self.current_state != "ALONE":
                        self.evaluate_state_transitions("ALONE", None)
                        print("[EXECUTIVE] Room vacancy timeout reached. Homing servos. Resuming research.")
                        self.neck.home()
                    absence_patience = PATIENCE_THRESHOLD + 1
                    
            elif state == "ENGAGED":
                absence_patience = 0  
                if self.current_state != "ENGAGED":
                    self.evaluate_state_transitions("ENGAGED", identity)
                    print(f"[EXECUTIVE] Collaborator identified: {identity}. Suspending research loop.")
                        
            elif state == "PERCEIVING_UNKNOWN":
                if self.current_state == "ENGAGED" or self.current_state == "CONVERSING":
                    absence_patience += 1
                    if absence_patience > PATIENCE_THRESHOLD:
                        print(f"[EXECUTIVE] Active session lock expired for user: {self.active_user}")
                        self.evaluate_state_transitions("ALONE", None)
                else:
                    if self.current_state != "PERCEIVING":
                        self.evaluate_state_transitions("PERCEIVING", "Unknown")
                        
                    if self.current_state == "PERCEIVING":
                        if metrics and metrics["both_eyes_visible"] and metrics["is_centered"]:
                            # Auto-Enrollment without Voice for V3
                            captured_frame = metrics.get("full_frame", frame)
                            timestamp_id = datetime.now().strftime("Guest_%H%M%S")
                            print(f"\n[EXECUTIVE] Unknown profile locked. Auto-enrolling as {timestamp_id}...")
                            
                            vision.save_new_face(timestamp_id, captured_frame)
                            self.append_journal("Security", f"Unrecognized profile enrolled as {timestamp_id}.")
                            self.evaluate_state_transitions("ENGAGED", timestamp_id)

            time.sleep(0.01)
            
        vision.yolo_driver.release()

    def _offline_task_worker(self):
        # This loop will eventually be managed/monitored by OpenCode
        while not self.stop_signal.is_set():
            self.task_gate.wait()
            # Placeholder for background research cycles
            time.sleep(10.0)

    def startup(self):
        self.neck.startup()
        self.threads["visual"] = threading.Thread(target=self._visual_worker, daemon=True)
        self.threads["offline_tasks"] = threading.Thread(target=self._offline_task_worker, daemon=True)
        
        self.task_gate.set() 
        for thread_object in self.threads.values():
            thread_object.start()

    def shutdown(self):
        self.stop_signal.set()
        self.task_gate.set()  
        for thread_object in self.threads.values():
            if thread_object.is_alive():
                thread_object.join(timeout=2.0)
        self.neck.shutdown()
