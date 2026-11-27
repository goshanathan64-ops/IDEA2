import sqlite3
import sys
import types
import unittest

from feature_engine import validate_feature_coverage, validate_generated_source
from generator_engine import generate_app_code


class CustomerManagerGeneratorTests(unittest.TestCase):
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
            namespace = {"__name__": "generated_customer_manager_test"}
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
            "template_id": "customer_manager",
            "name": "NexGen Customer Manager",
            "description": "Offline customer records and follow-ups",
            "features": features,
        })
        app = self.load_app_class(source)()
        app.db = sqlite3.connect(":memory:")
        app.db.execute("PRAGMA foreign_keys=ON")
        app.create_tables()
        return app, source

    def customer(self, name="Baba Popo Hardware", phone="0716129854"):
        return {
            "name": name, "phone": phone, "email": "sales@example.com",
            "address": "Gweshe Shopping Centre", "notes": "Hardware customer",
        }

    def test_generates_independent_valid_customer_app(self):
        app, source = self.make_app()
        self.assertTrue(validate_generated_source(source)["valid"])
        self.assertIn("customers.db", source)
        self.assertIn("CREATE TABLE IF NOT EXISTS customers", source)
        self.assertIn("CREATE TABLE IF NOT EXISTS followups", source)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS products", source)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS bookings", source)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS students", source)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS tasks", source)
        self.assertIn("# Template: customer_manager", source)
        app.db.close()

    def test_save_customer_and_search_by_name_phone_email_and_notes(self):
        app, _ = self.make_app()
        app._save_customer(self.customer())
        self.assertEqual(len(app._get_customers("Baba Popo")), 1)
        self.assertEqual(len(app._get_customers("0716129854")), 1)
        self.assertEqual(len(app._get_customers("example.com")), 1)
        self.assertEqual(len(app._get_customers("Hardware customer")), 1)
        app.db.close()

    def test_customer_update_preserves_id_and_replaces_contact_details(self):
        app, _ = self.make_app()
        app._save_customer(self.customer())
        app._save_customer({
            "customer_id": "1", "name": "Baba Popo Hardware",
            "phone": "0779000000", "email": "", "address": "Howard",
            "notes": "Updated contact",
        })
        row = app._get_customers()[0]
        self.assertEqual(row[0], 1)
        self.assertEqual(row[2], "0779000000")
        self.assertEqual(row[4], "Howard")
        self.assertEqual(row[5], "Updated contact")
        with self.assertRaisesRegex(ValueError, "not found"):
            app._save_customer({"customer_id": "999", "name": "Missing"})
        app.db.close()

    def test_customer_name_and_email_validation(self):
        app, _ = self.make_app()
        with self.assertRaisesRegex(ValueError, "name is required"):
            app._save_customer({"name": " "})
        with self.assertRaisesRegex(ValueError, "valid email"):
            app._save_customer({"name": "Customer", "email": "bad-email"})
        app.db.close()

    def test_save_followup_and_get_pending_history(self):
        app, _ = self.make_app()
        app._save_customer(self.customer())
        app._save_followup({
            "customer_id": "1", "followup_date": "2026-11-28",
            "note": "Call about solar equipment",
        })
        rows = app._get_followups("pending")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][2], "Baba Popo Hardware")
        self.assertEqual(rows[0][4], "Call about solar equipment")
        app.db.close()

    def test_followup_validation_and_customer_relation(self):
        app, _ = self.make_app()
        with self.assertRaisesRegex(ValueError, "Customer ID"):
            app._save_followup({"customer_id": "1", "followup_date": "2026-11-28", "note": "Call"})
        app._save_customer(self.customer())
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            app._save_followup({"customer_id": "1", "followup_date": "28/11/2026", "note": "Call"})
        with self.assertRaisesRegex(ValueError, "note is required"):
            app._save_followup({"customer_id": "1", "followup_date": "2026-11-28", "note": ""})
        app.db.close()

    def test_complete_followup_and_filter_due_records(self):
        app, _ = self.make_app()
        app._save_customer(self.customer())
        app._save_followup({"customer_id": "1", "followup_date": "2026-11-26", "note": "Past"})
        app._save_followup({"customer_id": "1", "followup_date": "2026-12-02", "note": "Future"})
        due = app._get_followups("pending", through_date="2026-11-27")
        self.assertEqual(len(due), 1)
        app._complete_followup(1)
        self.assertEqual(app._get_followups("pending")[0][0], 2)
        with self.assertRaisesRegex(ValueError, "Pending follow-up"):
            app._complete_followup(1)
        app.db.close()

    def test_summary_counts_customers_and_followups(self):
        app, _ = self.make_app()
        app._save_customer(self.customer())
        app._save_customer(self.customer("Second customer", ""))
        app._save_followup({"customer_id": "1", "followup_date": "2026-11-26", "note": "Due"})
        app._save_followup({"customer_id": "2", "followup_date": "2026-12-01", "note": "Later"})
        app._complete_followup(2)
        summary = app._get_summary()
        self.assertEqual(summary["customers"], 2)
        self.assertEqual(summary["with_phone"], 1)
        self.assertEqual(summary["pending"], 1)
        self.assertEqual(summary["completed"], 1)
        self.assertEqual(summary["due"], 1)
        app.db.close()

    def test_blueprint_verification_reports_unsupported_features(self):
        app, source = self.make_app(
            "customer profiles, contact details, customer notes, follow-up records, "
            "follow-up tracking, customer search, bulk SMS"
        )
        self.assertIn("customer_profiles", source)
        self.assertIn("contact_details", source)
        self.assertIn("follow_up_records", source)
        self.assertIn("# Unsupported by selected template: bulk_sms", source)
        coverage = validate_feature_coverage(
            source,
            ["customer_profiles", "contact_details", "customer_notes",
             "follow_up_records", "follow_up_tracking", "customer_search"],
            template_id="customer_manager",
        )
        self.assertTrue(coverage["complete"])
        app.db.close()


if __name__ == "__main__":
    unittest.main()
