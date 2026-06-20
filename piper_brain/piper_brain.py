# ==============================================================================
# Component:  jetson_nx_mind
# Module:     piper_brain.py
# Version:    1.0.0
# Purpose:    Piper's central asynchronous supervisor state machine, managing
#             task prioritization, skill execution, and environmental data TTL.
#
# Change History / Release Notes:
# Date        Version   Author    Description of Changes
# ----------  --------  --------  ----------------------------------------------
# 2026-06-19  1.0.0     OpenCode  Initial module architectural definition.
# ==============================================================================

import asyncio
import heapq
import threading
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Callable, Any, Dict, Coroutine

# --- Constants for Task Priority ---
PRIORITY_CRITICAL = 0
PRIORITY_HIGH = 1
PRIORITY_MEDIUM = 2
PRIORITY_LOW = 3
PRIORITY_IDLE = 4

# --- Skill Registry ---
SKILL_REGISTRY: Dict[str, Callable[..., Coroutine[Any, Any, None]]] = {}

def register_skill(skill_name: str):
    """
    Decorator to register an asynchronous function as a RobotSkill.
    Skills must be async functions that take no arguments or only optional arguments.
    """
    def decorator(func: Callable[..., Coroutine[Any, Any, None]]):
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(f"Skill '{skill_name}' must be an asynchronous function.")
        SKILL_REGISTRY[skill_name] = func
        return func
    return decorator

class ThreadSafePriorityQueue:
    """
    A thread-safe priority queue for managing tasks.
    Tasks are tuples: (priority, timestamp, task_name, *args, **kwargs)
    """
    def __init__(self):
        self._queue = []
        self._lock = threading.Lock()
        self._event = threading.Event() # Used to signal when new items are added

    def put(self, priority: int, task_name: str, *args, **kwargs):
        """Adds a task to the queue with a given priority and current timestamp."""
        with self._lock:
            # Add a timestamp to ensure stable ordering for same-priority items (FIFO)
            timestamp = time.monotonic()
            heapq.heappush(self._queue, (priority, timestamp, task_name, args, kwargs))
            self._event.set() # Signal that an item has been added

    def get(self):
        """Removes and returns the highest priority task."""
        with self._lock:
            if not self._queue:
                return None
            return heapq.heappop(self._queue)

    def empty(self) -> bool:
        """Checks if the queue is empty."""
        with self._lock:
            return not bool(self._queue)

    def wait_for_item(self, timeout: float = None):
        """Blocks until an item is available or timeout occurs."""
        self._event.wait(timeout)
        self._event.clear() # Clear the event after waking up

