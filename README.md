# Piper Project: Revamp
An advanced, low-latency distributed voice and vision assistant leveraging edge AI acceleration, gRPC transport, and a local large language model.

## Overview
The Piper Project is an agentic chatbot assistant split across three distinct compute tiers to optimize processing efficiency, eliminate audio latency, and achieve natural-sounding voice interactions. By treating physical I/O and cognitive AI processing as decoupled modules, the system guarantees real-time responsiveness and modular scalability.

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

1. Audio Capture: pi5_body captures user speech via the FusionHat mic array and streams raw audio chunks to jetson_nx_mind over a persistent, bidirectional gRPC stream.
2. Transcription & Cognition: jetson_nx_mind processes the stream via hardware-accelerated Faster-Whisper. The transcribed text is evaluated against the local agentic planning state.
3. Inference: The text prompt is dispatched to the Quantum PC via gRPC. The RTX 5070 processes the tokens and streams the text response back immediately.
4. Vocalization: As text tokens stream into jetson_nx_mind, they are instantly fed into the local accelerated TTS engine (Piper or Kokoro-82M).
5. Playback Execution: The resulting audio buffers are streamed back down the gRPC connection to pi5_body for real-time, low-latency execution through the FusionHat amplifier.

---

## Repository Structure

```text
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

## Core Goals & Performance Targets
1. Sub-Second Latency: Total Time-to-First-Audio (TTFA) of under 1.0 second from the moment the user finishes speaking.
2. High-Fidelity Audio: Natural phrasing and intonation by offloading TTS to the Jetson's GPU instead of relying on the Pi's CPU.
3. Modular Design: Clear separation of concerns allowing individual hardware tiers to be updated or replaced without breaking the pipeline.

## Development Tier: OpenCode Integration
To effectively scale the Piper Project without fragile code injection or excessive manual cut-and-paste overhead, OpenCode is deployed directly on the jetson_nx_mind tier.

Roles of the OpenCode Layer:
1. Central Workspace Management: Direct programmatic orchestration of compilation, testing, and synchronization tasks across both the Mind and Body tiers.
2. Automated Code Compilation: Manages the compilation of .proto definition files into identical Python gRPC stubs for both nodes simultaneously.
3. Incremental Testing: Executes local integration tests to guarantee that changes to code modules do not introduce latency spikes or transport protocol breakages.
4. Code Standards: History & Versioning
Every program, script, and component within this repository must include a standardized file header tracking versioning, changes, and release notes. This maintains absolute transparency as the software footprint scales.

### Standard Header Format:
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

## Core Goals & Performance Targets
1. Sub-Second Latency: Total Time-to-First-Audio (TTFA) of under 1.0 second from the moment the user finishes speaking, made possible by HTTP/2 stream multiplexing.
2. High-Fidelity Audio: Natural phrasing and intonation by offloading TTS generation entirely to the Jetson GPU.
3. Architecture Cleanliness: Compile-time type-safety via gRPC Protocol Buffers, replacing loose JSON/WebSocket structures.
