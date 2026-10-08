from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class Priority(Enum):
    """Task priority levels. Lower value = higher urgency."""
    HIGH   = 1
    MEDIUM = 2
    LOW    = 3

    def __str__(self) -> str:
        return self.name.capitalize()


class Task:
    """A schedulable task item."""

    _id_counter: int = 0

    def __init__(
        self,
        title: str,
        description: str,
        priority: Priority,
        due_date: Optional[str] = None,
    ) -> None:
        Task._id_counter += 1
        self._task_id:    int            = Task._id_counter
        self._title:      str            = title
        self._description: str           = description
        self._priority:   Priority       = priority
        self._due_date:   Optional[str]  = due_date
        self._completed:  bool           = False
        self._created_at: str            = datetime.now().strftime("%Y-%m-%d %H:%M")

    @property
    def task_id(self) -> int:
        return self._task_id

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        self._title = value

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        self._description = value

    @property
    def priority(self) -> Priority:
        return self._priority

    @priority.setter
    def priority(self, value: Priority) -> None:
        self._priority = value

    @property
    def due_date(self) -> Optional[str]:
        return self._due_date

    @due_date.setter
    def due_date(self, value: Optional[str]) -> None:
        self._due_date = value

    @property
    def completed(self) -> bool:
        return self._completed

    @property
    def created_at(self) -> str:
        return self._created_at

    def complete(self) -> Optional["Task"]:
        """Mark as completed."""
        self._completed = True
        return None

    def display(self) -> str:
        status = "DONE   " if self._completed else "PENDING"
        due    = f"  Due: {self._due_date}" if self._due_date else ""
        return (
            f"  [#{self._task_id:>3}] [{self._priority}] [{status}] {self._title}"
            f"{due}\n"
            f"         {self._description}"
        )

    def __lt__(self, other: "Task") -> bool:
        return self._priority.value < other._priority.value

    def __le__(self, other: "Task") -> bool:
        return self._priority.value <= other._priority.value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Task):
            return False
        return self._task_id == other._task_id

    def __repr__(self) -> str:
        return f"Task(#{self._task_id}, '{self._title}', {self._priority})"

    def to_dict(self) -> dict:
        return {
            "type":        "task",
            "task_id":     self._task_id,
            "title":       self._title,
            "description": self._description,
            "priority":    self._priority.value,
            "due_date":    self._due_date,
            "completed":   self._completed,
            "created_at":  self._created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        t = cls.__new__(cls)
        Task._id_counter = max(Task._id_counter, data["task_id"])
        t._task_id     = data["task_id"]
        t._title       = data["title"]
        t._description = data["description"]
        t._priority    = Priority(data["priority"])
        t._due_date    = data.get("due_date")
        t._completed   = data.get("completed", False)
        t._created_at  = data.get("created_at", "")
        return t


class RecurringTask(Task):
    """A task that automatically reschedules itself upon completion."""

    def __init__(
        self,
        title: str,
        description: str,
        priority: Priority,
        interval_days: int,
        due_date: Optional[str] = None,
    ) -> None:
        super().__init__(title, description, priority, due_date)
        self._interval_days: int = interval_days

    @property
    def interval_days(self) -> int:
        return self._interval_days

    @interval_days.setter
    def interval_days(self, value: int) -> None:
        self._interval_days = value

    def complete(self) -> Optional["RecurringTask"]:
        """Mark as done and return the next scheduled instance."""
        self._completed = True
        next_due = datetime.now() + timedelta(days=self._interval_days)
        return RecurringTask(
            title=self._title,
            description=self._description,
            priority=self._priority,
            interval_days=self._interval_days,
            due_date=next_due.strftime("%Y-%m-%d"),
        )

    def display(self) -> str:
        return super().display() + f"\n         [Recurs every {self._interval_days} day(s)]"

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["type"]          = "recurring"
        d["interval_days"] = self._interval_days
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "RecurringTask":
        t = cls.__new__(cls)
        Task._id_counter   = max(Task._id_counter, data["task_id"])
        t._task_id         = data["task_id"]
        t._title           = data["title"]
        t._description     = data["description"]
        t._priority        = Priority(data["priority"])
        t._due_date        = data.get("due_date")
        t._completed       = data.get("completed", False)
        t._created_at      = data.get("created_at", "")
        t._interval_days   = data.get("interval_days", 7)
        return t
