# ==============================================================================
# Component:  jetson_nx_mind
# Module:     main.py
# Version:    3.1.0 (V3 Agentic - Default Video Streaming)
# Purpose:    Provides a single orchestration script to spin up the local
#             thread executive loop for spatial tracking and OpenCode prep.
# ==============================================================================

import os
import sys
import time
import cv2
import argparse

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
sys.path.append(CURRENT_DIR)
sys.path.append(PARENT_DIR)

from core_exec import ExecutiveKernel

def main():
    parser = argparse.ArgumentParser(description="Piper Spatial Researcher Runtime Engine")
    parser.add_argument('--no-video', action='store_true', help="Disables localized Qt5/X11 video rendering, running entirely headless.")
    args = parser.parse_args()

    print("=====================================================")
    print("        INITIALIZING PIPER SPATIAL RESEARCHER        ")
    print("=====================================================\n")

    # Instantiate the Vision-Only Kernel
    executive = ExecutiveKernel()
    
    # Boot the hardware loops
    executive.startup()

    if not args.no_video:
        print("\n[SYSTEM] Video streaming active. Press 'q' on the video window to stop.")
    else:
        print("\n[SYSTEM] Master execution loop completely active running HEADLESS.")
        print("[SYSTEM] High-fidelity spatial tracking is fully operational. Press Ctrl+C to stop.")
    
    try:
        while True:
            if not args.no_video:
                if hasattr(executive, 'display_frame') and executive.display_frame is not None:
                    cv2.imshow("Piper Native Vision Engine", executive.display_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                else:
                    time.sleep(0.01)
            else:
                time.sleep(0.5)
                
    except KeyboardInterrupt:
        print("\n[SYSTEM] Intercepted shutdown request flag.")
    finally:
        cv2.destroyAllWindows()
        executive.shutdown()
        print("[SYSTEM] Core platform execution loop safely terminated.")

if __name__ == "__main__":
    main()
