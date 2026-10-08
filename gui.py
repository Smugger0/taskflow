# gui.py — tkinter GUI for TaskFlow
# Run with:  python gui.py

import os
import tkinter as tk
import webbrowser
from datetime import date, datetime, timedelta
from tkinter import messagebox, ttk

from models import Priority, RecurringTask, Task
from scheduler import TaskScheduler
from storage import load_tasks, save_tasks

SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.json")

# Map priority names to soft background colours for the Treeview rows
_ROW_COLORS = {
    "HIGH":     "#ffd6d6",
    "MEDIUM":   "#fff5cc",
    "LOW":      "#d6f5d6",
    "OVERDUE":  "#ff9999",   # past due date
    "DUE_SOON": "#ffd9a0",  # due within 3 days
}


class DatePickerPopup(tk.Toplevel):
    """Month-grid calendar popup. Sets target_var to the clicked date (YYYY-MM-DD)."""

    _DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

    def __init__(self, parent: tk.Widget, target_var: tk.StringVar) -> None:
        super().__init__(parent)
        self.title("Select date")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)
        self.bind("<Escape>", lambda _e: self.destroy())

        self._var = target_var
        try:
            self._view = datetime.strptime(target_var.get(), "%Y-%m-%d").date().replace(day=1)
        except ValueError:
            self._view = date.today().replace(day=1)

        self._frame = ttk.Frame(self, padding=8)
        self._frame.pack()
        self._render()

        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2 - self.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - self.winfo_height() // 2
        self.geometry(f"+{max(px, 0)}+{max(py, 0)}")

    def _render(self) -> None:
        for w in self._frame.winfo_children():
            w.destroy()

        # Navigation header
        nav = ttk.Frame(self._frame)
        nav.grid(row=0, column=0, columnspan=7, sticky="ew", pady=(0, 6))
        ttk.Button(nav, text="\u2039", width=2, command=self._prev_month).pack(side="left")
        ttk.Label(
            nav, text=self._view.strftime("%B %Y"),
            font=("", 10, "bold"), anchor="center", width=14,
        ).pack(side="left", expand=True)
        ttk.Button(nav, text="\u203a", width=2, command=self._next_month).pack(side="right")

        # Weekday column headers
        for col, name in enumerate(self._DAYS):
            ttk.Label(
                self._frame, text=name, width=4, anchor="center",
                font=("", 8), foreground="#666666",
            ).grid(row=1, column=col, padx=1, pady=1)

        # Day buttons
        today    = date.today()
        selected = self._var.get()
        y, m     = self._view.year, self._view.month
        next_m   = date(y + (m == 12), m % 12 + 1, 1)
        days_in  = (next_m - timedelta(days=1)).day

        row, col = 2, self._view.weekday()
        for day_num in range(1, days_in + 1):
            d = date(y, m, day_num)
            is_today    = (d == today)
            is_selected = (d.isoformat() == selected)
            bg = "#4a9eff" if is_selected else ("#c8eac8" if is_today else "SystemButtonFace")
            fg = "white"   if is_selected else "black"

            btn = tk.Button(
                self._frame, text=str(day_num), width=3,
                bg=bg, fg=fg, relief="flat", activebackground="#6db0ff",
                command=lambda d=d: self._pick(d),
            )
            btn.grid(row=row, column=col, padx=1, pady=1, sticky="nsew")
            col += 1
            if col == 7:
                col = 0
                row += 1

        ttk.Button(
            self._frame, text="Today",
            command=lambda: self._pick(date.today()),
        ).grid(row=row + 1, column=0, columnspan=7, sticky="ew", pady=(8, 0))

    def _pick(self, d: date) -> None:
        self._var.set(d.isoformat())
        self.destroy()

    def _prev_month(self) -> None:
        self._view = (self._view - timedelta(days=1)).replace(day=1)
        self._render()

    def _next_month(self) -> None:
        y, m = self._view.year, self._view.month
        self._view = date(y + (m == 12), m % 12 + 1, 1)
        self._render()


