import argparse
import scheduler
from gui import SchedulerApp
import tkinter as tk

def run_cli_mode():
    print("Running in CLI mode...")
    adaptive_scheduler = scheduler.AdaptiveScheduler()
    adaptive_scheduler.run()  # Directly execute scheduler

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", action="store_true", help="Run without GUI")
    args = parser.parse_args()

    if args.cli:
        run_cli_mode()
    else:
        root = tk.Tk()
        app = SchedulerApp(root)
        root.mainloop()

