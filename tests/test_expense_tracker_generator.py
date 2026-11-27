import sqlite3
import sys
import types
import unittest

from generator_engine import generate_app_code
from feature_engine import analyze_blueprint, validate_feature_coverage, validate_generated_source


class ExpenseTrackerGeneratorTests(unittest.TestCase):
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
        modules = {
            "kivy": kivy,
            "kivy.app": app_module,
            "kivy.metrics": metrics,
            "kivy.uix": uix,
        }
        for name, class_name in [
            ("boxlayout", "BoxLayout"), ("button", "Button"),
            ("label", "Label"), ("textinput", "TextInput"),
            ("popup", "Popup"), ("scrollview", "ScrollView"),
        ]:
            module = types.ModuleType("kivy.uix." + name)
            setattr(module, class_name, type(class_name, (), {}))
            modules["kivy.uix." + name] = module
        previous = {key: sys.modules.get(key) for key in modules}
        sys.modules.update(modules)
        try:
            namespace = {"__name__": "generated_expense_tracker_test"}
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
            "template_id": "expense_tracker",
            "name": "NexGen Daily Finance",
            "description": "Track money offline",
            "features": features,
        })
        app_class = self.load_app_class(source)
        app = app_class()
        app.summary_label = types.SimpleNamespace(text="")
        app.db = sqlite3.connect(":memory:")
        app.create_tables()
        return app, source

    def test_expense_tracker_generates_independent_valid_app(self):
        app, source = self.make_app()
        self.assertTrue(validate_generated_source(source)["valid"])
        self.assertIn("expense_tracker.db", source)
        self.assertIn("CREATE TABLE IF NOT EXISTS transactions", source)
        self.assertIn("def add_income", source)
        self.assertIn("def add_expense", source)
        self.assertIn("def _get_summary", source)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS products", source)
        self.assertNotIn("Products / Inventory", source)
        self.assertIn("# Template: expense_tracker", source)
        app.db.close()

    def test_income_expense_history_and_currency_summaries(self):
        app, _ = self.make_app()
        app._save_income({"description": "Shop sales", "category": "Sales", "amount": "100", "currency": "USD"})
        app._save_expense({"description": "Transport", "category": "Travel", "amount": "15", "currency": "USD"})
        app._save_income({"description": "Service", "category": "Design", "amount": "500", "currency": "ZIG"})
        self.assertEqual(app._get_summary()["USD"], {"income": 100.0, "expenses": 15.0, "balance": 85.0})
        self.assertEqual(app._get_summary()["ZIG"], {"income": 500.0, "expenses": 0.0, "balance": 500.0})
        history = app._get_history()
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0][0], "income")
        app.db.close()

    def test_invalid_amount_currency_and_description_are_rejected(self):
        app, _ = self.make_app()
        with self.assertRaisesRegex(ValueError, "positive"):
            app._save_income({"description": "Job", "amount": "0", "currency": "USD"})
        with self.assertRaisesRegex(ValueError, "Currency"):
            app._save_expense({"description": "Fuel", "amount": "2", "currency": "RAND"})
        with self.assertRaisesRegex(ValueError, "description"):
            app._save_income({"description": "", "amount": "2", "currency": "USD"})
        self.assertEqual(app.db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0], 0)
        app.db.close()

    def test_blueprint_selects_only_supported_expense_tracker_features(self):
        app, source = self.make_app("income records, expenses, transaction history, budgets")
        self.assertIn("income_records", source)
        self.assertIn("expense_records", source)
        self.assertIn("transaction_history", source)
        self.assertIn("# Unsupported by selected template: budgets", source)
        coverage = validate_feature_coverage(
            source,
            ["income_records", "expense_records", "transaction_history"],
            template_id="expense_tracker",
        )
        self.assertTrue(coverage["complete"])
        plan = analyze_blueprint({
            "template_id": "expense_tracker",
            "features": "income records, expenses, budgets",
        })
        self.assertTrue(plan["ready"])
        self.assertEqual(plan["available"], ["income_records", "expense_records"])
        self.assertEqual(plan["unsupported"], ["budgets"])
        app.db.close()

    def test_unready_school_template_stays_rejected(self):
        with self.assertRaisesRegex(ValueError, "not ready to generate"):
            generate_app_code({
                "template_id": "future_template",
                "name": "School Records",
                "features": "students, attendance",
            })


if __name__ == "__main__":
    unittest.main()
