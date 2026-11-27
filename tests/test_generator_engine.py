import sqlite3
import sys
import types
import unittest

from generator_engine import generate_app_code
from feature_engine import validate_generated_source


class GeneratorEngineTests(unittest.TestCase):
    def load_generated_app_class(self, source):
        # The database tests do not need a real Android/Kivy installation.
        kivy = types.ModuleType("kivy")
        kivy.__path__ = []
        app_module = types.ModuleType("kivy.app")
        class App:
            pass
        app_module.App = App
        metrics = types.ModuleType("kivy.metrics")
        metrics.dp = lambda value: value
        metrics.sp = lambda value: value
        uix = types.ModuleType("kivy.uix")
        uix.__path__ = []
        modules = {
            "kivy": kivy,
            "kivy.app": app_module,
            "kivy.metrics": metrics,
            "kivy.uix": uix,
        }
        for name, class_name in [
            ("boxlayout", "BoxLayout"), ("button", "Button"),
            ("label", "Label"), ("textinput", "TextInput"),
            ("popup", "Popup"), ("scrollview", "ScrollView"),
        ]:
            module = types.ModuleType("kivy.uix." + name)
            setattr(module, class_name, type(class_name, (), {}))
            modules["kivy.uix." + name] = module
        previous = {key: sys.modules.get(key) for key in modules}
        sys.modules.update(modules)
        try:
            namespace = {"__name__": "generated_shop_test"}
            exec(source, namespace)
            return namespace["GeneratedApp"]
        finally:
            for key, value in previous.items():
                if value is None:
                    sys.modules.pop(key, None)
                else:
                    sys.modules[key] = value

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

    def test_legacy_database_migrates_without_losing_records(self):
        source = generate_app_code({
            "template_id": "shop_inventory",
            "name": "My Shop",
            "description": "Offline shop manager",
            "features": "products, stock, sales",
        })
        app_class = self.load_generated_app_class(source)
        app = app_class()
        app.db = sqlite3.connect(":memory:")
        app.db.executescript("""
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                price REAL NOT NULL DEFAULT 0,
                quantity INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT DEFAULT ''
            );
            CREATE TABLE sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                customer TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO products(name, price, quantity) VALUES('Sugar', 2.50, 8);
            INSERT INTO sales(product_id, quantity, unit_price, customer)
                VALUES(1, 2, 2.50, 'Walk-in');
            INSERT INTO expenses(description, amount) VALUES('Transport', 1.25);
        """)
        app.create_tables()
        product = app.db.execute(
            "SELECT name, price, selling_price, quantity, currency, cost_price "
            "FROM products WHERE id=1"
        ).fetchone()
        sale = app.db.execute(
            "SELECT quantity, unit_price, currency, unit_cost, cost_known FROM sales WHERE id=1"
        ).fetchone()
        expense = app.db.execute(
            "SELECT description, amount, currency FROM expenses WHERE id=1"
        ).fetchone()
        self.assertEqual(product, ("Sugar", 2.5, 2.5, 8, "USD", 0.0))
        self.assertEqual(sale, (2, 2.5, "USD", 0.0, 0))
        self.assertEqual(expense, ("Transport", 1.25, "USD"))
        # Re-running the migration must be safe and must not duplicate rows.
        app.create_tables()
        self.assertEqual(app.db.execute("SELECT COUNT(*) FROM products").fetchone()[0], 1)
        app.db.close()

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