class AddTaskDialog(tk.Toplevel):
    """
    Modal dialog for creating a Task or RecurringTask.
    self.result holds constructor kwargs on confirm, or None on cancel.
    """

    def __init__(self, parent: tk.Tk, recurring: bool = False) -> None:
        super().__init__(parent)
        self.title("Add Recurring Task" if recurring else "Add Task")
        self.resizable(False, False)
        self.grab_set()         # make modal — blocks parent window
        self.transient(parent)  # keep on top of parent

        self.result = None
        self._recurring = recurring
        self._build()

        self.bind("<Return>", lambda _e: self._submit())
        self.bind("<Escape>", lambda _e: self.destroy())

        # Centre relative to parent
        self.update_idletasks()
        px, py = parent.winfo_x(), parent.winfo_y()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{px + (pw - w) // 2}+{py + (ph - h) // 2}")

        self.wait_window()  # block until dialog is destroyed

    def _build(self) -> None:
        pad = {"padx": 8, "pady": 5}
        f = ttk.Frame(self, padding=12)
        f.pack(fill="both", expand=True)

        # ---- Title ----
        ttk.Label(f, text="Title *").grid(row=0, column=0, sticky="w", **pad)
        self._title_var = tk.StringVar()
        ttk.Entry(f, textvariable=self._title_var, width=36).grid(
            row=0, column=1, sticky="ew", **pad
        )

        # ---- Description ----
        ttk.Label(f, text="Description").grid(row=1, column=0, sticky="nw", **pad)
        self._desc = tk.Text(f, width=36, height=3, wrap="word")
        self._desc.grid(row=1, column=1, sticky="ew", **pad)

        # ---- Priority ----
        ttk.Label(f, text="Priority").grid(row=2, column=0, sticky="w", **pad)
        self._priority_var = tk.StringVar(value="Medium")
        ttk.Combobox(
            f, textvariable=self._priority_var,
            values=["High", "Medium", "Low"],
            state="readonly", width=12,
        ).grid(row=2, column=1, sticky="w", **pad)

        # ---- Due date ----
        ttk.Label(f, text="Due date").grid(row=3, column=0, sticky="w", **pad)
        self._due_var = tk.StringVar()
        due_f = ttk.Frame(f)
        due_f.grid(row=3, column=1, sticky="w", **pad)
        ttk.Entry(due_f, textvariable=self._due_var, width=12).pack(side="left")
        ttk.Button(due_f, text="\U0001f4c5", width=3, command=self._pick_date).pack(side="left", padx=(2, 6))
        ttk.Button(due_f, text="Today", command=lambda: self._due_var.set(date.today().isoformat())).pack(side="left", padx=1)
        ttk.Button(due_f, text="+1d",   command=lambda: self._due_var.set((date.today() + timedelta(days=1)).isoformat())).pack(side="left", padx=1)
        ttk.Button(due_f, text="+7d",   command=lambda: self._due_var.set((date.today() + timedelta(days=7)).isoformat())).pack(side="left", padx=1)

        # ---- Interval (recurring only) ----
        if self._recurring:
            ttk.Label(f, text="Repeat every\n(days) *").grid(row=4, column=0, sticky="w", **pad)
            self._interval_var = tk.StringVar(value="7")
            ttk.Entry(f, textvariable=self._interval_var, width=8).grid(
                row=4, column=1, sticky="w", **pad
            )

        # ---- Buttons ----
        btn_row = 5 if self._recurring else 4
        btn_f = ttk.Frame(f)
        btn_f.grid(row=btn_row, column=0, columnspan=2, pady=(8, 0))
        ttk.Button(btn_f, text="Add",    command=self._submit).pack(side="left", padx=6)
        ttk.Button(btn_f, text="Cancel", command=self.destroy).pack(side="left", padx=6)

        f.columnconfigure(1, weight=1)
        self._title_var.set("")
        self.after(50, lambda: self.focus_force())

    def _pick_date(self) -> None:
        DatePickerPopup(self, self._due_var)

    def _submit(self) -> None:
        """Validate inputs and populate self.result, then close."""
        title = self._title_var.get().strip()
        if not title:
            messagebox.showwarning("Missing Field", "Title cannot be empty.", parent=self)
            return

        desc = self._desc.get("1.0", "end-1c").strip() or "(no description)"
        due  = self._due_var.get().strip() or None
        if due:
            try:
                datetime.strptime(due, "%Y-%m-%d")
            except ValueError:
                messagebox.showwarning(
                    "Invalid Date",
                    "Due date must be YYYY-MM-DD (e.g. 2025-12-31).",
                    parent=self,
                )
                return
        pri_map = {"High": Priority.HIGH, "Medium": Priority.MEDIUM, "Low": Priority.LOW}
        priority = pri_map[self._priority_var.get()]

        self.result = {
            "title":       title,
            "description": desc,
            "priority":    priority,
            "due_date":    due,
        }

        if self._recurring:
            try:
                interval = int(self._interval_var.get().strip())
                if interval <= 0:
                    raise ValueError("must be positive")
                self.result["interval_days"] = interval
            except ValueError as e:
                messagebox.showwarning(
                    "Invalid Input", f"Interval: {e}", parent=self
                )
                self.result = None
                return

        self.destroy()


class EditTaskDialog(tk.Toplevel):
    """Pre-filled modal dialog for editing an existing pending task."""

    def __init__(self, parent: tk.Tk, task: Task) -> None:
        super().__init__(parent)
        self.title("Edit Recurring Task" if isinstance(task, RecurringTask) else "Edit Task")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)

        self.result = None
        self._task = task
        self._recurring = isinstance(task, RecurringTask)
        self._build()

        self.bind("<Return>", lambda _e: self._submit())
        self.bind("<Escape>", lambda _e: self.destroy())

        self.update_idletasks()
        px, py = parent.winfo_x(), parent.winfo_y()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        w,  h  = self.winfo_width(),  self.winfo_height()
        self.geometry(f"+{px + (pw - w) // 2}+{py + (ph - h) // 2}")

        self.wait_window()

    def _build(self) -> None:
        pad = {"padx": 8, "pady": 5}
        f = ttk.Frame(self, padding=12)
        f.pack(fill="both", expand=True)

        # ---- Title ----
        ttk.Label(f, text="Title *").grid(row=0, column=0, sticky="w", **pad)
        self._title_var = tk.StringVar(value=self._task.title)
        ttk.Entry(f, textvariable=self._title_var, width=36).grid(
            row=0, column=1, sticky="ew", **pad
        )

        # ---- Description ----
        ttk.Label(f, text="Description").grid(row=1, column=0, sticky="nw", **pad)
        self._desc = tk.Text(f, width=36, height=3, wrap="word")
        desc_val = self._task.description if self._task.description != "(no description)" else ""
        self._desc.insert("1.0", desc_val)
        self._desc.grid(row=1, column=1, sticky="ew", **pad)

        # ---- Priority ----
        ttk.Label(f, text="Priority").grid(row=2, column=0, sticky="w", **pad)
        self._priority_var = tk.StringVar(value=self._task.priority.name.capitalize())
        ttk.Combobox(
            f, textvariable=self._priority_var,
            values=["High", "Medium", "Low"],
            state="readonly", width=12,
        ).grid(row=2, column=1, sticky="w", **pad)

        # ---- Due date ----
        ttk.Label(f, text="Due date").grid(row=3, column=0, sticky="w", **pad)
        self._due_var = tk.StringVar(value=self._task.due_date or "")
        due_f = ttk.Frame(f)
        due_f.grid(row=3, column=1, sticky="w", **pad)
        ttk.Entry(due_f, textvariable=self._due_var, width=12).pack(side="left")
        ttk.Button(due_f, text="\U0001f4c5", width=3, command=self._pick_date).pack(side="left", padx=(2, 6))
        ttk.Button(due_f, text="Today", command=lambda: self._due_var.set(date.today().isoformat())).pack(side="left", padx=1)
        ttk.Button(due_f, text="+1d",   command=lambda: self._due_var.set((date.today() + timedelta(days=1)).isoformat())).pack(side="left", padx=1)
        ttk.Button(due_f, text="+7d",   command=lambda: self._due_var.set((date.today() + timedelta(days=7)).isoformat())).pack(side="left", padx=1)

        # ---- Interval (recurring only) ----
        if self._recurring:
            ttk.Label(f, text="Repeat every\n(days) *").grid(row=4, column=0, sticky="w", **pad)
            self._interval_var = tk.StringVar(value=str(self._task.interval_days))
            ttk.Entry(f, textvariable=self._interval_var, width=8).grid(
                row=4, column=1, sticky="w", **pad
            )

        # ---- Buttons ----
        btn_row = 5 if self._recurring else 4
        btn_f = ttk.Frame(f)
        btn_f.grid(row=btn_row, column=0, columnspan=2, pady=(8, 0))
        ttk.Button(btn_f, text="Save",   command=self._submit).pack(side="left", padx=6)
        ttk.Button(btn_f, text="Cancel", command=self.destroy).pack(side="left", padx=6)

        f.columnconfigure(1, weight=1)
        self.after(50, lambda: self.focus_force())

    def _pick_date(self) -> None:
        DatePickerPopup(self, self._due_var)

    def _submit(self) -> None:
        title = self._title_var.get().strip()
        if not title:
            messagebox.showwarning("Missing Field", "Title cannot be empty.", parent=self)
            return

        desc = self._desc.get("1.0", "end-1c").strip() or "(no description)"
        due  = self._due_var.get().strip() or None
        if due:
            try:
                datetime.strptime(due, "%Y-%m-%d")
            except ValueError:
                messagebox.showwarning(
                    "Invalid Date",
                    "Due date must be YYYY-MM-DD (e.g. 2025-12-31).",
                    parent=self,
                )
                return

        pri_map = {"High": Priority.HIGH, "Medium": Priority.MEDIUM, "Low": Priority.LOW}
        self.result = {
            "title":       title,
            "description": desc,
            "priority":    pri_map[self._priority_var.get()],
            "due_date":    due,
        }

        if self._recurring:
            try:
                interval = int(self._interval_var.get().strip())
                if interval <= 0:
                    raise ValueError("must be positive")
                self.result["interval_days"] = interval
            except ValueError as e:
                messagebox.showwarning(
                    "Invalid Input", f"Interval: {e}", parent=self
                )
                self.result = None
                return

        self.destroy()


