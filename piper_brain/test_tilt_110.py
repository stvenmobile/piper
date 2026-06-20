#!/home/steve/piper/venv/bin/python3
# ==============================================================================
# Component: jetson_nx_mind
# Module: test_tilt_110.py
# Description: Moves the tilt servo to 110 degrees to test vertical range.
# ==============================================================================

import time
import sys
import os

# Add the path to find servo_controller
sys.path.append('/home/steve/.hermes/camera_stream')

try:
    from servo_controller import ServoController
except ImportError:
    print("Error: Could not import ServoController. Make sure it's in the python path.")
    sys.exit(1)

def test_tilt_110():
    print("Initializing ServoController...")
    servo_controller = ServoController()
    
    print("Moving tilt to 110 degrees...")
    # Inverted logic in ServoController: 0 is up, 180 is down
    servo_controller.set_tilt(110)
    time.sleep(1) # Give it time to reach the position
    print("Tilt moved to 110 degrees.")

if __name__ == '__main__':
    test_tilt_110()
