import unittest

from feature_engine import FEATURE_SOURCE_CHECKS, analyze_blueprint, canonical_feature, repair_generated_source, select_generated_features, split_requested_features, validate_feature_coverage, validate_generated_source


class FeatureEngineTests(unittest.TestCase):
    def test_splits_bullets_commas_and_newlines(self):
        self.assertEqual(split_requested_features("- Products, Stock\n• Sales"), ["products", "stock", "sales"])

    def test_maps_common_shop_wording(self):
        self.assertEqual(canonical_feature("USD and ZiG support"), "currency_support")
        self.assertEqual(canonical_feature("product catalogue"), "product_catalogue")
        self.assertEqual(canonical_feature("low-stock alerts"), "low_stock_alerts")

    def test_understands_plain_language_feature_requests_for_multiple_templates(self):
        shop = analyze_blueprint({
            "template_id": "shop_inventory",
            "features": "Add products, manage stock, sell products, daily reports, USD/ZiG balances",
        })
        self.assertEqual(
            shop["available"],
            ["product_catalogue", "stock_tracking", "record_sales", "basic_reports", "currency_support"],
        )
        school = analyze_blueprint({
            "template_id": "school_records",
            "features": "admission numbers, class lists, daily attendance, subject marks",
        })
        self.assertEqual(
            school["available"],
            ["student_records", "class_management", "attendance_tracking", "results_records"],
        )
        tasks = analyze_blueprint({
            "template_id": "task_manager",
            "features": "task title, task deadline, task priority, mark as completed",
        })
        self.assertEqual(
            tasks["available"],
            ["task_records", "due_dates", "priority_levels", "completion_tracking"],
        )

    def test_blueprint_explains_each_feature_status(self):
        plan = analyze_blueprint({
            "template_id": "customer_manager",
            "features": "phone and email contacts, follow-up dates, bulk SMS",
        })
        self.assertEqual(
            [item["status"] for item in plan["feature_status"]],
            ["available", "available", "unsupported"],
        )
        self.assertIn("not currently implemented", plan["feature_status"][2]["reason"])

    def test_punctuation_variants_are_normalized(self):
        self.assertEqual(canonical_feature("  USD/ZiG balances! "), "currency_support")
        self.assertEqual(canonical_feature("Follow-up dates"), "follow_up_records")

    def test_reports_candidates_separately_from_unsupported(self):
        plan = analyze_blueprint({"template_id": "shop_inventory", "features": "Products, stock, sales, USD and ZiG support, backup/restore"})
        self.assertEqual(plan["available"], ["product_catalogue", "stock_tracking", "record_sales", "currency_support"])
        self.assertEqual(plan["unsupported"], ["backup/restore"])

    def test_unknown_template_does_not_claim_support(self):
        plan = analyze_blueprint({"template_id": "future_template", "features": "student records, attendance"})
        self.assertFalse(plan["ready"])
        self.assertEqual(plan["available"], [])
        self.assertEqual(len(plan["unsupported"]), 2)

    def test_feature_selection_adds_dependencies_and_omits_unrequested_features(self):
        selected = select_generated_features(["record_sales"])
        self.assertEqual(selected, ["product_catalogue", "stock_tracking", "record_sales"])

    def test_empty_feature_list_keeps_full_ready_template(self):
        self.assertEqual(select_generated_features([]), list(FEATURE_SOURCE_CHECKS))

    def test_coverage_requires_all_source_fingerprints(self):
        source = "CREATE TABLE IF NOT EXISTS products def show_products quantity INTEGER def _save_sale quantity=quantity-?"
        coverage = validate_feature_coverage(source, ["product_catalogue", "stock_tracking", "record_sales"])
        self.assertEqual(coverage["implemented"], ["product_catalogue", "stock_tracking"])
        self.assertEqual(coverage["missing"], ["record_sales"])
        self.assertFalse(coverage["complete"])

    def test_repair_retries_once_and_accepts_valid_regeneration(self):
        calls = []
        def regenerate():
            calls.append(True)
            return "# CREATE TABLE IF NOT EXISTS products\ndef show_products():\n    pass"
        result = repair_generated_source(
            "incomplete source", ["product_catalogue"], regenerate
        )
        self.assertTrue(result["attempted"])
        self.assertTrue(result["repaired"])
        self.assertEqual(result["attempts"], 1)
        self.assertEqual(result["unresolved"], [])
        self.assertEqual(len(calls), 1)

    def test_repair_reports_unresolved_features_without_looping(self):
        calls = []
        def regenerate():
            calls.append(True)
            return "still incomplete"
        result = repair_generated_source(
            "incomplete source", ["product_catalogue"], regenerate
        )
        self.assertTrue(result["attempted"])
        self.assertFalse(result["repaired"])
        self.assertEqual(result["unresolved"], ["product_catalogue"])
        self.assertEqual(len(calls), 1)

    def test_repair_does_not_call_regenerator_when_source_is_complete(self):
        calls = []
        source = "# CREATE TABLE IF NOT EXISTS products\ndef show_products():\n    pass"
        result = repair_generated_source(
            source, ["product_catalogue"], lambda: calls.append(True)
        )
        self.assertFalse(result["attempted"])
        self.assertEqual(calls, [])

    def test_validates_python_syntax(self):
        self.assertTrue(validate_generated_source("value = 3")["valid"])
        self.assertFalse(validate_generated_source("def broken(:")["valid"])


if __name__ == "__main__":
    unittest.main()
