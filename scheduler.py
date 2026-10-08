from typing import Callable, List, Optional

from models import Priority, RecurringTask, Task
from structures import LinkedList, MinHeap


class TaskScheduler:
    """Core scheduler coordinating pending task priority queue and completed history."""

    def __init__(self) -> None:
        self._pending: MinHeap[Task]     = MinHeap()
        self._history: LinkedList[Task]  = LinkedList()

    def add_task(self, task: Task) -> None:
        self._pending.push(task)

    def complete_task(self, task_id: int) -> Optional[Task]:
        """
        Mark a pending task as done and move it to history.
        Recurring tasks return a rescheduled instance that is re-queued.
        """
        removed = self._pending.remove_by_id(task_id)
        if removed is None:
            raise ValueError(f"Task #{task_id} not found in pending tasks.")

        rescheduled = removed.complete()
        self._history.prepend(removed)

        if rescheduled is not None:
            self.add_task(rescheduled)
            return rescheduled

        return None

    def delete_task(self, task_id: int) -> None:
        """Remove a pending task permanently."""
        removed = self._pending.remove_by_id(task_id)
        if removed is None:
            raise ValueError(f"Task #{task_id} not found in pending tasks.")

    def update_task(self, task_id: int, **kwargs) -> None:
        """Edit fields of a pending task while maintaining heap ordering."""
        task = self._pending.remove_by_id(task_id)
        if task is None:
            raise ValueError(f"Task #{task_id} not found in pending tasks.")
        if "title"       in kwargs: task.title       = kwargs["title"]
        if "description" in kwargs: task.description = kwargs["description"]
        if "priority"    in kwargs: task.priority    = kwargs["priority"]
        if "due_date"    in kwargs: task.due_date    = kwargs["due_date"]
        if "interval_days" in kwargs and isinstance(task, RecurringTask):
            task.interval_days = kwargs["interval_days"]
        self._pending.push(task)

    def get_next_task(self) -> Optional[Task]:
        """Return the next highest-priority task without removing it."""
        if self._pending.is_empty():
            return None
        return self._pending.peek()

    def get_pending_tasks(self) -> List[Task]:
        """Return pending tasks ordered by priority."""
        return list(self._pending)

    def get_history(self) -> List[Task]:
        """Return completed tasks (most recent first)."""
        return list(self._history)

    def filter_tasks(self, predicate: Callable[[Task], bool]) -> List[Task]:
        """Filter pending tasks matching the predicate."""
        return list(filter(predicate, self._pending))

    def make_priority_filter(self, priority: Priority) -> Callable[[Task], bool]:
        """Build a predicate filter for a given priority."""
        def by_priority(task: Task) -> bool:
            return task.priority == priority
        return by_priority

    def search_tasks(self, keyword: str) -> List[Task]:
        """Case-insensitive keyword search over title and description."""
        kw = keyword.lower()
        return list(
            filter(
                lambda t: kw in t.title.lower() or kw in t.description.lower(),
                self._pending,
            )
        )

    def get_stats(self) -> dict:
        pending = list(self._pending)
        return {
            "total_pending":   len(pending),
            "total_completed": self._history.size,
            "high_priority":   len(list(filter(lambda t: t.priority == Priority.HIGH, pending))),
            "medium_priority": len(list(filter(lambda t: t.priority == Priority.MEDIUM, pending))),
            "low_priority":    len(list(filter(lambda t: t.priority == Priority.LOW, pending))),
            "pending_titles":  list(map(lambda t: t.title, pending)),
        }

    @property
    def pending_count(self) -> int:
        return self._pending.size

    @property
    def history_count(self) -> int:
        return self._history.size

    def set_tasks_from_data(
        self,
        pending: List[Task],
        history: List[Task],
    ) -> None:
        """Reset and repopulate scheduler state."""
        self._pending = MinHeap()
        self._history = LinkedList()
        for task in pending:
            self._pending.push(task)
        for task in history:
            self._history.append(task)
