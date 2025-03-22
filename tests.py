# tests.py
import unittest
from task import Task
from scheduler import AdaptiveScheduler

class TestTask(unittest.TestCase):
    def test_task_initialization(self):
        task = Task("Task1", 5, 10, 15, 1)
        self.assertEqual(task.name, "Task1")
        self.assertEqual(task.execution_time, 5)
        self.assertEqual(task.period, 10)
        self.assertEqual(task.relative_deadline, 15)
        self.assertEqual(task.base_priority, 1)

    def test_task_release(self):
        task = Task("Task1", 5, 10, 15, 1)
        task.release(0)
        self.assertGreater(task.remaining_time, 0)
        self.assertEqual(task.absolute_deadline, 15)

class TestAdaptiveScheduler(unittest.TestCase):
    def test_add_task(self):
        scheduler = AdaptiveScheduler()
        task = Task("Task1", 5, 10, 15, 1)
        result = scheduler.add_task(task)
        self.assertTrue(result)
        self.assertIn(task, scheduler.ready_queue)

if __name__ == "__main__":
    unittest.main()