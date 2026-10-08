import os
import sys

from models import Priority, RecurringTask, Task
from scheduler import TaskScheduler
from storage import load_tasks, save_tasks

SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.json")

PRIORITY_KEYS = {
    "h": Priority.HIGH,
    "1": Priority.HIGH,
    "m": Priority.MEDIUM,
    "2": Priority.MEDIUM,
    "l": Priority.LOW,
    "3": Priority.LOW,
}


def print_banner() -> None:
    print("\n" + "=" * 54)
    print("         TaskFlow — Priority Task Scheduler")
    print("=" * 54)


def print_menu() -> None:
    print("""
  [1] Add Task               [2] Add Recurring Task
  [3] View Pending Tasks     [4] Complete a Task
  [5] Next Priority Task     [6] Search Tasks
  [7] Filter by Priority     [8] View History
  [9] Statistics             [0] Save & Exit
""")


def _get_priority() -> Priority:
    print("  Priority: [H]igh / [M]edium / [L]ow")
    while True:
        choice = input("  > ").strip().lower()
        if choice in PRIORITY_KEYS:
            return PRIORITY_KEYS[choice]
        print("  Invalid input. Enter H, M, or L.")


def _get_nonempty(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("  Field cannot be empty. Please try again.")


def _add_task(scheduler: TaskScheduler) -> None:
    print("\n-- Add Task --")
    title       = _get_nonempty("  Title       : ")
    description = input("  Description : ").strip() or "(no description)"
    priority    = _get_priority()
    due_date    = input("  Due date (YYYY-MM-DD, or Enter to skip): ").strip()

    try:
        task = Task(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date if due_date else None,
        )
        scheduler.add_task(task)
        print(f"\n  Task #{task.task_id} added  [{task.priority}]  \"{task.title}\"")
    except Exception as e:
        print(f"  Error creating task: {e}")


def _add_recurring(scheduler: TaskScheduler) -> None:
    print("\n-- Add Recurring Task --")
    title       = _get_nonempty("  Title            : ")
    description = input("  Description       : ").strip() or "(no description)"
    priority    = _get_priority()

    try:
        interval = int(input("  Repeat every how many days? ").strip())
        if interval <= 0:
            raise ValueError("Interval must be a positive integer.")
    except ValueError as e:
        print(f"  Invalid interval: {e}")
        return

    try:
        task = RecurringTask(
            title=title,
            description=description,
            priority=priority,
            interval_days=interval,
        )
        scheduler.add_task(task)
        print(
            f"\n  Recurring Task #{task.task_id} added  "
            f"[{task.priority}]  \"{task.title}\"  "
            f"(repeats every {interval} day(s))"
        )
    except Exception as e:
        print(f"  Error creating task: {e}")


def _view_pending(scheduler: TaskScheduler) -> None:
    tasks = scheduler.get_pending_tasks()
    print(f"\n-- Pending Tasks ({len(tasks)}) --")
    if not tasks:
        print("  No pending tasks.")
        return
    for task in tasks:
        print(task.display())
        print()


def _complete_task(scheduler: TaskScheduler) -> None:
    _view_pending(scheduler)
    if scheduler.pending_count == 0:
        return

    try:
        task_id     = int(input("  Enter Task ID to complete: ").strip())
        rescheduled = scheduler.complete_task(task_id)
        print(f"  Task #{task_id} marked as complete.")
        if rescheduled is not None:
            print(
                f"  (Recurring) Rescheduled as Task #{rescheduled.task_id}"
                f" — due: {rescheduled.due_date}"
            )
    except ValueError as e:
        print(f"  Error: {e}")
    except Exception as e:
        print(f"  Unexpected error: {e}")


def _view_next(scheduler: TaskScheduler) -> None:
    task = scheduler.get_next_task()
    print("\n-- Next Priority Task --")
    if task is None:
        print("  No pending tasks.")
    else:
        print(task.display())


def _search(scheduler: TaskScheduler) -> None:
    keyword = input("\n  Keyword to search: ").strip()
    if not keyword:
        return
    results = scheduler.search_tasks(keyword)
    print(f"\n-- Search: '{keyword}'  ({len(results)} result(s)) --")
    if not results:
        print("  No matching tasks.")
        return
    for t in results:
        print(t.display())
        print()


def _filter_by_priority(scheduler: TaskScheduler) -> None:
    print("\n-- Filter by Priority --")
    priority  = _get_priority()
    predicate = scheduler.make_priority_filter(priority)
    results   = scheduler.filter_tasks(predicate)
    print(f"\n-- {priority} Priority Tasks ({len(results)}) --")
    if not results:
        print("  No tasks with this priority.")
        return
    for t in results:
        print(t.display())
        print()


def _view_history(scheduler: TaskScheduler) -> None:
    history = scheduler.get_history()
    print(f"\n-- Completed Task History ({len(history)}) --")
    if not history:
        print("  No completed tasks yet.")
        return
    for t in history:
        print(t.display())
        print()


def _view_stats(scheduler: TaskScheduler) -> None:
    stats = scheduler.get_stats()
    print("\n-- Statistics --")
    print(f"  Pending tasks   : {stats['total_pending']}")
    print(f"  Completed tasks : {stats['total_completed']}")
    print(f"  ─── Breakdown (pending) ───────────────")
    print(f"  High priority   : {stats['high_priority']}")
    print(f"  Medium priority : {stats['medium_priority']}")
    print(f"  Low priority    : {stats['low_priority']}")
    if stats["pending_titles"]:
        titles = ", ".join(f'"{t}"' for t in stats["pending_titles"])
        print(f"  Pending titles  : {titles}")


def _save_and_exit(scheduler: TaskScheduler) -> None:
    try:
        save_tasks(
            pending=scheduler.get_pending_tasks(),
            history=scheduler.get_history(),
            filepath=SAVE_FILE,
        )
        print(f"\n  Saved to '{SAVE_FILE}'.  Goodbye!")
    except IOError as e:
        print(f"  Warning: could not save tasks: {e}")
    sys.exit(0)


def main() -> None:
    print_banner()

    scheduler = TaskScheduler()

    try:
        pending, history = load_tasks(SAVE_FILE)
        scheduler.set_tasks_from_data(pending, history)
        if pending or history:
            print(
                f"\n  Loaded {len(pending)} pending "
                f"and {len(history)} completed task(s)."
            )
    except ValueError as e:
        print(f"  Warning: could not load saved data: {e}")

    action_map = {
        "1": lambda: _add_task(scheduler),
        "2": lambda: _add_recurring(scheduler),
        "3": lambda: _view_pending(scheduler),
        "4": lambda: _complete_task(scheduler),
        "5": lambda: _view_next(scheduler),
        "6": lambda: _search(scheduler),
        "7": lambda: _filter_by_priority(scheduler),
        "8": lambda: _view_history(scheduler),
        "9": lambda: _view_stats(scheduler),
        "0": lambda: _save_and_exit(scheduler),
    }

    while True:
        print_menu()
        choice = input("  Your choice: ").strip()

        action = action_map.get(choice)
        if action:
            action()
        else:
            print("  Invalid choice. Enter a number shown in the menu.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrupted. Goodbye!")
        sys.exit(0)
