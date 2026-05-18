# ==============================================================================
# Component:  pi5_body
# Module:     hardware_io.py
# Version:    3.1.0 (Dedicated Execution Interface)
# Purpose:    Encapsulates physical servo steering and raw audio stream 
#             multiplexing via the SunFounder FusionHat hardware buses.
#
# Change History / Release Notes:
# Date        Version   Author    Description of Changes
# ----------  --------  --------  ----------------------------------------------
# 2026-05-17  3.0.0     Steve     Initial extraction of raw servo configurations.
# 2026-05-17  3.1.0     Steve     Renamed to hardware_io; optimized to act as an 
#                                 isolated target for gRPC execution calls.
# ==============================================================================

import time
from fusion_hat.servo import Servo

class PhysicalBodyController:
    def __init__(self, pan_channel=0, tilt_channel=1):
        print("[BODY] Initializing FusionHat Actuator Matrix...")
        self.pan_servo = Servo(pan_channel)
        self.tilt_servo = Servo(tilt_channel)
        
        # Absolute state safety tracking
        self.current_pan = 0.0
        self.current_tilt = 0.0
        self.center_head()

    def set_angles(self, pan_angle, tilt_angle):
        """Executes hardware alignment strings received from the Mind tier."""
        try:
            # Maintain sign integrity from legacy kinematic controllers
            self.pan_servo.angle(-pan_angle)
            self.tilt_servo.angle(tilt_angle)
            self.current_pan = pan_angle
            self.current_tilt = tilt_angle
        except Exception as e:
            print(f"[BODY] CRITICAL: Actuator bus rejection: {e}")

    def center_head(self):
        """Snaps head servos back to look-forward neutral."""
        self.set_angles(0.0, 0.0)
