# Adaptive OS Scheduler for Real-Time Systems

[![GitHub License](https://img.shields.io/github/license/savinaysingh7/Adaptive-OS-Scheduler-for-Real-Time-Systems)](https://github.com/savinaysingh7/Adaptive-OS-Scheduler-for-Real-Time-Systems)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

An interactive simulation tool for real-time scheduling algorithms with live visualization capabilities.

![Scheduler Demo](https://via.placeholder.com/800x400.png?text=Gantt+Chart+and+Metrics+Demo) <!-- Replace with actual screenshot -->

## Table of Contents
- [Features](#features)
- [Algorithms Supported](#algorithms-supported)
- [Installation](#installation)
- [Usage](#usage)
- [Directory Structure](#directory-structure)
- [Web Interface](#web-interface)
- [Metrics Calculated](#metrics-calculated)
- [Contributing](#contributing)
- [License](#license)

## Features
- 🎛️ Multi-algorithm support (9+ scheduling strategies)
- 📊 Live Gantt chart visualization
- 🌡️ Real-time core status monitoring (temperature/frequency)
- 🔄 Dynamic algorithm switching
- 🛠️ Interactive task management
- ⚡ Energy consumption tracking
- 🔒 Deadlock simulation/resolution
- 🖥️ Dual interface (GUI + CLI)

-Adaptive Scheduling Algorithm - Dynamically prioritizes tasks based on workload and system constraints.
-Real-Time Task Management - Ensures deadlines are met for high-priority processes.
-CPU Utilization Optimization - Improves CPU efficiency by reducing idle time.
-Preemptive and Non-Preemptive Modes - Supports flexible scheduling policies.
-Performance Monitoring - Includes tools for analyzing execution times and system efficiency.


## Algorithms Supported
1. First-Come-First-Served (FCFS)
2. Shortest Job First (SJF)
3. Shortest Remaining Time First (SRTF)
4. Earliest Deadline First (EDF)
5. Round Robin (RR)
6. Priority-based Scheduling
7. Rate Monotonic Scheduling (RMS)
8. Least Laxity First (LLF)
9. Hybrid Approach

## Installation
```bash
# Clone repository
git clone https://github.com/savinaysingh7/Adaptive-OS-Scheduler-for-Real-Time-Systems.git

# Install dependencies
pip install -r requirements.txt

Overview:
The Adaptive OS Scheduler for Real-Time Systems is designed to optimize task scheduling in real-time environments. By dynamically adjusting scheduling policies based on system conditions, it enhances efficiency, reduces latency, and improves real-time task execution. This project is particularly useful for embedded systems, industrial automation, and critical real-time applications.


Problem Statement:
Traditional scheduling algorithms, such as Rate-Monotonic Scheduling (RMS) and Earliest Deadline First (EDF), are often static and fail to adapt to fluctuating workloads. This project aims to develop an adaptive scheduling mechanism that dynamically adjusts task execution strategies to improve system responsiveness and efficiency.

Technologies Used:
Programming Language: Python 

Simulation & Analysis: Gantt Charts, Scheduling Simulations

Real-Time Operating Systems Concepts: Preemptive Scheduling, Priority-based Execution
