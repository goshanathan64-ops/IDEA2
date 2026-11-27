import unittest

from feature_engine import FEATURE_SOURCE_CHECKS, analyze_blueprint, canonical_feature, prepare_blueprint_review, apply_blueprint_feature_selection, repair_generated_source, select_generated_features, split_requested_features, validate_feature_coverage, validate_generated_source


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

    def test_description_infers_features_without_overwriting_explicit_requests(self):
        plan = analyze_blueprint({
            "template_id": "shop_inventory",
            "name": "Village Shop",
            "description": "A small store for products, stock, sales and USD/ZiG reports.",
            "features": "record sales",
        })
        self.assertEqual(plan["explicit"], ["record_sales"])
        self.assertEqual(
            plan["inferred"],
            ["product_catalogue", "stock_tracking", "basic_reports", "currency_support"],
        )
        self.assertEqual(
            plan["requested"],
            ["record_sales", "product_catalogue", "stock_tracking", "basic_reports", "currency_support"],
        )
        self.assertEqual(
            [item["source"] for item in plan["feature_status"]],
            ["features", "description", "description", "description", "description"],
        )

    def test_description_inference_is_limited_to_selected_template(self):
        school = analyze_blueprint({
            "template_id": "school_records",
            "description": "Manage students, attendance, classes and exam marks.",
            "features": "",
        })
        self.assertEqual(
            school["inferred"],
            ["student_records", "class_management", "attendance_tracking", "results_records"],
        )
        unknown = analyze_blueprint({
            "template_id": "future_template",
            "description": "Manage students and attendance.",
            "features": "",
        })
        self.assertEqual(unknown["inferred"], [])
        self.assertEqual(unknown["unsupported"], [])

    def test_blueprint_review_contains_plan_and_approved_inferred_features(self):
        review = prepare_blueprint_review({
            "template_id": "shop_inventory",
            "name": "Village Shop",
            "description": "Products, stock and sales with USD/ZiG reports.",
            "target": "Tuckshop owners",
            "app_type": "Business",
            "features": "Record sales",
        })
        self.assertIn("BLUEPRINT REVIEW", review["text"])
        self.assertIn("Tuckshop owners", review["text"])
        self.assertIn("FEATURES INFERRED FROM DESCRIPTION", review["text"])
        self.assertEqual(
            review["data"]["features"],
            "record_sales, product_catalogue, stock_tracking, basic_reports, currency_support",
        )
        self.assertEqual(review["analysis"]["explicit"], ["record_sales"])

    def test_user_feature_selection_keeps_only_checked_features(self):
        original = {
            "name": "Village Shop",
            "template_id": "shop_inventory",
            "features": "products, stock, sales",
        }
        selected = apply_blueprint_feature_selection(
            original, ["stock_tracking", "custom_feature", "stock_tracking"]
        )
        self.assertEqual(
            selected["features"], "stock_tracking, custom_feature"
        )
        self.assertEqual(original["features"], "products, stock, sales")
        plan = analyze_blueprint(selected)
        self.assertEqual(plan["available"], ["stock_tracking"])
        self.assertEqual(plan["unsupported"], ["custom_feature"])

    def test_user_can_remove_all_inferred_features(self):
        selected = apply_blueprint_feature_selection(
            {"description": "Products, stock and sales", "template_id": "shop_inventory"},
            []
        )
        self.assertEqual(selected["features"], "")
        self.assertTrue(selected["feature_selection_locked"])
        plan = analyze_blueprint(selected)
        self.assertEqual(plan["explicit"], [])
        self.assertEqual(plan["inferred"], [])
        self.assertEqual(plan["requested"], [])

    def test_unticked_description_features_do_not_return_after_approval(self):
        selected = apply_blueprint_feature_selection(
            {
                "description": "Products, stock and sales",
                "features": "product catalogue, stock tracking, record sales",
                "template_id": "shop_inventory",
            },
            ["product_catalogue"],
        )
        plan = analyze_blueprint(selected)
        self.assertEqual(plan["requested"], ["product_catalogue"])
        self.assertEqual(plan["inferred"], [])
        self.assertEqual(plan["available"], ["product_catalogue"])

    def test_blueprint_review_keeps_unsupported_features_visible(self):
        review = prepare_blueprint_review({
            "template_id": "customer_manager",
            "name": "Customer Hub",
            "description": "Customer profiles and bulk SMS campaigns",
            "features": "WhatsApp automation",
        })
        self.assertIn("bulk_sms_campaigns", review["analysis"]["unsupported"])
        self.assertIn("whatsapp_automation", review["analysis"]["unsupported"])
        self.assertIn("NOT SUPPORTED YET", review["text"])

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

    def test_repair_rejects_candidate_that_drops_verified_features(self):
        original = "# CREATE TABLE IF NOT EXISTS products\ndef show_products():\n    pass"
        candidate = "# CREATE TABLE IF NOT EXISTS products"
        result = repair_generated_source(original, ["product_catalogue", "stock_tracking"], lambda: candidate)
        self.assertFalse(result["repaired"])
        self.assertEqual(result["source"], original)
        self.assertEqual(result["status"], "incomplete_features")
        self.assertTrue(any("removed verified features" in item for item in result["errors"]))

    def test_repair_reports_regeneration_exception(self):
        def broken_regenerator():
            raise RuntimeError("template unavailable")
        result = repair_generated_source("invalid source", ["product_catalogue"], broken_regenerator)
        self.assertTrue(result["attempted"])
        self.assertEqual(result["status"], "syntax_error")
        self.assertIn("template unavailable", result["diagnostics"]["repair_errors"][0])

    def test_repair_accepts_syntax_fix_without_feature_regression(self):
        result = repair_generated_source(
            "def broken(:", ["product_catalogue"],
            lambda: "# CREATE TABLE IF NOT EXISTS products\ndef show_products():\n    pass",
        )
        self.assertTrue(result["repaired"])
        self.assertEqual(result["status"], "repaired")
        self.assertEqual(result["diagnostics"]["syntax_errors"], [])

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
