"""
Unit tests for TaskFlow models, data structures, and scheduler.
"""

import json
import os
import tempfile

import pytest

from models import Priority, RecurringTask, Task
from scheduler import TaskScheduler
from storage import load_tasks, save_tasks
from structures import LinkedList, MinHeap


# ─────────────────────────── helpers ────────────────────────────────────────

def make_task(title="Test", priority=Priority.MEDIUM, due=None):
    return Task(title=title, description="desc", priority=priority, due_date=due)


def make_recurring(title="Recurring", priority=Priority.LOW, interval=7):
    return RecurringTask(
        title=title,
        description="desc",
        priority=priority,
        interval_days=interval,
    )


# ─────────────────────────── Priority ───────────────────────────────────────

class TestPriority:
    def test_values_are_ordered(self):
        assert Priority.HIGH.value < Priority.MEDIUM.value < Priority.LOW.value

    def test_str_representation(self):
        assert str(Priority.HIGH) == "High"
        assert str(Priority.MEDIUM) == "Medium"
        assert str(Priority.LOW) == "Low"


# ─────────────────────────── Task ───────────────────────────────────────────

class TestTask:
    def test_id_auto_increments(self):
        t1 = make_task("A")
        t2 = make_task("B")
        assert t2.task_id == t1.task_id + 1

    def test_default_not_completed(self):
        t = make_task()
        assert t.completed is False

    def test_complete_marks_done(self):
        t = make_task()
        result = t.complete()
        assert t.completed is True
        assert result is None  # base Task returns None

    def test_property_setters(self):
        t = make_task()
        t.title = "Updated"
        t.priority = Priority.HIGH
        assert t.title == "Updated"
        assert t.priority == Priority.HIGH

    def test_lt_uses_priority_value(self):
        high = make_task(priority=Priority.HIGH)
        low = make_task(priority=Priority.LOW)
        assert high < low  # HIGH.value=1 < LOW.value=3

    def test_eq_by_task_id(self):
        t = make_task()
        assert t == t
        assert t != make_task()

    def test_to_dict_and_from_dict_round_trip(self):
        t = make_task("Round-trip", Priority.HIGH, "2026-06-01")
        d = t.to_dict()
        restored = Task.from_dict(d)
        assert restored.task_id == t.task_id
        assert restored.title == t.title
        assert restored.priority == t.priority
        assert restored.due_date == t.due_date
        assert restored.completed == t.completed


# ─────────────────────────── RecurringTask ──────────────────────────────────

class TestRecurringTask:
    def test_complete_returns_new_instance(self):
        rt = make_recurring(interval=3)
        next_task = rt.complete()
        assert rt.completed is True
        assert isinstance(next_task, RecurringTask)
        assert next_task.task_id != rt.task_id  # new object
        assert next_task.interval_days == 3

    def test_rescheduled_due_date_is_in_future(self):
        from datetime import date
        rt = make_recurring(interval=5)
        next_task = rt.complete()
        scheduled = date.fromisoformat(next_task.due_date)
        assert scheduled >= date.today()

    def test_to_dict_preserves_interval(self):
        rt = make_recurring(interval=14)
        d = rt.to_dict()
        assert d["type"] == "recurring"
        assert d["interval_days"] == 14

    def test_from_dict_round_trip(self):
        rt = make_recurring(interval=10)
        d = rt.to_dict()
        restored = RecurringTask.from_dict(d)
        assert restored.interval_days == 10
        assert restored.title == rt.title


# ─────────────────────────── LinkedList ─────────────────────────────────────

class TestLinkedList:
    def test_empty_list(self):
        ll = LinkedList()
        assert ll.size == 0
        assert list(ll) == []

    def test_prepend_inserts_at_front(self):
        ll = LinkedList()
        ll.prepend(1)
        ll.prepend(2)
        assert list(ll) == [2, 1]

    def test_append_inserts_at_back(self):
        ll = LinkedList()
        ll.append("a")
        ll.append("b")
        assert list(ll) == ["a", "b"]

    def test_size_tracks_correctly(self):
        ll = LinkedList()
        for i in range(5):
            ll.prepend(i)
        assert ll.size == 5
        assert len(ll) == 5

    def test_iteration_is_lazy(self):
        ll = LinkedList()
        ll.prepend(10)
        ll.prepend(20)
        it = iter(ll)
        assert next(it) == 20
        assert next(it) == 10
        with pytest.raises(StopIteration):
            next(it)


# ─────────────────────────── MinHeap ────────────────────────────────────────

