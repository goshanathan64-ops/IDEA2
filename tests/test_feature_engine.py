import unittest

from feature_engine import (
    analyze_blueprint,
    canonical_feature,
    split_requested_features,
    validate_generated_source,
)


class FeatureEngineTests(unittest.TestCase):
    def test_splits_bullets_commas_and_newlines(self):
        self.assertEqual(
            split_requested_features("- Products, Stock\n• Sales"),
            ["products", "stock", "sales"],
        )

    def test_maps_common_shop_wording(self):
        self.assertEqual(canonical_feature("USD and ZiG support"), "usd_and_zig_support")
        self.assertEqual(canonical_feature("product catalogue"), "product_catalogue")
        self.assertEqual(canonical_feature("low-stock alerts"), "low_stock_alerts")

    def test_reports_supported_and_unsupported_features(self):
        plan = analyze_blueprint({
            "template_id": "shop_inventory",
            "features": "Products, stock, sales, USD and ZiG support, backup/restore",
        })
        self.assertEqual(
            plan["supported"],
            ["product_catalogue", "stock_tracking", "record_sales"],
        )
        self.assertEqual(
            plan["unsupported"],
            ["usd_and_zig_support", "backup/restore"],
        )

    def test_unknown_template_does_not_claim_support(self):
        plan = analyze_blueprint({
            "template_id": "school_records",
            "features": "student records, attendance",
        })
        self.assertFalse(plan["ready"])
        self.assertEqual(plan["supported"], [])
        self.assertEqual(len(plan["unsupported"]), 2)

    def test_validates_python_syntax(self):
        self.assertTrue(validate_generated_source("value = 3")["valid"])
        self.assertFalse(validate_generated_source("def broken(:")["valid"])


if __name__ == "__main__":
    unittest.main()
