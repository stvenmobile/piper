# ==============================================================================
# Component:  jetson_nx_mind
# Module:     vision.py
# Version:    1.0.0 (Biometric Facial Ingestion Engine)
# Purpose:    Processes local V4L2 camera arrays, calculates dual-eye horizontal
#             symmetry thresholds, and passes profile metrics to core execution.
# ==============================================================================

import os
import cv2
import numpy as np

class VisionEngine:
    def __init__(self):
        self.registration_path = os.path.expanduser("~/piper/jetson_nx_mind/models/faces/")
        os.makedirs(self.registration_path, exist_ok=True)
        
        # Load local Haar Cascades for rapid landmark estimation on CPU/GPU
        # (Can scale up to full MediaPipe FaceMesh / YOLOv8-Face as footprint expands)
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

    def analyze_frame(self, frame):
        """Scans frame for humans, checks centering, and validates dual-eye visibility."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))
        
        if len(faces) == 0:
            return "ALONE", None, None

        # Focus on the primary foreground face bounding box
        (x, y, w, h) = faces[0]
        face_roi_gray = gray[y:y+h, x:x+w]
        face_roi_color = frame[y:y+h, x:x+w]
        
        # Calculate bounding box midpoint deviation relative to camera center axis
        frame_center_x = frame.shape[1] // 2
        face_center_x = x + (w // 2)
        centering_delta = face_center_x - frame_center_x

        # Detect internal landmarks (eyes) inside the face region of interest
        eyes = self.eye_cascade.detectMultiScale(face_roi_gray, scaleFactor=1.1, minNeighbors=10)
        
        # Check explicit eye counting constraint
        both_eyes_visible = len(eyes) >= 2
        
        # Determine tracking orientation status
        is_centered = abs(centering_delta) < 40  # Threshold pixels from true center
        
        metrics = {
            "box": (x, y, w, h),
            "is_centered": is_centered,
            "centering_delta": centering_delta,
            "both_eyes_visible": both_eyes_visible,
            "roi": face_roi_color
        }

        # Placeholder matching check - for now, check against registered file matrices
        # If directory is empty, treat the user as unindexed
        known_profiles = [f for f in os.listdir(self.registration_path) if f.endswith('.jpg')]
        
        if len(known_profiles) > 0:
            # Simple simulation placeholder until deep FaceID vector maps are compiled next phase
            identity = known_profiles[0].split('.')[0]
            return "ENGAGED", identity, metrics
        else:
            return "PERCEIVING_UNKNOWN", "Unknown", metrics

    def save_new_face(self, name, roi_image):
        """Commits the verified frontal frame matrix snapshot to local disk storage."""
        filename = os.path.join(self.registration_path, f"{name.lower().strip()}.jpg")
        cv2.imwrite(filename, roi_image)
        print(f"[VISION] Successfully enrolled biometric profile: {filename}")
        return filename
