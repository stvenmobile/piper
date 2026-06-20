# ==============================================================================
# Component:  jetson_nx_mind
# Module:     target_test.py
# Version:    2.5.0 (Proportional Actuation Centering — Native KVM Build)
# Purpose:    Standalone local diagnostic for Rubik's Cube isolation. 
#             Features a Proportional Gain controller to force physical 
#             servo centering based on visual pixel error metrics.
# ==============================================================================

import os
import sys
import time
import cv2
import numpy as np

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
sys.path.append(CURRENT_DIR)
sys.path.append(PARENT_DIR)

from perception import VisionEngine as Camera
from neck import NeckEngine

GREEN_LOWER = np.array([35, 60, 50])
GREEN_UPPER = np.array([85, 255, 255])
MIN_CONTOUR_AREA = 250  

def _find_green(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, GREEN_LOWER, GREEN_UPPER)

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best = None
    best_area = 0
    for c in contours:
        area = cv2.contourArea(c)
        if area > MIN_CONTOUR_AREA and area > best_area:
            x, y, w, h = cv2.boundingRect(c)
            best = (x + w // 2, y + h // 2, w, h)
            best_area = area

    if best is not None:
        cx, cy, w, h = best
        cv2.rectangle(frame, (cx - w // 2, cy - h // 2), (cx + w // 2, cy + h // 2), (0, 255, 0), 2)
        cv2.circle(frame, (cx, cy), 4, (0, 255, 0), -1)
        cv2.putText(frame, f"TARGET ({cx},{cy})", (cx + 12, cy - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
        return (cx, cy, w, h), frame, mask

    return None, frame, mask

def _draw_status(frame, phase, pan_angle, tilt_angle, elapsed, loop_count):
    lines = [
        f"Tracking Phase: {phase}",
        f"Pan Position:   {pan_angle:.1f} deg",
        f"Tilt Position:  {tilt_angle:.1f} deg",
        f"Runtime Sync:   {elapsed:.0f}s",
        f"Loop Index:     {loop_count}",
        "Press 'q' to exit window"
    ]
    for i, txt in enumerate(lines):
        y = 24 + i * 22
        cv2.putText(frame, txt, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

def main():
    print("[TARGET] ==============================================")
    print("[TARGET]   Piper — Proportional Target Tracking Engine ")
    print("[TARGET] ==============================================\n")

    cam = Camera()
    neck = NeckEngine()
    neck.startup()

    SEARCH_STEP_DEG = 2.0       
    SEARCH_INTERVAL = 0.1       
    PAN_MIN, PAN_MAX = 30, 150  
    TILT_WORKSPACE = 115.0             

    phase = "SEARCHING"
    pan_angle = 90.0
    pan_dir = 1
    start_ts = time.time()
    loop_count = 0
    last_search_time = time.time()

    # PROPORTIONAL GAIN COEFFICIENT:
    # If she centers too slowly, increase this to 0.15 or 0.2
    # If she overshoots and shakes back and forth, lower this to 0.05
    KP_GAIN = 0.10
    DEADZONE_PIXELS = 15  # Ignore errors smaller than this to avoid motor twitching

    neck.look_at(pan_angle, TILT_WORKSPACE)
    time.sleep(0.6)

    feed_window = "1. Camera Feed"
    mask_window = "2. Color Threshold Mask"
    cv2.namedWindow(feed_window, cv2.WINDOW_AUTOSIZE)
    cv2.namedWindow(mask_window, cv2.WINDOW_AUTOSIZE)

    try:
        while True:
            loop_count += 1
            now = time.time()

            ret, frame = cam.get_frame()
            if not ret:
                time.sleep(0.01)
                continue

            green_result, display, mask_layer = _find_green(frame)
            green_found = green_result is not None

            if green_found:
                phase = "LOCKED"
            else:
                phase = "SEARCHING"

            if loop_count % 30 == 0:
                print(f"[STATUS] Mode: {phase} | Green Target: {green_found} | Frame: {loop_count}")

            h, w = display.shape[:2]
            fc_x, fc_y = w // 2, h // 2

            if phase == "SEARCHING":
                if now - last_search_time > SEARCH_INTERVAL:
                    neck.look_at(pan_angle, TILT_WORKSPACE)
                    pan_angle += pan_dir * SEARCH_STEP_DEG
                    if pan_angle >= PAN_MAX: pan_angle = PAN_MAX; pan_dir = -1
                    elif pan_angle <= PAN_MIN: pan_angle = PAN_MIN; pan_dir = 1
                    last_search_time = now

            elif phase == "LOCKED" and green_found:
                # 1. Compute physical pixel distance errors from the center anchor
                error_x = green_result[0] - fc_x
                error_y = green_result[1] - fc_y
                
                # 2. Check if the object is outside the deadzone crosshair center to actuate
                if abs(error_x) > DEADZONE_PIXELS or abs(error_y) > DEADZONE_PIXELS:
                    # Pass the raw, unthrottled pixel deltas directly into your tracking hardware layer.
                    # If she jerks outward instead of inward, invert the signs:
                    # step_x = -1 * error_x
                    # step_y = -1 * error_y
                    step_x = error_x
                    step_y = error_y
                    
                    # 3. Fire command straight to I2C register hardware
                    neck.track_delta(step_x, step_y)

            _draw_status(display, phase, pan_angle, TILT_WORKSPACE, now - start_ts, loop_count)

            cv2.imshow(feed_window, display)
            cv2.imshow(mask_window, mask_layer)

            if cv2.waitKey(30) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\n[TARGET] Loop execution halted.")
    finally:
        cv2.destroyAllWindows()
        neck.home()
        time.sleep(0.5)
        neck.shutdown()
        cam.release()
        print("[TARGET] Disconnected local assets cleanly.")

if __name__ == "__main__":
    main()