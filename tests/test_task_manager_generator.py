import sqlite3
import sys
import types
import unittest

from feature_engine import validate_feature_coverage, validate_generated_source
from generator_engine import generate_app_code


class TaskManagerGeneratorTests(unittest.TestCase):
    def load_app_class(self, source):
        kivy = types.ModuleType("kivy")
        kivy.__path__ = []
        app_module = types.ModuleType("kivy.app")
        app_module.App = type("App", (), {})
        metrics = types.ModuleType("kivy.metrics")
        metrics.dp = lambda value: value
        metrics.sp = lambda value: value
        uix = types.ModuleType("kivy.uix")
        uix.__path__ = []
        modules = {"kivy": kivy, "kivy.app": app_module, "kivy.metrics": metrics, "kivy.uix": uix}
        for name, class_name in [
            ("boxlayout", "BoxLayout"), ("button", "Button"), ("label", "Label"),
            ("textinput", "TextInput"), ("popup", "Popup"), ("scrollview", "ScrollView"),
        ]:
            module = types.ModuleType("kivy.uix." + name)
            setattr(module, class_name, type(class_name, (), {}))
            modules["kivy.uix." + name] = module
        previous = {key: sys.modules.get(key) for key in modules}
        sys.modules.update(modules)
        try:
            namespace = {"__name__": "generated_task_manager_test"}
            exec(source, namespace)
            return namespace["GeneratedApp"]
        finally:
            for key, value in previous.items():
                if value is None:
                    sys.modules.pop(key, None)
                else:
                    sys.modules[key] = value

    def make_app(self, features=""):
        source = generate_app_code({
            "template_id": "task_manager",
            "name": "NexGen Task Manager",
            "description": "Offline tasks and deadlines",
            "features": features,
        })
        app = self.load_app_class(source)()
        app.db = sqlite3.connect(":memory:")
        app.create_tables()
        return app, source

    def task(self, title="Prepare school posters", priority="high", due="2026-11-28"):
        return {
            "title": title, "description": "Prepare and check artwork",
            "category": "Design", "priority": priority, "due_date": due,
        }

    def test_generates_independent_valid_task_app(self):
        app, source = self.make_app()
        self.assertTrue(validate_generated_source(source)["valid"])
        self.assertIn("tasks.db", source)
        self.assertIn("CREATE TABLE IF NOT EXISTS tasks", source)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS products", source)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS bookings", source)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS students", source)
        self.assertIn("# Template: task_manager", source)
        app.db.close()

    def test_save_task_and_search_by_title_description_or_category(self):
        app, _ = self.make_app()
        app._save_task(self.task())
        self.assertEqual(len(app._get_tasks("school")), 1)
        self.assertEqual(len(app._get_tasks("Design")), 1)
        self.assertEqual(app._get_tasks()[0][1], "Prepare school posters")
        app.db.close()

    def test_priority_validation_and_ordering(self):
        app, _ = self.make_app()
        app._save_task(self.task("Low task", "low"))
        app._save_task(self.task("Medium task", "medium"))
        app._save_task(self.task("High task", "high"))
        self.assertEqual([row[1] for row in app._get_tasks()], [
            "High task", "Medium task", "Low task"
        ])
        with self.assertRaisesRegex(ValueError, "Priority"):
            app._save_task(self.task(priority="urgent"))
        app.db.close()

    def test_due_date_validation_and_overdue_filter(self):
        app, _ = self.make_app()
        app._save_task(self.task("Old task", due="2026-11-26"))
        app._save_task(self.task("Today task", due="2026-11-27"))
        app._save_task(self.task("Future task", due="2026-12-01"))
        self.assertEqual([row[1] for row in app._get_due_tasks("2026-11-27")], [
            "Old task", "Today task"
        ])
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            app._save_task(self.task(due="27/11/2026"))
        app.db.close()

    def test_complete_task_updates_state_and_prevents_double_completion(self):
        app, _ = self.make_app()
        app._save_task(self.task())
        app._complete_task(1)
        row = app._get_tasks()[0]
        self.assertEqual(row[6], "completed")
        self.assertTrue(row[7])
        with self.assertRaisesRegex(ValueError, "Pending task"):
            app._complete_task(1)
        with self.assertRaisesRegex(ValueError, "valid task ID"):
            app._complete_task("abc")
        app.db.close()

    def test_summary_counts_pending_completed_overdue_and_high_priority(self):
        app, _ = self.make_app()
        app._save_task(self.task("Past high", "high", "2026-11-26"))
        app._save_task(self.task("Future high", "high", "2026-12-01"))
        app._save_task(self.task("No deadline", "low", ""))
        app._complete_task(3)
        summary = app._get_summary()
        self.assertEqual(summary, {
            "total": 3, "pending": 2, "completed": 1, "overdue": 1, "high": 2
        })
        app.db.close()

    def test_blueprint_verification_reports_unsupported_features(self):
        app, source = self.make_app(
            "tasks, due dates, priorities, completion tracking, task search, recurring tasks"
        )
        self.assertIn("task_records", source)
        self.assertIn("due_dates", source)
        self.assertIn("priority_levels", source)
        self.assertIn("completion_tracking", source)
        self.assertIn("# Unsupported by selected template: recurring_tasks", source)
        coverage = validate_feature_coverage(
            source,
            ["task_records", "due_dates", "priority_levels", "completion_tracking", "task_search"],
            template_id="task_manager",
        )
        self.assertTrue(coverage["complete"])
        app.db.close()


if __name__ == "__main__":
    unittest.main()
