import os
import sqlite3
import tempfile
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
        self.assertIn("IDEA2APK V3 BLUEPRINT VERIFICATION", source)
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

    def make_shop_with_product(self, quantity=10, threshold=3):
        source = generate_app_code({
            "template_id": "shop_inventory",
            "name": "My Shop",
            "description": "Offline shop manager",
            "features": "products, stock, sales",
        })
        app_class = self.load_generated_app_class(source)
        app = app_class()
        app.db = sqlite3.connect(":memory:")
        app.create_tables()
        app.db.execute(
            "INSERT INTO products(name, price, quantity, cost_price, selling_price, currency, low_stock_threshold) "
            "VALUES(?,?,?,?,?,?,?)",
            ("Sugar", 3.0, quantity, 1.5, 3.0, "USD", threshold)
        )
        app.db.commit()
        return app

    def test_sale_records_and_reduces_stock_atomically(self):
        app = self.make_shop_with_product(quantity=10)
        total, currency = app._save_sale({
            "product": "Sugar", "quantity": "4", "customer": "Walk-in"
        })
        self.assertEqual((total, currency), (12.0, "USD"))
        self.assertEqual(
            app.db.execute("SELECT quantity FROM products WHERE name='Sugar'").fetchone()[0],
            6
        )
        sale = app.db.execute(
            "SELECT quantity, unit_price, unit_cost, currency, cost_known, customer FROM sales"
        ).fetchone()
        self.assertEqual(sale, (4, 3.0, 1.5, "USD", 1, "Walk-in"))
        app.db.close()

    def test_overselling_does_not_save_sale_or_change_stock(self):
        app = self.make_shop_with_product(quantity=3)
        with self.assertRaisesRegex(ValueError, "Not enough stock"):
            app._save_sale({"product": "Sugar", "quantity": "4", "customer": ""})
        self.assertEqual(
            app.db.execute("SELECT quantity FROM products WHERE name='Sugar'").fetchone()[0],
            3
        )
        self.assertEqual(app.db.execute("SELECT COUNT(*) FROM sales").fetchone()[0], 0)
        app.db.close()

    def test_sales_history_and_low_stock_queries(self):
        app = self.make_shop_with_product(quantity=5, threshold=3)
        app._save_sale({"product": "Sugar", "quantity": "2", "customer": "Tariro"})
        history = app._get_sales_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0][1:], ("Sugar", 2, 3.0, "USD", 6.0, "Tariro"))
        low_stock = app._get_low_stock_products()
        self.assertEqual(low_stock, [("Sugar", 3, 3, "USD")])
        app.db.close()

    def test_edit_product_preserves_stock(self):
        app = self.make_shop_with_product(quantity=17)
        app._update_product({
            "name": "Sugar", "cost_price": "2.0", "selling_price": "4.5",
            "currency": "ZIG", "low_stock_threshold": "6"
        })
        row = app.db.execute(
            "SELECT quantity, cost_price, selling_price, price, currency, low_stock_threshold "
            "FROM products WHERE name='Sugar'"
        ).fetchone()
        self.assertEqual(row, (17, 2.0, 4.5, 4.5, "ZIG", 6))
        app.db.close()

    def test_product_with_sales_cannot_be_deleted(self):
        app = self.make_shop_with_product(quantity=5)
        app._save_sale({"product": "Sugar", "quantity": "1", "customer": ""})
        with self.assertRaisesRegex(ValueError, "sales history"):
            app._delete_product("Sugar")
        self.assertEqual(
            app.db.execute("SELECT COUNT(*) FROM products WHERE name='Sugar'").fetchone()[0],
            1
        )
        app.db.close()

    def test_product_without_sales_can_be_deleted(self):
        app = self.make_shop_with_product(quantity=5)
        app._delete_product("Sugar")
        self.assertEqual(app.db.execute("SELECT COUNT(*) FROM products").fetchone()[0], 0)
        app.db.close()

    def test_local_backup_restore_preserves_shop_records(self):
        app_class = self.load_generated_app_class(generate_app_code({
            "template_id": "shop_inventory",
            "name": "My Shop",
            "description": "Offline shop manager",
            "features": "products, stock, sales",
        }))
        app = app_class()
        with tempfile.TemporaryDirectory() as directory:
            app.user_data_dir = directory
            app.db = sqlite3.connect(os.path.join(directory, "my_shop.db"))
            app.create_tables()
            app.db.execute(
                "INSERT INTO products(name, price, quantity, cost_price, selling_price, currency) "
                "VALUES('Sugar', 3, 8, 1, 3, 'USD')"
            )
            app.db.commit()
            backup_path = app._create_backup_file()
            app.db.execute("UPDATE products SET quantity=1 WHERE name='Sugar'")
            app.db.commit()
            restored = app._restore_latest_backup()
            self.assertEqual(os.path.basename(restored), os.path.basename(backup_path))
            quantity = app.db.execute(
                "SELECT quantity FROM products WHERE name='Sugar'"
            ).fetchone()[0]
            self.assertEqual(quantity, 8)
            backups = [
                name for name in os.listdir(os.path.join(directory, "backups"))
                if name.endswith(".db")
            ]
            self.assertGreaterEqual(len(backups), 2)
            app.db.close()

    def test_customer_save_updates_existing_name_and_searches(self):
        app = self.make_shop_with_product()
        app._save_customer("Tariro", "0771000000")
        app._save_customer("tariro", "0772000000")
        self.assertEqual(app.db.execute("SELECT COUNT(*) FROM customers").fetchone()[0], 1)
        self.assertEqual(app._get_customers("0772"), [("Tariro", "0772000000")])
        app.db.close()

    def test_expense_validation_and_history(self):
        app = self.make_shop_with_product()
        with self.assertRaisesRegex(ValueError, "positive"):
            app._save_expense("Transport", "-2", "USD")
        with self.assertRaisesRegex(ValueError, "Currency"):
            app._save_expense("Transport", "2", "RAND")
        app._save_expense("Transport", "2.50", "USD")
        app._save_expense("Airtime", "4", "ZIG")
        history = app._get_expense_history()
        self.assertEqual(len(history), 2)
        self.assertEqual({row[3] for row in history}, {"USD", "ZIG"})
        app.db.close()

    def test_daily_and_monthly_reports_split_currencies_and_costs(self):
        app = self.make_shop_with_product()
        app.db.execute(
            "INSERT INTO sales(product_id, quantity, unit_price, unit_cost, currency, cost_known, created_at) "
            "VALUES(1, 2, 3, 1.5, 'USD', 1, '2026-11-27 10:00:00')"
        )
        app.db.execute(
            "INSERT INTO sales(product_id, quantity, unit_price, unit_cost, currency, cost_known, created_at) "
            "VALUES(1, 1, 3, 0, 'ZIG', 0, '2026-11-27 11:00:00')"
        )
        app.db.execute(
            "INSERT INTO expenses(description, amount, currency, created_at) "
            "VALUES('Transport', 1, 'USD', '2026-11-27 12:00:00')"
        )
        app.db.execute(
            "INSERT INTO expenses(description, amount, currency, created_at) "
            "VALUES('Airtime', 2, 'ZIG', '2026-11-26 12:00:00')"
        )
        app.db.commit()
        daily = app._get_period_totals("daily", "2026-11-27")
        self.assertEqual(daily["USD"]["revenue"], 6.0)
        self.assertEqual(daily["USD"]["gross_profit_known"], 3.0)
        self.assertEqual(daily["USD"]["expenses"], 1.0)
        self.assertEqual(daily["ZIG"]["revenue"], 3.0)
        self.assertEqual(daily["ZIG"]["unknown_cost_sales"], 1)
        monthly = app._get_period_totals("monthly", "2026-11")
        self.assertEqual(monthly["USD"]["revenue"], 6.0)
        self.assertEqual(monthly["ZIG"]["expenses"], 2.0)
        self.assertEqual(monthly["ZIG"]["unknown_cost_sales"], 1)
        app.db.close()


    def test_generated_shop_ui_has_grouped_scrollable_navigation_and_dashboard(self):
        source = generate_app_code({
            "template_id": "shop_inventory",
            "name": "My Shop",
            "description": "Offline shop manager",
            "features": "products, stock, sales",
        })
        self.assertIn('ScrollView(do_scroll_x=False', source)
        self.assertIn('"SALES & STOCK"', source)
        self.assertIn('"CUSTOMERS & EXPENSES"', source)
        self.assertIn('"REPORTS & DATA SAFETY"', source)
        self.assertIn('"HOME / REFRESH"', source)
        self.assertIn('self.dashboard_summary.text = summary', source)
        self.assertIn('Low-stock items:', source)

    def test_generated_menu_is_filtered_by_requested_blueprint_features(self):
        source = generate_app_code({
            "template_id": "shop_inventory",
            "name": "Sales Only",
            "description": "Simple sales tool",
            "features": "record sales",
        })
        self.assertIn('ENABLED_FEATURES = ["product_catalogue", "stock_tracking", "record_sales"]', source)
        self.assertIn('if feature_enabled(feature)', source)
        self.assertIn('# Selected for app UI (including dependencies): product_catalogue, stock_tracking, record_sales', source)
        self.assertIn('("record_sales", "Record Sale", self.record_sale)', source)
        self.assertIn('("expense_records", "Record Expense", self.add_expense)', source)

    def test_blueprint_report_separates_unsupported_from_missing_features(self):
        source = generate_app_code({
            "template_id": "shop_inventory",
            "name": "Village Shop",
            "description": "A simple shop",
            "target": "Tuckshop owners",
            "features": "products, stock, bulk SMS",
        })
        self.assertIn("# App: Village Shop", source)
        self.assertIn("# Target users: Tuckshop owners", source)
        self.assertIn("# Unsupported by selected template: bulk_sms", source)
        self.assertIn("# Missing supported features: none", source)
        self.assertIn("# Completion: PARTIAL", source)

    def test_approved_blueprint_cannot_generate_with_no_selected_features(self):
        with self.assertRaisesRegex(ValueError, "Select at least one feature"):
            generate_app_code({
                "template_id": "shop_inventory",
                "name": "Empty Plan",
                "description": "Products and stock",
                "features": "",
                "feature_selection_locked": True,
            })

    def test_generated_menu_uses_all_features_when_blueprint_is_empty(self):
        source = generate_app_code({
            "template_id": "shop_inventory",
            "name": "Default Shop",
            "description": "Shop app",
            "features": "",
        })
        self.assertIn('"profit_loss_reports"', source)
        self.assertIn('"local_sqlite_storage"', source)

    def test_unready_template_is_not_misrepresented_as_shop_app(self):
        with self.assertRaisesRegex(ValueError, "not ready to generate"):
            generate_app_code({
                "template_id": "future_template",
                "name": "School App",
                "description": "School records",
                "features": "student records, attendance",
            })


if __name__ == "__main__":
    unittest.main()
