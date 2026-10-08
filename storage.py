import json
import os
from typing import List, Tuple

from models import RecurringTask, Task

DEFAULT_FILE = "tasks.json"


def save_tasks(
    pending: List[Task],
    history: List[Task],
    filepath: str = DEFAULT_FILE,
) -> None:
    """Save pending and completed tasks to a JSON file."""
    try:
        data = {
            "pending": [task.to_dict() for task in pending],
            "history": [task.to_dict() for task in history],
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        raise IOError(f"Failed to save tasks to '{filepath}': {e}") from e


def load_tasks(
    filepath: str = DEFAULT_FILE,
) -> Tuple[List[Task], List[Task]]:
    """Load tasks from a JSON file. Returns empty lists if file does not exist."""
    if not os.path.exists(filepath):
        return [], []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        pending = [_deserialize(t) for t in data.get("pending", [])]
        history = [_deserialize(t) for t in data.get("history", [])]
        return pending, history

    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        raise ValueError(f"Failed to load tasks from '{filepath}': {e}") from e


def _deserialize(data: dict) -> Task:
    """Deserialize a task dictionary to the appropriate Task instance."""
    if data.get("type") == "recurring":
        return RecurringTask.from_dict(data)
    return Task.from_dict(data)
