import unittest

from generator_engine import generate_app_code
from feature_engine import validate_generated_source


class GeneratorEngineTests(unittest.TestCase):
    def test_shop_template_generates_valid_python(self):
        source = generate_app_code({
            "template_id": "shop_inventory",
            "name": "My Shop",
            "description": "Offline shop manager",
            "features": "products, stock, sales",
        })
        self.assertTrue(validate_generated_source(source)["valid"])
        self.assertIn("IDEA2APK V3 BLUEPRINT ANALYSIS", source)
        self.assertIn("product_catalogue", source)
        self.assertIn("cost_price", source)
        self.assertIn("selling_price", source)
        self.assertIn("low_stock_threshold", source)
        self.assertIn("PRAGMA user_version = 2", source)
        self.assertIn("ALTER TABLE", source)
        self.assertIn("currency='USD'", source)
        self.assertIn("currency='ZIG'", source)
        self.assertIn("unit_cost", source)
        self.assertIn("cost_known", source)
        self.assertIn("Sales with unknown historical cost", source)

    def test_unready_template_is_not_misrepresented_as_shop_app(self):
        with self.assertRaisesRegex(ValueError, "not ready to generate"):
            generate_app_code({
                "template_id": "school_records",
                "name": "School App",
                "description": "School records",
                "features": "student records, attendance",
            })


if __name__ == "__main__":
    unittest.main()
