# Piper Project: Revamp
An advanced, low-latency distributed voice and vision assistant leveraging edge AI acceleration, gRPC transport, and a local large language model.

---

## `🔵` Overview
The Piper Project is an agentic chatbot assistant split across three distinct compute tiers to optimize processing efficiency, eliminate audio latency, and achieve natural-sounding voice interactions. By treating physical I/O and cognitive AI processing as decoupled modules, the system guarantees real-time responsiveness and modular scalability.

---

## `🔵` Core Goals & Performance Targets
* **Sub-Second Latency:** Total Time-to-First-Audio (TTFA) of under 1.0 second from the moment the user finishes speaking, made possible by HTTP/2 stream multiplexing.
* **High-Fidelity Audio:** Natural phrasing and intonation by offloading TTS generation entirely to the Jetson Orin NX GPU, completely unburdening the Pi 5 CPU.
* **Architecture Cleanliness:** Compile-time type-safety via gRPC Protocol Buffers, replacing loose JSON or fragile WebSocket structures.
* **Modular Design:** Clear separation of concerns allowing individual hardware tiers to be updated, scaled, or replaced without breaking the pipeline.

---

## `🔵` Roadmap & Development Phases
* **Step 0: Architectural Design Planning (COMPLETE)**
    * Establish system topology, device roles, data contracts, and directory mapping.
* **Step 1: OpenCode Environment Setup (COMPLETE)**
    * Initialize the OpenCode development tier on the Jetson Orin NX to manage workspace sync.
* **Step 2: gRPC Framework Definition (COMPLETE)**
    * Define bidirectional audio/video channels and Protocol Buffer communication contracts.
* **Step 3: Component Implementation & Cognition Loop (COMPLETE)**
    * Build out `pi5_body` mic streaming and `jetson_nx_mind` core orchestration.
    * Integrate external network-facing inference routing to the RTX 5070 compute layer.
* **Step 4: Biometric Facial Enrollment (CURRENT PHASE)**
    * Implement dual-eye horizontal symmetry validation thresholds to register new users on the fly.

---

## `🔵` System Architecture
The project distributes workloads across three hardware nodes, separating physical execution from cognitive processing:

| Tier | Component Name | Hardware | Core Functional Role | Primary Software Stack |
| :--- | :--- | :--- | :--- | :--- |
| **1. The Body** | `pi5_body` | * Raspberry Pi 5<br>* SunFounder FusionHat AI<br>* 7" Display<br>* Logitech Webcam | **Sensory Input & Physical Reflexes:** Continuous microphone capture, camera frame buffering, UI rendering, and pan/tilt actuator execution. | Python, PyAudio, gRPC Client |
| **2. The Mind** | `jetson_nx_mind` | * Jetson Orin NX (16GB)<br>* USB Audio Speaker | **Cognition, Acceleration, & Vocalization:** Local Whisper STT, local high-fidelity Neural Piper TTS, local USB audio spatial playback, and thread lifecycle orchestration. | OpenCode, OpenCV 4.11.0 (Native Wayland/Qt5 + CUDA 12.6 + cuDNN), Faster-Whisper, Piper TTS, SoundDevice, gRPC Server |
| **3. The Brain** | Central Compute | * Quantum PC<br>* NVIDIA RTX 5070 GPU | **Deep Inference:** Multi-turn conversational sliding context management and heavy-parameter local LLM execution. | Ollama, Hermes-3-8B / Llama-3.1 |

---

## `🔵` Data & Communication Flow