class App(tk.Tk):
    """Main window of the TaskFlow GUI."""

    def __init__(self) -> None:
        super().__init__()
        self.title("TaskFlow — Priority Task Scheduler")
        self.geometry("860x560")
        self.minsize(640, 420)

        self._scheduler = TaskScheduler()
        self._load_data()
        self._build_ui()
        self._refresh()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Control-n>", lambda _e: self._cmd_add_task())
        self.bind("<Control-r>", lambda _e: self._cmd_add_recurring())
        self.bind("<Control-e>", lambda _e: self._cmd_edit())
        self.bind("<Control-d>", lambda _e: self._cmd_delete())
        self.bind("<Control-s>", lambda _e: self._save())

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------

    def _load_data(self) -> None:
        try:
            pending, history = load_tasks(SAVE_FILE)
            self._scheduler.set_tasks_from_data(pending, history)
        except ValueError as e:
            messagebox.showwarning("Load Warning", str(e))

    def _save(self, notify: bool = True) -> None:
        try:
            save_tasks(
                pending=self._scheduler.get_pending_tasks(),
                history=self._scheduler.get_history(),
                filepath=SAVE_FILE,
            )
            self._set_status(f"Saved to '{SAVE_FILE}'.")
            if notify:
                messagebox.showinfo("Saved", "Tasks saved successfully.")
        except IOError as e:
            messagebox.showerror("Save Error", str(e))

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._build_toolbar()
        self._build_notebook()
        self._build_detail_panel()
        self._build_statusbar()

    def _build_toolbar(self) -> None:
        outer = ttk.Frame(self, padding=(5, 2))
        outer.pack(fill="x")

        # ---- Row 1: action buttons + utility buttons ----
        row1 = ttk.Frame(outer)
        row1.pack(fill="x", pady=(2, 1))

        ttk.Button(row1, text="＋ Add Task",     command=self._cmd_add_task).pack(side="left", padx=2)
        ttk.Button(row1, text="↻ Add Recurring", command=self._cmd_add_recurring).pack(side="left", padx=2)
        ttk.Button(row1, text="✓ Complete",      command=self._cmd_complete).pack(side="left", padx=2)
        ttk.Button(row1, text="\u270f Edit",        command=self._cmd_edit).pack(side="left", padx=2)
        ttk.Button(row1, text="\U0001f5d1 Delete",  command=self._cmd_delete).pack(side="left", padx=2)

        ttk.Button(row1, text="📊 Stats", command=self._cmd_stats).pack(side="right", padx=2)
        ttk.Button(row1, text="💾 Save",  command=self._save).pack(side="right", padx=2)
        ttk.Button(row1, text="❓ Help",  command=self._cmd_help).pack(side="right", padx=2)

        # ---- Row 2: search + filter ----
        row2 = ttk.Frame(outer)
        row2.pack(fill="x", pady=(1, 2))

        ttk.Label(row2, text="Search:").pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refresh())
        ttk.Entry(row2, textvariable=self._search_var, width=20).pack(side="left", padx=(4, 0))
        ttk.Button(row2, text="×", width=2, command=lambda: self._search_var.set("")).pack(side="left", padx=(2, 8))

        ttk.Separator(row2, orient="vertical").pack(side="left", padx=6, fill="y")

        ttk.Label(row2, text="Priority:").pack(side="left")
        self._filter_var = tk.StringVar(value="All")
        cb = ttk.Combobox(
            row2, textvariable=self._filter_var,
            values=["All", "High", "Medium", "Low"],
            state="readonly", width=8,
        )
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda _e: self._refresh())

    def _build_notebook(self) -> None:
        self._nb = ttk.Notebook(self)
        self._nb.pack(fill="both", expand=True, padx=5, pady=(0, 2))

        # ---- Pending tab ----
        pf = ttk.Frame(self._nb)
        self._nb.add(pf, text=" Pending Tasks ")

        cols = ("id", "priority", "title", "due", "type")
        self._ptree = ttk.Treeview(pf, columns=cols, show="headings", selectmode="browse")
        self._ptree.heading("id",       text="#",        anchor="center",
                            command=lambda: self._sort_column(self._ptree, "id", False))
        self._ptree.heading("priority", text="Priority", anchor="center",
                            command=lambda: self._sort_column(self._ptree, "priority", False))
        self._ptree.heading("title",    text="Title",
                            command=lambda: self._sort_column(self._ptree, "title", False))
        self._ptree.heading("due",      text="Due Date",  anchor="center",
                            command=lambda: self._sort_column(self._ptree, "due", False))
        self._ptree.heading("type",     text="Type",      anchor="center",
                            command=lambda: self._sort_column(self._ptree, "type", False))
        self._ptree.column("id",       width=42,  stretch=False, anchor="center")
        self._ptree.column("priority", width=80,  stretch=False, anchor="center")
        self._ptree.column("title",    width=340)
        self._ptree.column("due",      width=100, stretch=False, anchor="center")
        self._ptree.column("type",     width=90,  stretch=False, anchor="center")

        vsb = ttk.Scrollbar(pf, orient="vertical", command=self._ptree.yview)
        self._ptree.configure(yscrollcommand=vsb.set)
        self._ptree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        for tag, color in _ROW_COLORS.items():
            self._ptree.tag_configure(tag, background=color)

        self._ptree.bind("<<TreeviewSelect>>", lambda _e: self._on_select())
        self._ptree.bind("<Double-1>",         lambda _e: self._cmd_edit())

        # ---- History tab ----
        hf = ttk.Frame(self._nb)
        self._nb.add(hf, text=" Completed ")

        hcols = ("id", "priority", "title", "created", "type")
        self._htree = ttk.Treeview(hf, columns=hcols, show="headings", selectmode="browse")
        self._htree.heading("id",       text="#",       anchor="center")
        self._htree.heading("priority", text="Priority",anchor="center")
        self._htree.heading("title",    text="Title")
        self._htree.heading("created",  text="Added At", anchor="center")
        self._htree.heading("type",     text="Type",     anchor="center")
        self._htree.column("id",       width=42,  stretch=False, anchor="center")
        self._htree.column("priority", width=80,  stretch=False, anchor="center")
        self._htree.column("title",    width=340)
        self._htree.column("created",  width=130, stretch=False, anchor="center")
        self._htree.column("type",     width=90,  stretch=False, anchor="center")

        hvsb = ttk.Scrollbar(hf, orient="vertical", command=self._htree.yview)
        self._htree.configure(yscrollcommand=hvsb.set)
        self._htree.pack(side="left", fill="both", expand=True)
        hvsb.pack(side="right", fill="y")

        for tag, color in _ROW_COLORS.items():
            self._htree.tag_configure(tag, background=color)

        self._htree.bind("<<TreeviewSelect>>", lambda _e: self._on_select())

    def _build_detail_panel(self) -> None:
        """Small panel below the notebook that shows the selected task description."""
        frame = ttk.LabelFrame(self, text="Description", padding=4)
        frame.pack(fill="x", padx=5, pady=(0, 2))

        self._detail_var = tk.StringVar(value="Select a task to see its description.")
        lbl = ttk.Label(frame, textvariable=self._detail_var, wraplength=820, anchor="w")
        lbl.pack(fill="x")

    def _build_statusbar(self) -> None:
        self._status_var = tk.StringVar(value="Ready")
        ttk.Label(
            self, textvariable=self._status_var,
            relief="sunken", anchor="w", padding=(6, 2),
        ).pack(fill="x", side="bottom")

    # ------------------------------------------------------------------
    # Refresh — repopulate both trees from scheduler state
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        """Repopulate both Treeview widgets from current scheduler state."""
        for iid in self._ptree.get_children():
            self._ptree.delete(iid)
        for iid in self._htree.get_children():
            self._htree.delete(iid)

        kw   = self._search_var.get().lower()
        filt = self._filter_var.get()

        # Pending
        tasks = (
            self._scheduler.search_tasks(kw)
            if kw
            else self._scheduler.get_pending_tasks()
        )
        for task in tasks:
            if filt != "All" and task.priority.name.capitalize() != filt:
                continue
            kind = "Recurring" if isinstance(task, RecurringTask) else "Task"
            tag = task.priority.name
            if task.due_date:
                try:
                    due_d = datetime.strptime(task.due_date, "%Y-%m-%d").date()
                    _today = date.today()
                    if due_d < _today:
                        tag = "OVERDUE"
                    elif due_d <= _today + timedelta(days=3):
                        tag = "DUE_SOON"
                except ValueError:
                    pass
            self._ptree.insert(
                "", "end", iid=str(task.task_id),
                values=(task.task_id, str(task.priority), task.title,
                        task.due_date or "", kind),
                tags=(tag,),
            )

        # History
        for task in self._scheduler.get_history():
            kind = "Recurring" if isinstance(task, RecurringTask) else "Task"
            self._htree.insert(
                "", "end", iid=str(task.task_id),
                values=(task.task_id, str(task.priority), task.title,
                        task.created_at, kind),
                tags=(task.priority.name,),
            )

        stats = self._scheduler.get_stats()
        self._set_status(
            f"Pending: {stats['total_pending']}  │  "
            f"High: {stats['high_priority']}  "
            f"Medium: {stats['medium_priority']}  "
            f"Low: {stats['low_priority']}  │  "
            f"Completed: {stats['total_completed']}"
        )
        self._nb.tab(0, text=f" Pending ({stats['total_pending']}) ")
        self._nb.tab(1, text=f" Completed ({stats['total_completed']}) ")
    # ------------------------------------------------------------------
    # Event handlers (Event-driven design)
    # ------------------------------------------------------------------

    def _on_select(self) -> None:
        """Show selected task description in the detail panel."""
        # Determine which tree is active
        tree = (
            self._ptree
            if self._nb.index(self._nb.select()) == 0
            else self._htree
        )
        sel = tree.selection()
        if not sel:
            return

        task_id = int(sel[0])
        all_tasks = (
            self._scheduler.get_pending_tasks()
            + self._scheduler.get_history()
        )
        task = next((t for t in all_tasks if t.task_id == task_id), None)
        if task:
            extra = (
                f"  [Recurs every {task.interval_days} day(s)]"
                if isinstance(task, RecurringTask)
                else ""
            )
            self._detail_var.set(f"{task.description}{extra}")

    def _cmd_add_task(self) -> None:
        dlg = AddTaskDialog(self, recurring=False)
        if dlg.result:
            task = Task(**dlg.result)
            self._scheduler.add_task(task)
            self._refresh()
            self._set_status(f"Task #{task.task_id} added — \"{task.title}\".")

    def _cmd_add_recurring(self) -> None:
        dlg = AddTaskDialog(self, recurring=True)
        if dlg.result:
            task = RecurringTask(**dlg.result)
            self._scheduler.add_task(task)
            self._refresh()
            self._set_status(
                f"Recurring Task #{task.task_id} added — "
                f"\"{task.title}\" every {task.interval_days} day(s)."
            )

    def _cmd_complete(self) -> None:
        sel = self._ptree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a pending task first.")
            return

        task_id    = int(sel[0])
        task_title = self._ptree.item(sel[0])["values"][2]

        if not messagebox.askyesno(
            "Complete Task", f'Mark "{task_title}" as complete?'
        ):
            return

        try:
            rescheduled = self._scheduler.complete_task(task_id)
            self._refresh()
            if rescheduled:
                self._set_status(
                    f"Task #{task_id} done.  "
                    f"Rescheduled as Task #{rescheduled.task_id} "
                    f"(due: {rescheduled.due_date})."
                )
            else:
                self._set_status(f"Task #{task_id} marked as complete.")
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def _cmd_stats(self) -> None:
        stats = self._scheduler.get_stats()
        messagebox.showinfo(
            "Statistics",
            f"Pending tasks   :  {stats['total_pending']}\n"
            f"Completed tasks :  {stats['total_completed']}\n"
            f"\n"
            f"High priority   :  {stats['high_priority']}\n"
            f"Medium priority :  {stats['medium_priority']}\n"
            f"Low priority    :  {stats['low_priority']}",
        )

    def _cmd_edit(self) -> None:
        sel = self._ptree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a pending task first.")
            return

        task_id = int(sel[0])
        task = next(
            (t for t in self._scheduler.get_pending_tasks() if t.task_id == task_id),
            None,
        )
        if task is None:
            return

        dlg = EditTaskDialog(self, task)
        if dlg.result:
            try:
                self._scheduler.update_task(task_id, **dlg.result)
                self._refresh()
                self._set_status(f"Task #{task_id} updated.")
            except ValueError as e:
                messagebox.showerror("Error", str(e))

    def _cmd_delete(self) -> None:
        sel = self._ptree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a pending task first.")
            return

        task_id    = int(sel[0])
        task_title = self._ptree.item(sel[0])["values"][2]

        if not messagebox.askyesno(
            "Delete Task",
            f'Permanently delete "{task_title}"?\nThis cannot be undone.',
        ):
            return

        try:
            self._scheduler.delete_task(task_id)
            self._refresh()
            self._set_status(f"Task #{task_id} deleted.")
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def _sort_column(self, tree: ttk.Treeview, col: str, reverse: bool) -> None:
        items = [(tree.set(iid, col), iid) for iid in tree.get_children("")]
        items.sort(key=lambda x: x[0].lower(), reverse=reverse)
        for idx, (_, iid) in enumerate(items):
            tree.move(iid, "", idx)
        tree.heading(col, command=lambda c=col, r=reverse: self._sort_column(tree, c, not r))

    def _cmd_help(self) -> None:
        guide = os.path.join(os.path.dirname(os.path.abspath(__file__)), "guide.html")
        if os.path.exists(guide):
            webbrowser.open(f"file:///{guide.replace(os.sep, '/')}")
        else:
            messagebox.showinfo("Help", "guide.html not found next to this script.")

    def _on_close(self) -> None:
        if messagebox.askyesno("Exit", "Save tasks before exiting?"):
            self._save(notify=False)
        self.destroy()

    def _set_status(self, msg: str) -> None:
        self._status_var.set(msg)


if __name__ == "__main__":
    app = App()
    app.mainloop()
