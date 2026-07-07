#!/usr/bin/env python3
import cv2
import threading
import time

class ResilientTestStream:
    def __init__(self, index=1):
        self.index = index
        # Open with the explicit V4L2 backend
        self.cap = cv2.VideoCapture(self.index, cv2.CAP_V4L2)
        
        # Match Piper's low-latency stream baseline setup
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'YUYV'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        self.grabbed = False
        self.frame = None
        self.running = False
        self.lock = threading.Lock()

        if self.cap.isOpened():
            self.grabbed, self.frame = self.cap.read()
            print(f"✔️ Connected to Index {self.index} successfully.")
        else:
            print(f"❌ Failed to open Index {self.index}.")

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._update, args=())
        self.thread.daemon = True
        self.thread.start()
        return self

    def _update(self):
        # Dedicated background thread keeping the kernel buffer completely clear
        while self.running:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.001)
                continue
            
            with self.lock:
                self.grabbed = ret
                self.frame = frame

    def read(self):
        with self.lock:
            if self.frame is None:
                return False, None
            return self.grabbed, self.frame.copy()

    def stop(self):
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=1.0)
        self.cap.release()


def main():
    print("==========================================")
    print("Starting Multi-Threaded Video Stream Test")
    print("==========================================")
    
    # Target our verified master index
    stream = ResilientTestStream(index=1)
    
    if not stream.grabbed:
        print("Could not initialize video acquisition pipeline. Exiting.")
        return

    print("Launching background thread... displaying window.")
    print("-> Press 'q' inside the video window to stop.")
    stream.start()
    
    time.sleep(0.5)  # Let the stream warm up and stabilize

    while True:
        success, img = stream.read()
        if not success or img is None:
            # If the background thread is working, this won't stall the system
            print("Waiting for fresh thread frame buffer...")
            time.sleep(0.033)
            continue

        # Draw to the screen
        cv2.imshow(f"Live Feed - Index 1", img)
        
        # Break if user hits 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Stopping stream test via user request.")
            break

    stream.stop()
    cv2.destroyAllWindows()
    print("Test pipeline cleanly torn down.")

if __name__ == "__main__":
    main()
