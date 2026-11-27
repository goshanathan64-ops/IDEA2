"""Runtime smoke tests for generated IDEA2APK V3 app templates."""
import sqlite3
import sys
import types
import unittest

from generator_engine import generate_app_code
from feature_engine import validate_generated_source


def install_kivy_test_stubs():
    """Install minimal Kivy modules so generated database workflows run in CI."""
    names = {
        "kivy": None,
        "kivy.app": "App",
        "kivy.metrics": None,
        "kivy.uix": None,
        "kivy.uix.boxlayout": "BoxLayout",
        "kivy.uix.button": "Button",
        "kivy.uix.label": "Label",
        "kivy.uix.textinput": "TextInput",
        "kivy.uix.popup": "Popup",
        "kivy.uix.scrollview": "ScrollView",
    }
    modules = {}
    for module_name, class_name in names.items():
        module = types.ModuleType(module_name)
        if module_name in ("kivy", "kivy.uix"):
            module.__path__ = []
        if class_name:
            setattr(module, class_name, type(class_name, (), {}))
        modules[module_name] = module
    modules["kivy.metrics"].dp = lambda value: value
    modules["kivy.metrics"].sp = lambda value: value
    previous = {key: sys.modules.get(key) for key in modules}
    sys.modules.update(modules)
    return previous


def restore_modules(previous):
    for key, value in previous.items():
        if value is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = value


class GeneratedTemplateQualityTests(unittest.TestCase):
    def load_app(self, template_id, name):
        source = generate_app_code({
            "template_id": template_id,
            "name": name,
            "description": "Offline generated app quality test",
            "features": "",
        })
        self.assertTrue(validate_generated_source(source)["valid"])
        previous = install_kivy_test_stubs()
        try:
            namespace = {"__name__": "generated_template_quality_test"}
            exec(source, namespace)
            app = namespace["GeneratedApp"]()
        finally:
            restore_modules(previous)
        app.db = sqlite3.connect(":memory:")
        app.create_tables()
        return app

    def test_expense_tracker_saves_income_and_expense_and_calculates_balances(self):
        app = self.load_app("expense_tracker", "Test Accounts")
        app.summary_label = types.SimpleNamespace(text="")
        app._save_income({"description": "Shop sales", "category": "Sales", "amount": "25", "currency": "USD"})
        app._save_expense({"description": "Transport", "category": "Travel", "amount": "5", "currency": "USD"})
        totals = app._get_summary()
        self.assertEqual(totals["USD"], {"income": 25.0, "expenses": 5.0, "balance": 20.0})
        self.assertEqual(len(app._get_history()), 2)
        with self.assertRaisesRegex(ValueError, "positive"):
            app._save_transaction("income", {"description": "Bad", "amount": "0", "currency": "USD"})
        app.db.close()

    def test_school_records_persist_student_attendance_and_marks(self):
        app = self.load_app("school_records", "Test School")
        app._save_student({"admission_no": "S001", "name": "Tariro", "class_name": "ECD A"})
        app._record_attendance("S001", "2026-11-27", "present")
        app._save_result("S001", "Mathematics", "Term 3", 87, 100)
        self.assertEqual(app._get_students("Tariro")[0][:3], ("S001", "Tariro", "ECD A"))
        self.assertEqual(app._get_attendance()[0][-1], "present")
        self.assertEqual(app._get_results("S001")[0][3:6], ("Mathematics", "Term 3", 87.0))
        with self.assertRaisesRegex(ValueError, "between zero"):
            app._save_result("S001", "Maths", "Term 3", 120, 100)
        app.db.close()

    def test_booking_manager_blocks_overlaps_and_updates_status(self):
        app = self.load_app("booking_appointments", "Test Bookings")
        booking = {
            "customer_name": "Tariro", "phone": "0771000000", "service": "Haircut",
            "booking_date": "2026-11-28", "booking_time": "10:00",
            "duration_minutes": "60", "notes": "First visit",
        }
        app._save_booking(booking)
        self.assertEqual(len(app._get_history()), 1)
        with self.assertRaisesRegex(ValueError, "overlaps"):
            app._save_booking(dict(booking, booking_time="10:30"))
        booking_id = app._get_history()[0][0]
        app._update_booking_status(booking_id, "completed")
        self.assertEqual(app._get_history()[0][7], "completed")
        app.db.close()

    def test_task_manager_saves_searches_and_completes_tasks(self):
        app = self.load_app("task_manager", "Test Tasks")
        app._save_task({
            "title": "Submit school poster", "description": "Prepare final artwork",
            "category": "Work", "priority": "high", "due_date": "2026-11-28",
        })
        tasks = app._get_tasks(search="school")
        self.assertEqual(len(tasks), 1)
        task_id = tasks[0][0]
        app._complete_task(task_id)
        self.assertEqual(app._get_tasks(status="completed")[0][6], "completed")
        with self.assertRaisesRegex(ValueError, "Pending task"):
            app._complete_task(task_id)
        app.db.close()

    def test_customer_manager_saves_profiles_and_followups(self):
        app = self.load_app("customer_manager", "Test Customers")
        app._save_customer({
            "name": "Tariro", "phone": "0771000000", "email": "tariro@example.com",
            "address": "Gweshe", "notes": "School client",
        })
        customer_id = app._get_customers("Tariro")[0][0]
        app._save_followup({
            "customer_id": str(customer_id), "followup_date": "2026-11-28",
            "note": "Confirm certificate order",
        })
        followups = app._get_followups(status="pending")
        self.assertEqual(len(followups), 1)
        self.assertEqual(followups[0][2], "Tariro")
        app._complete_followup(followups[0][0])
        self.assertEqual(app._get_followups(status="completed")[0][5], "completed")
        app.db.close()


    def test_shop_manager_saves_products_sales_customers_and_expenses(self):
        app = self.load_app("shop_inventory", "Test Shop")
        app.db.execute(
            "INSERT INTO products(name, price, quantity, cost_price, selling_price, currency, low_stock_threshold) "
            "VALUES(?,?,?,?,?,?,?)",
            ("Mealie Meal", 8.0, 10, 5.0, 8.0, "USD", 3),
        )
        app.db.commit()
        total, currency = app._save_sale({
            "product": "Mealie Meal", "quantity": "2", "customer": "Tariro"
        })
        self.assertEqual((total, currency), (16.0, "USD"))
        self.assertEqual(app.db.execute(
            "SELECT quantity FROM products WHERE name='Mealie Meal'"
        ).fetchone()[0], 8)
        self.assertEqual(len(app._get_sales_history()), 1)
        self.assertEqual(app._get_low_stock_products(), [])
        app._save_customer("Tariro", "0771000000")
        self.assertEqual(app._get_customers("Tariro")[0], ("Tariro", "0771000000"))
        app._save_expense("Transport", 2.5, "USD")
        self.assertEqual(app._get_expense_history()[0][1:], ("Transport", 2.5, "USD"))
        with self.assertRaisesRegex(ValueError, "Not enough stock"):
            app._save_sale({"product": "Mealie Meal", "quantity": "20"})
        self.assertEqual(app.db.execute(
            "SELECT quantity FROM products WHERE name='Mealie Meal'"
        ).fetchone()[0], 8)
        app.db.close()


if __name__ == "__main__":
    unittest.main()
