# ==============================================================================
# Component:  jetson_nx_mind
# Module:     spatial_mapping.py
# Version:    3.0.0 (Relative Perturbation Starburst Build)
# Purpose:    Automated relative spatial mapping routine. Locks onto a static
#             workspace target and executes non-linear perturbation vectors 
#             to cleanly map motor deltas to true pixel displacements.
#
# Change History / Release Notes:
# Date        Version   Author    Description of Changes
# ----------  --------  --------  ----------------------------------------------
# 2026-05-30  3.0.0     Steve     Replaced absolute grid sweep with relative 
#                                 perturbation starburst logic to prevent target loss.
# ==============================================================================

import os
import sys
import time
import sqlite3
import cv2
import numpy as np

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
sys.path.append(CURRENT_DIR)
sys.path.append(PARENT_DIR)

from perception import VisionEngine as Camera
from neck import NeckEngine

# Color tracking configurations (Green workspace target)
GREEN_LOWER = np.array([35, 60, 50])
GREEN_UPPER = np.array([85, 255, 255])
MIN_CONTOUR_AREA = 250

FRAME_W, FRAME_H = 640, 480
DEADZONE_PIXELS = 25
SETTLE_SECONDS = 1.2
TARGET_ROWS = 100
DB_PATH = os.path.join(PARENT_DIR, "world_state.db")

# ==============================================================================
# CRITICAL PHYSICAL HARDWARE BOUNDARIES (Verified via servo_test.py)
# ==============================================================================
DEFAULT_PAN = 90.0
DEFAULT_TILT = 90.0   # True mechanical center

PAN_LEFT_MAX = 180.0  # Pan Left
PAN_RIGHT_MAX = 0.0   # Pan Right

TILT_UP_MAX = 30.0    # Safe look-up margin (0 is straight up)
TILT_DOWN_MAX = 105.0 # Bounded to 105 to safely avoid hitting the bracket at 120
# ==============================================================================


