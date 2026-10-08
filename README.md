# TaskFlow

A lightweight task management tool with both CLI and desktop (Tkinter) interfaces. Tasks are scheduled using an internal min-heap priority queue and persisted to local JSON storage.

## Features

- **Priority Queue**: Pending tasks are ordered dynamically by urgency (High, Medium, Low).
- **Recurring Tasks**: Automatic rescheduling upon completion (daily, weekly, or custom intervals).
- **Search & Filter**: Keyword search and priority-based filtering.
- **Task History**: Completed tasks are tracked in chronological order.
- **Persistence**: Automatically saves and loads state from `tasks.json`.
- **Dual Interface**: Interactive CLI menu and Tkinter desktop GUI.

## Quickstart

### CLI
```bash
python main.py
```

### GUI
```bash
python gui.py
```

## Running Tests

Tests are written using `pytest`:

```bash
pytest tests.py
```
