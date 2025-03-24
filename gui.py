import tkinter as tk
from tkinter import messagebox, ttk
import threading
import time
from typing import Optional, List
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.widgets import SpanSelector
import seaborn as sns
from ttkthemes import ThemedTk
from config import DEFAULT_BASE_CONTEXT_SWITCH_OVERHEAD, MAX_TEMPERATURE
from task import Task
from scheduler import AdaptiveScheduler
from config import DEFAULT_BASE_CONTEXT_SWITCH_OVERHEAD, MAX_TEMPERATURE

class ToolTip:
    """Class to create hover tooltips for widgets."""
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
    """Dialog for adding or editing tasks."""
    def __init__(self, parent, callback, existing_task: Optional[Task] = None):
        super().__init__(parent)
        self.title("Task Editor" if existing_task else "Add Task")
        self.callback = callback
        self.task = existing_task
        self.geometry("300x400")

        fields = [
            ("Task Name:", "name_entry", existing_task.name if existing_task else f"T{int(time.time())%10000}"),
            ("Arrival Time (ticks):", "arrival_entry", str(existing_task.arrival_time) if existing_task else "0"),
            ("Exec Time (ticks):", "exec_entry", str(existing_task.execution_time) if existing_task else "5"),
            ("Period (ticks, 0=one-shot):", "period_entry", str(existing_task.period) if existing_task else "0"),
            ("Deadline (ticks):", "deadline_entry", str(existing_task.relative_deadline) if existing_task else "10"),
            ("Priority (0=highest):", "priority_entry", str(existing_task.base_priority) if existing_task else "2"),
            ("Preemption Threshold:", "threshold_entry", str(existing_task.preemption_threshold) if existing_task else "32"),
            ("Dependencies:", "deps_entry", ", ".join(existing_task.dependencies) if existing_task else ""),
        ]
        for label_text, attr, default in fields:
            tk.Label(self, text=label_text).pack(pady=2)
            setattr(self, attr, tk.Entry(self))
            getattr(self, attr).pack()
            getattr(self, attr).insert(0, default)

        tk.Button(self, text="Save" if existing_task else "Add", command=self.on_save).pack(pady=10)

    def on_save(self):
        try:
            name = self.name_entry.get().strip()
            if not name:
                raise ValueError("Task name is required.")
            arrival_time = float(self.arrival_entry.get().strip() or "0")
            if arrival_time < 0:
                raise ValueError("Arrival time must be non-negative.")
            exec_time = float(self.exec_entry.get().strip() or "5")
            if exec_time <= 0:
                raise ValueError("Execution time must be greater than 0.")
            period = int(self.period_entry.get().strip() or "0")
            deadline = int(self.deadline_entry.get().strip() or "10")
            if deadline <= 0:
                raise ValueError("Deadline must be greater than 0.")
            priority = int(self.priority_entry.get().strip() or "2")
            threshold = int(self.threshold_entry.get().strip() or "32")
            deps = [d.strip() for d in self.deps_entry.get().split(",") if d.strip()]

            task = self.task or Task(name, exec_time, period, deadline, priority, arrival_time=arrival_time, dependencies=deps, preemption_threshold=threshold)
            if self.task:
                task.execution_time, task.period, task.relative_deadline = exec_time, period, deadline
                task.base_priority, task.arrival_time, task.preemption_threshold, task.dependencies = priority, arrival_time, threshold, deps
            self.callback(task)
            self.destroy()
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")

