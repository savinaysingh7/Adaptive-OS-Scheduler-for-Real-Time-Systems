# Adaptive OS Scheduler for Real-Time Systems

An interactive Python-based simulator for experimenting with real-time CPU scheduling strategies on multi-core systems. The project provides both a desktop GUI and a command-line interface for creating tasks, running scheduling simulations, visualizing execution timelines, and inspecting system metrics such as CPU utilization, energy consumption, temperature, preemptions, and deadline misses.

This repository is best understood as a teaching and prototyping tool for operating systems and real-time scheduling concepts rather than a production RTOS implementation.

## Features

- Supports multiple scheduling algorithms in one simulator:
  - FCFS
  - SJF
  - SRTF
  - EDF
  - Round Robin
  - Priority Scheduling
  - RMS
  - LLF
  - Hybrid deadline-plus-priority scheduling
- Simulates multi-core task execution.
- Models periodic and one-shot tasks with arrival time, deadline, and priority settings.
- Includes a desktop GUI for task creation, editing, deletion, and live simulation control.
- Shows live visualizations for:
  - Gantt-style execution timeline
  - ready/running/pending queue state
  - per-core utilization and temperature trends
- Tracks runtime metrics such as turnaround time, wait time, deadline misses, preemptions, energy use, and average temperature.
- Supports pause, resume, single-step execution, algorithm switching, and result export from the GUI.
- Provides a CLI mode for lightweight scripted runs and quick experimentation.

## Tech Stack

- Python 3
- Tkinter for the desktop UI
- `ttkthemes` for themed widgets
- Matplotlib for charts and exported visualizations
- Seaborn for color palettes
- NumPy as a plotting/data dependency

## Project Structure

```text
Adaptive-OS-Scheduler-for-Real-Time-Systems/
|-- config.py           # Global scheduler and simulation constants
|-- gui.py              # Tkinter GUI and live visualization dashboard
|-- main.py             # Application entry point for GUI and CLI modes
|-- resource_1.py       # Resource abstraction with priority-ceiling metadata
|-- scheduler.py        # AdaptiveScheduler implementation and algorithms
|-- task.py             # Task model and task-related helpers
|-- tests.py            # Basic unit tests
|-- visualization.py    # Standalone plotting utilities
|-- requirements.txt    # Python dependencies
`-- README.md
```

## How It Works

The simulator maintains pending, ready, running, and completed task sets. Tasks are released based on arrival time, dispatched across multiple cores according to the selected scheduling policy, and re-released if they are periodic. During simulation, the scheduler also tracks:

- execution intervals for Gantt visualization
- CPU utilization across cores
- temperature changes per core
- estimated energy consumption
- preemptions and missed deadlines

## Installation

### Prerequisites

- Python 3.10+ recommended
- A desktop environment if you want to use the GUI

### Setup

```bash
git clone https://github.com/savinaysingh7/Adaptive-OS-Scheduler-for-Real-Time-Systems.git
cd Adaptive-OS-Scheduler-for-Real-Time-Systems
python -m venv .venv
```

Activate the virtual environment:

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux or macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Notes:

- `tkinter` is included with many Python distributions, but on some systems it may need to be installed separately.

## Usage

### Run the GUI

Start the desktop simulator:

```bash
python main.py
```

From the GUI you can:

- choose the scheduling algorithm
- set the number of CPU cores
- add, edit, or remove tasks
- start, pause, resume, or step through the simulation
- export the current visualization as an image

### Run the CLI

If any command-line arguments are provided, the app switches to CLI mode.

```bash
python main.py --algorithm EDF --cores 2 --tasks "T1 2 5 5 1 0" "T2 1 4 4 0 0"
```

Task format:

```text
name execution_time period relative_deadline priority [arrival_time]
```

Example:

- `T1 2 5 5 1 0` means:
  - task name: `T1`
  - execution time: `2`
  - period: `5`
  - relative deadline: `5`
  - priority: `1`
  - arrival time: `0`

CLI output includes:

- execution log per core
- turnaround and wait statistics
- CPU utilization
- total energy consumed
- average temperature
- preemption count
- deadline miss metrics

## Example Workflow

### GUI

1. Launch `python main.py`.
2. Select an algorithm such as `EDF` or `RMS`.
3. Add a few tasks with different execution times, deadlines, and priorities.
4. Start the simulation and observe the live charts.
5. Review the summary metrics shown when the run completes.

### CLI

```bash
python main.py --algorithm PRIORITY --cores 2 --tasks "Sensor 2 10 10 0 0" "Logger 3 12 12 2 1"
```

Expected behavior:

- tasks are added to the scheduler
- the simulation runs until all released jobs finish
- the terminal prints the execution timeline and aggregate metrics

## Supported Algorithms

- `FCFS`
- `SJF`
- `SRTF`
- `EDF`
- `RR`
- `PRIORITY`
- `RMS`
- `LLF`
- `HYBRID`

## Configuration

Simulation constants are defined in [`config.py`](./config.py), including:

- maximum priority levels
- base context-switch overhead
- interrupt probability
- frequency bounds
- temperature thresholds

You can tune these values to experiment with different scheduling and system conditions.

## Tests

Basic unit tests live in [`tests.py`](./tests.py).

```bash
python -m unittest tests.py
```

At the time of writing, the test file does not fully match the current `AdaptiveScheduler` constructor and may require updates before it passes cleanly.

## License

This repository does not currently include a `LICENSE` file in the project root.

Until a license is added by the maintainer, the default legal position is that the code is not licensed for reuse beyond what is permitted by applicable law. If this project is intended for open-source distribution, add a license file such as MIT, Apache-2.0, or GPL-3.0 and update this section accordingly.
