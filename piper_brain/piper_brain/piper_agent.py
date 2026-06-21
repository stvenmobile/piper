# ==============================================================================
# Component:  jetson_nx_mind
# Module:     piper_agent.py
# Version:    5.1.0
# Purpose:    Core vision loop substrate executing on the Jetson node. Ingests
#             dual HTTP MJPEG streams served by the local Flask application,
#             processes YOLO tracking, and exposes a high-performance gRPC
#             SpatialMatrix streaming server over HTTP/2.
# ==============================================================================

import os
import sys
import time
import json
import threading
import cv2
import numpy as np
import requests
from datetime import datetime
from concurrent import futures
import grpc

# --- IMPORT AUTO-GENERATED GRPC STUBS ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import spatial_matrix_pb2
import spatial_matrix_pb2_grpc

# --- NETWORK STREAM CONFIGURATION ---
STREAM_URLS = {
    0: "http://192.168.1.60:5000/video_feed/0",
    1: "http://192.168.1.60:5000/video_feed/1"
}

# --- PATH RESOLUTION ALIGNED TO JETSON_NX_MIND TIER ---
ABS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MIND_ROOT = os.path.join(ABS_ROOT, "jetson_nx_mind")

PATHS = {
    "log": os.path.join(ABS_ROOT, "logs", "current_agent.log"),
    "yolo": os.path.join(MIND_ROOT, "models", "yolov8n-face.pt")
}

class VisionSharedState:
    def __init__(self):
        self.lock = threading.Lock()
        self.camera_frames = {0: b"", 1: b""}
        self.pan = 0.0
        self.tilt = -10.0
        self.active_id = "Unknown"
        self.is_thinking = False
        self.new_frame_event = threading.Event()

global_vision_state = VisionSharedState()

# --- GRPC SERVICER INFRASTRUCTURE LAYER ---
class SpatialMatrixServicer(spatial_matrix_pb2_grpc.SpatialMatrixServicer):
    def StreamVisionMatrix(self, request, context):
        print(f"[gRPC] Client '{request.client_id}' connected to visual matrix stream.")
        
        while context.is_active():
            # Wait for the next ingested frame across either camera channel
            if global_vision_state.new_frame_event.wait(timeout=1.0):
                global_vision_state.new_frame_event.clear()
                
                with global_vision_state.lock:
                    # Serve primary Camera 0 over the main pipeline block
                    jpeg_bytes = global_vision_state.camera_frames.get(0, b"")
                    if not jpeg_bytes:
                        continue
                        
                    yield spatial_matrix_pb2.VisionFrame(
                        timestamp=int(time.time() * 1000),
                        frame_bytes=jpeg_bytes,
                        current_pan=global_vision_state.pan,
                        current_tilt=global_vision_state.tilt,
                        active_id=global_vision_state.active_id,
                        is_thinking=global_vision_state.is_thinking
                    )
            time.sleep(0.01)

class PiperAgent:
    def __init__(self):
        os.makedirs(os.path.dirname(PATHS["log"]), exist_ok=True)
        self.log("SYSTEM", "Initializing Substrate Module (Network Stream Mode)...")
        
        try:
            from ultralytics import YOLO
            self.yolo_model = YOLO(PATHS["yolo"])
            self.log("SYSTEM", "YOLO Neural Engine loaded successfully.")
        except Exception as e:
            self.yolo_model = None
            self.log("WARNING", f"YOLO failed to load: {e}. Running blind.")

        self.running = True
        self.active_id = "Unknown"

    def log(self, context, message):
        t = datetime.now().strftime("%H:%M:%S")
        entry = f"[{t}] [{context}] {message}"
        print(entry)
        try:
            with open(PATHS["log"], "a") as f: 
                f.write(entry + "\n")
        except:
            pass

    def capture_network_stream(self, cam_id, url):
        """Robust MJPEG frame boundary accumulator for high-speed socket streams."""
        self.log("CAMERA", f"Spawning ingestion stream worker for Camera {cam_id} -> {url}")
        
        while self.running:
            try:
                # Request the raw byte stream from the Flask endpoint
                response = requests.get(url, stream=True, timeout=5)
                if response.status_code != 200:
                    self.log("CAMERA", f"Error connecting to Camera {cam_id} (Status: {response.status_code}). Retrying...")
                    time.sleep(2)
                    continue

                bytes_buffer = b""
                # Stream the chunks dynamically
                for chunk in response.iter_content(chunk_size=4096):
                    if not self.running: 
                        break
                    
                    bytes_buffer += chunk
                    
                    # Look for JPEG Start (0xFFD8) and End (0xFFD9) markers
                    while True:
                        start_idx = bytes_buffer.find(b'\xff\xd8')
                        end_idx = bytes_buffer.find(b'\xff\xd9')
                        
                        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                            # Extract complete frame bytes
                            jpg_bytes = bytes_buffer[start_idx:end_idx+2]
                            # Trim processed data out of buffer
                            bytes_buffer = bytes_buffer[end_idx+2:]
                            
                            # Convert to NumPy layout for CV2 processing
                            np_arr = np.frombuffer(jpg_bytes, dtype=np.uint8)
                            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                            
                            if frame is not None:
                                self.process_and_store_frame(cam_id, frame)
                        else:
                            break
                            
            except Exception as e:
                self.log("CAMERA", f"Connection lost on Camera {cam_id}: {e}. Reconnecting in 2s...")
                time.sleep(2)

    def process_and_store_frame(self, cam_id, frame):
        """Processes YOLO bounds on primary channel and packages bytes back to matrix memory map."""
        self.active_id = "Unknown"

        # Apply spatial model boundaries strictly to Camera 0 (Primary tracking eye)
        if cam_id == 0 and self.yolo_model:
            results = self.yolo_model(frame, conf=0.4, verbose=False)
            for r in results:
                boxes = r.boxes.xyxy.cpu().numpy()
                for b in boxes:
                    x1, y1, x2, y2 = map(int, b)
                    self.active_id = "steve"
                    # Render tracking boundary bounding boxes
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Re-encode to highly optimized compressed JPEG format
        ret, jpeg_buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if ret:
            jpeg_bytes = jpeg_buffer.tobytes()
            with global_vision_state.lock:
                global_vision_state.camera_frames[cam_id] = jpeg_bytes
                if cam_id == 0:
                    global_vision_state.active_id = self.active_id
            global_vision_state.new_frame_event.set()

    def run(self):
        # Fire up both background processing workers
        for cam_id, url in STREAM_URLS.items():
            t = threading.Thread(target=self.capture_network_stream, args=(cam_id, url), daemon=True)
            t.start()

        # Build and configure the local HTTP/2 high-speed gRPC server framework
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
        spatial_matrix_pb2_grpc.add_SpatialMatrixServicer_to_server(SpatialMatrixServicer(), server)
        server.add_insecure_port('[::]:50051')
        server.start()
        
        self.log("SYSTEM", "gRPC Spatial Matrix network intake service active on port 50051.")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            server.stop(0)
            self.log("SYSTEM", "Substrate closed gracefully.")

if __name__ == "__main__":
    agent = PiperAgent()
    agent.run()