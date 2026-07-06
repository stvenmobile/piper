#  # **Piper Project: Autonomous Dynamic World-Modeling**

An agentic, visually-aware embodied AI leveraging a distributed, cross-platform ROS 2 network, edge vision acceleration (Jetson Orin NX), local heavy inference (UM790 Pro), and OpenCode orchestration to explore and define a dynamic world model based on real-time video streaming data.

## **1. Piper - Overview and Purpose**

The Piper Project focuses on exploring and defining a dynamic world model based on real-time video data streamed from a camera hosted on the Jetson Orin NX (the sensory perception layer). By analyzing the physical relationship between her servo-actuated motor movements and the resulting shifts in her visual matrix, Piper actively learns the cause-and-effect of her embodiment.

Instead of waiting for conversational prompts, Piper operates autonomously, managing her own long-term focus and reading/writing to local file systems via OpenCode. Her operational profile adapts dynamically based on environmental telemetry, stabilized by a **20-second state machine hysteresis loop** to prevent erratic transitions from momentary profile shifts:

* **STATE: SOLO (The Researcher):** Piper focuses on world-model derivation, executing physical micro-movements using her pan/tilt servos and mapping visual matrix deltas to capture how environmental context shifts in the video frame.
* **STATE: TEAMING (The Collaborator):** When she visually identifies a collaborator via edge YOLO arrays, she transitions into an active support role—monitoring the web dashboard console, checking the task request ledger for directives, and parsing operational code requests.

---

## **2. Architectural Design**

### **Distributed ROS 2 Graph (Cross-Platform Topology)**
To maximize compute efficiency, Piper’s architecture is decoupled into a heterogeneous, multi-system ROS 2 graph utilizing **Eclipse CycloneDDS** to bridge hardware execution and high-level cognitive processes across a mixed-version network topology:

* **Sensory Perception Layer (Jetson Orin NX):** Runs **ROS 2 Humble** on Ubuntu 22.04 to leverage optimized, hardware-accelerated NVIDIA edge vision and I2C peripheral libraries.
* **Cognitive & Execution Layer (UM790 Pro):** Runs **ROS 2 Jazzy** on Ubuntu 24.04 within a modern Python `.venv` workstation environment to drive high-level agentic orchestration.

```text

[ JETSON ORIN NX (Edge Peripheral Layer) ]
            │
            ├──> camera_node ──> [/piper/camera0/image_raw/compressed]
            │                                 │
            ├──> vision_tracking_node ────────┼─> [/piper/perception/tracked_objects_json]
            │                                 │
            └──> servo_node <─────────────────┼─┐
                                              │ │  ( CycloneDDS Bridge )
──────────────────────────────────────────────┼─┼─────────────────────────
                                              │ │
       [ UM790 PRO PC (Cognitive & UI Layer) ]│ │
            │                                 ▼ ▼
            ├──> um790_dashboard_node <───────┘ │
            │       │                           │
            │       └──> [ Database: piper_memory.db ]
            │                                   │
            └──> piper_brain_node ──────────────┘

```

#### **Edge Hardware Layer (Jetson Orin NX Hub - `piper_drivers`)**
* **`camera_node`**: High-performance hardware abstraction layer that opens the CSI sensor via a hardware-accelerated GStreamer pipeline, applies a $180^\circ$ flip modification, and broadcasts compressed JPEG frames to protect network bandwidth.
* **`vision_tracking_node`**: Low-latency edge inference engine running quantized YOLO models locally on the Jetson GPU. It broadcasts a structured string payload (`/piper/perception/tracked_objects_json`) containing object labels, confidences, and raw pixel boundaries (`xmin`, `ymin`, `xmax`, `ymax`).

#### **Cognitive & UI Layer (UM790 Pro Workstation - `piper_brain`)**
* **`um790_dashboard_node`**: Multi-threaded Flask web server operating at `http://localhost:5000`. It maps structural data streams, processes relative servo command routing, and aggregates active objects inside a permanent frontend dashboard.
* **`piper_brain_node`**: The core supervisory engine running a `MultiThreadedExecutor` to manage asynchronous priority queues, handle action goal preemption routines, and run the OpenCode agentic loop.

---

## **3. Advanced Capabilities & Telemetry Stream Sync**

