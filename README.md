# Piper Project: Revamp
An advanced, low-latency distributed voice and vision assistant leveraging edge AI acceleration, gRPC transport, and a local large language model.

## Overview
The Piper Project is an agentic chatbot assistant split across three distinct compute tiers to optimize processing efficiency, eliminate audio latency, and achieve natural-sounding voice interactions. By treating physical I/O and cognitive AI processing as decoupled modules, the system guarantees real-time responsiveness and modular scalability.

---

## Core Goals & Performance Targets
* **Sub-Second Latency:** Total Time-to-First-Audio (TTFA) of under 1.0 second from the moment the user finishes speaking, made possible by HTTP/2 stream multiplexing.
* **High-Fidelity Audio:** Natural phrasing and intonation by offloading TTS generation entirely to the Jetson Orin NX GPU, completely unburdening the Pi 5 CPU.
* **Architecture Cleanliness:** Compile-time type-safety via gRPC Protocol Buffers, replacing loose JSON or fragile WebSocket structures.
* **Modular Design:** Clear separation of concerns allowing individual hardware tiers to be updated, scaled, or replaced without breaking the pipeline.

---

## Roadmap & Development Phases

* **Step 0: Architectural Design Planning (CURRENT PHASE)**
    * Establish system topology, device roles, data contracts, and directory mapping.
* **Step 1: OpenCode Environment Setup**
    * Initialize the OpenCode development tier on the Jetson Orin NX to manage code building, testing, and unified workspace synchronization across the stack.
* **Step 2: gRPC Framework Definition**
    * Draft `.proto` files defining the bidirectional audio/video streams and remote procedure calls.
* **Step 3: Component Implementation**
    * Build out `pi5_body` I/O routines and `jetson_nx_mind` orchestration services.

---

## System Architecture

The project distributes workloads across three hardware nodes, separating physical execution from cognitive processing:

| Tier | Component Name | Hardware | Core Functional Role | Primary Software Stack |
| :--- | :--- | :--- | :--- | :--- |
| **1. The Body** | `pi5_body` | Raspberry Pi 5 <br> SunFounder FusionHat AI <br> 7" Display <br> Logitech Webcam | **Sensory & Vocal I/O:** Audio capture/playback, UI rendering, camera streaming. | Python, PyAudio, PyQt/Tkinter, gRPC Client |
| **2. The Mind** | `jetson_nx_mind` | Jetson Orin NX (16GB) | **Cognition & Edge Acceleration:** Thinking, planning, motivation, local Whisper STT, and Piper/Kokoro TTS. | OpenCode, Faster-Whisper, Kokoro-82M, gRPC Server, CUDA/ONNX |
| **3. The Brain** | Central Compute | Quantum PC <br> NVIDIA RTX 5070 GPU | **Deep Inference:** High-parameter local LLM execution. | Ollama / vLLM, Llama-3 / Mistral |

---

## Data & Communication Flow

```text
+-----------------------------------------------------------------+
|                           pi5_body                              |
|             Raspberry Pi 5 + SunFounder FusionHat AI            |
|   (Captures raw mic input, drives 7" display & Logitech webcam) |
+-----------------------------------------------------------------+
           |                                             ^
           |                                             |
   [Raw Audio Stream]                            [Synthesized Audio]
  (gRPC / HTTP/2 Stream)                       (gRPC / HTTP/2 Stream)
           |                                             |
           v                                             |
+-----------------------------------------------------------------+
|                        jetson_nx_mind                           |
|                       Jetson Orin NX (16GB)                     |
+-----------------------------------------------------------------+
|  1. OpenCode Environment: Orchestrates building & maintenance.  |
|  2. Faster-Whisper (STT): Transcribes stream with GPU speed.   |
|  3. Cognitive Layer: Tracks context, planning, & motivation.    |
|  4. Piper / Kokoro (TTS): Synthesizes incoming response tokens. |
+-----------------------------------------------------------------+
           |                                             ^
           |                                             |
     [Text Prompt]                             [Text Response Stream]
    (gRPC / HTTP/2)                               (gRPC / HTTP/2)
           |                                             |
           v                                             |
+-----------------------------------------------------------------+
|                        CENTRAL COMPUTE                         |
|                  Quantum PC (NVIDIA RTX 5070)                   |
|               (Hosts heavy-parameter local LLM)                 |
+-----------------------------------------------------------------+
```

* Audio Capture: pi5_body captures user speech via the FusionHat mic array and streams raw audio chunks to jetson_nx_mind over a persistent, bidirectional gRPC stream.

* Transcription & Cognition: jetson_nx_mind processes the stream via hardware-accelerated Faster-Whisper. The transcribed text is evaluated against the local agentic planning state.

* Inference: The text prompt is dispatched to the Quantum PC via gRPC. The RTX 5070 processes the tokens and streams the text response back immediately.

* Vocalization: As text tokens stream into jetson_nx_mind, they are instantly fed into the local accelerated TTS engine (Piper or Kokoro-82M).

* Playback Execution: The resulting audio buffers are streamed back down the gRPC connection to pi5_body for real-time, low-latency execution through the FusionHat amplifier.

