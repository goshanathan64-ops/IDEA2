import unittest

from project_schema import normalize_project, validate_project
from template_catalog import get_template, list_templates, template_support_report


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

    def test_missing_name_is_an_error(self):
        errors, _warnings = validate_project({"id": "abc", "name": " "})
        self.assertTrue(any("app name" in item.lower() for item in errors))

    def test_name_length_is_checked(self):
        errors, _warnings = validate_project({"id": "abc", "name": "x" * 41})
        self.assertTrue(errors)

    def test_only_shop_template_is_ready(self):
        ready = [item["id"] for item in list_templates() if item["status"] == "ready"]
        self.assertEqual(ready, ["shop_inventory"])
        self.assertEqual(get_template("shop_inventory")["status"], "ready")
        self.assertEqual(get_template("school_records")["status"], "planned")

    def test_support_report_does_not_claim_unknown_features(self):
        report = template_support_report(
            "shop_inventory",
            ["product_catalogue", "online_payments"]
        )
        self.assertEqual(report["supported"], ["product_catalogue"])
        self.assertEqual(report["unsupported"], ["online_payments"])


if __name__ == "__main__":
    unittest.main()