class TestMinHeap:
    def test_push_and_pop_min_order(self):
        heap = MinHeap()
        t_low = make_task(priority=Priority.LOW)
        t_high = make_task(priority=Priority.HIGH)
        t_med = make_task(priority=Priority.MEDIUM)
        heap.push(t_low)
        heap.push(t_high)
        heap.push(t_med)
        assert heap.pop().priority == Priority.HIGH
        assert heap.pop().priority == Priority.MEDIUM
        assert heap.pop().priority == Priority.LOW

    def test_peek_does_not_remove(self):
        heap = MinHeap()
        t = make_task()
        heap.push(t)
        assert heap.peek() is t
        assert heap.size == 1

    def test_pop_empty_raises(self):
        heap = MinHeap()
        with pytest.raises(IndexError):
            heap.pop()

    def test_remove_by_id_found(self):
        heap = MinHeap()
        t = make_task()
        heap.push(t)
        removed = heap.remove_by_id(t.task_id)
        assert removed is t
        assert heap.size == 0

    def test_remove_by_id_not_found_returns_none(self):
        heap = MinHeap()
        assert heap.remove_by_id(9999) is None

    def test_iter_returns_sorted_tasks(self):
        heap = MinHeap()
        tasks = [
            make_task(priority=Priority.LOW),
            make_task(priority=Priority.HIGH),
            make_task(priority=Priority.MEDIUM),
        ]
        for t in tasks:
            heap.push(t)
        priorities = [t.priority for t in heap]
        assert priorities == [Priority.HIGH, Priority.MEDIUM, Priority.LOW]

    def test_heap_property_preserved_after_remove(self):
        heap = MinHeap()
        t1 = make_task(priority=Priority.HIGH)
        t2 = make_task(priority=Priority.MEDIUM)
        t3 = make_task(priority=Priority.LOW)
        for t in [t3, t1, t2]:
            heap.push(t)
        heap.remove_by_id(t2.task_id)
        assert heap.pop().priority == Priority.HIGH
        assert heap.pop().priority == Priority.LOW


# ─────────────────────────── TaskScheduler ──────────────────────────────────

class TestTaskScheduler:
    def setup_method(self):
        self.scheduler = TaskScheduler()

    def test_add_and_pending_count(self):
        self.scheduler.add_task(make_task())
        assert self.scheduler.pending_count == 1

    def test_complete_task_moves_to_history(self):
        t = make_task()
        self.scheduler.add_task(t)
        self.scheduler.complete_task(t.task_id)
        assert self.scheduler.pending_count == 0
        assert self.scheduler.history_count == 1

    def test_complete_recurring_re_queues(self):
        rt = make_recurring()
        self.scheduler.add_task(rt)
        rescheduled = self.scheduler.complete_task(rt.task_id)
        assert rescheduled is not None
        assert self.scheduler.pending_count == 1  # new instance in queue
        assert self.scheduler.history_count == 1

    def test_complete_invalid_id_raises(self):
        with pytest.raises(ValueError):
            self.scheduler.complete_task(9999)

    def test_delete_task(self):
        t = make_task()
        self.scheduler.add_task(t)
        self.scheduler.delete_task(t.task_id)
        assert self.scheduler.pending_count == 0

    def test_update_task_title(self):
        t = make_task("Original")
        self.scheduler.add_task(t)
        self.scheduler.update_task(t.task_id, title="Changed")
        pending = self.scheduler.get_pending_tasks()
        assert pending[0].title == "Changed"

    def test_get_next_task_returns_highest_priority(self):
        self.scheduler.add_task(make_task(priority=Priority.LOW))
        self.scheduler.add_task(make_task(priority=Priority.HIGH))
        assert self.scheduler.get_next_task().priority == Priority.HIGH

    def test_get_next_task_empty_returns_none(self):
        assert self.scheduler.get_next_task() is None

    def test_filter_tasks_by_priority(self):
        self.scheduler.add_task(make_task(priority=Priority.HIGH))
        self.scheduler.add_task(make_task(priority=Priority.LOW))
        pred = self.scheduler.make_priority_filter(Priority.HIGH)
        results = self.scheduler.filter_tasks(pred)
        assert len(results) == 1
        assert results[0].priority == Priority.HIGH

    def test_search_tasks_case_insensitive(self):
        self.scheduler.add_task(Task("Buy Milk", "grocery", Priority.LOW))
        self.scheduler.add_task(Task("Write Report", "work", Priority.HIGH))
        results = self.scheduler.search_tasks("milk")
        assert len(results) == 1
        assert results[0].title == "Buy Milk"

    def test_get_stats_counts(self):
        self.scheduler.add_task(make_task(priority=Priority.HIGH))
        self.scheduler.add_task(make_task(priority=Priority.HIGH))
        self.scheduler.add_task(make_task(priority=Priority.LOW))
        stats = self.scheduler.get_stats()
        assert stats["total_pending"] == 3
        assert stats["high_priority"] == 2
        assert stats["low_priority"] == 1


# ─────────────────────────── Storage ────────────────────────────────────────

class TestStorage:
    def test_save_and_load_round_trip(self):
        pending = [make_task("Save me", Priority.HIGH), make_recurring(interval=3)]
        history = [make_task("Done")]
        history[0].complete()

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            filepath = f.name

        try:
            save_tasks(pending, history, filepath)
            loaded_pending, loaded_history = load_tasks(filepath)

            assert len(loaded_pending) == 2
            assert len(loaded_history) == 1
            assert loaded_pending[0].title == "Save me"
            assert isinstance(loaded_pending[1], RecurringTask)
            assert loaded_pending[1].interval_days == 3
        finally:
            os.unlink(filepath)

    def test_load_missing_file_returns_empty(self):
        pending, history = load_tasks("/nonexistent/path/tasks.json")
        assert pending == []
        assert history == []

    def test_load_corrupt_file_raises_value_error(self):
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            f.write("not valid json{{{")
            filepath = f.name
        try:
            with pytest.raises(ValueError):
                load_tasks(filepath)
        finally:
            os.unlink(filepath)
