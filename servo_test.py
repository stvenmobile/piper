# ==============================================================================
# Script: servo_test.py
# Purpose: Diagnostic step-calibration for PCA9685 Pan/Tilt mechanism.
#          (Updated: Inverted Tilt Axis)
# ==============================================================================

import time
from adafruit_servokit import ServoKit

print("Initializing PCA9685 on the I2C bus...")

try:
    # Initialize the 16-channel PCA9685 board
    kit = ServoKit(channels=16)
except Exception as e:
    print(f"\n[FATAL] I2C Initialization Failed: {e}")
    exit(1)

# Map the servos to the channels
pan_servo = kit.servo[0]
tilt_servo = kit.servo[1]

# Set the operational pulse-width limits 
pan_servo.set_pulse_width_range(500, 2500)
tilt_servo.set_pulse_width_range(500, 2500)

print("\n[SUCCESS] Servos linked. Moving to home positions...")

# Initialize to absolute center coordinate
current_pan = 90
current_tilt = 90

pan_servo.angle = current_pan
tilt_servo.angle = current_tilt

print("=====================================================")
print("  PIPER PAN/TILT MANUAL OVERRIDE  ")
print("  Type a letter and press ENTER to move 10 degrees:")
print("    w : Tilt UP")
print("    s : Tilt DOWN")
print("    a : Pan LEFT")
print("    d : Pan RIGHT")
print("    c : Center Head (90, 90)")
print("    q : Quit")
print("=====================================================\n")

try:
    while True:
        cmd = input(f"[Pan: {current_pan:03d}° | Tilt: {current_tilt:03d}°] Command: ").strip().lower()
        
        if cmd == 'q':
            print("Exiting calibration. Returning to home (90, 90)...")
            pan_servo.angle = 90
            tilt_servo.angle = 90
            time.sleep(1)
            break
            
        elif cmd == 'w':
            # Inverted: Subtracting degrees to tilt UP
            current_tilt = max(0, current_tilt - 10)
        elif cmd == 's':
            # Inverted: Adding degrees to tilt DOWN
            current_tilt = min(180, current_tilt + 10)
        elif cmd == 'a':
            current_pan = min(180, current_pan + 10)
        elif cmd == 'd':
            current_pan = max(0, current_pan - 10)
        elif cmd == 'c':
            current_pan = 90
            current_tilt = 90
        else:
            print("Invalid command.")
            continue
            
        # Execute the combined movement
        pan_servo.angle = current_pan
        tilt_servo.angle = current_tilt

except KeyboardInterrupt:
    print("\nCalibration forcefully terminated.")