### **Hardware-Accelerated Bounding Boxes**
To maintain a near-zero resource tax on the Jetson Orin NX computational core, bounding boxes are completely offloaded to the client side. The dashboard uses an HTML5 transparent `<canvas>` element stacked directly on top of the live stream `<img>`. The client-side telemetry loop handles calculating display scale differences and rendering the tracking squares dynamically using hardware acceleration.

### **Session Persistence Ledger (SQLite)**
Every tracking event intercepted by the cognitive tier parses the incoming YOLO json array, derives the box's spatial **midpoint centroid** ($x_c, y_y$), and logs it to a persistent database:
$$\begin{array}{cc} x_c = \frac{x_{min} + x_{max}}{2} & y_c = \frac{y_{min} + y_{max}}{2} \end{array}$$
The database engine standardizes counts, max confidence metrics, and historical timestamps to construct a persistent semantic memory layer.

### **Manual Neck Servo Overrides**
The dashboard console embeds an absolute-jog controller loop. It feeds directional movement impulses (Up, Down, Left, Right) directly to the neck servos, custom-inverted to compensate for physical inverted-chassis hardware mounting constraints.

### **Deterministic Action Vocabulary**
The system incorporates an explicit action contract governed by a `vocabulary.json` schema. The first operational verb implemented is **`scan`**:
* **The Scan Behavior**: Initiates a dynamic 4-point rectangular bounding frame sweep ($40^\circ \text{ wide} \times 20^\circ \text{ tall}$) centered entirely relative to her current real-time viewpoint. 
* At each corner waypoint (P1 Top-Left $\rightarrow$ P2 Top-Right $\rightarrow$ P3 Bottom-Right $\rightarrow$ P4 Bottom-Left), the execution loop pauses for 1.5 seconds to settle hardware vibrations, captures a spatial snapshot of all localized object centroids, and permanently updates a dedicated **Active World Model Matrix** block inside the web console layout.

---

## **4. OpenCode Structural Components & File System Organization**

Piper's memory, motivation, and persistent tracking logs are governed by a specific sandbox directory of markdown and JSON files. OpenCode acts as the execution interface to read, parse, and update these documents:

* **`system_dna.md`**: The core system prompt and initialization parameters defining identity, hardware constraints, and primary directives.
* **`task_requests.md`**: The central inbox/outbox. Directives submitted via the dashboard console append directly here (e.g., `- [ ] **Task via Dashboard Console**: ...`) before invoking background subprocess shells.
* **`daily_journal.md`**: Chronological output log where Piper documents status updates, modified code blocks, and operational insights.
* **`world_model_definition.md`**: The scientific ledger where dynamic world-model findings are persistently mapped (e.g., pan/tilt servo changes relative to pixel coordinate drift).
* **`vocabulary.json`**: The machine-readable behavioral schema defining physical and cognitive verb specifications, expected outcomes, and parameters.

---

## **5. Implementation & Integration Notes**

* **Cross-Version RMW Interoperability:** Communicates seamlessly between ROS 2 Humble (Jetson) and ROS 2 Jazzy (UM790 Pro) over CycloneDDS. Stale type-hash warnings (`ParticipantEntitiesInfo_` USER_DATA omissions) are expected network parsing artifacts and do not degrade message throughput.
* **Workspace Splitting:** Packages are structurally isolated to protect target environments. High-level runtime templates, tracking assets, and supervisor engines sit in `piper_brain` on the workstation, while low-level peripheral drivers and vision node setups sit inside `piper_drivers` on the edge node.
* **Schema Upgrades**: Modifications to the SQLite tracking tables require explicit database migration scripts or clean slate resets (`rm *.db`) since the automated internal generation logic bypasses columns already initialized during old application lifecycles.

---

## **4. Implementation & Integration Notes**

* **Cross-Version RMW Interoperability:** Communicates seamlessly between ROS 2 Humble (Jetson) and ROS 2 Jazzy (UM790 Pro) over CycloneDDS. Stale type-hash warnings (`ParticipantEntitiesInfo_` USER_DATA omissions) are expected network parsing artifacts and do not degrade message throughput.
* **Workspace Splitting:** Packages are structurally isolated to protect target environments. High-level runtime templates, tracking assets, and supervisor engines sit in `piper_brain` on the workstation, while low-level peripheral drivers sit inside `piper_drivers` on the edge node.
* **Thread Isolation & Scoping:** The Flask streaming loop on the workstation relies on an independent background thread running concurrent to the main ROS subscription callbacks, utilizing global memory protections to stream high-frame-rate compressed JPEGs without blocking the main executor scope.