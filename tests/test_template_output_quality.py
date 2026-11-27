"""Structural quality gates for every ready IDEA2APK V3 app generator.

These checks complement syntax validation and feature fingerprints by verifying
that the selected generator emits the correct app identity, database tables,
business operations, and UI callback wiring.
"""
import ast
import re
import unittest

from generator_engine import generate_app_code
from feature_engine import validate_generated_source


TEMPLATE_CASES = {
    "shop_inventory": {
        "tables": {"products", "customers", "sales", "expenses"},
        "methods": {"add_product", "record_sale", "show_sales_history", "show_low_stock", "add_customer", "add_expense", "show_reports", "create_backup"},
        "ui_methods": {"add_product", "record_sale", "add_customer", "add_expense"},
        "forbidden_tables": {"students", "attendance", "results", "bookings", "tasks", "followups", "transactions"},
    },
    "school_records": {
        "tables": {"students", "attendance", "results"},
        "methods": {"_save_student", "_record_attendance", "_save_result", "show_students", "show_attendance", "show_results", "show_school_summary"},
        "ui_methods": {"add_student", "record_attendance", "record_result"},
        "forbidden_tables": {"products", "sales", "expenses", "bookings", "tasks", "followups", "transactions"},
    },
    "expense_tracker": {
        "tables": {"transactions"},
        "methods": {"_save_transaction", "_get_history", "_get_summary", "add_income", "add_expense", "show_history", "show_summary"},
        "ui_methods": {"add_income", "add_expense", "show_history", "show_summary"},
        "forbidden_tables": {"products", "sales", "students", "attendance", "results", "bookings", "tasks", "followups"},
    },
    "booking_appointments": {
        "tables": {"bookings"},
        "methods": {"_save_booking", "_get_history", "_get_upcoming", "_update_booking_status", "new_booking", "show_history", "show_upcoming", "update_status"},
        "ui_methods": {"new_booking", "show_history", "show_upcoming", "update_status"},
        "forbidden_tables": {"products", "sales", "students", "attendance", "results", "tasks", "followups", "transactions"},
    },
    "task_manager": {
        "tables": {"tasks"},
        "methods": {"_save_task", "_get_tasks", "_complete_task", "_get_due_tasks", "add_task", "show_tasks", "complete_task", "show_due_tasks"},
        "ui_methods": {"add_task", "show_tasks", "complete_task", "show_due_tasks"},
        "forbidden_tables": {"products", "sales", "students", "attendance", "results", "bookings", "followups", "transactions"},
    },
    "customer_manager": {
        "tables": {"customers", "followups"},
        "methods": {"_save_customer", "_get_customers", "_save_followup", "_get_followups", "_complete_followup", "add_customer", "search_customers", "add_followup", "show_followups"},
        "ui_methods": {"add_customer", "search_customers", "add_followup", "show_followups"},
        "forbidden_tables": {"products", "sales", "students", "attendance", "results", "bookings", "tasks", "transactions"},
    },
}


def inspect_generated_app(source):
    """Return AST-backed structure and SQL table names from generated source."""
    tree = ast.parse(source)
    app_class = next(
        (node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "GeneratedApp"),
        None,
    )
    if app_class is None:
        raise AssertionError("Generated source has no GeneratedApp class.")

    methods = {
        node.name: node for node in app_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assignments = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments[target.id] = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assignments[node.target.id] = node.value

    tables = set(re.findall(
        r"CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+([A-Za-z_][A-Za-z0-9_]*)",
        source,
        flags=re.IGNORECASE,
    ))
    build = methods.get("build")
    ui_methods = set()
    if build is not None:
        for node in ast.walk(build):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
                ui_methods.add(node.attr)
    return {
        "methods": set(methods),
        "tables": tables,
        "ui_methods": ui_methods,
        "title": ast.literal_eval(assignments["APP_TITLE"]) if "APP_TITLE" in assignments else None,
        "description": ast.literal_eval(assignments["APP_DESCRIPTION"]) if "APP_DESCRIPTION" in assignments else None,
    }


class TemplateOutputQualityTests(unittest.TestCase):
    def test_every_ready_template_generates_its_own_complete_app_structure(self):
        for template_id, expected in TEMPLATE_CASES.items():
            with self.subTest(template=template_id):
                data = {
                    "template_id": template_id,
                    "name": "Quality Gate Demo",
                    "description": "Generated for structural testing",
                    "features": "",
                }
                source = generate_app_code(data)
                self.assertTrue(validate_generated_source(source)["valid"])
                details = inspect_generated_app(source)

                self.assertEqual(details["title"], data["name"])
                self.assertEqual(details["description"], data["description"])
                self.assertIn("build", details["methods"])
                self.assertIn("create_tables", details["methods"])
                self.assertTrue(expected["methods"].issubset(details["methods"]))
                self.assertTrue(expected["ui_methods"].issubset(details["ui_methods"]))
                self.assertEqual(details["tables"], expected["tables"])
                self.assertTrue(expected["forbidden_tables"].isdisjoint(details["tables"]))

    def test_unknown_template_never_falls_back_to_an_unrelated_app(self):
        with self.assertRaisesRegex(ValueError, "not ready to generate"):
            generate_app_code({
                "template_id": "not_a_real_template",
                "name": "Wrong App",
                "description": "Must not become a shop app",
                "features": "records",
            })

    def test_different_templates_produce_distinct_source_and_database_designs(self):
        generated = {
            template_id: generate_app_code({
                "template_id": template_id,
                "name": "Distinct App",
                "description": "Template isolation test",
                "features": "",
            })
            for template_id in TEMPLATE_CASES
        }
        for left_id, left_source in generated.items():
            for right_id, right_source in generated.items():
                if left_id != right_id:
                    self.assertNotEqual(left_source, right_source)
                    self.assertNotEqual(
                        inspect_generated_app(left_source)["tables"],
                        inspect_generated_app(right_source)["tables"],
                    )


if __name__ == "__main__":
    unittest.main()
