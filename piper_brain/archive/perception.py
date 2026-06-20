# ==============================================================================
# Component:  jetson_nx_mind
# Module:     perception.py
# Version:    3.1.0 (Native Camera Direct-Capture)
# Purpose:    Hardware-accelerated local camera capture, frame enhancement, 
#             and YOLOv8-based face detection running directly on the Jetson GPU.
#
# Change History / Release Notes:
# Date        Version   Author    Description of Changes
# ----------  --------  --------  ----------------------------------------------
# 2026-05-17  3.0.0     Steve     Decoupled from local capture for streaming.
# 2026-05-17  3.1.0     Steve     Reverted to Native Capture. Re-implemented 
#                                 direct V4L2 hardware tuning for low-latency.
# ==============================================================================

import cv2
import os
import numpy as np

class VisionEngine:
    def __init__(self, model_path='../models/yolov8n-face.pt'):
        # Force Ultralytics to utilize the Jetson Orin NX Ampere GPU
        os.environ["CUDA_VISIBLE_DEVICES"] = "0"
        from ultralytics import YOLO
        self.model = YOLO(model_path)
        
        # Native V4L2 Video Capture directly on Jetson USB 3.0 Bus
        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Restored Legacy Hardware Tuning Parameters
        self.cap.set(cv2.CAP_PROP_BRIGHTNESS, 200) 
        self.cap.set(cv2.CAP_PROP_CONTRAST, 100)
        self.cap.set(cv2.CAP_PROP_SHARPNESS, 120)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Software Enhancement Tools
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        print("[VISION] YOLO Engine Online (Native GPU Direct-Capture Mode).")

    def get_frame(self):
        """Captures a native frame and applies sharpness and contrast filters."""
        ret, frame = self.cap.read()
        if ret:
            # Enhanced Contrast via CLAHE
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            l = self.clahe.apply(l)
            lab = cv2.merge((l, a, b))
            frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            
            # Unsharp Mask to strip out edge fuzziness
            gaussian = cv2.GaussianBlur(frame, (0, 0), 2.0)
            frame = cv2.addWeighted(frame, 1.5, gaussian, -0.5, 0)
            
        return ret, frame

    def detect_face(self, frame):
        """Runs YOLOv8 face detection on the local memory matrix."""
        results = self.model(frame, conf=0.5, verbose=False)
        for r in results:
            if len(r.boxes) > 0:
                b = r.boxes[0].xyxy[0].cpu().numpy().astype(int)
                # Normalize tracking coordinates based on local 640x480 geometry
                center_x = (b[0] + b[2]) / 2 / 640
                center_y = (b[1] + b[3]) / 2 / 480
                return b, (center_x, center_y)
        return None, None

    def release(self):
        """Gracefully tears down the local hardware V4L2 channel."""
        self.cap.release()
