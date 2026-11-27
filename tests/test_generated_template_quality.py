"""Runtime smoke tests for generated IDEA2APK V3 app templates."""
import os
import sqlite3
import sys
import tempfile
import types
import unittest

from generator_engine import generate_app_code
from feature_engine import validate_generated_source


def install_kivy_test_stubs():
    """Install minimal Kivy modules so generated database workflows run in CI."""
    names = {
        "kivy": None,
        "kivy.app": "App",
        "kivy.metrics": None,
        "kivy.uix": None,
        "kivy.uix.boxlayout": "BoxLayout",
        "kivy.uix.button": "Button",
        "kivy.uix.label": "Label",
        "kivy.uix.textinput": "TextInput",
        "kivy.uix.popup": "Popup",
        "kivy.uix.scrollview": "ScrollView",
    }
    modules = {}
    for module_name, class_name in names.items():
        module = types.ModuleType(module_name)
        if module_name in ("kivy", "kivy.uix"):
            module.__path__ = []
        if class_name:
            setattr(module, class_name, type(class_name, (), {}))
        modules[module_name] = module
    modules["kivy.metrics"].dp = lambda value: value
    modules["kivy.metrics"].sp = lambda value: value
    previous = {key: sys.modules.get(key) for key in modules}
    sys.modules.update(modules)
    return previous


def restore_modules(previous):
    for key, value in previous.items():
        if value is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = value


