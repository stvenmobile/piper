# ==============================================================================
# Component:  jetson_nx_mind
# Module:     neck.py
# Version:    1.0.0 (Native I2C Proportional Smoothing)
# Purpose:    Handles PCA9685 pan/tilt servos. Implements asynchronous
#             proportional easing to smoothly decelerate into target angles.
# ==============================================================================

import time
import threading
from adafruit_servokit import ServoKit

class NeckEngine:
    def __init__(self):
        print("[NECK] Initializing PCA9685 I2C Servo Controller...")
        try:
            self.kit = ServoKit(channels=16)
        except Exception as e:
            print(f"[FATAL] I2C Initialization Failed: {e}")
            raise

        self.pan_servo = self.kit.servo[0]
        self.tilt_servo = self.kit.servo[1]

        # Standard pulse width limits
        self.pan_servo.set_pulse_width_range(500, 2500)
        self.tilt_servo.set_pulse_width_range(500, 2500)

        # Hardware limits based on your 3D printed chassis
        self.PAN_MIN, self.PAN_MAX = 0, 180
        self.TILT_MIN, self.TILT_MAX = 0, 120  # 0 is straight UP, 120 is max DOWN limit

        # State tracking
        self.current_pan = 90.0
        self.current_tilt = 70.0
        self.target_pan = 90.0
        self.target_tilt = 70.0

        self.stop_signal = threading.Event()
        self.thread = threading.Thread(target=self._easing_loop, daemon=True)

    def startup(self):
        """Snaps to home position and starts the smoothing loop."""
        self.pan_servo.angle = self.current_pan
        self.tilt_servo.angle = self.current_tilt
        self.thread.start()
        print("[NECK] Hardware tracking loop online.")

    def look_at(self, pan_angle, tilt_angle):
        """Sets the new target coordinate. The easing loop will organically move here."""
        self.target_pan = max(self.PAN_MIN, min(self.PAN_MAX, pan_angle))
        self.target_tilt = max(self.TILT_MIN, min(self.TILT_MAX, tilt_angle))

    def track_delta(self, delta_x, delta_y):
        """Adjusts current target based on pixel offsets, with a deadzone to prevent hunting."""
        # Gain controls how aggressively the head chases the face. 
        PAN_GAIN = 0.04   # Slightly lowered to smooth out the approach
        TILT_GAIN = 0.04

        # DEADZONE: The "good enough" pixel radius. 
        # If the face is within this many pixels of center, don't move the servos.
        DEADZONE = 25  

        new_pan = self.target_pan
        new_tilt = self.target_tilt

        # Only calculate a new angle if the face is outside the deadzone
        if abs(delta_x) > DEADZONE:
            new_pan = self.target_pan - (delta_x * PAN_GAIN)
            
        if abs(delta_y) > DEADZONE:
            new_tilt = self.target_tilt + (delta_y * TILT_GAIN) 
            
        self.look_at(new_pan, new_tilt)


    def home(self):
        """Commands the head to return to true center."""
        self.look_at(90, 90)

    def _easing_loop(self):
        """Runs at 50Hz. Moves current angle 15% closer to target angle every tick."""
        EASING_FACTOR = 0.15  
        
        while not self.stop_signal.is_set():
            # If we are close enough to the target, stop doing micro-math to prevent servo hum
            if abs(self.target_pan - self.current_pan) > 0.5:
                self.current_pan += (self.target_pan - self.current_pan) * EASING_FACTOR
                self.pan_servo.angle = self.current_pan
                
            if abs(self.target_tilt - self.current_tilt) > 0.5:
                self.current_tilt += (self.target_tilt - self.current_tilt) * EASING_FACTOR
                self.tilt_servo.angle = self.current_tilt
                
            time.sleep(0.02)

    def shutdown(self):
        self.stop_signal.set()
        self.thread.join(timeout=1.0)
        print("[NECK] Servo smoothing loop terminated.")