class SchedulerApp:
    """Ultimate GUI application for RTOS scheduler simulation with advanced features."""
    def __init__(self, master: ThemedTk) -> None:
        self.master = master
        self.master.title("Ultimate RTOS Scheduler")
        self.master.geometry("1400x1000")
        self.master.set_theme("arc")
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Arial", 10))
        self.style.configure("TLabel", font=("Arial", 11))

        # Instance variables
        self.scheduler: Optional[AdaptiveScheduler] = None
        self.simulation_thread: Optional[threading.Thread] = None
        self.paused = False
        self.updating = True
        self.data_lock = threading.Lock()
        self.time_data: List[float] = []
        self.cpu_util_data: List[List[float]] = []
        self.temp_data: List[List[float]] = []
        self.gantt_data: List[tuple[str, float, float, int]] = []
        self.task_colors = sns.color_palette("husl", 16).as_hex()
        self.core_indicators = []

        # Main layout
        self.main_pane = ttk.PanedWindow(master, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left Panel
        self.left_frame = ttk.Frame(self.main_pane)
        self.main_pane.add(self.left_frame, weight=1)

        # Control Frame
        self.control_frame = ttk.LabelFrame(self.left_frame, text="Controls", padding=5)
        self.control_frame.pack(fill=tk.X, pady=5)
        ttk.Label(self.control_frame, text="Algorithm:").grid(row=0, column=0, padx=5, pady=2)
        self.algorithm_var = tk.StringVar(value="EDF")
        algo_menu = ttk.Combobox(self.control_frame, textvariable=self.algorithm_var, values=["EDF", "RR", "PRIORITY", "RMS", "LLF", "HYBRID", "FCFS", "SJF", "SRTF"])
        algo_menu.grid(row=0, column=1, padx=5, pady=2)
        algo_menu.bind("<<ComboboxSelected>>", lambda e: self.switch_algorithm(self.algorithm_var.get()))
        ToolTip(algo_menu, "Select scheduling algorithm")

        ttk.Label(self.control_frame, text="Cores:").grid(row=0, column=2, padx=5, pady=2)
        self.core_entry = ttk.Entry(self.control_frame, width=5)
        self.core_entry.insert(0, "2")
        self.core_entry.grid(row=0, column=3, padx=5, pady=2)
        ToolTip(self.core_entry, "Number of CPU cores")

        ttk.Label(self.control_frame, text="Overhead:").grid(row=0, column=4, padx=5, pady=2)
        self.overhead_entry = ttk.Entry(self.control_frame, width=5)
        self.overhead_entry.insert(0, f"{DEFAULT_BASE_CONTEXT_SWITCH_OVERHEAD}")
        self.overhead_entry.grid(row=0, column=5, padx=5, pady=2)
        ToolTip(self.overhead_entry, "Context switch overhead (seconds)")

        self.fault_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.control_frame, text="Fault Tolerance", variable=self.fault_var).grid(row=0, column=6, padx=5, pady=2)
        ToolTip(self.control_frame.winfo_children()[-1], "Enable fault tolerance mode")

        # Buttons
        self.button_frame = ttk.Frame(self.control_frame)
        self.button_frame.grid(row=1, column=0, columnspan=7, pady=5)
        buttons = [
            ("Add Task", self.add_task, "Add a new task"),
            ("Quick Add", self.quick_add, "Quickly add a default task"),
            ("Edit Task", self.edit_task, "Edit selected task"),
            ("Delete Task", self.delete_task, "Delete selected task"),
            ("Start", self.start_scheduling, "Start simulation"),
            ("Pause", self.pause_simulation, "Pause/resume simulation", tk.DISABLED),
            ("Step", self.step_simulation, "Step one tick", tk.DISABLED),
            ("Reset", self.reset_scheduler, "Reset all"),
            ("Export", self.export_results, "Export simulation results"),
        ]
        self.button_widgets = {}
        for idx, (text, cmd, tip, *state) in enumerate(buttons):
            btn = ttk.Button(self.button_frame, text=text, command=cmd, state=state[0] if state else tk.NORMAL)
            btn.grid(row=0, column=idx, padx=2)
            ToolTip(btn, tip)
            self.button_widgets[text] = btn

        ttk.Label(self.button_frame, text="Speed:").grid(row=0, column=len(buttons), padx=5)
        self.speed_slider = ttk.Scale(self.button_frame, from_=0.1, to=2.0, value=0.5, orient=tk.HORIZONTAL, length=150)
        self.speed_slider.grid(row=0, column=len(buttons) + 1, padx=5)
        ToolTip(self.speed_slider, "Simulation speed (seconds per tick)")

        # Task List
        self.task_frame = ttk.LabelFrame(self.left_frame, text="Tasks", padding=5)
        self.task_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.task_tree = ttk.Treeview(self.task_frame, columns=("Name", "Exec", "Arrival", "Period", "Deadline", "Prio", "Threshold", "Deps"), show="headings", selectmode="browse")
        for col, text in zip(self.task_tree["columns"], ["Name", "Exec Time", "Arrival", "Period", "Deadline", "Priority", "Threshold", "Deps"]):
            self.task_tree.heading(col, text=text)
            self.task_tree.column(col, width=80, anchor="center")
        self.task_tree.pack(fill=tk.BOTH, expand=True)
        self.task_tree.bind("<Double-1>", lambda e: self.edit_task())

        # Right Panel
        self.right_frame = ttk.Frame(self.main_pane)
        self.main_pane.add(self.right_frame, weight=2)

        # Status Bar
        self.status_frame = ttk.LabelFrame(self.right_frame, text="System Status", padding=5)
        self.status_frame.pack(fill=tk.X, pady=5)
        self.status_label = ttk.Label(self.status_frame, text="Status: Idle | Time: 0.0s")
        self.status_label.pack(side=tk.LEFT)
        self.core_frame = ttk.Frame(self.status_frame)
        self.core_frame.pack(side=tk.RIGHT)

        # Visualization Frame
        self.vis_frame = ttk.LabelFrame(self.right_frame, text="Live Visualizations", padding=5)
        self.vis_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.fig, (self.ax_gantt, self.ax_queue, self.ax_metrics) = plt.subplots(3, 1, figsize=(12, 8), gridspec_kw={"height_ratios": [2, 1, 1]})
        self.fig.patch.set_facecolor("#f0f0f0")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.vis_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.span = SpanSelector(self.ax_gantt, self.on_zoom, "horizontal", useblit=True)

        # Start visualization thread
        threading.Thread(target=self.update_live_visualization, daemon=True, name="visualization").start()

    def on_zoom(self, xmin, xmax):
        """Handle Gantt chart zooming."""
        self.ax_gantt.set_xlim(xmin, xmax)
        self.canvas.draw()

    def update_status(self, current_time: float) -> None:
        """Update status bar and core indicators."""
        def _update():
            state = "Paused" if self.paused else "Running" if self.simulation_thread else "Idle"
            self.status_label.config(text=f"Status: {state} | Time: {current_time:.1f}s | Algo: {self.algorithm_var.get()}")
            if self.scheduler:
                for i, (canvas, label) in enumerate(self.core_indicators):
                    task = self.scheduler.running_tasks[i].name if i < len(self.scheduler.running_tasks) and self.scheduler.running_tasks[i] else "Idle"
                    temp = self.scheduler.core_temperatures[i]
                    freq = self.scheduler.current_core_frequencies[i]
                    label.config(text=f"C{i}: {task} | {temp:.1f}°C | {freq:.2f}GHz")
                    canvas.itemconfig("indicator", fill="green" if task != "Idle" else "red")
        self.master.after(0, _update)

    def update_live_visualization(self) -> None:
        """Thread to update visualizations periodically."""
        while self.updating:
            if self.scheduler and self.simulation_thread and self.simulation_thread.is_alive():
                with self.data_lock:
                    self.time_data.append(self.scheduler.current_time)
                    cpu_util = [100 if task else 0 for task in self.scheduler.running_tasks]
                    self.cpu_util_data.append(cpu_util)
                    self.temp_data.append(self.scheduler.core_temperatures.copy())
                    self.gantt_data.extend([log for log in self.scheduler.execution_log if log not in self.gantt_data])
                self.master.after(0, self._update_plots)
            time.sleep(0.1)

    def _update_plots(self) -> None:
        """Update Gantt chart, queue status, and metrics plots."""
        if not self.scheduler:
            return
        num_cores = self.scheduler.num_cores

        # Gantt Chart
        self.ax_gantt.clear()
        self.ax_gantt.set_title("Task Execution (Gantt)", fontsize=12)
        self.ax_gantt.set_ylabel("Core")
        self.ax_gantt.set_yticks(range(num_cores))
        plotted_tasks = set()
        with self.data_lock:
            for task_name, start, end, core_id, _ in self.gantt_data:
                color = self.task_colors[hash(task_name) % len(self.task_colors)]
                label = task_name if task_name not in plotted_tasks else None
                rect = patches.Rectangle((start, core_id - 0.4), end - start, 0.8, fill=True, color=color, label=label, alpha=0.8)
                self.ax_gantt.add_patch(rect)
                self.ax_gantt.text(start + (end - start) / 2, core_id, task_name, ha="center", va="center", fontsize=8)
                plotted_tasks.add(task_name)
        self.ax_gantt.set_xlim(0, max(self.time_data) + 1 if self.time_data else 10)
        self.ax_gantt.legend(loc="upper right", fontsize=8)

        # Queue Visualization
        self.ax_queue.clear()
        self.ax_queue.set_title("Queue Status", fontsize=12)
        with self.data_lock:
            ready = [t.name for t in self.scheduler.ready_queue]
            running = [t.name if t else "Idle" for t in self.scheduler.running_tasks]
            pending = [t.name for t in self.scheduler.pending_tasks]
        queues = {"Ready": ready[:5], "Running": running, "Pending": pending[:5]}
        for i, (q_name, tasks) in enumerate(queues.items()):
            self.ax_queue.barh([f"{q_name} {j}" for j in range(len(tasks))], [1] * len(tasks), 
                              color=[self.task_colors[hash(t) % len(self.task_colors)] for t in tasks])
            for j, task in enumerate(tasks):
                self.ax_queue.text(0.5, f"{q_name} {j}", task, ha="center", va="center", fontsize=8)
        self.ax_queue.set_xlim(0, 1)
        self.ax_queue.set_xlabel("Tasks (Truncated)")

        # Metrics
        self.ax_metrics.clear()
        self.ax_metrics.set_title("System Metrics", fontsize=12)
        for core_id in range(num_cores):
            util_data = [data[core_id] for data in self.cpu_util_data]
            temp_data = [data[core_id] for data in self.temp_data]
            self.ax_metrics.plot(self.time_data, util_data, label=f"C{core_id} Util", linestyle="-", alpha=0.7)
            self.ax_metrics.plot(self.time_data, temp_data, label=f"C{core_id} Temp", linestyle="--", alpha=0.7)
        self.ax_metrics.set_ylim(0, max(100, MAX_TEMPERATURE + 10))
        self.ax_metrics.legend(loc="upper right", fontsize=8)
        self.ax_metrics.set_xlabel("Time (s)")

        self.fig.tight_layout()
        self.canvas.draw()

    def add_task(self) -> None:
        """Open dialog to add a new task."""
        TaskDialog(self.master, self.add_task_callback)

    def quick_add(self) -> None:
        """Quickly add a default task."""
        task = Task(f"T{len(self.task_tree.get_children())+1}", 5, 0, 10, 2)
        self.add_task_callback(task)

    def edit_task(self) -> None:
        """Open dialog to edit selected task."""
        selected = self.task_tree.selection()
        if selected and not self.simulation_thread:
            item = selected[0]
            values = self.task_tree.item(item, "values")
            task = Task(values[0], float(values[1]), int(values[3]), int(values[4]), int(values[5]), 
                        [d.strip() for d in values[7].split(",") if d.strip()], preemption_threshold=int(values[6]), arrival_time=float(values[2]))
            TaskDialog(self.master, lambda t: self.edit_task_callback(item, t), task)

    def add_task_callback(self, task: Task) -> None:
        """Add a task to the scheduler and task tree."""
        if not self.scheduler:
            try:
                self.scheduler = AdaptiveScheduler(
                    algorithm=self.algorithm_var.get(), num_cores=int(self.core_entry.get()),
                    base_context_overhead=float(self.overhead_entry.get()), status_callback=self.update_status,
                    enable_fault_tolerance=self.fault_var.get())
                self.core_indicators = [(tk.Canvas(self.core_frame, width=20, height=20), 
                                        ttk.Label(self.core_frame, text=f"C{i}: Idle | 20.0°C | 1.00GHz")) 
                                       for i in range(self.scheduler.num_cores)]
                for canvas, label in self.core_indicators:
                    canvas.pack(side=tk.LEFT, padx=2)
                    canvas.create_oval(5, 5, 15, 15, fill="red", outline="black", tags="indicator")
                    label.pack(side=tk.LEFT, padx=2)
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid configuration: {str(e)}")
                return
        self.scheduler.add_task(task)
        self.task_tree.insert("", "end", values=(task.name, task.execution_time, task.arrival_time, task.period, 
                                                 task.relative_deadline, task.base_priority, task.preemption_threshold, 
                                                 ", ".join(task.dependencies)))

    def edit_task_callback(self, item: str, task: Task) -> None:
        """Update task tree with edited task details."""
        self.task_tree.item(item, values=(task.name, task.execution_time, task.arrival_time, task.period, 
                                          task.relative_deadline, task.base_priority, task.preemption_threshold, 
                                          ", ".join(task.dependencies)))

    def delete_task(self) -> None:
        """Delete selected task from task tree."""
        selected = self.task_tree.selection()
        if selected and not self.simulation_thread:
            self.task_tree.delete(selected[0])

    def switch_algorithm(self, value: str) -> None:
        """Switch scheduling algorithm dynamically."""
        if self.scheduler:
            self.scheduler.switch_algorithm(value)

    def start_scheduling(self) -> None:
        """Start the scheduling simulation."""
        if not self.scheduler or not self.task_tree.get_children():
            messagebox.showwarning("Warning", "No tasks to schedule")
            return
        self.button_widgets["Pause"].config(state=tk.NORMAL)
        self.button_widgets["Step"].config(state=tk.NORMAL)
        self.paused = False
        self.simulation_thread = threading.Thread(target=self.scheduler.schedule, args=(self.speed_slider.get(),), daemon=True)
        self.simulation_thread.start()
        self.master.after(100, self.check_simulation)

    def check_simulation(self) -> None:
        """Check simulation status and show metrics on completion."""
        if self.simulation_thread and not self.simulation_thread.is_alive():
            self.updating = False
            metrics = self.scheduler.compute_metrics()
            messagebox.showinfo("Simulation Complete",
                                f"Total Completion Time: {metrics['total_completion_time']:.1f}s\n"
                                f"Simulation Time: {self.scheduler.current_time:.1f}s\n"
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
            self.button_widgets["Pause"].config(state=tk.DISABLED)
            self.button_widgets["Step"].config(state=tk.DISABLED)
        else:
            self.master.after(100, self.check_simulation)

    def pause_simulation(self) -> None:
        """Pause or resume the simulation."""
        if self.scheduler:
            self.paused = not self.paused
            self.scheduler.paused = self.paused
            self.button_widgets["Pause"].config(text="Resume" if self.paused else "Pause")

    def step_simulation(self) -> None:
        """Step through the simulation one tick at a time."""
        if self.scheduler and self.paused:
            self.scheduler.step_event.set()

    def reset_scheduler(self) -> None:
        """Reset the scheduler and GUI to initial state."""
        self.scheduler = None
        self.simulation_thread = None
        self.paused = False
        self.updating = True
        self.time_data.clear()
        self.cpu_util_data.clear()
        self.temp_data.clear()
        self.gantt_data.clear()
        self.task_tree.delete(*self.task_tree.get_children())
        self.ax_gantt.clear()
        self.ax_queue.clear()
        self.ax_metrics.clear()
        self.canvas.draw()
        for canvas, label in self.core_indicators:
            canvas.itemconfig("indicator", fill="red")
            label.config(text="C?: Idle | 20.0°C | 1.00GHz")
        self.core_indicators.clear()
        self.button_widgets["Pause"].config(state=tk.DISABLED, text="Pause")
        self.button_widgets["Step"].config(state=tk.DISABLED)

    def export_results(self) -> None:
        """Export simulation results as an image."""
        if self.scheduler:
            filename = f"simulation_{int(time.time())}.png"
            self.fig.savefig(filename)
            messagebox.showinfo("Export", f"Results saved as {filename}")

if __name__ == "__main__":
    root = ThemedTk()
    app = SchedulerApp(root)
    root.mainloop()