import tkinter as tk
from tkinter import messagebox, ttk
import threading
import time
from typing import Optional, List
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from task import Task
from scheduler import AdaptiveScheduler
from config import DEFAULT_BASE_CONTEXT_SWITCH_OVERHEAD, MAX_TEMPERATURE

# Tooltip class for hover hints
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event):
        if self.tip_window or not self.text:
            return
        x, y = self.widget.winfo_rootx() + 25, self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT, background="#ffffe0", relief=tk.SOLID, borderwidth=1)
        label.pack()

    def hide_tip(self, event):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class TaskDialog(tk.Toplevel):
    def __init__(self, parent, callback, existing_task: Optional[Task] = None):
        super().__init__(parent)
        self.title("Task Editor" if existing_task else "Add Task")
        self.callback = callback
        self.task = existing_task
        self.geometry("300x400")  # Increased height for new field

        tk.Label(self, text="Task Name:").pack(pady=2)
        self.name_entry = tk.Entry(self)
        self.name_entry.pack()
        self.name_entry.insert(0, existing_task.name if existing_task else f"T{int(time.time())%10000}")

        tk.Label(self, text="Arrival Time (ticks):").pack(pady=2)
        self.arrival_entry = tk.Entry(self)
        self.arrival_entry.pack()
        self.arrival_entry.insert(0, str(existing_task.arrival_time) if existing_task else "0")

        tk.Label(self, text="Exec Time (ticks):").pack(pady=2)
        self.exec_entry = tk.Entry(self)
        self.exec_entry.pack()
        self.exec_entry.insert(0, str(existing_task.execution_time) if existing_task else "5")

        tk.Label(self, text="Period (ticks, 0=one-shot):").pack(pady=2)
        self.period_entry = tk.Entry(self)
        self.period_entry.pack()
        self.period_entry.insert(0, str(existing_task.period) if existing_task else "0")

        tk.Label(self, text="Deadline (ticks):").pack(pady=2)
        self.deadline_entry = tk.Entry(self)
        self.deadline_entry.pack()
        self.deadline_entry.insert(0, str(existing_task.relative_deadline) if existing_task else "10")

        tk.Label(self, text="Priority (0=highest):").pack(pady=2)
        self.priority_entry = tk.Entry(self)
        self.priority_entry.pack()
        self.priority_entry.insert(0, str(existing_task.base_priority) if existing_task else "2")

        tk.Label(self, text="Preemption Threshold:").pack(pady=2)
        self.threshold_entry = tk.Entry(self)
        self.threshold_entry.pack()
        self.threshold_entry.insert(0, str(existing_task.preemption_threshold) if existing_task else "32")

        tk.Label(self, text="Dependencies:").pack(pady=2)
        self.deps_entry = tk.Entry(self)
        self.deps_entry.pack()
        self.deps_entry.insert(0, ", ".join(existing_task.dependencies) if existing_task else "")

        tk.Button(self, text="Save" if existing_task else "Add", command=self.on_save).pack(pady=10)

    def on_save(self):
        try:
            name = self.name_entry.get().strip()
            if not name:
                raise ValueError("Task name is required.")
            
            arrival_time_str = self.arrival_entry.get().strip()
            if not arrival_time_str:
                raise ValueError("Arrival time is required.")
            arrival_time = float(arrival_time_str)
            if arrival_time < 0:
                raise ValueError("Arrival time must be non-negative.")

            exec_time_str = self.exec_entry.get().strip()
            if not exec_time_str:
                raise ValueError("Execution time is required.")
            exec_time = float(exec_time_str)
            if exec_time <= 0:
                raise ValueError("Execution time must be greater than 0.")

            period_str = self.period_entry.get().strip()
            if not period_str:
                raise ValueError("Period is required.")
            period = int(period_str)

            deadline_str = self.deadline_entry.get().strip()
            if not deadline_str:
                raise ValueError("Deadline is required.")
            deadline = int(deadline_str)
            if deadline <= 0:
                raise ValueError("Deadline must be greater than 0.")

            priority_str = self.priority_entry.get().strip()
            if not priority_str:
                raise ValueError("Priority is required.")
            priority = int(priority_str)

            threshold_str = self.threshold_entry.get().strip()
            if not threshold_str:
                raise ValueError("Preemption threshold is required.")
            threshold = int(threshold_str)

            deps = [d.strip() for d in self.deps_entry.get().split(",") if d.strip()]
            task = self.task or Task(name, exec_time, period, deadline, priority, arrival_time=arrival_time, dependencies=deps, preemption_threshold=threshold)
            if self.task:
                task.execution_time = exec_time
                task.period = period
                task.relative_deadline = deadline
                task.base_priority = priority
                task.arrival_time = arrival_time
                task.preemption_threshold = threshold
                task.dependencies = deps
            self.callback(task)
            self.destroy()
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")

