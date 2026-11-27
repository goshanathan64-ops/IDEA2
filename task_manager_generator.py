"""Independent offline Task Manager app generator for IDEA2APK V3."""
from feature_engine import analyze_blueprint, validate_feature_coverage, validate_generated_source

TASK_FEATURES = [
    "task_records", "due_dates", "priority_levels", "completion_tracking",
    "task_categories", "task_search", "basic_reports", "local_sqlite_storage",
]

TEMPLATE = r'''import os
import sqlite3
from datetime import datetime, date

from kivy.app import App
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView

APP_TITLE = __APP_TITLE__
APP_DESCRIPTION = __APP_DESCRIPTION__
ENABLED_FEATURES = __ENABLED_FEATURES__


class GeneratedApp(App):
    def build(self):
        self.title = APP_TITLE
        self.db_path = os.path.join(self.user_data_dir, "tasks.db")
        self.db = sqlite3.connect(self.db_path)
        self.create_tables()
        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(7))
        root.add_widget(Label(text=APP_TITLE, size_hint_y=None, height=dp(44), font_size=sp(22)))
        root.add_widget(Label(text=APP_DESCRIPTION, size_hint_y=None, height=dp(38), font_size=sp(12)))
        self.summary_label = Label(text="", size_hint_y=None, height=dp(82), halign="left")
        root.add_widget(self.summary_label)
        scroll = ScrollView(do_scroll_x=False)
        menu = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(7))
        menu.bind(minimum_height=menu.setter("height"))
        actions = [
            ("task_records", "ADD TASK", self.add_task),
            ("task_search", "TASK LIST / SEARCH", self.show_tasks),
            ("completion_tracking", "MARK TASK COMPLETE", self.complete_task),
            ("due_dates", "UPCOMING / OVERDUE", self.show_due_tasks),
            ("basic_reports", "TASK SUMMARY", self.show_summary),
        ]
        for feature, caption, callback in actions:
            if feature in ENABLED_FEATURES:
                button = Button(text=caption, size_hint_y=None, height=dp(48))
                button.bind(on_release=callback)
                menu.add_widget(button)
        scroll.add_widget(menu)
        root.add_widget(scroll)
        refresh = Button(text="HOME / REFRESH", size_hint_y=None, height=dp(44))
        refresh.bind(on_release=self.refresh_dashboard)
        root.add_widget(refresh)
        self.status = Label(text="Tasks are stored offline on this device.", size_hint_y=None, height=dp(30), font_size=sp(11))
        root.add_widget(self.status)
        self.refresh_dashboard()
        return root

    def create_tables(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                category TEXT DEFAULT 'General',
                priority TEXT NOT NULL DEFAULT 'medium'
                    CHECK(priority IN ('low','medium','high')),
                due_date TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending','completed')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT DEFAULT ''
            )
        """)
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date)")
        self.db.commit()

    def _save_task(self, values):
        title = str(values.get("title", "")).strip()
        description = str(values.get("description", "")).strip()
        category = str(values.get("category", "")).strip() or "General"
        priority = str(values.get("priority", "medium")).strip().lower() or "medium"
        due_date = str(values.get("due_date", "")).strip()
        if not title:
            raise ValueError("Task title is required.")
        if priority not in ("low", "medium", "high"):
            raise ValueError("Priority must be low, medium or high.")
        if due_date:
            try:
                datetime.strptime(due_date, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Due date must use YYYY-MM-DD.")
        self.db.execute(
            "INSERT INTO tasks(title,description,category,priority,due_date) VALUES(?,?,?,?,?)",
            (title, description, category, priority, due_date)
        )
        self.db.commit()

    def _get_tasks(self, search="", status="all", limit=300):
        query = (
            "SELECT id,title,description,category,priority,due_date,status,created_at "
            "FROM tasks WHERE 1=1"
        )
        params = []
        if search:
            query += " AND (title LIKE ? OR description LIKE ? OR category LIKE ?)"
            pattern = "%" + str(search).strip() + "%"
            params.extend([pattern, pattern, pattern])
        if status in ("pending", "completed"):
            query += " AND status=?"
            params.append(status)
        query += " ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, "                  "CASE WHEN due_date='' THEN 1 ELSE 0 END, due_date, id DESC LIMIT ?"
        params.append(int(limit))
        return self.db.execute(query, params).fetchall()

    def _complete_task(self, task_id):
        try:
            identifier = int(task_id)
        except (TypeError, ValueError):
            raise ValueError("Enter a valid task ID.")
        cursor = self.db.execute(
            "UPDATE tasks SET status='completed', completed_at=CURRENT_TIMESTAMP "
            "WHERE id=? AND status='pending'", (identifier,)
        )
        if cursor.rowcount != 1:
            self.db.rollback()
            raise ValueError("Pending task ID was not found.")
        self.db.commit()

    def _get_due_tasks(self, today=None):
        day = today or date.today().isoformat()
        return self.db.execute(
            "SELECT id,title,category,priority,due_date,status FROM tasks "
            "WHERE status='pending' AND due_date!='' AND due_date<=? "
            "ORDER BY due_date,id", (day,)
        ).fetchall()

    def _get_summary(self):
        total = self.db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        pending = self.db.execute("SELECT COUNT(*) FROM tasks WHERE status='pending'").fetchone()[0]
        completed = self.db.execute("SELECT COUNT(*) FROM tasks WHERE status='completed'").fetchone()[0]
        overdue = self.db.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='pending' AND due_date!='' AND due_date<?",
            (date.today().isoformat(),)
        ).fetchone()[0]
        high = self.db.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='pending' AND priority='high'"
        ).fetchone()[0]
        return {"total": total, "pending": pending, "completed": completed, "overdue": overdue, "high": high}

    def refresh_dashboard(self, *_args):
        summary = self._get_summary()
        self.summary_label.text = (
            "Tasks: {} | Pending: {} | Completed: {}\n"
            "Overdue: {} | High priority pending: {}"
        ).format(summary["total"], summary["pending"], summary["completed"],
                 summary["overdue"], summary["high"])

    def add_task(self, *_args):
        self.open_form("Add Task", [
            ("title", "Task title"),
            ("description", "Description (optional)"),
            ("category", "Category (optional)"),
            ("priority", "Priority: low, medium or high"),
            ("due_date", "Due date YYYY-MM-DD (optional)"),
        ], self._after_task_save)

    def _after_task_save(self, values):
        self._save_task(values)
        self.refresh_dashboard()

    def show_tasks(self, *_args):
        self.open_form("Search Tasks", [("search", "Search title, description or category")],
                       lambda values: self._show_task_results(values.get("search", "")))

    def _show_task_results(self, search):
        rows = self._get_tasks(search)
        message = "\n".join(
            "#{} | {} | {} | {} | {} | {}".format(
                row[0], row[1], row[3], row[4], row[5] or "No due date", row[6]
            ) for row in rows
        ) or "No matching tasks."
        self.popup_message("Task List", message)

    def complete_task(self, *_args):
        self.open_form("Complete Task", [("task_id", "Task ID")], self._after_complete)

    def _after_complete(self, values):
        self._complete_task(values.get("task_id"))
        self.refresh_dashboard()

    def show_due_tasks(self, *_args):
        rows = self._get_due_tasks()
        message = "\n".join(
            "#{} | {} | due {} | {}".format(row[0], row[1], row[4], row[3])
            for row in rows
        ) or "No overdue or due-today pending tasks."
        self.popup_message("Overdue / Due Today", message)

    def show_summary(self, *_args):
        summary = self._get_summary()
        self.popup_message(
            "Task Summary",
            "Total: {}\nPending: {}\nCompleted: {}\nOverdue: {}\nHigh priority pending: {}".format(
                summary["total"], summary["pending"], summary["completed"],
                summary["overdue"], summary["high"]
            )
        )

    def open_form(self, title, field_specs, save_callback):
        body = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(7))
        fields = {}
        for key, hint in field_specs:
            field = TextInput(hint_text=hint, multiline=False, size_hint_y=None, height=dp(44))
            fields[key] = field
            body.add_widget(field)
        buttons = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(7))
        save = Button(text="SAVE")
        cancel = Button(text="CANCEL")
        buttons.add_widget(save)
        buttons.add_widget(cancel)
        body.add_widget(buttons)
        popup = Popup(title=title, content=body, size_hint=(0.92, 0.88))
        def submit(_button):
            values = {key: field.text.strip() for key, field in fields.items()}
            try:
                save_callback(values)
                popup.dismiss()
                self.status.text = title + " saved."
            except Exception as error:
                self.popup_message("Check your entries", str(error))
        save.bind(on_release=submit)
        cancel.bind(on_release=popup.dismiss)
        popup.open()

    def popup_message(self, title, message):
        body = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(7))
        scroll = ScrollView()
        label = Label(text=message, size_hint_y=None, halign="left", valign="top")
        label.bind(texture_size=lambda obj, size: setattr(obj, "height", size[1] + dp(18)))
        scroll.add_widget(label)
        body.add_widget(scroll)
        close = Button(text="CLOSE", size_hint_y=None, height=dp(42))
        body.add_widget(close)
        popup = Popup(title=title, content=body, size_hint=(0.92, 0.82))
        close.bind(on_release=popup.dismiss)
        popup.open()
'''


