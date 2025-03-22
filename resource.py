# resource.py
from typing import List, Optional

from task import Task

class Resource:
    """Represents a system resource with preemption and priority ceiling."""
    def __init__(self, name: str, is_preemptible: bool = False, access_ceiling: int = 0,
                 held_by: Optional[Task] = None, waiting_tasks: List[Task] = None):
        self.name = name
        self.is_preemptible = is_preemptible
        self.access_ceiling = access_ceiling
        self.held_by = held_by
        self.waiting_tasks = waiting_tasks if waiting_tasks is not None else []