class SchedulerApp:
    """GUI application for the scheduler with live visualization."""
    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        master.title("Advanced RTOS Scheduler with Live Visualization")
        master.geometry("1200x900")

        # Initialize all instance variables upfront
        self.scheduler: Optional[AdaptiveScheduler] = None
        self.simulation_thread: Optional[threading.Thread] = None
        self.paused = False
        self.updating = True
        self.time_data: List[float] = []
        self.cpu_util_data: List[List[float]] = []
        self.temp_data: List[List[float]] = []
        self.gantt_data: List[tuple[str, float, float, int]] = []
        self.task_colors = {
            'T1': 'skyblue', 'T2': 'salmon', 'T3': 'lightgreen', 'T4': 'gold',
            'T5': 'orchid', 'T6': 'lightcoral', 'T7': 'limegreen', 'T8': 'cyan'
        }
        self.core_canvases: List[tk.Canvas] = []
        self.core_labels: List[tk.Label] = []

        # Apply a modern theme
        style = ttk.Style()
        style.theme_use('clam')

        # Top Frame (Status and Config)
        self.top_frame = ttk.Frame(master)
        self.top_frame.pack(fill=tk.X, padx=10, pady=5)
        self.status_label = ttk.Label(self.top_frame, text="Status: Waiting", font=("Arial", 12))
        self.status_label.pack(side=tk.LEFT)
        ttk.Label(self.top_frame, text="Algorithm:").pack(side=tk.LEFT, padx=5)
        self.algorithm_var = tk.StringVar(value='EDF')
        self.algorithm_menu = ttk.OptionMenu(self.top_frame, self.algorithm_var, 'EDF', 'RR', 'PRIORITY', 'RMS', 'LLF', 'HYBRID', 'FCFS', 'SJF', 'SRTF', command=self.switch_algorithm)
        self.algorithm_menu.pack(side=tk.LEFT)
        ToolTip(self.algorithm_menu, "Select scheduling algorithm")

        self.config_frame = ttk.Frame(self.top_frame)
        self.config_frame.pack(side=tk.RIGHT)
        ttk.Label(self.config_frame, text="Cores:").pack(side=tk.LEFT)
        self.core_entry = ttk.Entry(self.config_frame, width=5)
        self.core_entry.insert(0, "2")
        self.core_entry.pack(side=tk.LEFT)
        ToolTip(self.core_entry, "Number of CPU cores")
        ttk.Label(self.config_frame, text="Overhead:").pack(side=tk.LEFT)
        self.overhead_entry = ttk.Entry(self.config_frame, width=5)
        self.overhead_entry.insert(0, f"{DEFAULT_BASE_CONTEXT_SWITCH_OVERHEAD}")
        self.overhead_entry.pack(side=tk.LEFT)
        ToolTip(self.overhead_entry, "Context switch overhead (seconds)")
        self.fault_var = tk.BooleanVar(value=False)
        self.fault_check = ttk.Checkbutton(self.config_frame, text="Fault Tolerance", variable=self.fault_var)
        self.fault_check.pack(side=tk.LEFT)
        ToolTip(self.fault_check, "Enable fault tolerance mode")

        # Button Frame
        self.button_frame = ttk.Frame(master)
        self.button_frame.pack(fill=tk.X, padx=10, pady=5)
        self.add_button = ttk.Button(self.button_frame, text="Add Task", command=self.add_task)
        self.add_button.pack(side=tk.LEFT, padx=5)
        ToolTip(self.add_button, "Add a new task to the scheduler")
        ttk.Button(self.button_frame, text="Quick Add", command=self.quick_add).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="Edit Task", command=self.edit_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="Delete Task", command=self.delete_task).pack(side=tk.LEFT, padx=5)
        self.start_button = ttk.Button(self.button_frame, text="Start", command=self.start_scheduling)
        self.start_button.pack(side=tk.LEFT, padx=5)
        ToolTip(self.start_button, "Start the simulation")
        self.pause_button = ttk.Button(self.button_frame, text="Pause", command=self.pause_simulation, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=5)
        ToolTip(self.pause_button, "Pause or resume the simulation")
        self.step_button = ttk.Button(self.button_frame, text="Step", command=self.step_simulation, state=tk.DISABLED)
        self.step_button.pack(side=tk.LEFT, padx=5)
        ToolTip(self.step_button, "Step through simulation one tick at a time")
        ttk.Button(self.button_frame, text="Reset", command=self.reset_scheduler).pack(side=tk.LEFT, padx=5)
        self.speed_slider = ttk.Scale(self.button_frame, from_=0, to=2, value=0.5, orient=tk.HORIZONTAL, length=150)
        self.speed_slider.pack(side=tk.RIGHT, padx=5)
        ToolTip(self.speed_slider, "Adjust simulation speed (seconds per tick)")

        # Main Frame (Tasks and Core Info)
        self.main_frame = ttk.Frame(master)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.task_frame = ttk.Frame(self.main_frame)
        self.task_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.task_tree = ttk.Treeview(self.task_frame, columns=("Name", "Exec", "Arrival", "Period", "Deadline", "Prio", "Threshold", "Deps"), show='headings')
        for col, text in zip(self.task_tree["columns"], ["Name", "Exec Time", "Arrival", "Period", "Deadline", "Priority", "Preemption", "Dependencies"]):
            self.task_tree.heading(col, text=text)
            self.task_tree.column(col, width=80)
        self.task_tree.pack(fill=tk.BOTH, expand=True)

        self.core_frame = ttk.Frame(self.main_frame)
        self.core_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)

        # Visualization Frame
        self.vis_frame = ttk.Frame(master)
        self.vis_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.fig, (self.ax_gantt, self.ax_cpu, self.ax_temp) = plt.subplots(3, 1, figsize=(10, 6), gridspec_kw={'height_ratios': [2, 1, 1]})
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.vis_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Set up Gantt chart axes
        self.ax_gantt.set_yticks(range(int(self.core_entry.get()) if self.core_entry.get().isdigit() else 2))
        threading.Thread(target=self.update_live_visualization, daemon=True).start()

    def update_status(self, current_time: float) -> None:
        def _update():
            self.status_label.config(text=f"Status: {'Paused' if self.paused else 'Running'} | Time: {current_time:.1f}s | Algo: {self.algorithm_var.get()}")
            if self.scheduler:
                for i, (canvas, label) in enumerate(zip(self.core_canvases, self.core_labels)):
                    task = self.scheduler.running_tasks[i].name if i < len(self.scheduler.running_tasks) and self.scheduler.running_tasks[i] else "Idle"
                    temp = self.scheduler.core_temperatures[i] if i < len(self.scheduler.core_temperatures) else 20.0
                    freq = self.scheduler.current_core_frequencies[i] if i < len(self.scheduler.current_core_frequencies) else 1.0
                    label.config(text=f"Core {i}: {task} | {temp:.1f}°C | {freq:.2f}")
                    color = "green" if task != "Idle" else "red"
                    canvas.delete("all")
                    canvas.create_oval(5, 5, 15, 15, fill=color, outline="black")
        self.master.after(0, _update)

    def update_live_visualization(self) -> None:
        while self.updating:
            if self.scheduler and self.simulation_thread and self.simulation_thread.is_alive():
                self.time_data.append(self.scheduler.current_time)
                metrics = self.scheduler.compute_metrics()
                cpu_util = [0] * self.scheduler.num_cores
                for core_id, task in enumerate(self.scheduler.running_tasks):
                    cpu_util[core_id] = 100 if task else 0
                self.cpu_util_data.append(cpu_util)
                self.temp_data.append(self.scheduler.core_temperatures.copy())
                new_logs = [log for log in self.scheduler.execution_log if log not in self.gantt_data]
                self.gantt_data.extend(new_logs)
                self.master.after(0, self._update_plots)
            time.sleep(0.5)

    def _update_plots(self) -> None:
        if not self.scheduler:
            return
        self.ax_gantt.clear()
        self.ax_gantt.set_title("Live Gantt Chart")
        self.ax_gantt.set_xlabel("Time (s)")
        self.ax_gantt.set_ylabel("Core")
        num_cores = self.scheduler.num_cores
        self.ax_gantt.set_ylim(-0.5, num_cores - 0.5)
        self.ax_gantt.set_yticks(range(num_cores))
        plotted_tasks = set()
        for task_name, start, end, core_id, _ in self.gantt_data:
            color = self.task_colors.get(task_name, 'gray')
            rect = patches.Rectangle((start, core_id - 0.4), end - start, 0.8, fill=True, color=color, label=task_name if task_name not in plotted_tasks else None)
            self.ax_gantt.add_patch(rect)
            self.ax_gantt.text(start + (end - start) / 2, core_id, task_name, ha='center', va='center', fontsize=8)
            plotted_tasks.add(task_name)
        self.ax_gantt.set_xlim(0, max(self.time_data) + 1 if self.time_data else 10)
        self.ax_gantt.legend(loc='upper right')

        self.ax_cpu.clear()
        self.ax_cpu.set_title("CPU Utilization per Core (%)")
        for core_id in range(num_cores):
            core_data = [data[core_id] for data in self.cpu_util_data]
            self.ax_cpu.plot(self.time_data, core_data, label=f"Core {core_id}")
        self.ax_cpu.set_ylim(0, 100)
        self.ax_cpu.legend()

        self.ax_temp.clear()
        self.ax_temp.set_title("Core Temperatures (°C)")
        for core_id in range(num_cores):
            temp_data = [data[core_id] for data in self.temp_data]
            self.ax_temp.plot(self.time_data, temp_data, label=f"Core {core_id}")
        self.ax_temp.set_ylim(20, MAX_TEMPERATURE + 10)
        self.ax_temp.legend()

        self.fig.tight_layout()
        self.canvas.draw()

    def add_task(self) -> None:
        TaskDialog(self.master, self.add_task_callback)

    def quick_add(self) -> None:
        task = Task(f"T{len(self.task_tree.get_children())+1}", 5, 0, 10, 2)
        self.add_task_callback(task)

    def edit_task(self) -> None:
        selected = self.task_tree.selection()
        if selected and not self.simulation_thread:
            item = selected[0]
            values = self.task_tree.item(item, "values")
            task = Task(values[0], float(values[1]), int(values[3]), int(values[4]), int(values[5]), 
                        [d.strip() for d in values[7].split(",") if d.strip()], preemption_threshold=int(values[6]), arrival_time=float(values[2]))
            TaskDialog(self.master, lambda t: self.edit_task_callback(item, t), task)

    def edit_task_callback(self, item: str, task: Task) -> None:
        self.task_tree.item(item, values=(task.name, task.execution_time, task.arrival_time, task.period, task.relative_deadline, 
                                          task.base_priority, task.preemption_threshold, ", ".join(task.dependencies)))

    def add_task_callback(self, task: Task) -> None:
        if not self.scheduler:
            try:
                self.scheduler = AdaptiveScheduler(
                    algorithm=self.algorithm_var.get(), num_cores=int(self.core_entry.get()),
                    base_context_overhead=float(self.overhead_entry.get()), status_callback=self.update_status,
                    enable_fault_tolerance=self.fault_var.get())
                self.core_canvases = [tk.Canvas(self.core_frame, width=20, height=20) for _ in range(self.scheduler.num_cores)]
                self.core_labels = [ttk.Label(self.core_frame, text=f"Core {i}: Idle | 20.0°C | 1.00") 
                                   for i in range(self.scheduler.num_cores)]
                for canvas, label in zip(self.core_canvases, self.core_labels):
                    canvas.pack(pady=2)
                    canvas.create_oval(5, 5, 15, 15, fill="red", outline="black")
                    label.pack(pady=2)
            except ValueError:
                messagebox.showerror("Error", "Invalid cores or overhead value")
                return
        
        if self.simulation_thread and self.simulation_thread.is_alive():
            with threading.Lock():
                if self.scheduler.add_task(task):
                    self.master.after(0, lambda: self.task_tree.insert("", "end", values=(
                        task.name, task.execution_time, task.arrival_time, task.period, task.relative_deadline, 
                        task.base_priority, task.preemption_threshold, ", ".join(task.dependencies))))
                    print(f"Task {task.name} added dynamically during simulation. Ready queue: {self.scheduler.ready_queue}")
        else:
            if self.scheduler.add_task(task):
                self.task_tree.insert("", "end", values=(task.name, task.execution_time, task.arrival_time, task.period, task.relative_deadline, 
                                                         task.base_priority, task.preemption_threshold, ", ".join(task.dependencies)))
                print(f"Task {task.name} added to scheduler. Ready queue: {self.scheduler.ready_queue}")

    def delete_task(self) -> None:
        selected = self.task_tree.selection()
        if selected and not self.simulation_thread:
            for item in selected:
                self.task_tree.delete(item)

    def switch_algorithm(self, value: str) -> None:
        if self.scheduler and self.simulation_thread and self.simulation_thread.is_alive():
            self.scheduler.switch_algorithm(value)

    def start_scheduling(self) -> None:
        if not self.scheduler or not self.task_tree.get_children():
            messagebox.showwarning("No Tasks", "Add tasks first")
            return
        print("Starting simulation...")
        self.pause_button.config(state=tk.NORMAL)
        self.step_button.config(state=tk.NORMAL)
        self.scheduler.paused = False
        self.simulation_thread = threading.Thread(target=self.scheduler.schedule, daemon=True)
        self.simulation_thread.start()
        print(f"Simulation thread started. Alive: {self.simulation_thread.is_alive()}")
        self.master.after(100, self.check_simulation)

    def check_simulation(self) -> None:
        if self.simulation_thread and not self.simulation_thread.is_alive():
            print("Simulation thread finished.")
            self.updating = False
            metrics = self.scheduler.compute_metrics()
            messagebox.showinfo("Simulation Complete", 
                                f"Time: {self.scheduler.current_time:.1f}s\n"
                                f"Avg Turnaround: {metrics['avg_turnaround']:.2f}s\n"
                                f"Avg Wait: {metrics['avg_wait']:.2f}s\n"
                                f"CPU Util: {metrics['cpu_util']:.1f}%\n"
                                f"Energy: {metrics['energy_consumed']:.1f}J\n"
                                f"Avg Temp: {metrics['avg_temperature']:.1f}°C\n"
                                f"Migrations: {metrics['migrations']}\n"
                                f"Preemptions: {metrics['preemptions']}\n"
                                f"Faults: {metrics['faults_detected']}\n"
                                f"Total Missed Deadlines: {metrics['total_misses']}\n"
                                f"Hard RT Missed Deadlines: {metrics['hard_misses']}\n"
                                f"Miss Ratio: {metrics['miss_ratio']:.2%}\n"
                                f"Total Releases: {metrics['total_releases']}")
            self.scheduler.visualize()
            self.pause_button.config(state=tk.DISABLED)
            self.step_button.config(state=tk.DISABLED)
        else:
            self.master.after(100, self.check_simulation)

    def pause_simulation(self) -> None:
        if self.scheduler:
            self.paused = not self.paused
            self.scheduler.paused = self.paused
            self.pause_button.config(text="Resume" if self.paused else "Pause")

    def step_simulation(self) -> None:
        if self.scheduler and self.paused:
            self.scheduler.step_event.set()

    def reset_scheduler(self) -> None:
        self.scheduler = None
        self.simulation_thread = None
        self.paused = False
        self.updating = True
        self.status_label.config(text="Status: Waiting")
        self.pause_button.config(state=tk.DISABLED, text="Pause")
        self.step_button.config(state=tk.DISABLED)
        self.task_tree.delete(*self.task_tree.get_children())
        self.time_data.clear()
        self.cpu_util_data.clear()
        self.temp_data.clear()
        self.gantt_data.clear()
        self.ax_gantt.clear()
        self.ax_cpu.clear()
        self.ax_temp.clear()
        self.canvas.draw()
        for canvas, label in zip(self.core_canvases, self.core_labels):
            canvas.delete("all")
            canvas.create_oval(5, 5, 15, 15, fill="red", outline="black")
            label.config(text="Core X: Idle | 20.0°C | 1.00")
        self.core_canvases.clear()
        self.core_labels.clear()
        if not any(t.name == "visualization" and t.is_alive() for t in threading.enumerate()):
            threading.Thread(target=self.update_live_visualization, daemon=True, name="visualization").start()

# Main entry point
if __name__ == "__main__":
    root = tk.Tk()
    app = SchedulerApp(root)
    root.mainloop()