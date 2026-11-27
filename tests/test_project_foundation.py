import unittest

from project_schema import normalize_project, validate_project
from template_catalog import blueprint_support_report, get_template, list_templates, template_planner_guide, template_support_report


class ProjectSchemaTests(unittest.TestCase):
    def test_legacy_project_is_preserved_and_upgraded(self):
        legacy = {
            "id": "abc",
            "name": "My Shop",
            "description": "A shop app",
            "target": "Owners",
            "app_type": "Business",
            "features": "Products, sales",
            "custom_note": "keep this",
        }
        upgraded = normalize_project(legacy)
        self.assertEqual(upgraded["schema_version"], 1)
        self.assertEqual(upgraded["custom_note"], "keep this")
        self.assertEqual(upgraded["id"], "abc")
        self.assertEqual(upgraded["template_id"], "shop_inventory")

    def test_template_selection_survives_project_normalization(self):
        for template_id in (
            "shop_inventory", "school_records", "expense_tracker",
            "booking_appointments", "task_manager", "customer_manager"
        ):
            project = normalize_project({
                "id": "project-" + template_id,
                "name": "Test App",
                "description": "A test app",
                "target": "Test users",
                "app_type": "Business",
                "features": "records",
                "template_id": template_id,
            })
            self.assertEqual(project["template_id"], template_id)
            errors, _warnings = validate_project(project)
            self.assertEqual(errors, [])

    def test_blank_template_defaults_to_shop_for_legacy_safety(self):
        project = normalize_project({"id": "old", "name": "Old Project", "template_id": ""})
        self.assertEqual(project["template_id"], "shop_inventory")

    def test_missing_name_is_an_error(self):
        errors, _warnings = validate_project({"id": "abc", "name": " "})
        self.assertTrue(any("app name" in item.lower() for item in errors))

    def test_name_length_is_checked(self):
        errors, _warnings = validate_project({"id": "abc", "name": "x" * 41})
        self.assertTrue(errors)

    def test_only_implemented_templates_are_ready(self):
        ready = [item["id"] for item in list_templates() if item["status"] == "ready"]
        self.assertEqual(ready, ["shop_inventory", "school_records", "expense_tracker", "booking_appointments", "task_manager", "customer_manager"])
        self.assertEqual(get_template("shop_inventory")["status"], "ready")
        self.assertEqual(get_template("expense_tracker")["status"], "ready")
        self.assertEqual(get_template("school_records")["status"], "ready")
        self.assertEqual(get_template("booking_appointments")["status"], "ready")
        self.assertEqual(get_template("task_manager")["status"], "ready")
        self.assertEqual(get_template("customer_manager")["status"], "ready")

    def test_each_ready_template_has_specific_planner_guidance(self):
        expected_terms = {
            "shop_inventory": "stock",
            "school_records": "attendance",
            "expense_tracker": "income",
            "booking_appointments": "appointment",
            "task_manager": "priority",
            "customer_manager": "follow-up",
        }
        for template_id, term in expected_terms.items():
            guide = template_planner_guide(template_id).lower()
            self.assertIn(term, guide)
        self.assertIn("Choose a ready template", template_planner_guide("future_template"))

    def test_support_report_does_not_claim_unknown_features(self):
        report = template_support_report(
            "shop_inventory",
            ["product_catalogue", "online_payments"]
        )
        self.assertEqual(report["supported"], ["product_catalogue"])
        self.assertEqual(report["unsupported"], ["online_payments"])

    def test_blueprint_support_report_is_template_specific(self):
        report = blueprint_support_report({
            "template_id": "expense_tracker",
            "features": "income, expenses, transaction history, budgets",
        })
        self.assertEqual(report["template_name"], "Expense Tracker")
        self.assertEqual(report["readiness"], "READY")
        self.assertEqual(
            report["supported"],
            ["income_records", "expense_records", "transaction_history"]
        )
        self.assertEqual(report["unsupported"], ["budgets"])

    def test_blueprint_report_marks_unknown_template_not_ready(self):
        report = blueprint_support_report({
            "template_id": "future_template",
            "features": "customer profiles, follow-ups",
        })
        self.assertEqual(report["readiness"], "NOT READY")
        self.assertEqual(report["supported"], [])
        self.assertEqual(report["unsupported"], ["customer_profiles", "follow_up_records"])


if __name__ == "__main__":
    unittest.main()
