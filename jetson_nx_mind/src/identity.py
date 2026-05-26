# ==============================================================================
# Component:  jetson_nx_mind
# Module:     identity.py
# Version:    3.2.0 (Forced Bounding Box Profile Indexer)
# Purpose:    Facial recognition matching against local database matrices.
#             UPDATED: Robust fallback scanning to prevent index validation drops.
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
                    friendly_name = file.split('-')[0].strip()
                    
                    # Skip broken empty name registration files
                    if not friendly_name:
                        continue
                        
                    try:
                        image = face_recognition.load_image_file(path)
                        # Attempt standard detection first
                        encodings = face_recognition.face_encodings(image)
                        
                        # Fallback: If it misses, treat the entire image area as the face box
                        if len(encodings) == 0:
                            h, w, _ = image.shape
                            # format: (top, right, bottom, left)
                            entire_frame_box = (0, w, h, 0)
                            encodings = face_recognition.face_encodings(image, [entire_frame_box])

                        if len(encodings) > 0:
                            self.known_encodings.append(encodings[0])
                            self.known_names.append(friendly_name)
                            print(f"[IDENTITY] + Successfully indexed profile for '{friendly_name}'")
                        else:
                            print(f"[IDENTITY] ! Failed index validation: {path} (No face features extracted)")
                    except Exception as e:
                        print(f"[IDENTITY] ! Exception processing asset {path}: {e}")

        print(f"[IDENTITY] Verification layer online. Known profiles: {len(self.known_names)}")

    def identify(self, frame, face_location):
        """Compares a localized bounding box region against known encodings."""
        if not self.known_encodings:
            return "Unknown"

        try:
            # face_recognition spatial tracking format: (top, right, bottom, left)
            current_encoding = face_recognition.face_encodings(frame, [face_location])[0]
            results = face_recognition.compare_faces(self.known_encodings, current_encoding, tolerance=0.5)
            
            if True in results:
                first_match_index = results.index(True)
                return self.known_names[first_match_index]
        except Exception:
            pass
        
        return "Unknown"
