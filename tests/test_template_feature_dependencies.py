"""Tests for dependency expansion across independent generated app templates."""
import ast
import unittest

from feature_engine import expand_template_features
from generator_engine import generate_app_code


class TemplateFeatureDependencyTests(unittest.TestCase):
    def test_expense_categories_include_transaction_workflows(self):
        self.assertEqual(
            expand_template_features("expense_tracker", ["category_tracking"], [
                "income_records", "expense_records", "category_tracking",
                "currency_support", "basic_reports", "local_sqlite_storage",
                "transaction_history",
            ]),
            ["income_records", "expense_records", "category_tracking"],
        )

    def test_school_attendance_and_results_include_student_records(self):
        available = [
            "student_records", "class_management", "attendance_tracking",
            "results_records", "basic_reports", "local_sqlite_storage",
        ]
        self.assertEqual(
            expand_template_features("school_records", ["attendance_tracking", "results_records"], available),
            ["student_records", "attendance_tracking", "results_records"],
        )

    def test_booking_views_and_status_include_booking_creation(self):
        available = [
            "booking_records", "appointment_scheduling", "customer_details",
            "booking_status", "booking_history", "basic_reports", "local_sqlite_storage",
        ]
        self.assertEqual(
            expand_template_features("booking_appointments", ["appointment_scheduling"], available),
            ["booking_records", "appointment_scheduling"],
        )

    def test_task_tools_include_task_creation(self):
        available = [
            "task_records", "due_dates", "priority_levels", "completion_tracking",
            "task_categories", "task_search", "basic_reports", "local_sqlite_storage",
        ]
        self.assertEqual(
            expand_template_features("task_manager", ["due_dates", "task_search"], available),
            ["task_records", "due_dates", "task_search"],
        )

    def test_customer_followups_include_customer_profiles(self):
        available = [
            "customer_profiles", "contact_details", "customer_notes", "follow_up_records",
            "follow_up_tracking", "customer_search", "basic_reports", "local_sqlite_storage",
        ]
        self.assertEqual(
            expand_template_features("customer_manager", ["follow_up_records"], available),
            ["customer_profiles", "follow_up_records"],
        )

    def test_empty_selection_keeps_full_template_and_unknowns_are_ignored(self):
        available = ["task_records", "due_dates", "local_sqlite_storage"]
        self.assertEqual(expand_template_features("task_manager", [], available), available)
        self.assertEqual(
            expand_template_features("task_manager", ["unknown", "due_dates"], available),
            ["task_records", "due_dates"],
        )

    def test_each_generator_includes_required_workflow_dependencies(self):
        cases = [
            ("expense_tracker", "category_tracking", {"income_records", "expense_records", "category_tracking"}),
            ("school_records", "attendance_tracking", {"student_records", "attendance_tracking"}),
            ("booking_appointments", "appointment_scheduling", {"booking_records", "appointment_scheduling"}),
            ("task_manager", "due_dates", {"task_records", "due_dates"}),
            ("customer_manager", "follow_up_records", {"customer_profiles", "follow_up_records"}),
        ]
        for template_id, feature, expected in cases:
            with self.subTest(template=template_id):
                source = generate_app_code({
                    "template_id": template_id,
                    "name": "Dependency Test",
                    "description": "Verify required parent workflows",
                    "features": feature,
                })
                module = ast.parse(source)
                enabled = next(
                    ast.literal_eval(node.value)
                    for node in module.body
                    if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == "ENABLED_FEATURES" for target in node.targets)
                )
                self.assertTrue(expected.issubset(set(enabled)), (template_id, enabled))


if __name__ == "__main__":
    unittest.main()
