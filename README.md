# Piper Project: ROS 2 Distributed Robot

This repository contains the software for the Piper distributed robot system, designed to operate across a Jetson Orin NX edge node and a UM790 Pro MiniPC brain node. The system leverages ROS 2 for inter-node communication and task orchestration, focusing on a robust and efficient robotics platform for tasks like autonomous drawing and vision tracking.

## 1. ROS 2 Environment Setup

The Piper project utilizes a distributed ROS 2 environment with specific configurations for each hardware platform:

*   **Domain ID:** 42 (ensures proper communication between nodes)
*   **RMW Implementation:** CycloneDDS (consistent across both Jetson and UM790)
*   **ROS 2 Distributions:**
    *   **Jetson Orin NX:** Humble
    *   **UM790 Pro MiniPC:** Jazzy

**Important:**
*   Always use ROS 2 (`rclpy`), never ROS 1 (`rospy`).
*   Ensure proper sourcing order: `source /opt/ros/jazzy/setup.bash && source install/setup.bash`

## 2. Build & Run Instructions

All commands should be executed from the `/home/steve/piper_ws` directory.

### 2.1 Building the Workspace

```bash
colcon build
```

### 2.2 Sourcing the Workspace

After building, you must source the workspace to make the ROS 2 packages available:

```bash
source install/setup.bash
```

### 2.3 Running Nodes

#### UM790 Pro MiniPC (Brain Nodes)

To start the full brain-side stack, including the dashboard and background processes:

```bash
./start_piper_brain.sh
```

Alternatively, to launch individual brain nodes:

```bash
ros2 launch piper_brain piper_brain_launch.py
```

This typically runs `dashboard_node.py` in the foreground, while `hermes_supervisor` and `autonomous_drawing` run as background processes.

#### Jetson Orin NX (Edge Nodes)

To start the drivers and vision components on the Jetson:

```bash
./src/start_jetson.sh
```

Alternatively, to launch individual Jetson nodes:

```bash
ros2 launch piper_drivers piper_hardware_launch.py
```

## 3. Packages & Entry Points

The project is structured into several ROS 2 packages, each with specific nodes and functionalities, distributed across the Jetson and UM790.

| Package           | Entry Points / Nodes                                   | Description                                                                                                                                                                                                            | Hardware Location |
| :---------------- | :----------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :---------------- |
| `piper_brain`     | `piper_brain_node`, `dashboard_node`, `autonomous_drawing` | `piper_brain_node`: Supervisor and action server with priority preemption. `dashboard_node`: Flask web interface (:5000) with ROS subscriber. `autonomous_drawing`: Periodic sketch generation loop.                 | UM790 MiniPC      |
| `piper_drivers`   | `camera_node`, `servo_node`, `vision_tracking_node`    | `camera_node`: Manages camera sensor. `servo_node`: Controls robot servos (neck pan/tilt). `vision_tracking_node`: Processes camera data for object detection (YOLO detections).                                 | Jetson Orin NX    |
| `hermes_mind`     | `task_supervisor`                                      | Manages tasks, uses Ollama (hermes3 + qwen2.5-coder) for HITL codegen, and stages code for human approval via the dashboard. Watches `piper_brain/tasks/current_tasks.md`.                                       | UM790 MiniPC      |
| `piper_interfaces`| `ExecuteSkill.action`                                  | Defines ROS 2 action interfaces, specifically `ExecuteSkill.action` for priority-based preemption of robot skills.                                                                                                       | Both              |

## 4. Key ROS 2 Topics

These topics facilitate communication between different nodes across the distributed system.

| Topic                               | Type              | Description                                        |
| :---------------------------------- | :---------------- | :------------------------------------------------- |
| `/piper/camera0/image_raw/compressed` | `CompressedImage` | Compressed camera stream (consumed on brain side)  |
| `/piper/neck/set_position`          | `Vector3`         | Servo commands for neck (x=pan, y=tilt)            |
| `/piper/perception/tracked_objects_json` | `String`          | YOLO object detections in JSON format              |
| `/hermes/status_stream`             | `String`          | Hermes supervisor dashboard updates                |
| `/hermes/human_approval`            | `String`          | Human-in-the-Loop (HITL) approval channel for Hermes |

## 5. Architecture Highlights

*   **MultiThreadedExecutor:** Utilized across the system to ensure safe blocking operations like `time.sleep()`.
*   **Jetson Edge (`piper_drivers`):**
    *   `camera_node` feeds into `vision_tracking_node`.
    *   Nodes are sequenced via `OnProcessStart` to avoid GStreamer race conditions.
*   **UM790 Brain (`piper_brain`):**
    *   `dashboard_node` (Flask + ROS subscriber) provides the UI.
    *   `piper_brain_node` acts as an action server with priority preemption.
    *   `autonomous_drawing` runs a periodic sketching loop.
*   **Hermes (`hermes_mind`):** Operates as a background file-watcher on `current_tasks.md`, driving an Ollama-based codegen pipeline with a Human-in-the-Loop (HITL) gate.

## 6. Critical Gotchas

*   **`autonomous_drawing` Entry Point:** This node is currently broken when built with `colcon`. It **must** be run via direct Python: `~/.venv/bin/python3 src/piper_brain/piper_brain/autonomous_drawing.py`.
*   **Python Path Injection:** For standalone scripts to import sibling modules, `sys.path.append('/home/steve/piper_ws/src/piper_brain/piper_brain')` is required.
*   **gRPC Stubs:** Files like `spatial_matrix_pb2*` are auto-generated Protobuf code; **do not hand-edit** them.
*   **SQLite Schema Upgrades:** Manual migration or `rm *.db` is necessary for schema changes; no automatic migration is provided.
*   **Robot Vocabulary:** Defined in `piper_brain/vocabulary.json`.
*   **Dashboard Sketch Assets:** Image assets for the dashboard must be placed in `piper_brain/assets/sketchbook/` and named `sketch_<unix_timestamp>.jpg`.
*   **Avoid `autonomous_sketch`:** Do not use `autonomous_sketch` as a filename or package name, as it causes dashboard route conflicts. Use `autonomous_drawing` instead.
*   **Hermes Supervisor:** Monitors `piper_brain/tasks/current_tasks.md` for tasks, uses Ollama, and stages code for human approval on the dashboard before writing to disk.
*   **Workspace Root:** The root for all source code is `/home/steve/piper_ws/src/`.
*   **Python Virtual Environment:** Located at `/home/steve/piper_ws/.venv` with dependencies listed in `src/requirements.txt`.
*   **Tests:** `pytest` is used per package, adhering to standard ROS 2 tests (ament_flake8/pep257).