def generate_task_manager_code(data):
    data = data if isinstance(data, dict) else {}
    plan = analyze_blueprint(dict(data, template_id="task_manager"))
    name = str(data.get("name") or "My Task Manager").strip() or "My Task Manager"
    description = str(data.get("description") or "Offline task and deadline manager").strip()
    requested = plan["requested"]
    selected = expand_template_features("task_manager", requested, TASK_FEATURES)
    generated = TEMPLATE.replace("__APP_TITLE__", repr(name))
    generated = generated.replace("__APP_DESCRIPTION__", repr(description))
    generated = generated.replace("__ENABLED_FEATURES__", repr(selected))
    checks = validate_feature_coverage(generated, selected, template_id="task_manager")
    generated += "\n".join([
        "",
        "# IDEA2APK V3 BLUEPRINT VERIFICATION",
        "# Template: task_manager",
        "# Requested: " + (", ".join(requested) or "none (template defaults)"),
        "# Selected for app UI: " + (", ".join(selected) or "none"),
        "# Actually generated and verified: " + (", ".join(checks["implemented"]) or "none"),
        "# Missing from generated code: " + (", ".join(checks["missing"]) or "none"),
        "# Unsupported by selected template: " + (", ".join(plan["unsupported"]) or "none"),
        "# Completion: " + ("COMPLETE" if checks["complete"] and not plan["unsupported"] else "PARTIAL - review unsupported or missing features"),
        "# Source checks are deterministic fingerprints, not a substitute for device testing.",
        "",
    ])
    validation = validate_generated_source(generated)
    if not validation["valid"]:
        raise ValueError("Task Manager generator produced invalid Python: " + "; ".join(validation["errors"]))
    return generated
