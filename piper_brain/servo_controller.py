# ==============================================================================
# Component: jetson_nx_mind
# Module: servo_controller.py
# Version: 1.0.0
# Author: Steve
# ==============================================================================

from adafruit_servokit import ServoKit

class ServoController:
    def __init__(self):
        print("Initializing PCA9685 on the I2C bus...")
        try:
            # Initialize the 16-channel PCA9685 board
            self.kit = ServoKit(channels=16)
        except Exception as e:
            print(f"\n[FATAL] I2C Initialization Failed: {e}")
            raise

        # Map the servos to the channels
        self.pan_servo = self.kit.servo[0]
        self.tilt_servo = self.kit.servo[1]

        # Set the operational pulse-width limits
        self.pan_servo.set_pulse_width_range(500, 2500)
        self.tilt_servo.set_pulse_width_range(500, 2500)

        self.current_pan = 90
        self.current_tilt = 70
        self.center()
        print("\n[SUCCESS] Servos initialized and centered.")

    def set_pan(self, angle):
        """Sets the pan angle (0-180 degrees)."""
        self.current_pan = max(0, min(180, angle))
        self.pan_servo.angle = self.current_pan

    def set_tilt(self, angle):
        """Sets the tilt angle (0-180 degrees) with inverted logic."""
        # Inverted logic: 0 is up, 180 is down as per servo_test.py
        self.current_tilt = max(0, min(180, angle))
        self.tilt_servo.angle = self.current_tilt

    def center(self):
        """Centers both pan and tilt servos to 90 degrees."""
        self.set_pan(90)
        self.set_tilt(70)

    def get_pan(self):
        """Returns the current pan angle."""
        return self.current_pan

    def get_tilt(self):
        """Returns the current tilt angle."""
        return self.current_tilt
