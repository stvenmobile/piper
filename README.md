# **Piper Project: Autonomous Dynamic World-Modeling**

An agentic, visually-aware embodied AI leveraging a distributed, cross-platform ROS 2 network, edge vision acceleration (Jetson Orin NX), local heavy inference (UM790 Pro), and OpenCode orchestration to explore and define a dynamic world model based on real-time video streaming data.

## **1. Piper - Overview and Purpose**

The Piper Project focuses on exploring and defining a dynamic world model based on real-time video data streamed from a camera hosted on the Jetson Orin NX (the sensory perception layer). By analyzing the physical relationship between her servo-actuated motor movements and the resulting shifts in her visual matrix, Piper actively learns the cause-and-effect of her embodiment.

Instead of waiting for conversational prompts, Piper operates autonomously, managing her own long-term focus and reading/writing to local file systems via OpenCode. Her operational profile adapts dynamically based on social environment telemetry:

* **STATE: ALONE (The Researcher):** When the room is empty, Piper focuses on world-model derivation, executing physical micro-movements using her pan/tilt servos and mapping visual matrix deltas to capture how environmental context shifts in the video frame.
* **STATE: ENGAGED (The Collaborator):** When she visually identifies Steve, she immediately suspends background world-modeling and shifts into an active support role—monitoring the web dashboard console, checking the task request ledger for directives, and parsing operational code requests.

---

## **2. Architectural Design**

### **Distributed ROS 2 Graph (Cross-Platform Topology)**
To maximize compute efficiency, Piper’s architecture is decoupled into a heterogeneous, multi-system ROS 2 graph utilizing **Eclipse CycloneDDS** to bridge hardware execution and high-level cognitive processes across the local network:

[ Jetson Orin NX (Ubuntu 22.04 / ROS 2 Humble) ]
          │
          ├──> camera_node (CSI IMX219 / GStreamer 180° Flip Pipeline)
          │       │
          │       └──> [ Topic: /piper/camera0/image_raw ] ───( CycloneDDS )───┐
          │                                                                    │
          └──> servo_node (PCA9685 I2C / Adafruit ServoKit Actuation)          │
                  ▲                                                            │
                  └───────────( CycloneDDS )─── [ Action Server ] ◄──────┐     │
                                                                         │     │

─────────────────────────────────────────────────────────────────────────────┼─────┼──
│     │
[ UM790 Pro Mini PC (Fedora Linux / ROS 2 Jazzy / Python .VENV) ]        │     │
│                                                              │     │
├──> um790_dashboard_node (Flask UI / Face Rec Inference) ◄────┼─────┘
│                                                              │
└──> piper_brain_node (Supervisor Engine / OpenCode Core) ─────┘


#### **Edge Hardware Layer (Jetson Orin NX Hub - `piper_drivers`)**
* **`camera_node`**: High-performance hardware abstraction layer that opens the CSI sensor via a hardware-accelerated GStreamer pipeline, applies a $180^\circ$ flip modification, and broadcasts the raw `sensor_msgs/msg/Image` frames across the network to drive the sensory perception layer.
* **`servo_node`**: Actuator hardware layer hosting the action server interfaces to translate target angles straight to the physical PCA9685 I2C interface.

#### **Cognitive & UI Layer (UM790 Pro Workstation - `piper_brain`)**
* **`um790_dashboard_node`**: Multi-threaded Flask web server operating at `http://localhost:5000`. It subscribes to the remote camera stream, processes heavy facial tracking/inference using workstation CPU cycles, handles face recognition profiles, and provides an active visual web dashboard and command ingestion console.
* **`piper_brain_node`**: The core supervisory engine running a `MultiThreadedExecutor` to manage asynchronous priority queues, handle action goal preemption routines, and run the OpenCode agentic loop.

---

## **3. OpenCode Structural Components & File System Organization**

Piper's memory, motivation, and persistent tracking logs are governed by a specific sandbox directory of markdown and JSON files. OpenCode acts as the execution interface to read, parse, and update these documents:

* **`system_dna.md`**: The core system prompt and initialization parameters defining identity, hardware constraints, and primary directives.
* **`task_requests.md`**: The central inbox/outbox. Directives submitted via the dashboard console append directly here (e.g., `- [ ] **Task via Dashboard Console**: ...`) before invoking background subprocess shells.
* **`daily_journal.md`**: Chronological output log where Piper documents status updates, modified code blocks, and operational insights.
* **`world_model_definition.md`**: The scientific ledger where dynamic world-model findings are persistently mapped (e.g., pan/tilt servo changes relative to pixel coordinate drift).

---

## **4. Implementation & Integration Notes**

* **Cross-Version RMW Interoperability:** Communicates seamlessly between ROS 2 Humble (Jetson) and ROS 2 Jazzy (UM790 Pro) over CycloneDDS. Stale type-hash warnings (`ParticipantEntitiesInfo_` USER_DATA omissions) are expected network parsing artifacts and do not degrade message throughput.
* **Workspace Splitting:** Packages are structurally isolated to protect target environments. High-level runtime templates, tracking assets, and supervisor engines sit in `piper_brain` on the workstation, while low-level peripheral drivers sit inside `piper_drivers` on the edge node.
* **Thread Isolation & Scoping:** The Flask streaming loop on the workstation relies on an independent background thread running concurrent to the main ROS subscription callbacks, utilizing global memory protections to stream high-frame-rate compressed JPEGs without blocking the main executor scope.