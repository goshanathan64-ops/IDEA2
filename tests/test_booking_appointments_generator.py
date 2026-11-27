import sqlite3
import sys
import types
import unittest

from generator_engine import generate_app_code
from feature_engine import validate_feature_coverage, validate_generated_source


class BookingAppointmentsGeneratorTests(unittest.TestCase):
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
            namespace = {"__name__": "generated_booking_test"}
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
            "template_id": "booking_appointments",
            "name": "NexGen Booking Manager",
            "description": "Offline appointments",
            "features": features,
        })
        app = self.load_app_class(source)()
        app.db = sqlite3.connect(":memory:")
        app.create_tables()
        return app, source

    def booking(self, customer="Tariro", service="Haircut", time="10:00", duration=60):
        return {
            "customer_name": customer, "phone": "0771000000", "service": service,
            "booking_date": "2026-12-01", "booking_time": time,
            "duration_minutes": duration, "notes": "Test appointment",
        }

    def test_generates_independent_valid_booking_app(self):
        app, source = self.make_app()
        self.assertTrue(validate_generated_source(source)["valid"])
        self.assertIn("bookings.db", source)
        self.assertIn("CREATE TABLE IF NOT EXISTS bookings", source)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS products", source)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS students", source)
        self.assertIn("# Template: booking_appointments", source)
        app.db.close()

    def test_save_booking_and_history(self):
        app, _ = self.make_app()
        app._save_booking(self.booking())
        rows = app._get_history()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "Tariro")
        self.assertEqual(rows[0][3], "Haircut")
        self.assertEqual(rows[0][7], "scheduled")
        app.db.close()

    def test_rejects_overlapping_bookings_for_same_service(self):
        app, _ = self.make_app()
        app._save_booking(self.booking(time="10:00", duration=60))
        with self.assertRaisesRegex(ValueError, "overlaps"):
            app._save_booking(self.booking(customer="Rudo", time="10:30", duration=30))
        app._save_booking(self.booking(customer="Rudo", service="Consultation", time="10:30"))
        app.db.close()

    def test_cancelled_booking_does_not_block_new_booking(self):
        app, _ = self.make_app()
        app._save_booking(self.booking())
        app._update_booking_status(1, "cancelled")
        app._save_booking(self.booking(customer="Kuda", time="10:15"))
        self.assertEqual(len(app._get_history()), 2)
        app.db.close()

    def test_booking_input_validation_and_status_updates(self):
        app, _ = self.make_app()
        with self.assertRaisesRegex(ValueError, "Customer name"):
            app._save_booking(self.booking(customer=""))
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            bad = self.booking()
            bad["booking_date"] = "01/12/2026"
            app._save_booking(bad)
        with self.assertRaisesRegex(ValueError, "HH:MM"):
            bad = self.booking()
            bad["booking_time"] = "10am"
            app._save_booking(bad)
        with self.assertRaisesRegex(ValueError, "Duration"):
            bad = self.booking()
            bad["duration_minutes"] = 2
            app._save_booking(bad)
        app._save_booking(self.booking())
        app._update_booking_status(1, "completed")
        self.assertEqual(app._get_history()[0][7], "completed")
        with self.assertRaisesRegex(ValueError, "Status"):
            app._update_booking_status(1, "pending")
        app.db.close()

    def test_summary_and_upcoming_filter(self):
        app, _ = self.make_app()
        app._save_booking(self.booking())
        app._save_booking(self.booking(customer="Rudo", service="Braids", time="12:00"))
        app._update_booking_status(2, "completed")
        summary = app._get_summary()
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["scheduled"], 1)
        self.assertEqual(summary["completed"], 1)
        self.assertEqual(summary["cancelled"], 0)
        self.assertEqual(len(app._get_upcoming("2026-12-01")), 1)
        app.db.close()

    def test_blueprint_reports_supported_and_unsupported_features(self):
        app, source = self.make_app(
            "bookings, appointment scheduling, customer details, booking history, automatic reminders"
        )
        self.assertIn('"booking_records"', source)
        self.assertIn('"appointment_scheduling"', source)
        self.assertIn('"customer_details"', source)
        self.assertIn('"booking_history"', source)
        self.assertIn("# Unsupported by selected template: automatic_reminders", source)
        coverage = validate_feature_coverage(
            source,
            ["booking_records", "appointment_scheduling", "customer_details", "booking_history"],
            template_id="booking_appointments",
        )
        self.assertTrue(coverage["complete"])
        app.db.close()


if __name__ == "__main__":
    unittest.main()