```plaintext
+-----------------------------------------------------------------+
|                           pi5_body                              |
|             Raspberry Pi 5 + SunFounder FusionHat AI            |
|   (Captures raw mic array input, drives 7" display & webcam)    |
+-----------------------------------------------------------------+
           |                                             
           |                                             
   [Raw Audio Stream]                            
  (16kHz Mono PCM Chunks via gRPC)                       
           |                                             
           v                                             
+-----------------------------------------------------------------+
|                        jetson_nx_mind                           |
|         Jetson Orin NX (16GB) + Local USB Audio Speaker         |
+-----------------------------------------------------------------+
|  1. OpenCode Environment: Orchestrates building & maintenance.  |
|  2. Faster-Whisper (STT): Transcribes stream with GPU speed.    |
|  3. Cognitive Layer: Manages thread state & local .env tokens.  |
|  4. Piper TTS: Streams high-fidelity audio chunks locally.      |
+-----------------------------------------------------------------+
           |                                             ^
           |                                             |
   [Transcribed Text]                          [Text Response Stream]
    (HTTP/2 POST Payload)                        (JSON Content Frame)
           |                                             |
           v                                             |
+-----------------------------------------------------------------+
|                        CENTRAL COMPUTE                          |
|             Quantum PC (NVIDIA RTX 5070 Workstation)            |
|         (Hosts Hermes-3 / Llama-3.1 via Networked Ollama)       |
+-----------------------------------------------------------------+

* **Audio Ingestion:** pi5_body captures user speech via the SunFounder FusionHat mic array <br> at 16kHz Mono and streams raw PCM chunks over a persistent gRPC connection to jetson_nx_mind.
* **Transcription:** jetson_nx_mind ingests the raw stream and processes it via hardware-accelerated <br> Faster-Whisper down to clean text strings.
* **Distributed Inference:** The Jetson packages the text string and forwards it via a network POST <br> request to Ollama listening on the Quantum PC (192.168.1.150:11434). The RTX 5070 processes the prompt through an 8B context window and returns a text block response.
* **Cognitive Memory Ledger:** The interaction transaction is permanently committed to journal_queries.md <br>on the Jetson filesystem, updating a sliding FIFO context queue to protect working VRAM limits.
* **Neural Vocalization:** The text response is fed directly into the Jetson's local Piper TTS engine <br>using the en_US-hfc_female-medium ONNX checkpoint.
* **Low-Latency Execution:** To achieve zero-latency room playback, audio frames are streamed <br>slice-by-slice out of the Jetson’s dedicated local USB audio hardware interface, completely bypassing remote network audio transport overhead.
```
---
## `🔵` Repository Structure
```plaintext
├── jetson_nx_mind/       # Runs on Jetson Orin NX (Managed via OpenCode)
│   ├── proto/            # Master .proto definitions and compiled stubs
│   ├── src/
│   │   ├── main.py       # Unified runtime entry point and initialization manager
│   │   ├── core_exec.py  # Executive control model and thread lifecycle orchestrator
│   │   ├── vision.py     # Biometric facial landmark processing and evaluation engine
│   │   ├── cognition.py  # Rolling memory window manager and remote Ollama link
│   │   └── gateway.py    # gRPC Server coordinating stream interceptions
│   ├── memory/           # Persistent JSON interaction storage
│   │   └── journal.json  # System interaction historical records
│   ├── voices/           # High-fidelity ONNX speech checkpoints
│   │   └── en_US-hfc_female-medium.onnx
│   ├── journal_queries.md # Chronological markdown conversation log
│   └── models/           # Local model registries
```
---
## `🔵` Development Tier: OpenCode Integration
To effectively scale the Piper Project without fragile code injection or excessive manual cut-and-paste overhead, OpenCode is deployed directly on the jetson_nx_mind tier.

Roles of the OpenCode Layer
* Central Workspace Management: Direct programmatic orchestration of compilation, testing, and synchronization tasks across both the Mind and Body tiers.
* Automated Code Compilation: Manages the compilation of .proto definition files into identical Python gRPC stubs for both nodes simultaneously.
* Incremental Testing: Executes local integration tests to guarantee that changes to code modules do not introduce latency spikes or transport protocol breakages.

---
## `🔵` Code Standards: History & Versioning
Every program, script, and component within this repository must include a standardized file header tracking versioning, changes, and release notes. This maintains absolute transparency as the software footprint scales.

### Standard Header Format
```Python
# ==============================================================================
# Component:  jetson_nx_mind / pi5_body
# Module:     [Filename / Module Name]
# Version:    X.Y.Z (Semantic Versioning)
# Purpose:    [Brief explanation of code responsibilities]
#
# Change History / Release Notes:
# Date        Version   Author    Description of Changes
# ----------  --------  --------  ----------------------------------------------
# 2026-05-17  1.0.0     Steve     Initial module architectural definition.
# ==============================================================================
```

---
## `🔵` Thread Architecture & Executive Control Model

The `jetson_nx_mind` tier runs an asynchronous, multi-threaded state engine driven by a central orchestrator (`main.py`). This design prevents blocking across high-compute tasks (vision/inference) and raw hardware operations, allowing Piper to maintain an internal state of "motivation," priority management, and long-term memory.

```text
               +-----------------------------------------+
               |  PROCESS THREAD (main.py Executive)     |
               |  - Goals, Priorities, State Machine     |
               |  - System Memory & Proactive Intent     |
               +-----------------------------------------+
                 /          |                  \
                /           |                   \
               v            v                    v
      [Visual Thread]   [Listening Thread]   [Quantum PC Link]
      - Native USB 3.0  - Wake Word Gate      - Networked Ollama
      - YOLOv8 / FaceID - Faster-Whisper STT  - 4-Turn FIFO Memory
      - Servo Tracking  - Local Piper TTS     - journal_queries.md
```
---
## `🔵` The Process Thread (main.py Executive Core)
### 1. State Machine thread (motivation). 
This is the primary thread managing Piper’s cognitive state machine, goals, and behavioral context. It operates independently of raw I/O loops and coordinates the activation of sub-threads based on four operational states:

* **STATE: ALONE (World Modeling & Spatial Hypothesis):** When no humans are present, Piper shifts from reactive text processing to active environmental learning. The _offline_task_worker utilizes the Visual Thread to test physical hypotheses.
	* Proprioception Testing: Piper executes micro-movements with its servos and compares the expected visual matrix shift against the actual camera input, refining its internal calibration.
	* Object Permanence: Utilizing YOLOv8 combined with a localized spatial memory matrix, Piper tracks moving objects (e.g., pets, rolling items, shifting shadows), predicts their trajectories when occluded, and actively searches if the environment violates its physical predictions.
* **STATE: PERCEIVING (Identification):** Triggered when the Visual Thread detects a human presence. The Process Thread temporarily pauses background tasks and waits for the identity verification layer.
* **STATE: ENGAGED (Proactive Summary):** When a recognized user (e.g., Steve) is identified, the thread checks its historical memory, calculates elapsed time since the last interaction, and actively initiates a vocal summary of standalone activities.
* **STATE: CONVERSING (Reactive Interaction):** Minimizes internal task overhead to focus entirely on the low-latency text-to-speech loop between the local gRPC streams and the Quantum PC.


### 2. The Visual Thread (Onboard Jetson NX)
* Hardware Connection: The Logitech webcam connects directly to a native USB 3.0 port on the Jetson Orin NX, utilizing direct V4L2 hardware capture buffers.
* Execution: Runs a continuous frame-capture loop directly into Jetson GPU memory. It applies localized image enhancements (CLAHE contrast normalizer and Unsharp masking) before running YOLOv8 face tracking.
* Reflex Control: When a face is actively tracked, this thread skips the master process queue and streams high-frequency servo angle floats (pan, tilt) down the local gRPC line to the Pi 5 to maintain zero-latency physical alignment.

### 3. The Listening & Comms Thread (gRPC Gateway)
Manages the persistent HTTP/2 gRPC channels connecting the Mind to the Body and the Central Compute tiers, enforcing strict stream gating:

* Wake Word Gate: The Raspberry Pi 5 runs a localized, low-overhead wake word listener. When triggered, it fires a lightweight event upstream. The Jetson opens the gRPC audio capture gate and instantly streams raw audio into its accelerated Faster-Whisper STT pipeline.
* Vocal Muting Gate: When the Process Thread pushes a textual response to the local TTS engine (Piper/Kokoro-82M), this thread activates a synchronization flag across the communication link to mute the Pi 5’s mic stream, preventing Piper from processing its own vocalizations.


---
## `🔵` Executive Kernel Core Functions (`core_exec.py`)

The `core_exec.py` module serves as the primary cognitive runtime commander on the `jetson_nx_mind` tier. It initializes memory structures, controls thread lifecycle states, and acts as the master decision-making gatekeeper.

### Lifecycle & Memory Management
* **`__init__()`**
  Initializes the executive layer kernel. Spawns the master thread-synchronization primitives (`stop_signal` and `task_gate`), instantiates system state tracking variables, and maps local directory anchors.
* **`init_memory_store()`**
  Executes low-level file system validation at boot. Ensures that the relative `memory/` directory exists and populates missing base files (`system_dna.json`, `journal.json`, `task_progress.json`) to guarantee structural disk read/writes during execution.
* **`append_journal(context, message)`**
  A thread-safe logging interface that injects timestamped, contextual ledger entries into the persistent JSON historical record, ensuring Piper maintains a traceable chronological memory of its experiences.

### Subordinate Thread Worker Loops
* **`_visual_worker()`**
  Drives the local USB 3.0 V4L2 camera capture stream. Orchestrates the local `VisionEngine` face-detection loops, updates global user tracking parameters, and routes rapid spatial data adjustments.
* **`_listening_worker()`**
  Manages the network-facing gRPC ingestion pipes. Monitors incoming audio frame packets streamed from the `pi5_body` and coordinates transcription payloads with the central text generation loops.
* **`_offline_task_worker()`**
  The workspace engine for standalone autonomous operations. It runs background operations, handles long-term planning routines, and monitors task progress while Piper is alone. This loop is tightly governed by the executive thread gate to ensure zero CPU overhead when a user is present.

### State Orchestration & Control
* **`evaluate_state_transitions()`**
  The core state-machine engine. It continuously evaluates environment variables (e.g., human presence) and manipulates the thread synchronization gates. It instantly clears the execution gate to suspend offline processing when a face is verified, or opens the gate to resume autonomous thinking when the room empties.
* **`startup()`**
  The system entry method. Commits the boot log to the journal, instantiates the background thread pool as isolated daemon processes, establishes initial thread gates, and begins the main supervisor execution loop.
