import copy
from typing import Generic, Iterator, List, Optional, TypeVar

T = TypeVar("T")


class Node(Generic[T]):
    """Single node in a singly linked list."""

    def __init__(self, data: T) -> None:
        self.data: T = data
        self.next: Optional["Node[T]"] = None

    def __repr__(self) -> str:
        return f"Node({self.data!r})"


class LinkedList(Generic[T]):
    """Singly linked list for recording task history."""

    def __init__(self) -> None:
        self._head: Optional[Node[T]] = None
        self._size: int = 0

    def prepend(self, data: T) -> None:
        """Insert element at the front (O(1))."""
        new_node = Node(data)
        new_node.next = self._head
        self._head    = new_node
        self._size   += 1

    def append(self, data: T) -> None:
        """Insert element at the end (O(n))."""
        new_node = Node(data)
        if self._head is None:
            self._head = new_node
        else:
            current = self._head
            while current.next is not None:
                current = current.next
            current.next = new_node
        self._size += 1

    def to_list(self) -> List[T]:
        return list(self)

    @property
    def size(self) -> int:
        return self._size

    def __iter__(self) -> Iterator[T]:
        current = self._head
        while current is not None:
            yield current.data
            current = current.next

    def __len__(self) -> int:
        return self._size

    def __repr__(self) -> str:
        items = " -> ".join(repr(item) for item in self)
        return f"LinkedList([{items}])"


class MinHeap(Generic[T]):
    """Array-backed min-heap priority queue."""

    def __init__(self) -> None:
        self._heap: List[T] = []

    def push(self, item: T) -> None:
        self._heap.append(item)
        self._sift_up(len(self._heap) - 1)

    def pop(self) -> T:
        """Remove and return the lowest element (highest priority)."""
        if not self._heap:
            raise IndexError("pop from empty heap")
        self._heap[0], self._heap[-1] = self._heap[-1], self._heap[0]
        item = self._heap.pop()
        if self._heap:
            self._sift_down(0)
        return item

    def peek(self) -> T:
        """Return lowest element without removing it."""
        if not self._heap:
            raise IndexError("peek from empty heap")
        return self._heap[0]

    def remove_by_id(self, task_id: int) -> Optional[T]:
        """Remove an item matching task_id and maintain heap invariance."""
        for i, task in enumerate(self._heap):
            if hasattr(task, "task_id") and task.task_id == task_id:
                self._heap[i], self._heap[-1] = self._heap[-1], self._heap[i]
                removed = self._heap.pop()
                if i < len(self._heap):
                    self._sift_down(i)
                    self._sift_up(i)
                return removed
        return None

    def to_sorted_list(self) -> List[T]:
        """Return items sorted by priority without mutating the heap."""
        temp = MinHeap()
        temp._heap = copy.copy(self._heap)
        result: List[T] = []
        while temp._heap:
            result.append(temp.pop())
        return result

    @property
    def size(self) -> int:
        return len(self._heap)

    def is_empty(self) -> bool:
        return len(self._heap) == 0

    def __iter__(self) -> Iterator[T]:
        yield from self.to_sorted_list()

    def __len__(self) -> int:
        return len(self._heap)

    def __repr__(self) -> str:
        return f"MinHeap(size={len(self._heap)})"

    def _sift_up(self, index: int) -> None:
        if index == 0:
            return
        parent = (index - 1) // 2
        if self._heap[index] < self._heap[parent]:
            self._heap[index], self._heap[parent] = (
                self._heap[parent],
                self._heap[index],
            )
            self._sift_up(parent)

    def _sift_down(self, index: int) -> None:
        size     = len(self._heap)
        left     = 2 * index + 1
        right    = 2 * index + 2
        smallest = index

        if left  < size and self._heap[left]  < self._heap[smallest]:
            smallest = left
        if right < size and self._heap[right] < self._heap[smallest]:
            smallest = right

        if smallest != index:
            self._heap[index], self._heap[smallest] = (
                self._heap[smallest],
                self._heap[index],
            )
            self._sift_down(smallest)
