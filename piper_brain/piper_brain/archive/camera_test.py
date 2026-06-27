# ==============================================================================
# Component:  jetson_nx_mind (Diagnostic Utilities)
# Module:     camera_test.py
# Version:    3.6.0 (Hardware Accelerated Orientation & Contrast Tuning)
# Purpose:    Hardware validation utility. Hooks into dual CSI camera buses 
#             simultaneously via GStreamer, applies hardware-level 180 flips,
#             and injects manual contrast/gamma tuning parameters.
# ==============================================================================

import cv2
import sys
import time
import numpy as np

def get_jetson_gstreamer_source(sensor_id, width=640, height=480, framerate=30):
    """Generates an accelerated hardware-level string to capture, flip, and tune

    CSI color matrices natively via the Jetson ISP.
    """
    # --------------------------------------------------------------------------
    # JETSON ISP TUNING PARAMETERS (Adjust to change image presentation)
    # flip-method=2 : Executes a hardware-level 180-degree rotation (Flip both H and V)
    # ispdigitalgainrange : Clamps digital gain matrices to boost mid-tone details
    # exposuretimerange : Manually optimizes saturation thresholds
    # ee-mode/ee-strength : Controls edge enhancement sharpening matrices
    # --------------------------------------------------------------------------
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} "
        f"ispdigitalgainrange=\"1.5 1.5\" " # Hard-inject contrast floor boost
        f"ee-mode=1 ee-strength=1.0 ! "    # Inject hardware edge sharpening
        f"video/x-raw(memory:NVMM), width=(int)1280, height=(int)720, format=(string)NV12, framerate=(fraction){framerate}/1 ! "
        f"nvvidconv flip-method=2 ! "      # 180-degree physical rotation
        f"video/x-raw, width=(int){width}, height=(int){height}, format=(string)BGRx ! "
        f"videoconvert ! "
        f"video/x-raw, format=(string)BGR ! appsink drop=true sync=false"
    )

def run_comparison():
    print("====================================================")
    print("   TUNED & ALIGNED DUAL CSI BENCHMARKING TOOL       ")
    print("====================================================")
    print("[INIT] Spawning flipped, high-contrast GStreamer lanes...")

    gst_str_left = get_jetson_gstreamer_source(sensor_id=0, width=640, height=480)
    gst_str_right = get_jetson_gstreamer_source(sensor_id=1, width=640, height=480)

    cap0 = cv2.VideoCapture(gst_str_left, cv2.CAP_GSTREAMER)
    cap1 = cv2.VideoCapture(gst_str_right, cv2.CAP_GSTREAMER)

    if not cap0.isOpened() or not cap1.isOpened():
        print("[CRITICAL] Failed to open tuned accelerated pipelines. Aborting.")
        cap0.release()
        cap1.release()
        sys.exit(1)

    print("\n[SUCCESS] Both CSI tuned pipelines online!")
    print("[BENCHMARK] Orientation corrected. Gamma adjustment applied.")
    print("            -> Press 'q' inside the preview screen to close.")
    time.sleep(1.0)

    try:
        while True:
            ret0, frame0 = cap0.read()
            ret1, frame1 = cap1.read()

            if not ret0 or not ret1:
                continue

            # Apply a localized, safe fallback software gamma/contrast multiplier 
            # if the hardware ISP locks aren't fully capturing your room's shadows:
            # Formula: New_Frame = Frame * Alpha (Contrast) + Beta (Brightness)
            frame0 = cv2.convertScaleAbs(frame0, alpha=1.2, beta=5)
            frame1 = cv2.convertScaleAbs(frame1, alpha=1.2, beta=5)

            # Label the individual streams inside the frame arrays
            cv2.putText(frame0, "LEFT PORT (/dev/video0)", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(frame1, "RIGHT PORT (/dev/video1)", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)

            # STEREOSCOPIC STITCH
            side_by_side_frame = np.hstack((frame0, frame1))

            # Push the stitched composition down to the window manager loop
            cv2.imshow("Piper Dual-Eye Stereo Benchmark View", side_by_side_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\n[BENCHMARK] Execution manually interrupted.")
    finally:
        cap0.release()
        cap1.release()
        cv2.destroyAllWindows()
        print("[BENCHMARK] Pipelines cleared cleanly.")

if __name__ == "__main__":
    run_comparison()
