# ==============================================================================
# Component:  jetson_nx_mind
# Module:     core_exec.py
# Version:    1.0.0 (Executive Orchestration Engine)
# Purpose:    Central life-cycle controller managing subordinate threads, localized
#             json memory stores, and state-gated background task execution.
#
# Change History / Release Notes:
# Date        Version   Author    Description of Changes
# ----------  --------  --------  ----------------------------------------------
# 2026-05-18  1.0.0     Steve     Initial core executive framework design with
#                                 thread-pausing gates and state architecture.
# ==============================================================================

import threading
import time
import json
import os
from datetime import datetime

class CoreExecutive:
    def __init__(self):
        print("[EXEC] Awakening Core Executive Layer...")
        self.memory_dir = "../memory"
        
        # Thread Synchronization Controls
        self.stop_signal = threading.Event()
        self.task_gate = threading.Event()  # Internal Gate: Cleared = Paused, Set = Running
        
        # System State
        self.current_state = "ALONE"
        self.user_present = False
        
        # Initialize Memory Databases
        self.init_memory_store()

    def init_memory_store(self):
        """Guarantees that memory assets exist on disk before launching loops."""
        os.makedirs(self.memory_dir, exist_ok=True)
        paths = {
            "dna": f"{self.memory_dir}/system_dna.json",
            "journal": f"{self.memory_dir}/journal.json",
            "tasks": f"{self.memory_dir}/task_progress.json"
        }
        
        for name, path in paths.items():
            if not os.path.exists(path):
                with open(path, "w") as f:
                    json.dump({"info": f"Initial {name} state created."}, f, indent=2)
                print(f"[EXEC] Created missing memory file: {path}")

    def append_journal(self, context, message):
        """Writes a strict, timestamped entry into the historical record."""
        path = f"{self.memory_dir}/journal.json"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {"timestamp": timestamp, "context": context, "entry": message}
        
        try:
            data = []
            if os.path.exists(path):
                with open(path, "r") as f:
                    try:
                        data = json.load(f)
                        if not isinstance(data, list): data = []
                    except json.JSONDecodeError:
                        data = []
            
            data.append(entry)
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[EXEC] ERROR: Failed to write journal: {e}")

    # Subordinate Worker Threads
    def _visual_worker(self):
        """Thread 1: Native vision capture, tracking loop, and identification."""
        print("[THREAD] Visual Engine Thread Online.")
        while not self.stop_signal.is_set():
            # Mocking perception logic for architecture test
            # In production, this pulls from perception.py and updates self.user_present
            time.sleep(1.0)

    def _listening_worker(self):
        """Thread 2: gRPC audio ingestion and automated wake-word detection."""
        print("[THREAD] Listening/Comms Thread Online.")
        while not self.stop_signal.is_set():
            time.sleep(0.5)

    def _offline_task_worker(self):
        """Thread 3: Autonomous planning and background maintenance loop."""
        print("[THREAD] Offline Task Manager Thread Online.")
        while not self.stop_signal.is_set():
            # This gate blocks execution natively without wasting CPU polling cycles
            self.task_gate.wait()
            
            print("[OFFLINE-TASK] Executing internal goals, organizing databases...")
            self.append_journal("OFFLINE", "Executed periodic database memory defragmentation.")
            time.sleep(5.0)  # Simulated task step duration

    # State Machine Engine
    def evaluate_state_transitions(self):
        """Evaluates sensory variables and updates operational gates."""
        if self.user_present and self.current_state == "ALONE":
            # Pivot from background thinking to active focus
            print("[EXEC] Transitioning from ALONE to PERCEIVING/ENGAGED.")
            self.task_gate.clear()  # Instantly pauses the offline thread
            self.current_state = "ENGAGED"
            self.append_journal("SYSTEM", "Steve detected. Suspended all background tasking.")
            
        elif not self.user_present and self.current_state != "ALONE":
            # Pivot from focus to standalone planning
            print("[EXEC] User departed. Resuming autonomous background thinking.")
            self.current_state = "ALONE"
            self.append_journal("SYSTEM", "Environment cleared. Awakening offline task processing.")
            self.task_gate.set()    # Releases the block on the offline thread

    def startup(self):
        """Launches all concurrent thread processing systems cleanly."""
        self.append_journal("SYSTEM", "Piper Executive Control Engine booted successfully.")
        
        # Configure threads
        self.threads = {
            "visual": threading.Thread(target=self._visual_worker, daemon=True),
            "listening": threading.Thread(target=self._listening_worker, daemon=True),
            "offline_tasks": threading.Thread(target=self._offline_task_worker, daemon=True)
        }
        
        # Initial gate state: Assume alone at startup
        self.task_gate.set()
        
        # Launch everything
        for t in self.threads.values():
            t.start()
            
        # Run main control check loop
        try:
            while not self.stop_signal.is_set():
                self.evaluate_state_transitions()
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self):
        """Gracefully halts execution and synchronizes all pending disk buffers."""
        print("\n[EXEC] Initiating ordered shutdown sequence...")
        self.append_journal("SYSTEM", "System shutdown sequence commanded.")
        self.stop_signal.set()
        self.task_gate.set()  # Clear gate block so thread can exit cleanly
        print("[EXEC] Core systems offline. Safe to disconnect.")

if __name__ == "__main__":
    controller = CoreExecutive()
    controller.startup()
