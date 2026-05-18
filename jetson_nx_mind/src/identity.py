# ==============================================================================
# Component:  jetson_nx_mind
# Module:     identity.py
# Version:    3.1.0 (Zero-Copy Local Inference)
# Purpose:    Facial recognition matching against local database matrices.
#
# Change History / Release Notes:
# Date        Version   Author    Description of Changes
# ----------  --------  --------  ----------------------------------------------
# 2026-05-17  3.0.0     Steve     Updated face directory paths for revamp.
# 2026-05-17  3.1.0     Steve     Confirmed local-memory compatibility for 
#                                 zero-copy frame sharing with VisionEngine.
# ==============================================================================

import face_recognition
import os
import cv2
import logging

class FaceManager:
    def __init__(self, face_dir='../models/faces'):
        self.face_dir = face_dir
        self.known_encodings = []
        self.known_names = []
        self.logger = logging.getLogger()
        self.load_faces()

    def load_faces(self):
        """Scans relative storage directories to build known face encodings."""
        self.known_encodings = []
        self.known_names = []
        
        if not os.path.exists(self.face_dir):
            print(f"[IDENTITY] WARNING: Database path not found: {self.face_dir}")
            return

        print(f"[IDENTITY] Scanning {self.face_dir} for structured assets...")

        for root, dirs, files in os.walk(self.face_dir):
            for file in files:
                if file.lower().endswith(".jpg") and "-001" in file:
                    path = os.path.join(root, file)
                    try:
                        image = face_recognition.load_image_file(path)
                        encodings = face_recognition.face_encodings(image)
                        
                        if len(encodings) > 0:
                            self.known_encodings.append(encodings[0])
                            friendly_name = file.split('-')[0]
                            self.known_names.append(friendly_name)
                            print(f"[IDENTITY] + Loaded reference for '{friendly_name}'")
                        else:
                            print(f"[IDENTITY] ! Failed index validation: {path}")
                    except Exception as e:
                        print(f"[IDENTITY] ! Exception processing asset {path}: {e}")

        print(f"[IDENTITY] Verification layer online. Known profiles: {len(self.known_names)}")

    def identify(self, frame, face_location):
        """Compares a localized bounding box region against known encodings."""
        if not self.known_encodings:
            return "Unknown"

        # face_recognition spatial tracking format: (top, right, bottom, left)
        current_encoding = face_recognition.face_encodings(frame, [face_location])[0]
        results = face_recognition.compare_faces(self.known_encodings, current_encoding, tolerance=0.5)
        
        if True in results:
            first_match_index = results.index(True)
            return self.known_names[first_match_index]
        
        return "Unknown"
