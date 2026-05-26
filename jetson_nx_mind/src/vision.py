# ==============================================================================
# Component:  jetson_nx_mind
# Module:     vision.py
# Version:    2.1.0 (GPU-Accelerated YOLOv8 - Full Frame Enrollment Fix)
# Purpose:    Wraps perception.py hardware loops, computes dual-eye visibility,
#             and enforces real-time bounding box metrics for the executive.
#             UPDATED: Saves full frame context to ensure face_recognition indexes.
# ==============================================================================

import os
import cv2
import numpy as np
from perception import VisionEngine as NativeYOLOEngine
from identity import FaceManager

class VisionEngine:
    def __init__(self):
        self.registration_path = os.path.expanduser("~/piper/jetson_nx_mind/models/faces/")
        os.makedirs(self.registration_path, exist_ok=True)
        
        # Initialize your native, hardware-tuned YOLO engine and Face ID matcher
        self.yolo_driver = NativeYOLOEngine(model_path=os.path.expanduser('~/piper/jetson_nx_mind/models/yolov8n-face.pt'))
        self.identity_matcher = FaceManager(face_dir=self.registration_path)
        
        # Explicitly point to our local repository cascade models to prevent environment path drops
        models_base = os.path.expanduser("~/piper/jetson_nx_mind/models/")
        self.face_cascade = cv2.CascadeClassifier(os.path.join(models_base, 'haarcascade_frontalface_default.xml'))
        self.eye_cascade = cv2.CascadeClassifier(os.path.join(models_base, 'haarcascade_eye.xml'))

    def analyze_frame(self, frame):
        """Processes frame via GPU YOLOv8, runs symmetry checks, and returns tracking vectors."""
        # 1. Grab bounding box and normalized centers directly from your GPU YOLO pipeline
        bbox, center_coords = self.yolo_driver.detect_face(frame)
        
        if bbox is None:
            return "ALONE", None, None

        x1, y1, x2, y2 = bbox
        w, h = x2 - x1, y2 - y1
        
        # Isolate the facial Region of Interest (ROI)
        face_roi_color = frame[y1:y2, x1:x2]
        face_roi_gray = cv2.cvtColor(face_roi_color, cv2.COLOR_BGR2GRAY)

        # 2. Compute Centering Delta relative to your 640x480 frame space
        frame_center_x = frame.shape[1] // 2
        face_center_x = x1 + (w // 2)
        centering_delta = face_center_x - frame_center_x
        is_centered = abs(centering_delta) < 50  # Dynamic tracking lock threshold in pixels

        # 3. Enforce Dual-Eye Constraint inside the bounded face region
        eyes = self.eye_cascade.detectMultiScale(face_roi_gray, scaleFactor=1.1, minNeighbors=7)
        both_eyes_visible = len(eyes) >= 2

        metrics = {
            "box": (x1, y1, w, h),
            "is_centered": is_centered,
            "centering_delta": centering_delta,
            "both_eyes_visible": both_eyes_visible,
            "roi": face_roi_color,
            "full_frame": frame.copy() # THIS IS THE CRITICAL KEY NEEDED BY CORE_EXEC
        }

        # 4. Run Identity Verification via face_recognition matrix
        fr_location = (y1, x2, y2, x1)
        identity = self.identity_matcher.identify(frame, fr_location)

        if identity != "Unknown":
            return "ENGAGED", identity, metrics
        else:
            return "PERCEIVING_UNKNOWN", "Unknown", metrics

    def save_new_face(self, name, full_frame_image):
        """Commits the full frame array to disk to optimize frontal face recognition indexing."""
        # Sanitize string to clean up double utterances, trailing spaces, or invalid characters
        clean_name = name.lower().strip()
        clean_name = " ".join(clean_name.split()) 
        clean_name = clean_name.replace(" ", "_") 
        
        # Follow your structured identity naming requirement format: [name]-001.jpg
        filename = os.path.join(self.registration_path, f"{clean_name}-001.jpg")
        
        cv2.imwrite(filename, full_frame_image)
        print(f"[VISION] Enrolled new biometric profile matrix: {filename}")
        
        # Hot-reload the database so she knows them on the very next frame loop
        self.identity_matcher.load_faces()
        return filename
