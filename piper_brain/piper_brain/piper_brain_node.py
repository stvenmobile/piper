#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from piper_interfaces.action import ExecuteSkill
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
import time

class PiperSupervisor(Node):

    def __init__(self):
        super().__init__('piper_supervisor')
        self._callback_group = ReentrantCallbackGroup()
        self.get_logger().info("Piper Supervisor Node initialized.")

        self._action_server = ActionServer(
            self,
            ExecuteSkill,
            'execute_skill',
            execute_callback=self._execute_callback,
            goal_callback=self._goal_callback,
            cancel_callback=self._cancel_callback,
            callback_group=self._callback_group)
        
        self.current_goal_handle = None
        self.current_priority = 4  # Default to IDLE priority, where lower number = higher priority

    def destroy(self):
        self._action_server.destroy()
        super().destroy()

    def _goal_callback(self, goal_request):
        """
        Evaluates incoming goals based on priority.
        """
        self.get_logger().info(f"Received goal request for skill: {goal_request.skill_name} with priority: {goal_request.priority}")

        # If there's an active goal and the new goal has higher priority (lower number)
        if self.current_goal_handle and self.current_goal_handle.is_active and \
           goal_request.priority < self.current_priority:
            self.get_logger().info(f"Preempting current goal (Priority: {self.current_priority}) with higher priority goal: {goal_request.skill_name} (Priority: {goal_request.priority})")
            return GoalResponse.ACCEPT
        
        # If no goal is running
        elif not self.current_goal_handle or not self.current_goal_handle.is_active:
            self.get_logger().info(f"No active goal, accepting new goal: {goal_request.skill_name}")
            return GoalResponse.ACCEPT
        
        # If the incoming goal is lower or equal priority
        else:
            self.get_logger().info(f"Rejecting goal '{goal_request.skill_name}' due to lower or equal priority (Current: {self.current_priority}, Incoming: {goal_request.priority})")
            return GoalResponse.REJECT

    def _cancel_callback(self, goal_handle):
        """
        Allows execution goals to be canceled cleanly.
        """
        self.get_logger().info(f"Received cancel request for goal ID: {goal_handle.goal_id}")
        return CancelResponse.ACCEPT

    def _execute_callback(self, goal_handle):
        """
        Executes the skill associated with the accepted goal.
        """
        self.get_logger().info(f"Executing goal for skill: {goal_handle.request.skill_name}")

        # If a previous lower-priority goal is still active, explicitly abort it before taking over
        if self.current_goal_handle and self.current_goal_handle.is_active and \
           goal_handle.request.priority < self.current_priority:
            
            # FIXED NESTED QUOTES STRINGS HERE:
            self.get_logger().info(f"Aborting previous lower priority goal '{self.current_goal_handle.request.skill_name}' (Priority: {self.current_priority})")
            
            old_result = ExecuteSkill.Result()
            old_result.success = False
            old_result.message = f"Preempted by higher priority task: {goal_handle.request.skill_name}"
            self.current_goal_handle.abort(old_result)

        # Update the current goal handle and priority
        self.current_goal_handle = goal_handle
        self.current_priority = goal_handle.request.priority
        self.get_logger().info(f"Current active goal: {goal_handle.request.skill_name} (Priority: {self.current_priority})")

        feedback_msg = ExecuteSkill.Feedback()
        result = ExecuteSkill.Result()
        success = True
        message = "Skill executed successfully."

        # Placeholder skill runner: loop 1 to 10 with a 1-second sleep
        for i in range(1, 11):
            if goal_handle.is_cancel_requested:
                self.get_logger().info(f"Goal {goal_handle.request.skill_name} was cancelled.")
                success = False
                message = "Skill execution cancelled."
                break

            percentage = (float(i) / 10.0) * 100.0
            feedback_msg.percentage_complete = percentage
            feedback_msg.status_message = f"Executing step {i} of 10 for {goal_handle.request.skill_name}"
            goal_handle.publish_feedback(feedback_msg)
            
            self.get_logger().info(f"Published feedback: {percentage:.1f}% complete")
            time.sleep(1)  # Threaded executor handles blocking tasks cleanly

        if success:
            goal_handle.succeed()
        else:
            goal_handle.abort()

        result.success = success
        result.message = message

        # Reset active trackers if this specific goal handle finished naturally
        if self.current_goal_handle == goal_handle:
            self.current_goal_handle = None
            self.current_priority = 4  # Reset to IDLE priority

        return result

def main(args=None):
    rclpy.init(args=args)

    node = PiperSupervisor()
    executor = MultiThreadedExecutor()
    executor.add_node(node)

    try:
        node.get_logger().info("Beginning to spin executor...")
        executor.spin()
    except KeyboardInterrupt:
        node.get_logger().info("Keyboard interrupt, shutting down.")
    finally:
        node.get_logger().info("Shutting down executor...")
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()