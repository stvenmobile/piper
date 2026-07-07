markdown
# Piper Project: Autonomous Dynamic World-Modeling

An agentic, visually-aware embodied AI leveraging a distributed, cross-platform ROS 2 network, edge vision acceleration (Jetson Orin NX), local heavy inference (UM790 Pro), and OpenCode orchestration to explore and define a dynamic world model based on real-time video streaming data.

## Introduction

Piper is an advanced autonomous system designed to explore and understand its environment through real-time video data. It utilizes a dual-node Jazzy architecture, leveraging ROS 2 for communication between nodes. Piper's capabilities include dynamic state management, edge computing, and high-level cognitive processing, all orchestrated by OpenCode.

## Dependencies

To run Piper, you will need the following dependencies:
- ROS 2 (specifically rclpy)
- Eclipse CycloneDDS
- NVIDIA Jetson Orin NX for hardware acceleration
- UM790 Pro workstation for cognitive processing
- Python 3.8 or later
- SQLite for session persistence

## Installation Instructions

1. **Set up your ROS 2 workspace:**