import threading
import time
from typing import List, Optional
from task import Task

class AdaptiveScheduler:
    def __init__(self, algorithm: str, num_cores: int, base_context_overhead: float, status_callback, enable_fault_tolerance: bool = False):
        """
        Initialize the AdaptiveScheduler with energy and temperature tracking.
        
        Args:
            algorithm (str): Scheduling algorithm (e.g., 'FCFS', 'SJF', etc.)
            num_cores (int): Number of CPU cores
            base_context_overhead (float): Overhead for context switching
            status_callback: Function to call with status updates
            enable_fault_tolerance (bool): Whether to enable fault tolerance
        """
        self.algorithm = algorithm
        self.num_cores = num_cores
        self.base_context_overhead = base_context_overhead
        self.status_callback = status_callback
        self.enable_fault_tolerance = enable_fault_tolerance
        self.ready_queue: List[Task] = []
        self.pending_tasks: List[Task] = []  # Tasks waiting for arrival time
        self.running_tasks = [None] * num_cores
        self.current_time = 0.0
        self.execution_log = []
        self.core_temperatures = [20.0] * num_cores  # Initial temperature at 20°C
        self.current_core_frequencies = [1.0] * num_cores  # Fixed frequency in GHz
        self.paused = False
        self.step_event = threading.Event()
        self.completed_tasks = []
        self.preemptions = 0
        self.total_releases = 0
        self.time_slice = 2.0  # Time slice for Round Robin
        
        # Energy and temperature constants
        self.total_energy = 0.0  # Total energy consumed in watt-seconds (Joules)
        self.ROOM_TEMPERATURE = 20.0  # °C
        self.MAX_TEMPERATURE = 100.0  # °C
        self.HEATING_RATE = 5.0  # °C per second when busy
        self.COOLING_RATE = 2.0  # °C per second when idle
        self.IDLE_POWER = 2.0  # Watts when idle
        self.BUSY_POWER_BASE = 5.0  # Base power in Watts when busy
        self.BUSY_POWER_PER_FREQUENCY = 10.0  # Watts per GHz when busy

    def add_task(self, task: Task) -> bool:
        """Add a task to the pending queue."""
        task.remaining_time = task.execution_time
        task.next_deadline = task.arrival_time + task.relative_deadline if task.period > 0 else task.relative_deadline
        self.pending_tasks.append(task)
        self.total_releases += 1
        return True

    def switch_algorithm(self, new_algorithm: str):
        """Switch the scheduling algorithm."""
        self.algorithm = new_algorithm
        print(f"Switched to {new_algorithm}")

    def run(self):
        """
        Run the scheduler simulation for CLI mode.
        This method avoids GUI-specific features like time.sleep and status callbacks.
        """
        while self.pending_tasks or self.ready_queue or any(self.running_tasks):
            # Move tasks from pending to ready based on arrival time
            for task in self.pending_tasks[:]:
                if self.current_time >= task.arrival_time:
                    self.ready_queue.append(task)
                    self.pending_tasks.remove(task)

            # Update tasks and schedule new ones
            self._release_periodic_tasks()
            self._update_running_tasks()

            # Increment time
            self.current_time += 1.0

    def schedule(self, speed: float = 0.5):
        """Run the scheduler simulation for GUI mode."""
        while self.pending_tasks or self.ready_queue or any(self.running_tasks):
            if self.paused:
                self.step_event.wait()
                self.step_event.clear()

            # Move tasks from pending to ready based on arrival time
            for task in self.pending_tasks[:]:
                if self.current_time >= task.arrival_time:
                    self.ready_queue.append(task)
                    self.pending_tasks.remove(task)

            # Update tasks and schedule new ones
            self._release_periodic_tasks()
            self._update_running_tasks()
            self.status_callback(self.current_time)

            # Increment time
            self.current_time += 1.0
            time.sleep(speed)

    def _release_periodic_tasks(self):
        """Release periodic tasks when their next deadline is reached."""
        for task in self.completed_tasks[:]:
            if task.period > 0 and self.current_time >= task.next_deadline:
                print(f"Re-releasing task {task.name} at time {self.current_time}")
                new_task = Task(
                    f"{task.name}_{self.total_releases}", task.execution_time, task.period,
                    task.relative_deadline, task.base_priority, arrival_time=self.current_time,
                    dependencies=task.dependencies, preemption_threshold=task.preemption_threshold
                )
                new_task.remaining_time = new_task.execution_time
                new_task.next_deadline = self.current_time + new_task.relative_deadline
                self.pending_tasks.append(new_task)
                self.total_releases += 1
                self.completed_tasks.remove(task)

    def _update_running_tasks(self):
        """
        Update running tasks, calculate energy consumption, and adjust core temperatures
        based on the state during the previous time step [t-1, t).
        """
        # Update energy and temperature based on what was running
        for i in range(self.num_cores):
            if self.running_tasks[i]:
                # Core was busy during [t-1, t)
                self.core_temperatures[i] += self.HEATING_RATE
                if self.core_temperatures[i] > self.MAX_TEMPERATURE:
                    self.core_temperatures[i] = self.MAX_TEMPERATURE
                power = self.BUSY_POWER_BASE + self.current_core_frequencies[i] * self.BUSY_POWER_PER_FREQUENCY
                self.total_energy += power * 1.0  # Time step is 1.0 second
            else:
                # Core was idle during [t-1, t)
                self.core_temperatures[i] -= self.COOLING_RATE
                if self.core_temperatures[i] < self.ROOM_TEMPERATURE:
                    self.core_temperatures[i] = self.ROOM_TEMPERATURE
                power = self.IDLE_POWER
                self.total_energy += power * 1.0

        # Update the state of running tasks
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

        # Schedule new tasks based on algorithm
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
        """First-Come, First-Served scheduling."""
        available_cores = [i for i, task in enumerate(self.running_tasks) if task is None]
        for core in available_cores:
            if self.ready_queue:
                task = self.ready_queue.pop(0)
                task.start_time = self.current_time
                task.last_update_time = self.current_time
                self.running_tasks[core] = task

    def _schedule_sjf(self):
        """Shortest Job First scheduling."""
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
        """Shortest Remaining Time First scheduling."""
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
        """Earliest Deadline First scheduling."""
        for i in range(self.num_cores):
            if self.ready_queue:
                self.ready_queue.sort(key=lambda x: x.next_deadline)
                if self.running_tasks[i]:
                    if self.ready_queue[0].next_deadline < self.running_tasks[i].next_deadline:
                        preempted_task = self.running_tasks[i]
                        self.ready_queue.append(preempted_task)
                        self.preemptions += 1
                        self.execution_log.append((preempted_task.name, preempted_task.start_time, self.current_time, i, "Preempted"))
                        new_task = self.ready_queue.pop(0)
                        new_task.start_time = self.current_time
                        new_task.last_update_time = self.current_time
                        self.running_tasks[i] = new_task
                else:
                    task = self.ready_queue.pop(0)
                    task.start_time = self.current_time
                    task.last_update_time = self.current_time
                    self.running_tasks[i] = task

    def _schedule_rr(self):
        """Round Robin scheduling."""
        available_cores = [i for i, task in enumerate(self.running_tasks) if task is None]
        for core in available_cores:
            if self.ready_queue:
                task = self.ready_queue.pop(0)
                task.start_time = self.current_time
                task.last_update_time = self.current_time
                self.running_tasks[core] = task

    def _schedule_priority(self):
        """Priority-based scheduling (lower number = higher priority)."""
        available_cores = [i for i, task in enumerate(self.running_tasks) if task is None]
        if available_cores and self.ready_queue:
            self.ready_queue.sort(key=lambda x: x.base_priority)
            for core in available_cores:
                if self.ready_queue:
                    task = self.ready_queue.pop(0)
                    task.start_time = self.current_time
                    task.last_update_time = self.current_time
                    self.running_tasks[core] = task

    def _schedule_rms(self):
        """Rate Monotonic Scheduling (shorter period = higher priority)."""
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
        """Least Laxity First scheduling."""
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
        """Hybrid scheduling combining EDF and Priority."""
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
        """Compute and return scheduling metrics including energy and temperature."""
        total_turnaround = 0.0
        total_wait = 0.0
        total_misses = 0
        total_completion_time = 0.0
        cpu_busy_time = sum(end - start for _, start, end, _, _ in self.execution_log)
        cpu_util = (cpu_busy_time / (self.current_time * self.num_cores)) * 100 if self.current_time > 0 else 0.0
        avg_temp = sum(self.core_temperatures) / self.num_cores if self.num_cores > 0 else 0.0

        for task in self.completed_tasks:
            turnaround = task.completion_time - task.arrival_time
            wait = turnaround - task.execution_time
            total_completion_time = max(total_completion_time, task.completion_time)
            print(f"Task {task.name}: Arrival={task.arrival_time}, Completion={task.completion_time}, Exec={task.execution_time}, Turnaround={turnaround}, Wait={wait}")
            total_turnaround += turnaround
            total_wait += wait
            if task.completion_time > task.next_deadline:
                total_misses += 1

        avg_turnaround = total_turnaround / len(self.completed_tasks) if self.completed_tasks else 0.0
        avg_wait = total_wait / len(self.completed_tasks) if self.completed_tasks else 0.0
        miss_ratio = total_misses / self.total_releases if self.total_releases > 0 else 0.0

        return {
            'total_completion_time': total_completion_time,
            'avg_turnaround': avg_turnaround,
            'avg_wait': avg_wait,
            'cpu_util': cpu_util,
            'energy_consumed': self.total_energy,
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
        """Placeholder for visualization."""
        print("Visualization placeholder")


"""""def hybrid_scheduler(tasks, current_time, resource_manager):
    
    Smart task scheduler that balances urgency, fairness, and efficiency:
    - Urgency: Prioritizes tasks with near deadlines.
    - Fairness: Prevents starvation by giving weight to waiting tasks.
    - Efficiency: Prefers shorter tasks to improve throughput.
    - Adapts dynamically to system load and available resources.
    

    # Find tasks that have arrived and still need to be completed
    ready_tasks = [task for task in tasks if current_time >= task.arrival_time and task.remaining_time > 0]
    
    if not ready_tasks:
        return None  # No tasks to schedule right now

    # Adjust weight distribution based on system load (number of active tasks)
    task_count = len(ready_tasks)
    urgency_weight = 0.5 + (0.1 * (task_count / 10))  # More tasks = higher urgency
    fairness_weight = 0.3 + (0.1 * (task_count / 15))  # More tasks = fairness matters more
    efficiency_weight = 1.0 - (urgency_weight + fairness_weight)  # Remaining weight for short tasks

    # Find the max wait time and max burst time for normalization
    longest_wait = max((current_time - task.arrival_time for task in ready_tasks), default=1)
    longest_burst = max((task.remaining_time for task in ready_tasks), default=1)

    best_task = None
    highest_priority = float('-inf')

    for task in ready_tasks:
       
        time_left = task.deadline - current_time
        urgency_score = 1.0 if time_left <= 0 else min(1.0 / (time_left + 1), 1.0)

      
        wait_time = current_time - task.arrival_time
        fairness_score = wait_time / longest_wait if longest_wait > 0 else 0

      
        efficiency_score = 1.0 - (task.remaining_time / longest_burst) if longest_burst > 0 else 0

        if wait_time > 20:
            fairness_score += 0.2  

      
        priority_score = (
            (urgency_weight * urgency_score) +
            (fairness_weight * fairness_score) +
            (efficiency_weight * efficiency_score)
        )

       
        if resource_manager.is_task_runnable(task):
            if priority_score > highest_priority:
                highest_priority = priority_score
                best_task = task  # Pick the task with the best score

    return best_task  #
"""""