class PiperBrain:
    """
    Piper's central asynchronous supervisor state machine.
    Manages task prioritization, skill execution, and environmental data TTL.
    """
    def __init__(self, db_path: str = '/home/steve/piper/jetson_nx_mind/world_state.db'):
        self.task_queue = ThreadSafePriorityQueue()
        self.db_path = db_path
        self._running = False
        self._janitor_thread = None
        self.current_task_handle: asyncio.Task | None = None
        self.current_task_priority: int = float('inf') # Stores the priority of the currently running task, inf if no task is running


    async def _execute_skill(self, task_name: str, *args, **kwargs):
        """Executes a registered skill."""
        skill = SKILL_REGISTRY.get(task_name)
        if skill:
            try:
                print(f"Executing skill: {task_name} with args={args}, kwargs={kwargs}")
                await skill(*args, **kwargs)
                print(f"Skill {task_name} completed.")
            except asyncio.CancelledError:
                print(f"Skill '{task_name}' was interrupted by a higher priority task.")
                # Here, you might add logic to safely reset hardware state if necessary
            except Exception as e:
                print(f"Error executing skill '{task_name}': {e}")
            finally:
                # Reset the current task tracking only if this task was the one being tracked
                if self.current_task_handle and self.current_task_handle.done():
                    self.current_task_handle = None
                    self.current_task_priority = float('inf')
        else:
            print(f"Error: Skill '{task_name}' not registered.")

    async def main_loop(self):
        """
        The main asynchronous loop that continuously pops the highest priority task
        and coordinates its execution.
        """
        self._running = True
        print("PiperBrain main loop started.")
        while self._running:
            if self.task_queue.empty():
                # Wait for a new task to be added
                await asyncio.to_thread(self.task_queue.wait_for_item, timeout=1.0)
                continue

            task_data = self.task_queue.get()
            if task_data:
                priority, timestamp, task_name, args, kwargs = task_data
                print(f"Popped task: {task_name} (Priority: {priority}, Timestamp: {timestamp})")

                # Case 1: A task is running, and the new task is higher priority (lower number)
                if self.current_task_handle and not self.current_task_handle.done() and priority < self.current_task_priority:
                    print(f"Interrupting running task (Priority: {self.current_task_priority}) with higher priority task '{task_name}' (Priority: {priority}).")
                    self.current_task_handle.cancel()
                    await asyncio.sleep(0.05) # Yield to allow cancellation to propagate
                    
                    # Execute the higher priority task
                    task_handle = asyncio.create_task(self._execute_skill(task_name, *args, **kwargs))
                    self.current_task_handle = task_handle
                    self.current_task_priority = priority
                    def _task_done_callback(fut):
                        if fut is self.current_task_handle:
                            self.current_task_handle = None
                            self.current_task_priority = float('inf')
                    task_handle.add_done_callback(_task_done_callback)


                # Case 2: A task is running, but the new task is LOWER or EQUAL priority
                elif self.current_task_handle and not self.current_task_handle.done() and priority >= self.current_task_priority:
                    print(f"Brain is busy with higher priority task (Active: {self.current_task_priority}). Re-queueing '{task_name}' (Priority: {priority}).")
                    # Re-queue it securely without altering original args/kwargs structure
                    self.task_queue.put(priority, task_name, *args, **kwargs)
                    await asyncio.sleep(0.1) # Brief rest to avoid a tight thrashing loop

                # Case 3: No task is currently running
                else:
                    task_handle = asyncio.create_task(self._execute_skill(task_name, *args, **kwargs))
                    self.current_task_handle = task_handle
                    self.current_task_priority = priority
                    def _task_done_callback(fut):
                        if fut is self.current_task_handle:
                            self.current_task_handle = None
                            self.current_task_priority = float('inf')
                    task_handle.add_done_callback(_task_done_callback)

            await asyncio.sleep(0.01) # Prevent tight loop

    def _janitor_process(self):
        """
        Background thread for the Time-To-Live (TTL) janitor process.
        Connects to world_state.db and deletes old data.
        """
        print("TTL Janitor process started.")
        while self._running:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    # Calculate the cutoff timestamp (48 hours ago)
                    cutoff_time = datetime.now() - timedelta(hours=48)
                    cutoff_timestamp = cutoff_time.timestamp() # Assuming UNIX timestamp in DB

                    # Delete rows older than 48 hours.
                    # This assumes a 'timestamp' column in relevant tables.
                    # Need to generalize or make configurable for specific tables/schemas.
                    # For now, a placeholder for a 'world_state' table.
                    try:
                        cursor.execute(
                            "DELETE FROM world_state WHERE timestamp < ?",
                            (cutoff_timestamp,)
                        )
                        conn.commit()
                        if cursor.rowcount > 0:
                            print(f"Janitor: Deleted {cursor.rowcount} old rows from world_state.")
                    except sqlite3.OperationalError as e:
                        print(f"Janitor: Warning - Could not delete from world_state table (maybe it doesn't exist or column name is different): {e}")

            except sqlite3.Error as e:
                print(f"Janitor: Database error: {e}")
            except Exception as e:
                print(f"Janitor: An unexpected error occurred: {e}")

            time.sleep(3600) # Run once every hour

    def start(self):
        """Starts the main loop and the janitor thread."""
        if self._running:
            print("PiperBrain is already running.")
            return

        print("Starting PiperBrain...")
        self._running = True
        self._janitor_thread = threading.Thread(target=self._janitor_process, daemon=True)
        self._janitor_thread.start()
        asyncio.run(self.main_loop()) # This will block until main_loop stops

    def stop(self):
        """Stops the PiperBrain."""
        print("Stopping PiperBrain...")
        self._running = False
        if self._janitor_thread and self._janitor_thread.is_alive():
            self._janitor_thread.join(timeout=5) # Wait for janitor to finish gracefully
        print("PiperBrain stopped.")

# --- Example Usage (for testing purposes) ---
if __name__ == "__main__":
    # Create a dummy database for testing the janitor
    test_db_path = '/tmp/test_world_state.db'
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS world_state (
            id INTEGER PRIMARY KEY,
            data TEXT,
            timestamp REAL
        );
    ''')
    conn.commit()

    # Insert some dummy data
    now = datetime.now().timestamp()
    old_time = (datetime.now() - timedelta(hours=50)).timestamp()
    cursor.execute("INSERT INTO world_state (data, timestamp) VALUES (?, ?)", ("Recent data", now))
    cursor.execute("INSERT INTO world_state (data, timestamp) VALUES (?, ?)", ("Old data", old_time))
    conn.commit()
    conn.close()

    print(f"Initial data in {test_db_path}:")
    with sqlite3.connect(test_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM world_state")
        for row in cursor.fetchall():
            print(row)

    # Example skills
    @register_skill("spatial_exploration")
    async def spatial_exploration_skill(area: str = "default"):
        print(f"Performing spatial exploration in {area}...")
        await asyncio.sleep(2)
        print("Spatial exploration completed.")

    @register_skill("person_tracking")
    async def person_tracking_skill(person_id: int):
        print(f"Tracking person {person_id}...")
        await asyncio.sleep(1)
        print("Person tracking completed.")

    brain = PiperBrain(db_path=test_db_path)

    async def run_brain_and_add_tasks():
        # Start the brain in a separate task to allow adding tasks
        brain_task = asyncio.create_task(brain.main_loop())

        # Give the brain a moment to start its loop
        await asyncio.sleep(0.1)

        brain.task_queue.put(PRIORITY_HIGH, "person_tracking", person_id=123)
        brain.task_queue.put(PRIORITY_CRITICAL, "spatial_exploration", area="living room")
        brain.task_queue.put(PRIORITY_LOW, "person_tracking", person_id=456)
        brain.task_queue.put(PRIORITY_IDLE, "spatial_exploration", area="kitchen")

        # Allow tasks to run
        await asyncio.sleep(5)
        brain.stop() # Stop the brain after some time

    try:
        asyncio.run(run_brain_and_add_tasks())
    except KeyboardInterrupt:
        print("Shutting down due to keyboard interrupt.")
        brain.stop()

    print(f"Data in {test_db_path} after janitor might have run:")
    with sqlite3.connect(test_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM world_state")
        for row in cursor.fetchall():
            print(row)

    # Clean up the test database
    import os
    os.remove(test_db_path)
    print(f"Cleaned up {test_db_path}")
