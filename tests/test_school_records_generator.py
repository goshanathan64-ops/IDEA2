import sqlite3
import sys
import types
import unittest

from generator_engine import generate_app_code
from feature_engine import validate_feature_coverage, validate_generated_source


class SchoolRecordsGeneratorTests(unittest.TestCase):
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
            namespace = {"__name__": "generated_school_records_test"}
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
            "template_id": "school_records",
            "name": "NexGen School Manager",
            "description": "Offline school administration",
            "features": features,
        })
        app = self.load_app_class(source)()
        app.summary_label = types.SimpleNamespace(text="")
        app.db = sqlite3.connect(":memory:")
        app.create_tables()
        return app, source

    def test_generates_independent_valid_school_app(self):
        app, source = self.make_app()
        self.assertTrue(validate_generated_source(source)["valid"])
        self.assertIn("school_records.db", source)
        self.assertIn("CREATE TABLE IF NOT EXISTS students", source)
        self.assertIn("CREATE TABLE IF NOT EXISTS attendance", source)
        self.assertIn("CREATE TABLE IF NOT EXISTS results", source)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS products", source)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS transactions", source)
        self.assertIn("# Template: school_records", source)
        app.db.close()

    def test_student_save_updates_existing_admission_number(self):
        app, _ = self.make_app()
        app._save_student({
            "admission_no": "N001", "name": "Tariro Moyo", "class_name": "ECD A",
            "guardian_name": "Parent One", "guardian_phone": "0771000000",
        })
        app._save_student({
            "admission_no": "N001", "name": "Tariro Moyo", "class_name": "ECD B",
            "guardian_name": "Parent Two", "guardian_phone": "0772000000",
        })
        self.assertEqual(app.db.execute("SELECT COUNT(*) FROM students").fetchone()[0], 1)
        self.assertEqual(app._get_students("ECD B")[0][2:], ("ECD B", "Parent Two", "0772000000"))
        app.db.close()

    def test_attendance_is_validated_and_upserted_by_day(self):
        app, _ = self.make_app()
        app._save_student({"admission_no": "N002", "name": "Kuda", "class_name": "Grade 1"})
        app._record_attendance("N002", "2026-11-27", "present")
        app._record_attendance("N002", "2026-11-27", "late")
        self.assertEqual(app.db.execute("SELECT COUNT(*) FROM attendance").fetchone()[0], 1)
        self.assertEqual(app._get_attendance()[0][-1], "late")
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            app._record_attendance("N002", "27/11/2026", "present")
        with self.assertRaisesRegex(ValueError, "Status"):
            app._record_attendance("N002", "2026-11-28", "excused")
        app.db.close()

    def test_results_validate_marks_and_school_summary(self):
        app, _ = self.make_app()
        app._save_student({"admission_no": "N003", "name": "Rudo", "class_name": "Grade 2"})
        app._save_result("N003", "Mathematics", "Term 1", "80", "100")
        app._save_result("N003", "English", "Term 1", "40", "50")
        self.assertEqual(len(app._get_results("N003")), 2)
        summary = app._get_school_summary()
        self.assertEqual(summary["students"], 1)
        self.assertEqual(summary["classes"], 1)
        self.assertEqual(summary["results_count"], 2)
        self.assertAlmostEqual(summary["average_percentage"], 80.0)
        with self.assertRaisesRegex(ValueError, "between zero"):
            app._save_result("N003", "Science", "Term 1", "110", "100")
        app.db.close()

    def test_blueprint_reports_supported_and_unsupported_school_features(self):
        app, source = self.make_app("students, classes, attendance, exam results, timetable generation")
        self.assertIn('"student_records"', source)
        self.assertIn("class_management", source)
        self.assertIn('"attendance_tracking"', source)
        self.assertIn('"results_records"', source)
        self.assertIn("# Unsupported by selected template: timetable_generation", source)
        coverage = validate_feature_coverage(
            source,
            ["student_records", "class_management", "attendance_tracking", "results_records"],
            template_id="school_records",
        )
        self.assertTrue(coverage["complete"])
        app.db.close()


if __name__ == "__main__":
    unittest.main()