class GeneratedTemplateQualityTests(unittest.TestCase):
    def load_app(self, template_id, name):
        source = generate_app_code({
            "template_id": template_id,
            "name": name,
            "description": "Offline generated app quality test",
            "features": "",
        })
        self.assertTrue(validate_generated_source(source)["valid"])
        previous = install_kivy_test_stubs()
        try:
            namespace = {"__name__": "generated_template_quality_test"}
            exec(source, namespace)
            app = namespace["GeneratedApp"]()
        finally:
            restore_modules(previous)
        app.db = sqlite3.connect(":memory:")
        app.create_tables()
        return app

    def test_expense_tracker_saves_income_and_expense_and_calculates_balances(self):
        app = self.load_app("expense_tracker", "Test Accounts")
        app.summary_label = types.SimpleNamespace(text="")
        app._save_income({"description": "Shop sales", "category": "Sales", "amount": "25", "currency": "USD"})
        app._save_expense({"description": "Transport", "category": "Travel", "amount": "5", "currency": "USD"})
        totals = app._get_summary()
        self.assertEqual(totals["USD"], {"income": 25.0, "expenses": 5.0, "balance": 20.0})
        self.assertEqual(len(app._get_history()), 2)
        with self.assertRaisesRegex(ValueError, "positive"):
            app._save_transaction("income", {"description": "Bad", "amount": "0", "currency": "USD"})
        app.db.close()

    def test_school_records_persist_student_attendance_and_marks(self):
        app = self.load_app("school_records", "Test School")
        app._save_student({"admission_no": "S001", "name": "Tariro", "class_name": "ECD A"})
        app._record_attendance("S001", "2026-11-27", "present")
        app._save_result("S001", "Mathematics", "Term 3", 87, 100)
        self.assertEqual(app._get_students("Tariro")[0][:3], ("S001", "Tariro", "ECD A"))
        self.assertEqual(app._get_attendance()[0][-1], "present")
        self.assertEqual(app._get_results("S001")[0][3:6], ("Mathematics", "Term 3", 87.0))
        with self.assertRaisesRegex(ValueError, "between zero"):
            app._save_result("S001", "Maths", "Term 3", 120, 100)
        app.db.close()

    def test_booking_manager_blocks_overlaps_and_updates_status(self):
        app = self.load_app("booking_appointments", "Test Bookings")
        booking = {
            "customer_name": "Tariro", "phone": "0771000000", "service": "Haircut",
            "booking_date": "2026-11-28", "booking_time": "10:00",
            "duration_minutes": "60", "notes": "First visit",
        }
        app._save_booking(booking)
        self.assertEqual(len(app._get_history()), 1)
        with self.assertRaisesRegex(ValueError, "overlaps"):
            app._save_booking(dict(booking, booking_time="10:30"))
        booking_id = app._get_history()[0][0]
        app._update_booking_status(booking_id, "completed")
        self.assertEqual(app._get_history()[0][7], "completed")
        app.db.close()

    def test_task_manager_saves_searches_and_completes_tasks(self):
        app = self.load_app("task_manager", "Test Tasks")
        app._save_task({
            "title": "Submit school poster", "description": "Prepare final artwork",
            "category": "Work", "priority": "high", "due_date": "2026-11-28",
        })
        tasks = app._get_tasks(search="school")
        self.assertEqual(len(tasks), 1)
        task_id = tasks[0][0]
        app._complete_task(task_id)
        self.assertEqual(app._get_tasks(status="completed")[0][6], "completed")
        with self.assertRaisesRegex(ValueError, "Pending task"):
            app._complete_task(task_id)
        app.db.close()

    def test_customer_manager_saves_profiles_and_followups(self):
        app = self.load_app("customer_manager", "Test Customers")
        app._save_customer({
            "name": "Tariro", "phone": "0771000000", "email": "tariro@example.com",
            "address": "Gweshe", "notes": "School client",
        })
        customer_id = app._get_customers("Tariro")[0][0]
        app._save_followup({
            "customer_id": str(customer_id), "followup_date": "2026-11-28",
            "note": "Confirm certificate order",
        })
        followups = app._get_followups(status="pending")
        self.assertEqual(len(followups), 1)
        self.assertEqual(followups[0][2], "Tariro")
        app._complete_followup(followups[0][0])
        self.assertEqual(app._get_followups(status="completed")[0][5], "completed")
        app.db.close()


    def test_shop_manager_saves_products_sales_customers_and_expenses(self):
        app = self.load_app("shop_inventory", "Test Shop")
        app.db.execute(
            "INSERT INTO products(name, price, quantity, cost_price, selling_price, currency, low_stock_threshold) "
            "VALUES(?,?,?,?,?,?,?)",
            ("Mealie Meal", 8.0, 10, 5.0, 8.0, "USD", 3),
        )
        app.db.commit()
        total, currency = app._save_sale({
            "product": "Mealie Meal", "quantity": "2", "customer": "Tariro"
        })
        self.assertEqual((total, currency), (16.0, "USD"))
        self.assertEqual(app.db.execute(
            "SELECT quantity FROM products WHERE name='Mealie Meal'"
        ).fetchone()[0], 8)
        self.assertEqual(len(app._get_sales_history()), 1)
        self.assertEqual(app._get_low_stock_products(), [])
        app._save_customer("Tariro", "0771000000")
        self.assertEqual(app._get_customers("Tariro")[0], ("Tariro", "0771000000"))
        app._save_expense("Transport", 2.5, "USD")
        self.assertEqual(app._get_expense_history()[0][1:], ("Transport", 2.5, "USD"))
        with self.assertRaisesRegex(ValueError, "Not enough stock"):
            app._save_sale({"product": "Mealie Meal", "quantity": "20"})
        self.assertEqual(app.db.execute(
            "SELECT quantity FROM products WHERE name='Mealie Meal'"
        ).fetchone()[0], 8)
        app.db.close()


    def test_shop_reports_keep_usd_and_zig_revenue_costs_and_expenses_separate(self):
        app = self.load_app("shop_inventory", "Currency Separation")
        app.db.executemany(
            "INSERT INTO products(name, price, quantity, cost_price, selling_price, currency) "
            "VALUES(?,?,?,?,?,?)",
            [
                ("USD Item", 10.0, 10, 6.0, 10.0, "USD"),
                ("ZiG Item", 75.0, 10, 45.0, 75.0, "ZIG"),
            ],
        )
        app.db.commit()

        usd_total, usd_currency = app._save_sale({"product": "USD Item", "quantity": "2"})
        zig_total, zig_currency = app._save_sale({"product": "ZiG Item", "quantity": "2"})
        self.assertEqual((usd_total, usd_currency), (20.0, "USD"))
        self.assertEqual((zig_total, zig_currency), (150.0, "ZIG"))

        app._save_expense("USD transport", 3.0, "USD")
        app._save_expense("ZiG supplies", 20.0, "ZIG")
        today = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
        totals = app._get_period_totals("daily", today)

        self.assertEqual(totals["USD"]["revenue"], 20.0)
        self.assertEqual(totals["USD"]["known_cost"], 12.0)
        self.assertEqual(totals["USD"]["gross_profit_known"], 8.0)
        self.assertEqual(totals["USD"]["expenses"], 3.0)
        self.assertEqual(totals["USD"]["net_result_known_costs"], 5.0)
        self.assertEqual(totals["ZIG"]["revenue"], 150.0)
        self.assertEqual(totals["ZIG"]["known_cost"], 90.0)
        self.assertEqual(totals["ZIG"]["gross_profit_known"], 60.0)
        self.assertEqual(totals["ZIG"]["expenses"], 20.0)
        self.assertEqual(totals["ZIG"]["net_result_known_costs"], 40.0)
        self.assertEqual(totals["USD"]["sale_count"], 1)
        self.assertEqual(totals["ZIG"]["sale_count"], 1)
        app.db.close()


    def test_shop_backup_restores_data_and_preserves_pre_restore_database(self):
        app = self.load_app("shop_inventory", "Backup Test")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            app.db.execute(
                "INSERT INTO products(name, price, quantity, cost_price, selling_price, currency) "
                "VALUES(?,?,?,?,?,?)",
                ("Original stock", 12.0, 7, 8.0, 12.0, "USD"),
            )
            app.db.commit()
            backup_path = app._create_backup_file()
            self.assertTrue(os.path.isfile(backup_path))

            app.db.execute("DELETE FROM products")
            app.db.execute(
                "INSERT INTO products(name, price, quantity, cost_price, selling_price, currency) "
                "VALUES(?,?,?,?,?,?)",
                ("Newer stock", 20.0, 4, 15.0, 20.0, "ZIG"),
            )
            app.db.commit()

            restored_path = app._restore_latest_backup()
            self.assertEqual(restored_path, backup_path)
            names = [row[0] for row in app.db.execute("SELECT name FROM products ORDER BY name")]
            self.assertEqual(names, ["Original stock"])

            backups = [
                name for name in os.listdir(os.path.join(backup_root, "backups"))
                if name.endswith(".db")
            ]
            self.assertGreaterEqual(len(backups), 2)
            preserved = []
            for filename in backups:
                connection = sqlite3.connect(os.path.join(backup_root, "backups", filename))
                try:
                    preserved.extend(row[0] for row in connection.execute("SELECT name FROM products"))
                finally:
                    connection.close()
            self.assertIn("Newer stock", preserved)
        app.db.close()

    def test_shop_backup_is_verified_after_creation(self):
        app = self.load_app("shop_inventory", "Verified Backup Test")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            app.db.execute(
                "INSERT INTO products(name, price, quantity, cost_price, selling_price, currency) "
                "VALUES(?,?,?,?,?,?)",
                ("Verified item", 9.0, 5, 6.0, 9.0, "USD"),
            )
            app.db.commit()
            backup_path = app._create_backup_file()
            self.assertTrue(os.path.isfile(backup_path))
            self.assertTrue(app._is_valid_backup_file(backup_path))
            backup_db = sqlite3.connect(backup_path)
            try:
                self.assertEqual(
                    backup_db.execute("PRAGMA quick_check").fetchone()[0], "ok"
                )
                self.assertEqual(
                    backup_db.execute("SELECT name FROM products").fetchone()[0],
                    "Verified item",
                )
            finally:
                backup_db.close()
        app.db.close()


    def test_shop_restore_skips_corrupted_newest_backup(self):
        app = self.load_app("shop_inventory", "Corrupt Backup Test")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            app.db.execute(
                "INSERT INTO products(name, price, quantity, cost_price, selling_price, currency) "
                "VALUES(?,?,?,?,?,?)",
                ("Safe saved stock", 15.0, 6, 9.0, 15.0, "USD"),
            )
            app.db.commit()
            valid_path = app._create_backup_file()

            corrupt_path = os.path.join(
                backup_root, "backups", "my_shop_99999999_999999_999999.db"
            )
            with open(corrupt_path, "wb") as handle:
                handle.write(b"not a sqlite database")

            restored_path = app._restore_latest_backup()
            self.assertEqual(restored_path, valid_path)
            names = [
                row[0] for row in app.db.execute("SELECT name FROM products ORDER BY name")
            ]
            self.assertEqual(names, ["Safe saved stock"])
        app.db.close()

    def test_shop_restore_rejects_when_only_backup_is_corrupted(self):
        app = self.load_app("shop_inventory", "Only Corrupt Backup")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            directory = os.path.join(backup_root, "backups")
            os.makedirs(directory)
            corrupt_path = os.path.join(directory, "my_shop_corrupt.db")
            with open(corrupt_path, "wb") as handle:
                handle.write(b"broken database")
            with self.assertRaisesRegex(ValueError, "No valid backup"):
                app._restore_latest_backup()
        app.db.close()


    def test_shop_restore_rejects_backup_missing_required_tables(self):
        app = self.load_app("shop_inventory", "Incomplete Backup")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            directory = os.path.join(backup_root, "backups")
            os.makedirs(directory)
            incomplete_path = os.path.join(directory, "my_shop_incomplete.db")
            connection = sqlite3.connect(incomplete_path)
            try:
                connection.execute(
                    "CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, quantity INTEGER, selling_price REAL, currency TEXT)"
                )
                connection.commit()
            finally:
                connection.close()
            with self.assertRaisesRegex(ValueError, "No valid backup"):
                app._restore_latest_backup()
        app.db.close()


    def test_shop_restore_without_backup_returns_clear_error(self):
        app = self.load_app("shop_inventory", "Empty Backup Test")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            with self.assertRaisesRegex(ValueError, "No backup"):
                app._restore_latest_backup()
        app.db.close()


    def test_shop_backup_manager_source_has_selectable_valid_entries_and_confirmation(self):
        source = generate_app_code({
            "template_id": "shop_inventory",
            "name": "Backup UI Check",
            "description": "Verify backup selection interface",
        })
        self.assertIn("Choose a backup to restore", source)
        self.assertIn("valid backup(s) available", source)
        self.assertIn("invalid backup(s) blocked", source)
        self.assertIn("Total backup storage:", source)
        self.assertIn("total_mb", source)
        self.assertIn('item["created_at"]', source)
        self.assertIn("confirm_restore_selected_backup", source)
        self.assertIn('disabled=not item["valid"]', source)
        self.assertIn("Current data will first be backed up.", source)

    def test_shop_cleanup_removes_only_invalid_backups_and_keeps_valid_ones(self):
        app = self.load_app("shop_inventory", "Safe Backup Cleanup")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            valid_path = app._create_backup_file()
            invalid_path = os.path.join(
                backup_root, "backups", "my_shop_corrupt_cleanup.db"
            )
            with open(invalid_path, "wb") as handle:
                handle.write(b"not a valid sqlite backup")
            removed = app._delete_invalid_backups()
            self.assertEqual(removed, 1)
            self.assertTrue(os.path.isfile(valid_path))
            self.assertFalse(os.path.exists(invalid_path))
            self.assertEqual(
                [item["filename"] for item in app._get_backup_inventory()],
                [os.path.basename(valid_path)],
            )
        app.db.close()

    def test_shop_backup_manager_offers_confirmed_invalid_backup_cleanup(self):
        source = generate_app_code({
            "template_id": "shop_inventory",
            "name": "Backup Cleanup UI",
        })
        self.assertIn("REMOVE INVALID BACKUPS", source)
        self.assertIn("confirm_clean_invalid_backups", source)
        self.assertIn("Valid backups and current shop data will be kept.", source)
        self.assertIn("def _delete_invalid_backups(self):", source)

    def test_shop_restore_selected_backup_restores_that_version_and_preserves_current(self):
        app = self.load_app("shop_inventory", "Selected Backup Restore")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            app.db.execute(
                "INSERT INTO products(name, price, quantity, cost_price, selling_price, currency) "
                "VALUES(?,?,?,?,?,?)",
                ("Older saved stock", 10.0, 5, 6.0, 10.0, "USD"),
            )
            app.db.commit()
            selected = app._create_backup_file()
            app.db.execute("DELETE FROM products")
            app.db.execute(
                "INSERT INTO products(name, price, quantity, cost_price, selling_price, currency) "
                "VALUES(?,?,?,?,?,?)",
                ("Current stock", 20.0, 8, 12.0, 20.0, "ZIG"),
            )
            app.db.commit()
            app._create_backup_file()
            restored = app._restore_backup(selected)
            self.assertEqual(restored, selected)
            self.assertEqual(
                [row[0] for row in app.db.execute("SELECT name FROM products")],
                ["Older saved stock"],
            )
            preserved = [
                row[0] for row in app.db.execute(
                    "SELECT name FROM products WHERE name='Older saved stock'"
                )
            ]
            self.assertEqual(preserved, ["Older saved stock"])
            self.assertGreaterEqual(len(app._get_backup_inventory()), 3)
        app.db.close()

    def test_shop_restore_rejects_backup_outside_local_backup_folder(self):
        app = self.load_app("shop_inventory", "Reject External Restore")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            outside = os.path.join(backup_root, "outside.db")
            connection = sqlite3.connect(outside)
            connection.close()
            with self.assertRaisesRegex(ValueError, "local backup folder"):
                app._restore_backup(outside)
        app.db.close()

    def test_shop_restore_can_recover_the_pre_restore_database(self):
        app = self.load_app("shop_inventory", "Backup Recovery Round Trip")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            app.db.execute(
                "INSERT INTO products(name, price, quantity, cost_price, selling_price, currency) "
                "VALUES(?,?,?,?,?,?)",
                ("Original stock", 10.0, 5, 6.0, 10.0, "USD"),
            )
            app.db.commit()
            original_backup = app._create_backup_file()

            app.db.execute("DELETE FROM products")
            app.db.execute(
                "INSERT INTO products(name, price, quantity, cost_price, selling_price, currency) "
                "VALUES(?,?,?,?,?,?)",
                ("Current stock", 20.0, 8, 12.0, 20.0, "ZIG"),
            )
            app.db.commit()

            restored = app._restore_latest_backup()
            self.assertEqual(restored, original_backup)
            self.assertEqual(
                [row[0] for row in app.db.execute("SELECT name FROM products")],
                ["Original stock"],
            )

            # The pre-restore database was saved automatically and can itself
            # be restored in a later recovery operation.
            recovered = app._restore_latest_backup()
            self.assertNotEqual(recovered, original_backup)
            self.assertTrue(app._is_valid_backup_file(recovered))
            self.assertEqual(
                [row[0] for row in app.db.execute("SELECT name FROM products")],
                ["Current stock"],
            )
        app.db.close()


    def test_shop_backup_verification_failure_cleans_temporary_file(self):
        app = self.load_app("shop_inventory", "Failed Backup Cleanup")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            app._is_valid_backup_file = lambda _path: False
            with self.assertRaisesRegex(
                sqlite3.DatabaseError, "Backup verification failed"
            ):
                app._create_backup_file()
            directory = os.path.join(backup_root, "backups")
            self.assertEqual(os.listdir(directory), [])
        app.db.close()

    def test_shop_backup_is_published_only_after_verification(self):
        app = self.load_app("shop_inventory", "Atomic Backup Publication")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            backup_path = app._create_backup_file()
            directory = os.path.join(backup_root, "backups")
            self.assertTrue(os.path.isfile(backup_path))
            self.assertTrue(app._is_valid_backup_file(backup_path))
            self.assertEqual(
                os.listdir(directory),
                [os.path.basename(backup_path)],
            )
            self.assertFalse(os.path.exists(backup_path + ".tmp"))
            inventory = app._get_backup_inventory()
            self.assertEqual(len(inventory), 1)
            self.assertEqual(inventory[0]["path"], backup_path)
            self.assertTrue(inventory[0]["valid"])
        app.db.close()

    def test_shop_backup_inventory_sorts_by_actual_creation_time(self):
        app = self.load_app("shop_inventory", "Backup Date Ordering")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            older_path = app._create_backup_file()
            newer_path = app._create_backup_file()
            os.utime(older_path, (1000, 1000))
            os.utime(newer_path, (2000, 2000))
            inventory = app._get_backup_inventory()
            self.assertEqual(inventory[0]["path"], newer_path)
            self.assertEqual(inventory[1]["path"], older_path)
            self.assertGreater(
                inventory[0]["created_timestamp"],
                inventory[1]["created_timestamp"],
            )
        app.db.close()

    def test_shop_backup_inventory_ignores_symlinks_and_matching_directories(self):
        app = self.load_app("shop_inventory", "Backup Inventory Entry Safety")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            valid_path = app._create_backup_file()
            directory = os.path.join(backup_root, "backups")
            matching_directory = os.path.join(directory, "my_shop_fake.db")
            os.makedirs(matching_directory)
            external_path = os.path.join(backup_root, "external.db")
            connection = sqlite3.connect(external_path)
            try:
                connection.executescript("""
                    CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, quantity INTEGER, selling_price REAL, currency TEXT);
                    CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, phone TEXT);
                    CREATE TABLE sales (id INTEGER PRIMARY KEY, product_id INTEGER, quantity INTEGER, unit_price REAL, currency TEXT);
                    CREATE TABLE expenses (id INTEGER PRIMARY KEY, description TEXT, amount REAL, currency TEXT);
                """)
                connection.commit()
            finally:
                connection.close()
            symlink_path = os.path.join(directory, "my_shop_external.db")
            try:
                os.symlink(external_path, symlink_path)
            except (OSError, NotImplementedError):
                symlink_path = None

            inventory = app._get_backup_inventory()
            self.assertEqual([item["path"] for item in inventory], [valid_path])
            self.assertTrue(os.path.isfile(external_path))
            if symlink_path:
                self.assertTrue(os.path.islink(symlink_path))
        app.db.close()

    def test_shop_backup_inventory_reports_valid_and_invalid_files(self):
        app = self.load_app("shop_inventory", "Backup Inventory")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            valid_path = app._create_backup_file()
            invalid_path = os.path.join(
                backup_root, "backups", "my_shop_99999999_999999_999999.db"
            )
            with open(invalid_path, "wb") as handle:
                handle.write(b"invalid sqlite data")

            inventory = app._get_backup_inventory()
            self.assertEqual(len(inventory), 2)
            self.assertEqual(inventory[0]["filename"], os.path.basename(invalid_path))
            self.assertFalse(inventory[0]["valid"])
            self.assertTrue(inventory[1]["valid"])
            self.assertEqual(inventory[1]["path"], valid_path)
            self.assertTrue(inventory[1]["created_at"])
            self.assertGreater(inventory[1]["size_bytes"], 0)
        app.db.close()


    def test_shop_restore_rejects_backup_symlink(self):
        app = self.load_app("shop_inventory", "Reject Backup Symlink")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            directory = os.path.join(backup_root, "backups")
            os.makedirs(directory)
            real_backup = app._create_backup_file()
            link_path = os.path.join(directory, "my_shop_link.db")
            try:
                os.symlink(real_backup, link_path)
            except (OSError, NotImplementedError):
                self.skipTest("Symbolic links are not supported in this environment.")
            with self.assertRaisesRegex(ValueError, "Symbolic-link backups"):
                app._restore_backup(link_path)
            self.assertTrue(app._is_valid_backup_file(real_backup))
        app.db.close()

    def test_shop_restore_rejects_symlinked_backup_directory(self):
        app = self.load_app("shop_inventory", "Reject Symlinked Backup Folder")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            directory = os.path.join(backup_root, "backups")
            os.makedirs(directory)
            real_backup = app._create_backup_file()
            alias = os.path.join(backup_root, "backup_alias")
            try:
                os.symlink(directory, alias)
            except (OSError, NotImplementedError):
                self.skipTest("Symbolic links are not supported in this environment.")
            aliased_path = os.path.join(alias, os.path.basename(real_backup))
            with self.assertRaisesRegex(ValueError, "Symbolic-link backups"):
                app._restore_backup(aliased_path)
            self.assertTrue(os.path.isfile(real_backup))
        app.db.close()



    def test_shop_restore_aborts_if_pre_restore_backup_fails(self):
        app = self.load_app("shop_inventory", "Restore Backup Creation Failure")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            directory = os.path.join(backup_root, "backups")
            os.makedirs(directory)
            selected_backup = app._create_backup_file()
            app.db.execute(
                "INSERT INTO products (name, quantity, selling_price, currency) VALUES (?, ?, ?, ?)",
                ("Current item", 7, 2.5, "USD"),
            )
            app.db.commit()
            original_create_backup = app._create_backup_file
            try:
                app._create_backup_file = lambda: (_ for _ in ()).throw(
                    sqlite3.DatabaseError("simulated backup storage failure")
                )
                with self.assertRaisesRegex(sqlite3.DatabaseError, "simulated backup storage failure"):
                    app._restore_backup(selected_backup)
            finally:
                app._create_backup_file = original_create_backup
            row = app.db.execute(
                "SELECT quantity FROM products WHERE name = ?", ("Current item",)
            ).fetchone()
            self.assertEqual(row[0], 7)
        app.db.close()

    def test_shop_restore_connection_remains_usable_after_restore(self):
        app = self.load_app("shop_inventory", "Restore Connection Usability")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            app.db.execute(
                "INSERT INTO products(name, price, quantity, cost_price, selling_price, currency) "
                "VALUES(?,?,?,?,?,?)",
                ("Restored stock", 10.0, 4, 6.0, 10.0, "USD"),
            )
            app.db.commit()
            selected = app._create_backup_file()
            app.db.execute("DELETE FROM products")
            app.db.commit()
            app._restore_backup(selected)
            app.db.execute(
                "INSERT INTO products(name, price, quantity, cost_price, selling_price, currency) "
                "VALUES(?,?,?,?,?,?)",
                ("Post-restore stock", 15.0, 3, 9.0, 15.0, "ZIG"),
            )
            app.db.commit()
            names = [
                row[0] for row in app.db.execute(
                    "SELECT name FROM products ORDER BY name"
                )
            ]
            self.assertEqual(names, ["Post-restore stock", "Restored stock"])
        app.db.close()

    def test_shop_restore_keeps_selected_backup_snapshot_unchanged(self):
        app = self.load_app("shop_inventory", "Restore Snapshot Integrity")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            directory = os.path.join(backup_root, "backups")
            os.makedirs(directory)
            app.db.execute(
                "INSERT INTO products (name, quantity, selling_price, currency) VALUES (?, ?, ?, ?)",
                ("Saved item", 9, 5.0, "USD"),
            )
            app.db.commit()
            selected_backup = app._create_backup_file()
            app._restore_backup(selected_backup)
            self.assertTrue(app._is_valid_backup_file(selected_backup))
            snapshot = sqlite3.connect(selected_backup)
            try:
                row = snapshot.execute(
                    "SELECT quantity FROM products WHERE name = ?", ("Saved item",)
                ).fetchone()
            finally:
                snapshot.close()
            self.assertEqual(row[0], 9)
        app.db.close()

    def test_shop_restore_does_not_commit_unrelated_pending_transaction(self):
        app = self.load_app("shop_inventory", "Restore Pending Transaction Safety")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            directory = os.path.join(backup_root, "backups")
            os.makedirs(directory)
            selected_backup = app._create_backup_file()
            app.db.execute(
                "INSERT INTO products (name, quantity, selling_price, currency) VALUES (?, ?, ?, ?)",
                ("Pending item", 4, 3.0, "USD"),
            )
            self.assertTrue(app.db.in_transaction)
            app._restore_backup(selected_backup)
            self.assertFalse(app.db.in_transaction)
            self.assertIsNone(
                app.db.execute(
                    "SELECT id FROM products WHERE name = ?", ("Pending item",)
                ).fetchone()
            )
        app.db.close()

    def test_shop_restore_reenables_foreign_key_enforcement(self):
        app = self.load_app("shop_inventory", "Restore Foreign Key Enforcement")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            directory = os.path.join(backup_root, "backups")
            os.makedirs(directory)
            selected_backup = app._create_backup_file()
            app.db.execute(
                "INSERT INTO products (name, quantity, selling_price, currency) VALUES (?, ?, ?, ?)",
                ("Temporary item", 3, 1.0, "USD"),
            )
            app.db.commit()
            app.db.execute("PRAGMA foreign_keys = ON")
            self.assertEqual(app.db.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            app._restore_backup(selected_backup)
            self.assertEqual(app.db.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertIsNone(
                app.db.execute(
                    "SELECT id FROM products WHERE name = ?", ("Temporary item",)
                ).fetchone()
            )
        app.db.close()

    def test_shop_restore_invalid_backup_does_not_create_pre_restore_backup(self):
        app = self.load_app("shop_inventory", "Invalid Backup No Side Effect")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            directory = os.path.join(backup_root, "backups")
            os.makedirs(directory)
            invalid_path = os.path.join(directory, "my_shop_invalid_restore.db")
            with open(invalid_path, "wb") as handle:
                handle.write(b"not a valid sqlite database")
            before = sorted(os.listdir(directory))
            with self.assertRaisesRegex(ValueError, "invalid or incomplete"):
                app._restore_backup(invalid_path)
            self.assertEqual(sorted(os.listdir(directory)), before)
        app.db.close()

    def test_shop_restore_rejects_empty_backup_file(self):
        app = self.load_app("shop_inventory", "Reject Empty Backup")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            directory = os.path.join(backup_root, "backups")
            os.makedirs(directory)
            empty_path = os.path.join(directory, "my_shop_empty.db")
            with open(empty_path, "wb"):
                pass
            with self.assertRaisesRegex(ValueError, "backup is empty"):
                app._restore_backup(empty_path)
            self.assertEqual(os.path.getsize(empty_path), 0)
        app.db.close()

    def test_shop_restore_rejects_unreadable_backup_file(self):
        app = self.load_app("shop_inventory", "Reject Unreadable Backup")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            directory = os.path.join(backup_root, "backups")
            os.makedirs(directory)
            backup_path = app._create_backup_file()
            original_access = os.access
            try:
                os.access = lambda path, mode: False if path == backup_path and mode == os.R_OK else original_access(path, mode)
                with self.assertRaisesRegex(ValueError, "not readable"):
                    app._restore_backup(backup_path)
            finally:
                os.access = original_access
            self.assertTrue(app._is_valid_backup_file(backup_path))
        app.db.close()

    def test_shop_restore_rejects_hard_linked_backup_entry(self):
        app = self.load_app("shop_inventory", "Reject Hard-linked Backup")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            directory = os.path.join(backup_root, "backups")
            os.makedirs(directory)
            real_backup = app._create_backup_file()
            alias_path = os.path.join(directory, "my_shop_hardlink.db")
            try:
                os.link(real_backup, alias_path)
            except (OSError, NotImplementedError):
                self.skipTest("Hard links are not supported in this environment.")
            with self.assertRaisesRegex(ValueError, "Hard-linked backup files"):
                app._restore_backup(alias_path)
            self.assertTrue(app._is_valid_backup_file(real_backup))
        app.db.close()

    def test_shop_restore_rejects_fifo_or_non_regular_backup_entry(self):
        app = self.load_app("shop_inventory", "Reject Non Regular Backup")
        with tempfile.TemporaryDirectory() as backup_root:
            app.user_data_dir = backup_root
            directory = os.path.join(backup_root, "backups")
            os.makedirs(directory)
            fifo_path = os.path.join(directory, "my_shop_fifo.db")
            if not hasattr(os, "mkfifo"):
                self.skipTest("FIFO entries are not supported in this environment.")
            try:
                os.mkfifo(fifo_path)
            except (OSError, NotImplementedError):
                self.skipTest("FIFO entries cannot be created in this environment.")
            with self.assertRaisesRegex(ValueError, "regular local file"):
                app._restore_backup(fifo_path)
        app.db.close()

if __name__ == "__main__":
    unittest.main()
