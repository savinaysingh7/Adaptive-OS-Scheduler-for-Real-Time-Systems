# task.py
import random
from typing import List, Optional, Tuple

from config import MAX_PRIORITY_LEVELS

def context_switch_overhead(base_overhead: float, task_load: int) -> float:
    """Dynamic context switch overhead based on system load."""
    load_factor = min(task_load / 10, 1.0)  # Normalize task load (0 to 1)
    return base_overhead * (1 + load_factor * 0.2)  # Increase overhead with load


class Task:
    """Represents a task with real-time properties."""
    def __init__(self, name: str, execution_time: float, period: int, relative_deadline: int,
                 base_priority: int, arrival_time: float = 0.0, dependencies: Optional[List[str]] = None,
                 is_interrupt: bool = False, criticality: str = 'SOFT', energy_usage: float = 1.0,
                 memory_usage: float = 1.0, affinity: Optional[List[int]] = None,
                 preemption_threshold: int = MAX_PRIORITY_LEVELS) -> None:
        self.name = name
        self.execution_time = execution_time
        self.remaining_time = execution_time
        self.period = period
        self.relative_deadline = relative_deadline
        self.base_priority = min(base_priority, MAX_PRIORITY_LEVELS - 1)
        self.priority = self.base_priority
        self.arrival_time = arrival_time  # User-defined arrival time
        self.dependencies = dependencies if dependencies else []
        self.is_interrupt = is_interrupt
        self.last_run_time = 0.0
        self.next_release = arrival_time if period > 0 else float('inf')
        self.absolute_deadline = arrival_time + relative_deadline if period > 0 else relative_deadline
        self.worst_case_execution_time = execution_time * 1.5
        self.best_case_execution_time = execution_time * 0.8
        self.criticality = criticality.upper()
        self.energy_usage = energy_usage
        self.memory_usage = memory_usage
        self.affinity = affinity
        self.preemption_threshold = min(preemption_threshold, MAX_PRIORITY_LEVELS - 1)
        self.response_times: List[float] = []
        self.preemption_count = 0
        self.blocking_time = 0.0
        self.laxity: float = 0.0
        self.utility = 1.0
        self.execution_history: List[Tuple[float, float]] = []
        self.acquired_resources: List[str] = []
        self.current_core: Optional[int] = None
        self.replica: Optional["Task"] = None
        self.backup_triggered = False

    def __lt__(self, other: "Task") -> bool:
        """Compare tasks for priority queue ordering."""
        if self.is_interrupt != other.is_interrupt:
            return self.is_interrupt
        return self.priority < other.priority

    def release(self, current_time: float) -> None:
        """Release or re-release a task at the given time."""
        self.last_run_time = current_time
        self.remaining_time = random.uniform(self.best_case_execution_time, self.worst_case_execution_time)
        self.next_release = current_time + self.period if self.period > 0 else float('inf')
        self.absolute_deadline = current_time + self.relative_deadline
        self.laxity = self.relative_deadline - self.remaining_time
        self.backup_triggered = False  # Reset on release

    def reset(self, current_time: float) -> None:
        """Reset task state for next execution."""
        self.release(current_time)
        self.priority = self.base_priority

    def update_laxity(self, current_time: float) -> float:
        """Update and return the task's laxity."""
        self.laxity = self.absolute_deadline - current_time - self.remaining_time
        return self.laxity

    def __str__(self):
        return (f"Task(name={self.name}, exec_time={self.execution_time}, period={self.period}, "
                f"deadline={self.relative_deadline}, priority={self.base_priority}, "
                f"arrival_time={self.arrival_time})")