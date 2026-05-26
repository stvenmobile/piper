*Piper Project: Autonomous Spatial Researcher**

An agentic, visually-aware embodied AI leveraging edge acceleration
(Jetson Orin NX), YOLOv8 perception, and OpenCode orchestration to
conduct spatial research and autonomous task management.

**1. Piper - Overview and Purpose**

The Piper Project has evolved from a reactive voice assistant into a
proactive, agentic spatial researcher. Piper\'s primary directive is to
build an internal \"world model\" by studying the physical relationship
between her servo-actuated motor movements and the resulting shifts in
her visual matrix.

Instead of waiting for conversational prompts, Piper operates
autonomously. She manages her own long-term focus, reads and writes to
local file systems via OpenCode, and alters her behavior based on
environmental context. When alone, she conducts spatial hypothesis
testing (e.g., tracking geometric shapes as she moves her camera). When
she recognizes a collaborator (Steve), she shifts into a support role,
checking dedicated request files to assist with coding, status
reporting, or local system modifications.

**2. Architectural Design**

**State Machine**

Piper's operational mode is entirely dictated by her visual awareness.

- **STATE: ALONE (The Researcher):** When the room is empty, Piper
  focuses on her task requests journal and spatial mapping. She executes
  physical micro-movements using her pan/tilt servos and records how
  bounding boxes shift in the video frame, actively learning the
  cause-and-effect of her physical embodiment.

- **STATE: ENGAGED (The Collaborator):** When Piper visually identifies
  Steve, she immediately suspends background spatial research. She
  shifts into an active support state, checking the task requests
  journal for new directives, logging completed tasks, and clearing
  outdated entries.

**OpenCode Integration (The Brain)**

OpenCode serves as Piper\'s asynchronous agentic core. It replaces
traditional LLM chat loops by providing direct, read/write access to the
local file system. OpenCode allows Piper to maintain long-term project
focus, execute local Python scripts, modify her own codebase, and
asynchronously generate status reports in markdown files.

**Visual Process (Perception & Identification)**

- **Continuous Frame Analysis:** A hardware-accelerated local V4L2
  camera loop captures the environment directly into Jetson GPU memory.

- **Biometric Verification:** Symmetrical dual-eye validation and facial
  encodings allow Piper to seamlessly distinguish between known
  collaborators and unknown entities, driving the State Machine.

**YOLO Features & Spatial Tracking**

Piper utilizes Ultralytics YOLOv8 to track specific regions of interest
(ROIs). For her world-model research, she locks onto distinct geometric
shapes or colored objects against blank backgrounds. She calculates the
pixel delta of these bounding boxes before and after actuating her
servos, mapping motor-steps to visual-frame shifts.

**Cognition Process**

Piper\'s cognition is now decoupled from reactive speech. Her
\"thoughts\" are asynchronous and file-driven. She reads a queue of
tasks, formulates a plan, executes Python/Bash commands via OpenCode,
observes the results through her camera or terminal outputs, and writes
her conclusions to a persistent journal.

**3. OpenCode Structural Components & File System Organization**

Piper\'s memory and motivation are governed by a specific directory of
markdown and JSON files. OpenCode acts as the interface to read, parse,
and update these documents.

- system_dna.md: The core system prompt and initialization parameters.
  It defines Piper\'s identity, her hardware constraints, and her
  primary directives (e.g., \"You are an autonomous researcher\...\").

- task_requests.md: The central inbox/outbox. Steve adds new research
  goals, code modification requests, or system queries here. When
  engaged, Piper reads this file, executes the tasks, and clears out
  completed items.

- daily_journal.md: Piper\'s chronological output log. She writes
  detailed status reports here, including tasks completed, code
  modified, and overall project progress.

- world_model_definition.md: The scientific ledger. Piper logs her
  spatial research findings here (e.g., \"Actuating Pan +10 degrees
  results in a -45 pixel horizontal shift of the target bounding box at
  1 meter distance\").

**4. Implementation Notes**

- **V3 Paradigm Shift:** All prior STT (Faster-Whisper), TTS (Piper
  Voice), and audio-streaming dependencies (PyAudio, SoundDevice) have
  been completely purged from the codebase to maximize GPU availability
  for vision and agentic processing.

- **Hardware Execution:** The system runs entirely on a localized Jetson
  Orin NX using a direct USB 3.0 webcam and I2C PCA9685 servo
  controllers.

- **Servo Hunting Mitigation:** A deadzone threshold is implemented in
  the neck tracking math to prevent mechanical oscillation/jitter when
  YOLO bounding boxes fluctuate at the sub-pixel level.

**5. Next Steps**

1.  Cleanse existing main.py and core_exec.py modules of all residual
    audio routing, listening threads, and gRPC gateway imports.

2.  Delete gateway.py entirely.

3.  Establish the OpenCode directory structure (system_dna,
    task_requests, daily_journal).

4.  Grant OpenCode agentic responsibility over the project workspace to
    monitor the requests file and initiate background research loops.

5.  Introduce color/shape recognition parameters into the YOLO pipeline
    to facilitate the spatial mapping phase.
