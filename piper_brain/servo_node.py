#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Vector3
import time

# Import your working legacy hardware controller class
from piper_brain.servo_controller import ServoController


class PiperServoNode(Node):

    def __init__(self):
        super().__init__('piper_servo_node')
        self.get_logger().info("Initializing Smooth Piper Servo Actuator Node...")

        # Initialize physical hardware
        self.servo = ServoController()

        # Target tracking states (Where we WANT to be)
        self.target_pan = 90.0
        self.target_tilt = 70.0

        # Current actual states (Where we ARE right now)
        self.current_pan = 90.0
        self.current_tilt = 70.0

        # Easing factor (Lower = smoother/slower, Higher = snappier). Range: 0.01 to 1.0
        self.easing_factor = 0.02 

        # Run startup validation sweep sequence
        self._perform_startup_sweep()

        # Subscribe to target positions (X=Pan, Y=Tilt)
        self.subscription = self.create_subscription(
            Vector3,
            '/piper/neck/set_position',
            self._servo_callback,
            10)
        
        # High-frequency hardware update timer (50Hz = every 0.02 seconds)
        self.timer_period = 0.02
        self.timer = self.create_timer(self.timer_period, self._update_interpolation_loop)

        self.get_logger().info("Smooth Servo Node listening on /piper/neck/set_position")

    def _perform_startup_sweep(self):
        self.get_logger().info("Executing hardware validation sweep...")
        self.servo.center()
        time.sleep(0.5)
        
        try:
            self.servo.set_pan(45)
            time.sleep(0.5)
            self.servo.set_pan(135)
            time.sleep(0.5)
        except AttributeError:
            self.get_logger().warn("set_pan/set_tilt signatures differ. Defaulting to standard centering.")
            
        self.servo.center()
        self.get_logger().info("Hardware sweep complete. Servos centered.")

    def _servo_callback(self, msg):
        self.target_pan = max(0.0, min(180.0, msg.x))
        self.target_tilt = max(0.0, min(180.0, msg.y))

    def _update_interpolation_loop(self):
        # 1. Calculate delta/distance left to travel
        pan_delta = self.target_pan - self.current_pan
        tilt_delta = self.target_tilt - self.current_tilt

        # 2. Check if we are close enough to care (mitigates sub-degree oscillations)
        deadzone = 0.3
        moved = False

        if abs(pan_delta) > deadzone:
            self.current_pan += pan_delta * self.easing_factor
            self.servo.set_pan(int(round(self.current_pan)))
            moved = True
        else:
            self.current_pan = self.target_pan

        if abs(tilt_delta) > deadzone:
            self.current_tilt += tilt_delta * self.easing_factor
            self.servo.set_tilt(int(round(self.current_tilt)))
            moved = True
        else:
            self.current_tilt = self.target_tilt


def main(args=None):
    rclpy.init(args=args)
    node = PiperServoNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node.destroy_node()
        except Exception:
            pass
            
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass
            
        print("\n[INFO] Servo driver detached. Clean shutdown complete.")


if __name__ == '__main__':
    main()