* **`shutdown()`**
  An orderly termination sequence. Signals all asynchronous loops to stop, bypasses blocking thread gates safely, flushes pending data buffers to disk, and gracefully brings the cognitive layers offline.

### Executive Logic - Additional Notes

[State: ALONE] ---> (Visual Thread sees Steve) 
                         |
                         v
            Is Absence Delta > 5 Mins?
               /                  \
            (Yes)                 (No)
             /                      \
            v                        v
    [State: ENGAGED]         [State: CONVERSING]
  1. Speak Greeting           1. Silent Tracking Resumed
  2. Open 5s Mic Window       2. Await standard Wake Word
  3. Evaluate Command


The Three Operational Intent Commands
Once the microphone is open during that engagement window, core_exec.py will parse intent into one of three buckets:

* Intent A: Status Update ("What are you doing?" / "Update")
The executive reads task_progress.json and compiles a concise narrative: "I am currently 40% through your journal vectorization, and I noted a system drop on node Quantum at 14:00."

* Intent B: New Directive ("Help me with..." / "New task")
Piper pauses background tasks entirely, hands total focus over to the local LLM connection on the Quantum PC, and opens a continuous, multi-turn conversational loop.

* Intent C: Dismissal ("Go back to work" / "Clear")
Piper acknowledges: "Understood, returning to background operations." The state snaps right back to ALONE, and the Offline Task Thread is instantly un-paused to resume its goals.

### Handling Unknown Faces (Biometric Enrollment Loop)
To expand Piper's relational memory without requiring manual administrative file modification, un-indexed users are onboarded automatically via a real-time vocal conversation gate:

1. **Symmetry Filtering:** If an un-indexed profile is encountered, the system checks the facial landmark boundaries to ensure both eyes are visible and centered. This prevents capturing unusable side profiles.
2. **The Vocal Inquiry:** Once optimal frontal positioning is confirmed, the Process Thread enters the `PERCEIVING` state. Piper speaks out loud locally: *"Hello. I do not recognize your profile footprint yet. What is your name?"*
3. **Stream Interception:** The gateway server flags the incoming gRPC stream from the Pi 5. When the user responds, their voice is transcribed by Faster-Whisper, and the resulting string is intercepted directly by the visual thread to act as the user's name payload.
4. **Permanent Disk Commitment:** The visual thread associates the name string with the cached image array, writes the profile `.jpg` to the models directory, appends the event to `journal.json`, and updates her neural voice greetings for all future interactions.

---
## `🔵` Module Initialization Sequence
```
[ STEP 1 ]               [ STEP 2 ]               [ STEP 3 ]               [ STEP 4 ]
  Quantum PC  --------->   Jetson Mind  --------->   Jetson Mind  --------->  Raspberry Pi
 (Ollama Engine)          (core_exec.py Core)       (gRPC Server Port)        (body_server.py)
```

### Step 1: Brain Layer Ignition (Quantum PC)
**Action:** Launch the networked Ollama daemon on your workstation.
**Command:** (PowerShell): ollama serve (Ensure OLLAMA_HOST=0.0.0.0 is exposed in Windows system environment variables).
**Notes:** The Jetson's cognition kernel will immediately verify connection integrity to 192.168.1.150:11434 upon boot.

### Step 2: Unified Executive Core & Network Exposure (Jetson Orin NX)

> [!IMPORTANT]
> **Wayland & KVM Display Routing (JetPack 6.1 Architecture):**
> Because JetPack 6.1 leverages a native Wayland/Weston display compositor, legacy X11 windows will fail to open on default ports. Ensure your local terminal environment explicitly targets your active desktop display layer (experimentally mapped to display layer `:2`) before launching the master executive core:
> ```bash
> export DISPLAY=:2
> python3 jetson_nx_mind/src/main.py
> ```
**Action:** Run the unified runtime launch script on the Jetson.
**Notes:** This single entry point spins up the executive state manager, allocates your local camera buffers, initializes your CognitiveKernel network destinations, and exposes your gRPC service listening ports simultaneously on port 50051.

### Step 3: Sensory Binding (Raspberry Pi 5)
**Action:** Run the hardware proxy daemon on the robot's physical chassis.
**Command:** (Terminal): python3 src/body_server.py
**Notes:** This exposes the network-facing gRPC server to the local subnet, waiting for data streams from the edge node.


## Milestones and Next Steps
### Completed:
1. Core mind and body processes built and validated
2. gRPC audio stream processing built and validated

### In-Process 
1. Visual Perception: Person detection and face tracking enablement via OpenCV2 and Yolov8
2. Fine-tuning assistant behavior and prompts to more natural interaction

### Next steps
1. Enablement of OpenCode to allow code enhancements via self-update
2. Improve task tracking, memory storage and goal-driven motivation to enable autonomous behaviors
