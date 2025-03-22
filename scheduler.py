import threading
import time
from typing import List, Optional
from task import Task

class AdaptiveScheduler:
    def __init__(self, algorithm: str, num_cores: int, base_context_overhead: float, status_callback, enable_fault_tolerance: bool = False):
        self.algorithm = algorithm
        self.num_cores = num_cores
        self.base_context_overhead = base_context_overhead
        self.status_callback = status_callback
        self.enable_fault_tolerance = enable_fault_tolerance
        self.ready_queue: List[Task] = []
        self.pending_tasks: List[Task] = []  # New list for tasks waiting for their arrival time
        self.running_tasks = [None] * num_cores
        self.current_time = 0.0
        self.execution_log = []
        self.core_temperatures = [20.0] * num_cores
        self.current_core_frequencies = [1.0] * num_cores
        self.paused = False
        self.step_event = threading.Event()
        self.completed_tasks = []
        self.preemptions = 0
        self.total_releases = 0
        self.time_slice = 2.0  # For RR, adjust as needed

    def add_task(self, task: Task) -> bool:
        task.remaining_time = task.execution_time
        task.next_deadline = task.arrival_time + task.relative_deadline if task.period > 0 else task.relative_deadline
        self.pending_tasks.append(task)  # Add to pending tasks instead of ready queue
        self.total_releases += 1
        return True

    def switch_algorithm(self, new_algorithm: str):
        self.algorithm = new_algorithm
        print(f"Switched to {new_algorithm}")

    def schedule(self, speed: float = 0.5):
        while self.pending_tasks or self.ready_queue or any(self.running_tasks):
            if self.paused:
                self.step_event.wait()
                self.step_event.clear()

            # Move tasks from pending to ready if their arrival time has been reached
            for task in self.pending_tasks[:]:
                if self.current_time >= task.arrival_time:
                    self.ready_queue.append(task)
                    self.pending_tasks.remove(task)

            # Schedule tasks before incrementing time
            self._release_periodic_tasks()
            self._update_running_tasks()
            self.status_callback(self.current_time)

            # Increment time after scheduling
            self.current_time += 1.0
            time.sleep(speed)  # Use the speed value from GUI

    def _release_periodic_tasks(self):
        for task in self.completed_tasks[:]:
            if task.period > 0 and self.current_time >= task.next_deadline:
                new_task = Task(
                    f"{task.name}_{self.total_releases}", task.execution_time, task.period,
                    task.relative_deadline, task.base_priority, arrival_time=self.current_time,
                    dependencies=task.dependencies, preemption_threshold=task.preemption_threshold
                )
                new_task.remaining_time = new_task.execution_time
                new_task.next_deadline = self.current_time + new_task.relative_deadline
                self.pending_tasks.append(new_task)  # Add to pending tasks
                self.total_releases += 1
                self.completed_tasks.remove(task)

    def _update_running_tasks(self):
        for i in range(self.num_cores):
            if self.running_tasks[i]:
                elapsed = self.current_time - (self.running_tasks[i].last_update_time if hasattr(self.running_tasks[i], 'last_update_time') else self.running_tasks[i].start_time)
                self.running_tasks[i].remaining_time -= 1.0
                self.running_tasks[i].last_update_time = self.current_time
                if self.running_tasks[i].remaining_time <= 0:
                    self.execution_log.append((self.running_tasks[i].name, self.running_tasks[i].start_time, self.current_time, i, None))
                    self.completed_tasks.append(self.running_tasks[i])
                    self.running_tasks[i].completion_time = self.current_time
                    self.running_tasks[i] = None
                elif self.algorithm == 'RR' and elapsed >= self.time_slice:
                    self.ready_queue.append(self.running_tasks[i])
                    self.execution_log.append((self.running_tasks[i].name, self.running_tasks[i].start_time, self.current_time, i, "Time Slice"))
                    self.running_tasks[i] = None

        if self.algorithm == 'FCFS':
            self._schedule_fcfs()
        elif self.algorithm == 'SJF':
            self._schedule_sjf()
        elif self.algorithm == 'SRTF':
            self._schedule_srtf()
        elif self.algorithm == 'EDF':
            self._schedule_edf()
        elif self.algorithm == 'RR':
            self._schedule_rr()
        elif self.algorithm == 'PRIORITY':
            self._schedule_priority()
        elif self.algorithm == 'RMS':
            self._schedule_rms()
        elif self.algorithm == 'LLF':
            self._schedule_llf()
        elif self.algorithm == 'HYBRID':
            self._schedule_hybrid()

    def _schedule_fcfs(self):
        available_cores = [i for i, task in enumerate(self.running_tasks) if task is None]
        for core in available_cores:
            if self.ready_queue:
                task = self.ready_queue.pop(0)
                task.start_time = self.current_time
                task.last_update_time = self.current_time
                self.running_tasks[core] = task

    def _schedule_sjf(self):
        available_cores = [i for i, task in enumerate(self.running_tasks) if task is None]
        if available_cores and self.ready_queue:
            self.ready_queue.sort(key=lambda x: x.execution_time)
            for core in available_cores:
                if self.ready_queue:
                    task = self.ready_queue.pop(0)
                    task.start_time = self.current_time
                    task.last_update_time = self.current_time
                    self.running_tasks[core] = task

    def _schedule_srtf(self):
        for i in range(self.num_cores):
            if self.ready_queue:
                current_task = self.running_tasks[i]
                min_remaining = current_task.remaining_time if current_task else float('inf')
                shortest_task = None
                shortest_idx = -1
                for idx, task in enumerate(self.ready_queue):
                    if task.remaining_time < min_remaining:
                        min_remaining = task.remaining_time
                        shortest_task = task
                        shortest_idx = idx
                if shortest_task and (not current_task or shortest_task.remaining_time < current_task.remaining_time):
                    if current_task:
                        self.ready_queue.append(current_task)
                        self.preemptions += 1
                        self.execution_log.append((current_task.name, current_task.start_time, self.current_time, i, "Preempted"))
                    task = self.ready_queue.pop(shortest_idx)
                    task.start_time = self.current_time
                    task.last_update_time = self.current_time
                    self.running_tasks[i] = task

    def _schedule_edf(self):
        available_cores = [i for i, task in enumerate(self.running_tasks) if task is None]
        if available_cores and self.ready_queue:
            self.ready_queue.sort(key=lambda x: x.next_deadline)
            for core in available_cores:
                if self.ready_queue:
                    task = self.ready_queue.pop(0)
                    task.start_time = self.current_time
                    task.last_update_time = self.current_time
                    self.running_tasks[core] = task

    def _schedule_rr(self):
        available_cores = [i for i, task in enumerate(self.running_tasks) if task is None]
        for core in available_cores:
            if self.ready_queue:
                task = self.ready_queue.pop(0)
                task.start_time = self.current_time
                task.last_update_time = self.current_time
                self.running_tasks[core] = task

    def _schedule_priority(self):
        available_cores = [i for i, task in enumerate(self.running_tasks) if task is None]
        if available_cores and self.ready_queue:
            self.ready_queue.sort(key=lambda x: x.base_priority)  # 0 = highest priority
            for core in available_cores:
                if self.ready_queue:
                    task = self.ready_queue.pop(0)
                    task.start_time = self.current_time
                    task.last_update_time = self.current_time
                    self.running_tasks[core] = task

    def _schedule_rms(self):
        # Rate Monotonic: Priority based on period (shorter period = higher priority)
        available_cores = [i for i, task in enumerate(self.running_tasks) if task is None]
        if available_cores and self.ready_queue:
            self.ready_queue.sort(key=lambda x: x.period if x.period > 0 else float('inf'))
            for core in available_cores:
                if self.ready_queue:
                    task = self.ready_queue.pop(0)
                    task.start_time = self.current_time
                    task.last_update_time = self.current_time
                    self.running_tasks[core] = task

    def _schedule_llf(self):
        # Least Laxity First: Priority based on slack time (deadline - remaining time)
        available_cores = [i for i, task in enumerate(self.running_tasks) if task is None]
        if available_cores and self.ready_queue:
            self.ready_queue.sort(key=lambda x: (x.next_deadline - self.current_time) - x.remaining_time)
            for core in available_cores:
                if self.ready_queue:
                    task = self.ready_queue.pop(0)
                    task.start_time = self.current_time
                    task.last_update_time = self.current_time
                    self.running_tasks[core] = task

    def _schedule_hybrid(self):
        # Simple hybrid: EDF + Priority
        available_cores = [i for i, task in enumerate(self.running_tasks) if task is None]
        if available_cores and self.ready_queue:
            self.ready_queue.sort(key=lambda x: (x.next_deadline, x.base_priority))
            for core in available_cores:
                if self.ready_queue:
                    task = self.ready_queue.pop(0)
                    task.start_time = self.current_time
                    task.last_update_time = self.current_time
                    self.running_tasks[core] = task

    def compute_metrics(self):
        total_turnaround = 0.0
        total_wait = 0.0
        total_misses = 0
        cpu_busy_time = sum(end - start for _, start, end, _, _ in self.execution_log)
        cpu_util = (cpu_busy_time / (self.current_time * self.num_cores)) * 100 if self.current_time > 0 else 0.0
        avg_temp = sum(self.core_temperatures) / self.num_cores if self.num_cores > 0 else 0.0

        for task in self.completed_tasks:
            turnaround = task.completion_time - task.arrival_time
            wait = turnaround - task.execution_time
            print(f"Task {task.name}: Arrival={task.arrival_time}, Completion={task.completion_time}, Exec={task.execution_time}, Turnaround={turnaround}, Wait={wait}")
            total_turnaround += turnaround
            total_wait += wait
            if task.completion_time > task.next_deadline:
                total_misses += 1

        avg_turnaround = total_turnaround / len(self.completed_tasks) if self.completed_tasks else 0.0
        avg_wait = total_wait / len(self.completed_tasks) if self.completed_tasks else 0.0
        miss_ratio = total_misses / self.total_releases if self.total_releases > 0 else 0.0

        return {
            'avg_turnaround': avg_turnaround,
            'avg_wait': avg_wait,
            'cpu_util': cpu_util,
            'energy_consumed': 0.0,
            'avg_temperature': avg_temp,
            'migrations': 0,
            'preemptions': self.preemptions,
            'faults_detected': 0,
            'total_misses': total_misses,
            'hard_misses': 0,
            'miss_ratio': miss_ratio,
            'total_releases': self.total_releases
        }

    def visualize(self):
        print("Visualization placeholder")