# visualization.py
import matplotlib.pyplot as plt
from collections import defaultdict

class SchedulerVisualizer:
    @staticmethod
    def plot_gantt_chart(ax1, core_intervals, colors):
        """Plot the Gantt chart for task scheduling."""
        ypos = 10
        height = 8
        for core_id, intervals in core_intervals.items():
            for start, duration, task_name in intervals:
                ax1.broken_barh([(start, duration)], (ypos, height), facecolors=(colors[core_id % len(colors)]))
                ax1.text(start - 2, ypos + height / 2, f"{task_name} (C{core_id})", va='center', ha='right', fontsize=8)
            ypos += height + 5
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Core Intervals')
        ax1.set_title('Scheduling Gantt Chart')

    @staticmethod
    def plot_core_metrics(ax2, ax3, core_temperatures, current_core_frequencies, num_cores):
        """Plot core temperature and frequency metrics."""
        ax2.plot(range(num_cores), core_temperatures, 'ro-', label='Temperature (°C)')
        ax2.set_ylim(0, 100)
        ax2.set_xlabel('Core ID')
        ax2.set_ylabel('Temp (°C)')
        ax2.legend()

        ax3.plot(range(num_cores), current_core_frequencies, 'bo-', label='Frequency')
        ax3.set_ylim(0, 1.2)
        ax3.set_xlabel('Core ID')
        ax3.set_ylabel('Freq')
        ax3.legend()

    @staticmethod
    def visualize(execution_log, core_temperatures, current_core_frequencies, num_cores):
        """Visualize scheduling results with Gantt chart and core metrics."""
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 10), gridspec_kw={'height_ratios': [3, 1, 1]})
        colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:purple']
        core_intervals = defaultdict(list)
        for task_name, start, finish, core, _ in execution_log:
            core_intervals[core].append((start, finish - start, task_name))
        SchedulerVisualizer.plot_gantt_chart(ax1, core_intervals, colors)
        SchedulerVisualizer.plot_core_metrics(ax2, ax3, core_temperatures, current_core_frequencies, num_cores)
        plt.tight_layout()
        plt.savefig("gantt_chart.png")
        plt.show()