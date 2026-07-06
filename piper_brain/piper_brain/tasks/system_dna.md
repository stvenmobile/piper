# 🧬 PIPER ROBOT SYSTEM DNA

## Hardware Infrastructure
* **UM790 Workstation Core**: Acts as the central high-level brain engine running Ubuntu 24.04 LTS. Hosts the interactive web dashboard telemetry server, internal processing nodes, and local OpenCode execution environments.
* **Jetson Orin NX Edge Node**: Handles direct low-latency spatial tasks including GStreamer video stream acquisition, hardware-accelerated YOLO parsing, and PWM servo tracking communication.

## Network & Communication Layer
* **ROS 2 Ecosystem**: Configured across all distributed machines using the `Jazzy Jalisco` long-term support distribution.
* **RMW Transport Broker**: Tied directly to an Eclipse `CycloneDDS` network interface topology to manage cross-machine topic discovery without requiring a central discovery server.
* **Subnet & Domain Mapping**: Fixed on network domain ID `42` across the local area network subnet partition (`192.168.1.0/24`).

## Repository Workspace & Assets Path
* **Core Task Path**: `src/piper_brain/piper_brain/tasks/` maps persistent state logging ledgers (`current_tasks.md`, `task_progress.md`).
* **Visual Asset Workspace**: `src/piper_brain/piper_brain/assets/sketchbook/` acts as the definitive directory for generated image matrices exposed by the Flask telemetry front-end.
* **Environment Sourcing Rules**: Any script interacting with ROS 2 or importing local package layers must explicitly source the underlying environments:
    1. `source /opt/ros/jazzy/setup.bash`
    2. `source /home/steve/piper_ws/install/setup.bash`

## Dashboard Integration & Inter-Agent Standards
* **The ROS 2 Strict Rule**: This system runs ROS 2 Jazzy ONLY. NEVER use `import rospy` or any ROS 1 paradigms. Always use `import rclpy` and standard ROS 2 node architecture.
* **The "Findings" Protocol**: Hermes must work continuously to fulfill engineering tasks and improve system capability. If optimal upgrades or technical gaps are identified, Hermes must document them explicitly under a "### 🧠 Findings" section inside `task_progress.md`.
* **The Progress Ledger Compaction Rule**: When writing to `task_progress.md`, you must maintain a lean, high-level summary structure. Older historical execution logs must be truncated or replaced by a single consolidated "Latest Status Table." Do not append continuous, multi-page raw code proposals to the ledger. Keep the total ledger size under 500 lines.
* **Asset Exposure Pipeline**: The Flask dashboard serves images statically from `src/piper_brain/piper_brain/assets/sketchbook/`. All completed drawings must be saved to this folder with the naming convention `sketch_<unix_timestamp>.jpg` to be auto-discovered by the UI.
* **The Code Trap Guardrail**: To prevent dashboard route conflicts, never use the phrase `autonomous_sketch` for filenames or packages handled dynamically. Use `autonomous_drawing` or `canvas_generation`.
* **Python Path Rule**: When writing standalone Python automation scripts, Hermes must always append the absolute path to the workspace before importing local sibling classes to ensure correct execution context:
  `import sys; sys.path.append('/home/steve/piper_ws/src/piper_brain/piper_brain')`

* **The ROS 2 Strict Rule**: This system runs ROS 2 Jazzy ONLY. NEVER use `import rospy`, `rospy.Subscriber`, or any ROS 1 paradigms. Always use `import rclpy`, proper ROS 2 node class structures, and correct message type imports (`from sensor_msgs.msg import CompressedImage`).

