# ==============================================================================
# Component:  jetson_nx_mind
# Module:     core_exec.py
# Version:    1.0.0 (Executive Control Model & Thread Orchestrator)
# Purpose:    Acts as the main cognitive runtime commander. Coordinates the 
#             asynchronous visual worker, listening pipes, and state gates.
#             Enforces dual-eye verification rules for unknown user registration.
# ==============================================================================

import os
import sys
import time
import json
import cv2
import threading
from datetime import datetime

# Import our visualization substrate
from vision import VisionEngine

class ExecutiveKernel:
    def __init__(self, gateway_instance=None):
        """Initializes the executive layer kernel and thread-synchronization primitives."""
        self.stop_signal = threading.Event()
        self.task_gate = threading.Event()
        self.gateway = gateway_instance
        
        # Core State Variables
        self.current_state = "ALONE"  # ALONE, PERCEIVING, ENGAGED, CONVERSING
        self.active_user = None
        self.lock = threading.Lock()
        
        # Path Anchors
        self.base_dir = os.path.expanduser("~/piper/jetson_nx_mind")
        self.memory_dir = os.path.join(self.base_dir, "memory")
        self.journal_path = os.path.join(self.memory_dir, "journal.json")
        
        # Initialize file tracking structures
        self.init_memory_store()
        
        # Thread Registry
        self.threads = {}

    def init_memory_store(self):
        """Executes low-level file system validation at boot."""
        try:
            os.makedirs(self.memory_dir, exist_ok=True)
            
            # Ensure base journal file exists structurally
            if not os.path.exists(self.journal_path):
                with open(self.journal_path, "w") as f:
                    json.dump({"boot_records": [], "interactions": []}, f, indent=4)
                    
            # Set up default placeholder configuration structures if missing
            dna_path = os.path.join(self.memory_dir, "system_dna.json")
            if not os.path.exists(dna_path):
                with open(dna_path, "w") as f:
                    json.dump({"name": "Piper", "version": "3.3.0", "creator": "Steve"}, f, indent=4)
                    
            task_path = os.path.join(self.memory_dir, "task_progress.json")
            if not os.path.exists(task_path):
                with open(task_path, "w") as f:
                    json.dump({"current_tasks": [], "completed_tasks": []}, f, indent=4)
                    
        except Exception as e:
            print(f"[EXECUTIVE] Memory store directory mapping fault: {e}")

    def append_journal(self, context, message):
        """Thread-safe logging interface that injects entries into persistent JSON storage."""
        with self.lock:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                with open(self.journal_path, "r") as f:
                    data = json.load(f)
                
                entry = {"timestamp": timestamp, "context": context, "message": message}
                data["interactions"].append(entry)
                
                with open(self.journal_path, "w") as f:
                    json.dump(data, f, indent=4)
            except Exception as e:
                print(f"[EXECUTIVE] Journal logging write hazard: {e}")

    def evaluate_state_transitions(self, target_state, user_identity=None):
        """Manages the centralized state machine transitions and thread gates."""
        if target_state == self.current_state and user_identity == self.active_user:
            return

        print(f"[STATE] Transitioning from {self.current_state} -> {target_state} (User: {user_identity})")
        self.current_state = target_state
        self.active_user = user_identity

        if target_state in ["ENGAGED", "CONVERSING", "PERCEIVING"]:
            # Suspend background tasks instantly when a human presence is being evaluated
            self.task_gate.clear()
        else:
            # Re-open background execution threads when the space is empty
            self.task_gate.set()


    def _visual_worker(self):
        """Drives hardware-accelerated camera frames through unified YOLO and identity filters."""
        print("[EXECUTIVE] Spawning asynchronous visual tracking worker loop...")
        
        # Instantiate our newly fused GPU-accelerated Vision Engine
        vision = VisionEngine()
        
        # Enrollment Lifecycle Primitives
        awaiting_name_string = False
        captured_roi = None
        
        while not self.stop_signal.is_set():
            # Let your custom V4L2 hooks inside perception handle hardware reads, CLAHE, and Unsharp sharpening
            ret, frame = vision.yolo_driver.get_frame()
            if not ret:
                time.sleep(0.01)
                continue

            # Run frame extraction metrics
            state, identity, metrics = vision.analyze_frame(frame)
            
            # --- STATE MANAGEMENT EVALUATION INTERFACE ---
            if state == "ALONE":
                if self.current_state != "ALONE" and not awaiting_name_string:
                    self.evaluate_state_transitions("ALONE", None)
                    print("[EXECUTIVE] Room vacancy discovered. Returning look-angles to true zero.")
                    
            elif state == "ENGAGED":
                if self.current_state == "ALONE":
                    self.evaluate_state_transitions("ENGAGED", identity)
                    print(f"[EXECUTIVE] Biometric match confirmed: Welcoming {identity}.")
                    self.append_journal("FACIAL_RECOGNITION", f"Verified user {identity} entered frame matrix.")
                    
                    if self.gateway:
                        greeting = f"Welcome back, {identity}. Spatial tracking metrics locked."
                        self.gateway.stream_vocalize_text(greeting)
                        
            elif state == "PERCEIVING_UNKNOWN":
                if self.current_state == "ALONE" and not awaiting_name_string:
                    self.evaluate_state_transitions("PERCEIVING", "Unknown")
                    
                    # Verify structural enrollment constraints before spawning the blocking Whisper check
                    if metrics["both_eyes_visible"] and metrics["is_centered"]:
                        print("[EXECUTIVE] Optimal frontal alignment acquired. Triggering vocal prompt sequence...")
                        
                        if self.gateway:
                            captured_roi = metrics["roi"]
                            awaiting_name_string = True
                            
                            self.gateway.stream_vocalize_text("Hello. I do not recognize your profile footprint yet. What is your name?")
                            print("[EXECUTIVE] Listening for name transcription string...")
                            
                            # Reset the thread event flag before entering the wait state
                            self.gateway.transcription_ready.clear()
                            
                            # Block for up to 8 seconds waiting for the gRPC thread to intercept the user's name
                            success = self.gateway.transcription_ready.wait(timeout=8.0)
                            
                            if success and self.gateway.latest_transcription:
                                name_payload = self.gateway.latest_transcription.strip()
                                saved_file = vision.save_new_face(name_payload, captured_roi)
                                self.append_journal("USER_ENROLLMENT", f"Registered profile identity '{name_payload}' via file {saved_file}")
                                self.gateway.stream_vocalize_text(f"Understood. Biometric parameters saved. Nice to meet you, {name_payload}.")
                            else:
                                print("[EXECUTIVE] Registration window timed out or text payload was empty.")
                                self.gateway.stream_vocalize_text("Registration window timed out. Profile discarded.")
                                
                            awaiting_name_string = False
                            captured_roi = None

            time.sleep(0.01)
            
        # Clean up the camera connection via your native perception release method
        vision.yolo_driver.release()
        print("[EXECUTIVE] Visual worker lifecycle loop brought down safely.")


    def _listening_worker(self):
        """Monitors network-facing gRPC pipelines and logs interaction metrics."""
        print("[EXECUTIVE] Spawning network gRPC listening monitor loop...")
        while not self.stop_signal.is_set():
            # If the audio pipeline shifts into heavy active stream iteration, track state
            if self.gateway and hasattr(self.gateway, 'is_streaming') and self.gateway.is_streaming:
                if self.current_state != "CONVERSING":
                    self.evaluate_state_transitions("CONVERSING", self.active_user)
            time.sleep(0.5)

    def _offline_task_worker(self):
        """Executes lower priority standalone tasks when the environment space is clear."""
        print("[EXECUTIVE] Spawning autonomous background task supervisor loop...")
        while not self.stop_signal.is_set():
            # This thread blocks passively here until the gate is set to True (State: ALONE)
            self.task_gate.wait()
            
            # Simple simulation tracking of offline background vectorization or memory cleanups
            # print("[EXECUTIVE] Idle environment status: Executing vector index health validations...")
            time.sleep(10.0)

    def startup(self):
        """System entry execution method. Spawns sub-threads into operational status."""
        print("[EXECUTIVE] Commencing kernel initialization protocols...")
        self.append_journal("KERNEL_LIFECYCLE", "System executive layers booted cleanly.")
        
        # Initial Thread Initialization Management
        self.threads["visual"] = threading.Thread(target=self._visual_worker, daemon=True)
        self.threads["listening"] = threading.Thread(target=self._listening_worker, daemon=True)
        self.threads["offline_tasks"] = threading.Thread(target=self._offline_task_worker, daemon=True)
        
        # Kickoff tasks execution
        self.task_gate.set() # Allow idle workflows to process initially if clear
        for thread_name, thread_object in self.threads.items():
            thread_object.start()
            
        print("[EXECUTIVE] All core auxiliary background worker nodes are running.")

    def shutdown(self):
        """Orderly termination sequence. Flushes buffers and unlocks internal gates safely."""
        print("\n[EXECUTIVE] Intercepted termination sequence command. Powering down tiers...")
        self.stop_signal.set()
        self.task_gate.set()  # Unblock the offline loop if it's currently waiting on the gate
        
        for thread_name, thread_object in self.threads.items():
            if thread_object.is_alive():
                thread_object.join(timeout=2.0)
                
        self.append_journal("KERNEL_LIFECYCLE", "System runtime execution environment halted gracefully.")
        print("[EXECUTIVE] Executive core successfully brought offline.")

if __name__ == "__main__":
    # Local simulation standalone unit verification test block execution
    exec_kernel = ExecutiveKernel()
    try:
        exec_kernel.startup()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        exec_kernel.shutdown()