## Repository Structure
```
├── open_code_config/     # OpenCode development environments & deployment configurations
├── pi5_body/             # Runs on Raspberry Pi 5
│   ├── proto/            # Compiled gRPC stubs
│   ├── src/
│   │   ├── audio_io.py   # Handles FusionHat mic input and speaker output
│   │   ├── display.py    # 7" Display UI interface
│   │   └── camera.py     # Logitech webcam stream handler
│   └── config.json
├── jetson_nx_mind/       # Runs on Jetson Orin NX (Managed via OpenCode)
│   ├── proto/            # Master .proto definitions and compiled stubs
│   ├── src/
│   │   ├── stt_engine.py # Faster-Whisper orchestration
│   │   ├── tts_engine.py # Hardware-accelerated TTS generation
│   │   └── gateway.py    # Main gRPC Server handling pi5_body and Central Compute
│   └── models/           # Local ONNX/TensorRT models (Whisper/Kokoro)
└── README.md
```

## Development Tier: OpenCode Integration
To effectively scale the Piper Project without fragile code injection or excessive manual cut-and-paste overhead, OpenCode is deployed directly on the jetson_nx_mind tier.

Roles of the OpenCode Layer
* Central Workspace Management: Direct programmatic orchestration of compilation, testing, and synchronization tasks across both the Mind and Body tiers.
* Automated Code Compilation: Manages the compilation of .proto definition files into identical Python gRPC stubs for both nodes simultaneously.
* Incremental Testing: Executes local integration tests to guarantee that changes to code modules do not introduce latency spikes or transport protocol breakages.

## Code Standards: History & Versioning
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
## Thread Architecture & Executive Control Model

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
      - Native USB 3.0  - Wake Word Gate      - Heavy LLM Prompts
      - YOLOv8 / FaceID - Faster-Whisper STT  - Memory Sync
      - Servo Tracking  - Piper/Kokoro TTS
```

##The Process Thread (main.py Executive Core)
This is the primary thread managing Piper’s cognitive state machine, goals, and behavioral context. It operates independently of raw I/O loops and coordinates the activation of sub-threads based on four operational states:
1. State Machine
* STATE: ALONE (Proactive Processing): When no humans are detected, the thread executes internal goals, handles memory database curation, or runs low-priority background planning tasks.
* STATE: PERCEIVING (Identification): Triggered when the Visual Thread detects a human presence. The Process Thread temporarily pauses background tasks and waits for the identity verification layer.
* STATE: ENGAGED (Proactive Summary): When a recognized user (e.g., Steve) is identified, the thread checks its historical memory, calculates elapsed time since the last interaction, and actively initiates a vocal summary of standalone activities.
* STATE: CONVERSING (Reactive Interaction): Minimizes internal task overhead to focus entirely on the low-latency text-to-speech loop between the local gRPC streams and the Quantum PC.

2. The Visual Thread (Onboard Jetson NX)
* Hardware Connection: The Logitech webcam connects directly to a native USB 3.0 port on the Jetson Orin NX, utilizing direct V4L2 hardware capture buffers.
* Execution: Runs a continuous frame-capture loop directly into Jetson GPU memory. It applies localized image enhancements (CLAHE contrast normalizer and Unsharp masking) before running YOLOv8 face tracking.
* Reflex Control: When a face is actively tracked, this thread skips the master process queue and streams high-frequency servo angle floats (pan, tilt) down the local gRPC line to the Pi 5 to maintain zero-latency physical alignment.

3. The Listening & Comms Thread (gRPC Gateway)
Manages the persistent HTTP/2 gRPC channels connecting the Mind to the Body and the Central Compute tiers, enforcing strict stream gating:

* Wake Word Gate: The Raspberry Pi 5 runs a localized, low-overhead wake word listener. When triggered, it fires a lightweight event upstream. The Jetson opens the gRPC audio capture gate and instantly streams raw audio into its accelerated Faster-Whisper STT pipeline.
* Vocal Muting Gate: When the Process Thread pushes a textual response to the local TTS engine (Piper/Kokoro-82M), this thread activates a synchronization flag across the communication link to mute the Pi 5’s mic stream, preventing Piper from processing its own vocalizations.

4. The Body Hardware Proxy Daemon (pi5_body)
To ensure the physical reflexes remain entirely non-blocking, the Raspberry Pi 5 is stripped of high-level state logic. It operates a streamlined multi-threaded proxy server (body_server.py) handling three concurrent real-time tasks:

* Thread A (Audio Capture Engine): Monitors the SunFounder FusionHat mic array, maintaining a local wake-word trigger loop and forwarding raw PCM chunks upon a verified alert.
* Thread B (Audio Playback Engine): Decodes incoming binary audio streams sent from the Jetson's TTS engine and writes them directly to the FusionHat speaker amplifier.
* Thread C (Actuator Control Engine): Listens on a dedicated gRPC event loop for floating-point angular parameters, passing them instantly to the FusionHat hardware I2C/PWM registers to control physical look angles.