def _find_green(frame):
    """Parses incoming frames via HSV thresholding to find the target centroid."""
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
            best = (x + w // 2, y + h // 2)
            best_area = area
    return best


def _init_database():
    """Establishes sqlite3 framework for mapping telemetry data storage."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS spatial_vectors (
            test_id             INTEGER PRIMARY KEY,
            timestamp           TEXT,
            heading             TEXT,
            motor_pan_start     REAL,
            motor_tilt_start    REAL,
            pixel_x_start       INTEGER,
            pixel_y_start       INTEGER,
            motor_pan_displaced REAL,
            motor_tilt_displaced REAL,
            pixel_x_displaced   INTEGER,
            pixel_y_displaced   INTEGER,
            motor_delta_pan     REAL,
            motor_delta_tilt    REAL,
            pixel_delta_x       INTEGER,
            pixel_delta_y       INTEGER
        )
    ''')
    conn.commit()
    return conn


def _center_target(cam, neck, max_iterations=300):
    """Proportional feedback alignment tracking loop to lock target on frame center."""
    for _ in range(max_iterations):
        ret, frame = cam.get_frame()
        if not ret:
            time.sleep(0.01)
            continue
        target = _find_green(frame)
        if target is None:
            return False
        error_x = target[0] - FRAME_W // 2
        error_y = target[1] - FRAME_H // 2
        if abs(error_x) <= DEADZONE_PIXELS and abs(error_y) <= DEADZONE_PIXELS:
            return True
        neck.track_delta(error_x, error_y)
        time.sleep(0.05)
    return False


def _search_and_center(cam, neck):
    """Parent state machine handling automated environment target lock acquisitions."""
    for _ in range(20):
        ret, frame = cam.get_frame()
        if not ret:
            continue
        if _find_green(frame) is not None:
            return _center_target(cam, neck)
        time.sleep(0.05)
    
    # Simple fallback: return to verified physical home and check
    neck.look_at(DEFAULT_PAN, DEFAULT_TILT)
    time.sleep(1.0)
    return _center_target(cam, neck)


def _capture_fresh_frame(cam):
    """Flushes out V4L2 queue buffers to yield non-stale environment frame data."""
    for _ in range(3):
        ret, frame = cam.get_frame()
        if ret:
            return frame
        time.sleep(0.02)
    return None


def main():
    print("[SPATIAL] ==============================================")
    print("[SPATIAL]    Piper — Relative Perturbation Mapping     ")
    print("[SPATIAL] ==============================================\n")

    cam = Camera()
    neck = NeckEngine()
    neck.startup()
    
    print(f"[SPATIAL] Initializing hardware to verified center ({DEFAULT_PAN}, {DEFAULT_TILT})...")
    neck.look_at(DEFAULT_PAN, DEFAULT_TILT)
    time.sleep(1.5)

    conn = _init_database()

    print("[SPATIAL] Searching for green target on workspace mat...")
    if not _search_and_center(cam, neck):
        print("[SPATIAL] FATAL: Could not locate green target at center. Aborting.")
        neck.look_at(DEFAULT_PAN, DEFAULT_TILT)
        time.sleep(0.5)
        neck.shutdown()
        cam.release()
        conn.close()
        return

    print("[SPATIAL] Target acquired. Initializing Relative Perturbation Matrix...\n")

    rows_committed = 0
    
    # Distinct starburst vectors (Pan Delta, Tilt Delta) designed to map all quadrants
    TEST_PERTURBATIONS = [
        # Bounded Cardinal Adjustments (Pan, Tilt)
        (+15.0,   0.0), (-15.0,   0.0), (  0.0, +10.0), (  0.0, -10.0),
        (+30.0,   0.0), (-30.0,   0.0), (  0.0, +20.0), (  0.0, -20.0),
        # Intercardinal Diagonal Quadrants
        (+15.0, +10.0), (-15.0, +10.0), (+15.0, -10.0), (-15.0, -10.0),
        (+30.0, +15.0), (-30.0, +15.0), (+30.0, -15.0), (-30.0, -15.0),
        # Fine-grain precision adjustments
        ( +8.0,   0.0), ( -8.0,   0.0), (  0.0,  +6.0), (  0.0,  -6.0),
        ( +8.0,  +6.0), ( -8.0,  +6.0), ( +8.0,  -6.0), ( -8.0,  -6.0),
    ]

    # Keep looping through the vector array combinations until we hit 100 rows
    while rows_committed < TARGET_ROWS:
        for delta_pan, delta_tilt in TEST_PERTURBATIONS:
            if rows_committed >= TARGET_ROWS:
                break
                
            # Step 1: Ensure we are explicitly locked and centered on the physical cube
            if not _search_and_center(cam, neck):
                print("[SPATIAL] Target drifted. Executing recovery center snap...")
                neck.look_at(DEFAULT_PAN, DEFAULT_TILT)
                time.sleep(1.0)
                if not _search_and_center(cam, neck):
                    print("[SPATIAL] Target completely lost. Skipping sequence branch.")
                    continue
            
            # Capture starting state baseline references
            motor_pan_start = neck.current_pan
            motor_tilt_start = neck.current_tilt
            
            start_frame = _capture_fresh_frame(cam)
            start_target = _find_green(start_frame) if start_frame is not None else None
            if start_target is None:
                continue
            pixel_x_start, pixel_y_start = int(start_target[0]), int(start_target[1])
            
            # Step 2: Compute absolute destination vectors
            target_pan = motor_pan_start + delta_pan
            target_tilt = motor_tilt_start + delta_tilt
            
            # Hard physical boundary constraint guardrails
            if not (PAN_RIGHT_MAX <= target_pan <= PAN_LEFT_MAX and TILT_UP_MAX <= target_tilt <= TILT_DOWN_MAX):
                continue # Safely skip adjustments that would impact structural brackets
                
            # Step 3: Pivot camera to target perturbation coordinate
            neck.look_at(target_pan, target_tilt)
            time.sleep(SETTLE_SECONDS)
            
            # Capture post-displacement tracking metrics
            displaced_frame = _capture_fresh_frame(cam)
            displaced_target = _find_green(displaced_frame) if displaced_frame is not None else None
            
            # If the offset throws the target out of view, reject the reading and reset cleanly
            if displaced_target is None:
                continue
                
            motor_pan_displaced = neck.current_pan
            motor_tilt_displaced = neck.current_tilt
            pixel_x_displaced = int(displaced_target[0])
            pixel_y_displaced = int(displaced_target[1])

            # Calculate actual mechanical and optical deltas
            motor_delta_pan = round(motor_pan_displaced - motor_pan_start, 4)
            motor_delta_tilt = round(motor_tilt_displaced - motor_tilt_start, 4)
            pixel_delta_x = pixel_x_displaced - pixel_x_start
            pixel_delta_y = pixel_y_displaced - pixel_y_start

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Execute database commit using exact column balances
            conn.execute('''
                INSERT INTO spatial_vectors (
                    timestamp, heading,
                    motor_pan_start, motor_tilt_start,
                    pixel_x_start, pixel_y_start,
                    motor_pan_displaced, motor_tilt_displaced,
                    pixel_x_displaced, pixel_y_displaced,
                    motor_delta_pan, motor_delta_tilt,
                    pixel_delta_x, pixel_delta_y
                ) VALUES (?, 'PERTURB', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp,
                motor_pan_start, motor_tilt_start,
                pixel_x_start, pixel_y_start,
                motor_pan_displaced, motor_tilt_displaced,
                pixel_x_displaced, pixel_y_displaced,
                motor_delta_pan, motor_delta_tilt,
                pixel_delta_x, pixel_delta_y
            ))
            conn.commit()

            print(f"[SPATIAL] Pre-Commit -> M_Start:({motor_pan_start:.1f},{motor_tilt_start:.1f}) | Offset:({delta_pan:+.1f},{delta_tilt:+.1f}) | ΔPx:({pixel_delta_x:+4d},{pixel_delta_y:+4d})")

            rows_committed += 1
            print(f"[SPATIAL] Row {rows_committed:3d}/100 | M({target_pan:5.1f},{target_tilt:5.1f}) | ΔM({motor_delta_pan:+6.2f},{motor_delta_tilt:+6.2f}) ΔPx({pixel_delta_x:+4d},{pixel_delta_y:+4d})")

        if rows_committed < TARGET_ROWS:
            time.sleep(0.2)

    print(f"\n[SPATIAL] Mapping complete. {rows_committed}/{TARGET_ROWS} high-integrity rows committed to {DB_PATH}")

    conn.close()
    neck.look_at(DEFAULT_PAN, DEFAULT_TILT)
    time.sleep(0.5)
    neck.shutdown()
    cam.release()
    print("[SPATIAL] All hardware assets released clean.")


if __name__ == "__main__":
    main()