# OpenCode System Rules for Project Piper

You are executing within the `piper` repository. You must adhere to the strict structural boundaries, nomenclature, and coding standards outlined below for every single code operation.

## Nomenclature & Architectural Scope

1. **`pi5_body` Tier:** Handles the physical I/O infrastructure. This includes microphone audio capture (SunFounder FusionHat), speaker playback, webcam operations (Logitech), and UI presentation (7" Display).
2. **`jetson_nx_mind` Tier:** Handles local intelligence, coordination, and edge acceleration. This includes local Speech-to-Text (`Faster-Whisper`), local Text-to-Speech synthesis (`Piper` / `Kokoro-82M`), state evaluation, and gRPC orchestration.
3. **Transport Protocol:** All data exchange between `pi5_body` and `jetson_nx_mind` MUST utilize strongly-typed gRPC bidirectional streams over HTTP/2. Raw WebSockets or un-typed JSON messaging are strictly prohibited.

## Mandatory Coding Standards & Release History

Every single new script, source file, compilation target, or module created or modified within this workspace MUST begin with the standardized file header format. 

You must strictly bump semantic versioning and append clear change notes whenever modifying an existing module.

### Mandatory File Header Block:
```python
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

## Tooling Execution Constraints
* Never attempt to directly execute cross-compiled scripts designated for the pi5_body node directly on the Jetson Orin NX host unless performing mock unit testing.
* When executing code updates via the build agent, verify file edits do not compromise the low-latency goal (TTFA < 1.0s).


---

