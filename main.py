import argparse
from scheduler import AdaptiveScheduler
from task import Task
from gui import SchedulerApp
from ttkthemes import ThemedTk  # Import ThemedTk instead of tk.Tk
import sys

def run_cli_mode():
    """Run the scheduler in CLI mode with user-specified tasks."""
    parser = argparse.ArgumentParser(description="Real-Time Scheduler CLI")
    parser.add_argument(
        "--tasks",
        nargs='+',
        help="Task parameters: name execution_time period relative_deadline priority [arrival_time]",
        default=[]
    )
    parser.add_argument(
        "--algorithm",
        type=str,
        default="EDF",
        help="Scheduling algorithm (e.g., EDF, FCFS, RR)"
    )
    parser.add_argument(
        "--cores",
        type=int,
        default=2,
        help="Number of CPU cores"
    )
    args = parser.parse_args()

    scheduler = AdaptiveScheduler(
        algorithm=args.algorithm,
        num_cores=args.cores,
        base_context_overhead=0.1,
        status_callback=lambda x: None,
        enable_fault_tolerance=False
    )

    for task_str in args.tasks:
        parts = task_str.split()
        if len(parts) < 5:
            print(f"Skipping invalid task: {task_str}")
            continue
        name = parts[0]
        try:
            execution_time = float(parts[1])
            period = int(parts[2])
            relative_deadline = int(parts[3])
            priority = int(parts[4])
            arrival_time = float(parts[5]) if len(parts) > 5 else 0.0
        except (ValueError, IndexError) as e:
            print(f"Skipping invalid task: {task_str}. Error: {e}")
            continue

        task = Task(
            name=name,
            execution_time=execution_time,
            period=period,
            relative_deadline=relative_deadline,
            base_priority=priority,
            arrival_time=arrival_time
        )
        scheduler.add_task(task)
        print(f"Added task: {task}")

    print("\nStarting simulation...")
    scheduler.run()

    print("\nExecution Log:")
    for entry in scheduler.execution_log:
        task_name, start, end, core, reason = entry
        reason_str = f" ({reason})" if reason else ""
        print(f"Task {task_name} on Core {core}: {start} to {end}{reason_str}")

    print("\nMetrics:")
    metrics = scheduler.compute_metrics()
    for key, value in metrics.items():
        print(f"{key}: {value}")

def main():
    """Main entry point for the scheduler application."""
    if len(sys.argv) > 1:
        run_cli_mode()
    else:
        root = ThemedTk()  # Use ThemedTk instead of tk.Tk
        app = SchedulerApp(root)
        root.mainloop()

if __name__ == "__main__":
    main()