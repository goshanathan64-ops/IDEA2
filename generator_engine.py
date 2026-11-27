"""IDEA2APK Generator Engine V2.

Generates a functional SQLite-backed shop-management starter app.
The generated app uses Kivy and Python's standard-library sqlite3 module.
"""
import json
import os
import re
import sqlite3
from datetime import datetime

from feature_engine import analyze_blueprint, repair_generated_source, select_generated_features, validate_feature_coverage, validate_generated_source


def generate_app_code(data):
    data = data if isinstance(data, dict) else {}
    template_id = str(data.get("template_id") or "shop_inventory")
    if template_id == "expense_tracker":
        from expense_tracker_generator import generate_expense_tracker_code
        return generate_expense_tracker_code(data)
    if template_id != "shop_inventory":
        raise ValueError("The selected template is not ready to generate apps yet: " + template_id)

    name = (data.get("name") or "My Shop").strip()
    description = (data.get("description") or "Shop management application").strip()
    safe_title = re.sub(r"[^A-Za-z0-9 _-]", "", name) or "My Shop"

    template = r'''import os
import sqlite3
import math
from datetime import datetime

from kivy.app import App
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView


APP_TITLE = __APP_TITLE__
APP_DESCRIPTION = __APP_DESCRIPTION__
ENABLED_FEATURES = __ENABLED_FEATURES__


def feature_enabled(feature):
    return feature in ENABLED_FEATURES


class GeneratedApp(App):
    def build(self):
        self.title = APP_TITLE
        self.db_path = os.path.join(self.user_data_dir, "my_shop.db")
        self.db = sqlite3.connect(self.db_path)
        self.db.execute("PRAGMA foreign_keys = ON")
        self.create_tables()

        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(6))
        header = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(76), spacing=dp(2))
        header.add_widget(Label(text=APP_TITLE, font_size=sp(23), size_hint_y=None, height=dp(42)))
        header.add_widget(Label(text=APP_DESCRIPTION, font_size=sp(12), size_hint_y=None, height=dp(30)))
        root.add_widget(header)

        self.dashboard_summary = Label(
            text="Loading business summary...",
            size_hint_y=None, height=dp(104), font_size=sp(13),
            halign="left", valign="middle"
        )
        self.dashboard_summary.bind(size=lambda obj, size: setattr(obj, "text_size", size))
        root.add_widget(self.dashboard_summary)

        menu = ScrollView(do_scroll_x=False, bar_width=dp(4))
        menu_content = BoxLayout(
            orientation="vertical", size_hint_y=None, spacing=dp(7), padding=(0, dp(4))
        )
        menu_content.bind(minimum_height=menu_content.setter("height"))

        sections = [
            ("SALES & STOCK", [
                ("product_catalogue", "Products / Inventory", self.show_products),
                ("product_catalogue", "Add Product", self.add_product),
                ("product_catalogue", "Edit Product", self.edit_product),
                ("product_catalogue", "Delete Product", self.delete_product),
                ("record_sales", "Record Sale", self.record_sale),
                ("record_sales", "Sales History", self.show_sales_history),
                ("stock_tracking", "Low Stock Alerts", self.show_low_stock),
            ]),
            ("CUSTOMERS & EXPENSES", [
                ("customer_records", "Add / Update Customer", self.add_customer),
                ("customer_records", "Customer List / Search", self.show_customers),
                ("expense_records", "Record Expense", self.add_expense),
                ("expense_records", "Expense History", self.show_expense_history),
            ]),
            ("REPORTS & DATA SAFETY", [
                ("basic_reports", "Business Reports", self.show_reports),
                ("basic_reports", "Today's Report", self.show_daily_report),
                ("basic_reports", "This Month's Report", self.show_monthly_report),
                ("local_sqlite_storage", "Create Backup", self.create_backup),
                ("local_sqlite_storage", "Restore Latest Backup", self.confirm_restore_backup),
            ]),
        ]
        for section_title, actions in sections:
            visible_actions = [
                (caption, callback) for feature, caption, callback in actions
                if feature_enabled(feature)
            ]
            if not visible_actions:
                continue
            heading = Label(
                text=section_title, size_hint_y=None, height=dp(30),
                font_size=sp(13), bold=True
            )
            menu_content.add_widget(heading)
            for caption, callback in visible_actions:
                button = Button(text=caption, size_hint_y=None, height=dp(48))
                button.bind(on_release=callback)
                menu_content.add_widget(button)
        menu.add_widget(menu_content)
        root.add_widget(menu)

        footer = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        home_button = Button(text="HOME / REFRESH")
        home_button.bind(on_release=self.show_dashboard)
        footer.add_widget(home_button)
        self.status = Label(
            text="Ready. Records are saved on this device.",
            font_size=sp(11), size_hint_x=1.4
        )
        footer.add_widget(self.status)
        root.add_widget(footer)

        self.root_layout = root
        self.show_dashboard()
        return root

    def create_tables(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                price REAL NOT NULL DEFAULT 0,
                quantity INTEGER NOT NULL DEFAULT 0,
                cost_price REAL NOT NULL DEFAULT 0,
                selling_price REAL NOT NULL DEFAULT 0,
                currency TEXT NOT NULL DEFAULT 'USD',
                low_stock_threshold INTEGER NOT NULL DEFAULT 5
            );
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                customer TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                unit_cost REAL NOT NULL DEFAULT 0,
                currency TEXT NOT NULL DEFAULT 'USD',
                cost_known INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(product_id) REFERENCES products(id)
            );
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                currency TEXT NOT NULL DEFAULT 'USD'
            );
        """)
        # Add columns in place so older shop databases keep their records.
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self._ensure_column("products", "cost_price", "REAL NOT NULL DEFAULT 0")
            self._ensure_column("products", "selling_price", "REAL NOT NULL DEFAULT 0")
            self._ensure_column("products", "currency", "TEXT NOT NULL DEFAULT 'USD'")
            self._ensure_column("products", "low_stock_threshold", "INTEGER NOT NULL DEFAULT 5")
            self._ensure_column("sales", "unit_cost", "REAL NOT NULL DEFAULT 0")
            self._ensure_column("sales", "currency", "TEXT NOT NULL DEFAULT 'USD'")
            self._ensure_column("sales", "cost_known", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column("expenses", "currency", "TEXT NOT NULL DEFAULT 'USD'")
            self.db.execute("UPDATE products SET selling_price=price WHERE selling_price=0 AND price<>0")
            self.db.execute("UPDATE products SET price=selling_price")
            self.db.execute("UPDATE products SET currency='USD' WHERE currency IS NULL OR TRIM(currency)=''")
            self.db.execute("UPDATE sales SET currency='USD' WHERE currency IS NULL OR TRIM(currency)=''")
            self.db.execute("UPDATE expenses SET currency='USD' WHERE currency IS NULL OR TRIM(currency)=''")
            self.db.execute("PRAGMA user_version = 2")
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _ensure_column(self, table, column, definition):
        columns = {row[1] for row in self.db.execute("PRAGMA table_info({})".format(table)).fetchall()}
        if column not in columns:
            self.db.execute("ALTER TABLE {} ADD COLUMN {} {}".format(table, column, definition))

    def popup_message(self, title, message):
        body = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        scroll = ScrollView()
        label = Label(text=message, size_hint_y=None, halign="left", valign="top")
        label.bind(texture_size=lambda obj, size: setattr(obj, "height", size[1] + dp(20)))
        scroll.add_widget(label)
        body.add_widget(scroll)
        close = Button(text="CLOSE", size_hint_y=None, height=dp(44))
        body.add_widget(close)
        popup = Popup(title=title, content=body, size_hint=(0.92, 0.82))
        close.bind(on_release=popup.dismiss)
        popup.open()

    def open_form(self, title, field_specs, save_callback):
        body = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        inputs = {}
        for key, hint in field_specs:
            field = TextInput(hint_text=hint, multiline=False, size_hint_y=None, height=dp(46))
            inputs[key] = field
            body.add_widget(field)
        buttons = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        save = Button(text="SAVE")
        cancel = Button(text="CANCEL")
        buttons.add_widget(save)
        buttons.add_widget(cancel)
        body.add_widget(buttons)
        popup = Popup(title=title, content=body, size_hint=(0.92, 0.88))
        def do_save(_button):
            values = {key: field.text.strip() for key, field in inputs.items()}
            try:
                save_callback(values)
                popup.dismiss()
                self.status.text = title + " saved."
            except Exception as error:
                self.popup_message("Check your entries", str(error))
        save.bind(on_release=do_save)
        cancel.bind(on_release=popup.dismiss)
        popup.open()

    def add_product(self, *_args):
        def save(values):
            name = values["name"]
            cost_price = float(values["cost_price"])
            selling_price = float(values["selling_price"])
            quantity = int(values["quantity"])
            low_stock_threshold = int(values["low_stock_threshold"])
            currency = values["currency"].upper()
            if currency not in ("USD", "ZIG"):
                raise ValueError("Currency must be USD or ZiG.")
            if not name or min(cost_price, selling_price, quantity, low_stock_threshold) < 0:
                raise ValueError("Enter valid non-negative prices, stock and alert level.")
            self.db.execute(
                "INSERT INTO products(name, price, quantity, cost_price, selling_price, currency, low_stock_threshold) "
                "VALUES(?,?,?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET "
                "price=excluded.price, quantity=excluded.quantity, cost_price=excluded.cost_price, "
                "selling_price=excluded.selling_price, currency=excluded.currency, "
                "low_stock_threshold=excluded.low_stock_threshold",
                (name, selling_price, quantity, cost_price, selling_price, currency, low_stock_threshold)
            )
            self.db.commit()
            self.show_products()
        self.open_form("Add / Update Product", [
            ("name", "Product name"),
            ("cost_price", "Cost price"),
            ("selling_price", "Selling price"),
            ("currency", "Currency: USD or ZIG"),
            ("quantity", "Opening stock quantity"),
            ("low_stock_threshold", "Low-stock alert quantity (e.g. 5)")
        ], save)

    def _update_product(self, values):
        name = values["name"].strip()
        cost_price = float(values["cost_price"])
        selling_price = float(values["selling_price"])
        currency = values["currency"].strip().upper()
        threshold = int(values["low_stock_threshold"])
        if not name or min(cost_price, selling_price, threshold) < 0:
            raise ValueError("Enter a product name and non-negative prices and alert level.")
        if currency not in ("USD", "ZIG"):
            raise ValueError("Currency must be USD or ZiG.")
        cursor = self.db.execute(
            "UPDATE products SET cost_price=?, selling_price=?, price=?, currency=?, "
            "low_stock_threshold=? WHERE name=? COLLATE NOCASE",
            (cost_price, selling_price, selling_price, currency, threshold, name)
        )
        if cursor.rowcount != 1:
            raise ValueError("Product not found. Check the exact product name.")
        self.db.commit()

    def edit_product(self, *_args):
        def save(values):
            self._update_product(values)
            self.show_products()
        self.open_form("Edit Product (stock is preserved)", [
            ("name", "Exact existing product name"),
            ("cost_price", "New cost price"),
            ("selling_price", "New selling price"),
            ("currency", "Currency: USD or ZIG"),
            ("low_stock_threshold", "Low-stock alert quantity")
        ], save)

    def _delete_product(self, name):
        name = name.strip()
        if not name:
            raise ValueError("Enter a product name.")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute(
                "SELECT id FROM products WHERE name=? COLLATE NOCASE", (name,)
            ).fetchone()
            if row is None:
                raise ValueError("Product not found.")
            sale_count = self.db.execute(
                "SELECT COUNT(*) FROM sales WHERE product_id=?", (row[0],)
            ).fetchone()[0]
            if sale_count:
                raise ValueError(
                    "This product has sales history and cannot be deleted. "
                    "Keep the record and set its stock to zero instead."
                )
            self.db.execute("DELETE FROM products WHERE id=?", (row[0],))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def delete_product(self, *_args):
        def save(values):
            self._delete_product(values["name"])
            self.show_products()
        self.open_form("Delete Product (no sales history)", [
            ("name", "Exact product name to delete")
        ], save)

    def _backup_directory(self):
        directory = os.path.join(self.user_data_dir, "backups")
        os.makedirs(directory, exist_ok=True)
        return directory

    def _create_backup_file(self):
        self.db.commit()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = os.path.join(self._backup_directory(), "my_shop_{}.db".format(stamp))
        destination = sqlite3.connect(path)
        try:
            self.db.backup(destination)
        finally:
            destination.close()
        return path

    def create_backup(self, *_args):
        path = self._create_backup_file()
        self.status.text = "Backup saved inside the app's private storage."
        self.popup_message(
            "Backup created",
            "Your shop database has been backed up safely on this device.\\n\\n"
            "Backup filename: " + os.path.basename(path) + "\\n"
            "For protection if the phone is lost, copy backups outside the app when an export option is added."
        )

    def _restore_latest_backup(self):
        directory = self._backup_directory()
        backups = [
            os.path.join(directory, filename)
            for filename in os.listdir(directory)
            if filename.startswith("my_shop_") and filename.endswith(".db")
        ]
        if not backups:
            raise ValueError("No backup is available on this device.")
        latest = max(backups, key=os.path.getmtime)
        # Preserve the current database before replacing it.
        self._create_backup_file()
        source = sqlite3.connect(latest)
        try:
            source.backup(self.db)
            self.db.execute("PRAGMA foreign_keys = ON")
            self.db.commit()
        finally:
            source.close()
        return latest

    def confirm_restore_backup(self, *_args):
        body = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        body.add_widget(Label(
            text="Restore the newest local backup? Current data will first be backed up.",
            halign="center"
        ))
        buttons = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        confirm = Button(text="RESTORE")
        cancel = Button(text="CANCEL")
        buttons.add_widget(confirm)
        buttons.add_widget(cancel)
        body.add_widget(buttons)
        popup = Popup(title="Confirm database restore", content=body, size_hint=(0.9, 0.42))
        def do_restore(_button):
            try:
                restored = self._restore_latest_backup()
                popup.dismiss()
                self.status.text = "Restored latest local backup."
                self.popup_message("Restore complete", "Restored from: " + os.path.basename(restored))
                self.show_dashboard()
            except Exception as error:
                self.popup_message("Restore failed", str(error))
        confirm.bind(on_release=do_restore)
        cancel.bind(on_release=popup.dismiss)
        popup.open()

    def show_products(self, *_args):
        rows = self.db.execute(
            "SELECT name, cost_price, selling_price, currency, quantity, low_stock_threshold "
            "FROM products ORDER BY name"
        ).fetchall()
        if not rows:
            text = "No products yet. Use Add Product to create your first item."
        else:
            text = "PRODUCT | COST | SELL | CURRENCY | STOCK | ALERT\n"
            text += "\n".join(
                "{} | {:.2f} | {:.2f} | {} | {} | {}".format(*row)
                for row in rows
            )
        self.popup_message("Products and Inventory", text)

    def _save_sale(self, values):
        product_name = values["product"].strip()
        quantity = int(values["quantity"])
        customer = values.get("customer", "").strip()
        if not product_name or quantity <= 0:
            raise ValueError("Enter a product name and a quantity greater than zero.")

        # The sale and stock deduction are one atomic database operation.
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute(
                "SELECT id, selling_price, quantity, cost_price, currency "
                "FROM products WHERE name=? COLLATE NOCASE",
                (product_name,)
            ).fetchone()
            if row is None:
                raise ValueError("Product not found. Add it first using Add Product.")
            product_id, price, stock, cost_price, currency = row
            if quantity > stock:
                raise ValueError("Not enough stock. Available quantity: {}".format(stock))

            self.db.execute(
                "INSERT INTO sales(product_id, quantity, unit_price, customer, unit_cost, currency, cost_known) "
                "VALUES(?,?,?,?,?,?,1)",
                (product_id, quantity, price, customer, cost_price, currency)
            )
            updated = self.db.execute(
                "UPDATE products SET quantity=quantity-? WHERE id=? AND quantity>=?",
                (quantity, product_id, quantity)
            )
            if updated.rowcount != 1:
                raise ValueError("Stock changed during the sale. Please try again.")
            self.db.commit()
            return price * quantity, currency
        except Exception:
            self.db.rollback()
            raise

    def record_sale(self, *_args):
        def save(values):
            total, currency = self._save_sale(values)
            self.status.text = "Sale saved. Total: {:.2f} {}".format(total, currency)
            self.show_dashboard()
        self.open_form("Record Sale", [
            ("product", "Exact product name"),
            ("quantity", "Quantity sold"),
            ("customer", "Customer name (optional)")
        ], save)

    def _get_sales_history(self, limit=100):
        return self.db.execute(
            "SELECT sales.created_at, products.name, sales.quantity, sales.unit_price, "
            "sales.currency, sales.quantity * sales.unit_price, sales.customer "
            "FROM sales JOIN products ON products.id=sales.product_id "
            "ORDER BY sales.id DESC LIMIT ?",
            (int(limit),)
        ).fetchall()

    def show_sales_history(self, *_args):
        rows = self._get_sales_history()
        if not rows:
            message = "No sales recorded yet."
        else:
            message = "DATE | PRODUCT | QTY | UNIT PRICE | CURRENCY | TOTAL | CUSTOMER\n"
            message += "\n".join(
                "{} | {} | {} | {:.2f} | {} | {:.2f} | {}".format(*row)
                for row in rows
            )
        self.popup_message("Sales History", message)

    def _get_low_stock_products(self):
        return self.db.execute(
            "SELECT name, quantity, low_stock_threshold, currency "
            "FROM products WHERE quantity <= low_stock_threshold ORDER BY quantity, name"
        ).fetchall()

    def show_low_stock(self, *_args):
        rows = self._get_low_stock_products()
        if not rows:
            message = "No products need restocking."
        else:
            message = "PRODUCT | LEFT IN STOCK | ALERT LEVEL | CURRENCY\n"
            message += "\n".join(
                "{} | {} | {} | {}".format(*row)
                for row in rows
            )
        self.popup_message("Low-stock products", message)

    def _save_customer(self, name, phone=""):
        name = str(name or "").strip()
        phone = str(phone or "").strip()
        if not name:
            raise ValueError("Customer name is required.")
        existing = self.db.execute(
            "SELECT id FROM customers WHERE name=? COLLATE NOCASE ORDER BY id LIMIT 1",
            (name,)
        ).fetchone()
        if existing:
            self.db.execute("UPDATE customers SET phone=? WHERE id=?", (phone, existing[0]))
        else:
            self.db.execute("INSERT INTO customers(name, phone) VALUES(?,?)", (name, phone))
        self.db.commit()

    def _get_customers(self, search=""):
        search = str(search or "").strip()
        if search:
            pattern = "%" + search + "%"
            return self.db.execute(
                "SELECT name, phone FROM customers WHERE name LIKE ? OR phone LIKE ? ORDER BY name",
                (pattern, pattern)
            ).fetchall()
        return self.db.execute("SELECT name, phone FROM customers ORDER BY name").fetchall()

    def add_customer(self, *_args):
        def save(values):
            self._save_customer(values["name"], values.get("phone", ""))
            self.popup_message("Customer saved", "Customer details saved. Open Customer List / Search to view records.")
        self.open_form("Add / Update Customer", [
            ("name", "Customer name"),
            ("phone", "Phone number (optional)")
        ], save)

    def show_customers(self, *_args):
        rows = self._get_customers()
        if not rows:
            message = "No customers saved yet."
        else:
            message = "CUSTOMER | PHONE\n" + "\n".join(
                "{} | {}".format(*row) for row in rows
            )
        self.popup_message("Customer List", message)

    def _save_expense(self, description, amount, currency):
        description = str(description or "").strip()
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            raise ValueError("Enter a valid expense amount.")
        currency = str(currency or "").strip().upper()
        if currency not in ("USD", "ZIG"):
            raise ValueError("Currency must be USD or ZiG.")
        if not description or not math.isfinite(amount) or amount <= 0:
            raise ValueError("Enter an expense description and a positive, valid amount.")
        self.db.execute(
            "INSERT INTO expenses(description, amount, currency) VALUES(?,?,?)",
            (description, amount, currency)
        )
        self.db.commit()

    def _get_expense_history(self, limit=100):
        return self.db.execute(
            "SELECT created_at, description, amount, currency FROM expenses "
            "ORDER BY id DESC LIMIT ?",
            (int(limit),)
        ).fetchall()

    def add_expense(self, *_args):
        def save(values):
            self._save_expense(values["description"], values["amount"], values["currency"])
            self.status.text = "Expense saved."
            self.show_expense_history()
        self.open_form("Record Expense", [
            ("description", "Expense description / category"),
            ("amount", "Amount"),
            ("currency", "Currency: USD or ZIG")
        ], save)

    def show_expense_history(self, *_args):
        rows = self._get_expense_history()
        if not rows:
            message = "No expenses recorded yet."
        else:
            message = "DATE | DESCRIPTION | AMOUNT | CURRENCY\n"
            message += "\n".join(
                "{} | {} | {:.2f} | {}".format(*row) for row in rows
            )
        self.popup_message("Expense History", message)

    def _get_period_totals(self, period, period_value):
        if period == "daily":
            expression = "substr(created_at, 1, 10)"
            expected_length = 10
        elif period == "monthly":
            expression = "substr(created_at, 1, 7)"
            expected_length = 7
        else:
            raise ValueError("Period must be daily or monthly.")
        period_value = str(period_value or "").strip()
        if len(period_value) != expected_length:
            raise ValueError("Invalid report date.")
        totals = {}
        for currency in ("USD", "ZIG"):
            sales = self.db.execute(
                "SELECT COALESCE(SUM(quantity * unit_price),0), "
                "COALESCE(SUM(CASE WHEN cost_known=1 THEN quantity * unit_price ELSE 0 END),0), "
                "COALESCE(SUM(CASE WHEN cost_known=1 THEN quantity * unit_cost ELSE 0 END),0), "
                "COALESCE(SUM(CASE WHEN cost_known=0 THEN 1 ELSE 0 END),0), COUNT(*) "
                "FROM sales WHERE currency=? AND " + expression + "=?",
                (currency, period_value)
            ).fetchone()
            expenses = self.db.execute(
                "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE currency=? AND "
                + expression + "=?",
                (currency, period_value)
            ).fetchone()[0]
            revenue, known_revenue, known_cost, unknown_cost_sales, sale_count = sales
            totals[currency] = {
                "revenue": revenue,
                "known_revenue": known_revenue,
                "known_cost": known_cost,
                "gross_profit_known": known_revenue - known_cost,
                "expenses": expenses,
                "net_result_known_costs": known_revenue - known_cost - expenses,
                "unknown_cost_sales": unknown_cost_sales,
                "sale_count": sale_count,
            }
        return totals

    def _show_period_report(self, period, period_value, title):
        totals = self._get_period_totals(period, period_value)
        lines = [title, period_value, ""]
        for currency in ("USD", "ZIG"):
            item = totals[currency]
            lines.extend([
                currency,
                "Sales transactions: {}".format(item["sale_count"]),
                "Sales revenue: {:.2f}".format(item["revenue"]),
                "Revenue with known costs: {:.2f}".format(item["known_revenue"]),
                "Known cost of goods sold: {:.2f}".format(item["known_cost"]),
                "Gross profit on known-cost sales: {:.2f}".format(item["gross_profit_known"]),
                "Expenses: {:.2f}".format(item["expenses"]),
                "Net result on known costs: {:.2f}".format(item["net_result_known_costs"]),
                "Sales with unknown historical cost: {}".format(item["unknown_cost_sales"]),
                ""
            ])
        lines.append("Historical sales without recorded costs are excluded from profit calculations.")
        self.popup_message(title, "\n".join(lines))

    def show_daily_report(self, *_args):
        self._show_period_report("daily", datetime.now().strftime("%Y-%m-%d"), "DAILY REPORT")

    def show_monthly_report(self, *_args):
        self._show_period_report("monthly", datetime.now().strftime("%Y-%m"), "MONTHLY REPORT")

    def show_reports(self, *_args):
        products = self.db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        stock = self.db.execute("SELECT COALESCE(SUM(quantity),0) FROM products").fetchone()[0]
        customers = self.db.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        lines = ["BUSINESS REPORT", "", "Products: {}".format(products),
                 "Units currently in stock: {}".format(stock),
                 "Customers: {}".format(customers), ""]
        for currency in ("USD", "ZIG"):
            sales = self.db.execute(
                "SELECT COALESCE(SUM(quantity * unit_price),0), "
                "COALESCE(SUM(CASE WHEN cost_known=1 THEN quantity * unit_price ELSE 0 END),0), "
                "COALESCE(SUM(CASE WHEN cost_known=1 THEN quantity * unit_cost ELSE 0 END),0), "
                "COALESCE(SUM(CASE WHEN cost_known=0 THEN 1 ELSE 0 END),0), COUNT(*) "
                "FROM sales WHERE currency=?", (currency,)
            ).fetchone()
            expenses = self.db.execute(
                "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE currency=?", (currency,)
            ).fetchone()[0]
            revenue, known_revenue, known_cost, unknown_cost_sales, sale_count = sales
            gross_profit = known_revenue - known_cost
            net_profit = gross_profit - expenses
            lines.extend([
                "{} SUMMARY".format(currency),
                "Sales transactions: {}".format(sale_count),
                "Sales revenue: {:.2f}".format(revenue),
                "Revenue from sales with known costs: {:.2f}".format(known_revenue),
                "Known cost of goods sold: {:.2f}".format(known_cost),
                "Gross profit on sales with known costs: {:.2f}".format(gross_profit),
                "Expenses: {:.2f}".format(expenses),
                "Net result on recorded costs: {:.2f}".format(net_profit),
                "Sales with unknown historical cost: {}".format(unknown_cost_sales), ""
            ])
        lines.append(
            "IMPORTANT: Old sales have unknown costs. Their profit is incomplete; "
            "do not treat the figures as final accounting profit."
        )
        lines.append("Daily and monthly reports are available from the home menu.")
        self.popup_message("Business Reports", "\n".join(lines))

    def show_dashboard(self, *_args):
        products = self.db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        stock = self.db.execute("SELECT COALESCE(SUM(quantity),0) FROM products").fetchone()[0]
        usd_sales = self.db.execute("SELECT COALESCE(SUM(quantity * unit_price),0) FROM sales WHERE currency='USD'").fetchone()[0]
        zig_sales = self.db.execute("SELECT COALESCE(SUM(quantity * unit_price),0) FROM sales WHERE currency='ZIG'").fetchone()[0]
        low_stock = self.db.execute("SELECT COUNT(*) FROM products WHERE quantity <= low_stock_threshold").fetchone()[0]
        customers = self.db.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        summary = (
            "BUSINESS OVERVIEW\\n"
            "Products: {}     Units in stock: {}\\n"
            "Low-stock items: {}     Customers: {}\\n"
            "Sales recorded: USD {:.2f}  |  ZiG {:.2f}"
        ).format(products, stock, low_stock, customers, usd_sales, zig_sales)
        self.dashboard_summary.text = summary
        self.status.text = "Dashboard updated. Your records remain on this device."

    def on_stop(self):
        if getattr(self, "db", None):
            self.db.close()


if __name__ == "__main__":
    GeneratedApp().run()
'''
    generated = (
        template
        .replace("__APP_TITLE__", json.dumps(safe_title))
        .replace("__APP_DESCRIPTION__", json.dumps(description))
        .replace("__ENABLED_FEATURES__", json.dumps(select_generated_features(analyze_blueprint(data)["requested"])))
    )

    # Retry generation once if supported features are missing or source is invalid.
    plan = analyze_blueprint(data)
    selected_features = select_generated_features(plan["requested"])
    repair = repair_generated_source(
        generated,
        selected_features,
        regenerate_callback=lambda: (
            template
            .replace("__APP_TITLE__", json.dumps(safe_title))
            .replace("__APP_DESCRIPTION__", json.dumps(description))
            .replace("__ENABLED_FEATURES__", json.dumps(selected_features))
        ),
    )
    generated = repair["source"]
    coverage = validate_feature_coverage(generated, plan["requested"])
    validation = validate_generated_source(generated)
    if not validation["valid"]:
        raise ValueError("; ".join(validation["errors"]))

    report = [
        "",
        "# IDEA2APK V3 BLUEPRINT VERIFICATION",
        "# Requested: " + (", ".join(plan["requested"]) or "none"),
        "# Selected for app UI: " + (", ".join(selected_features) or "none"),
        "# Actually generated and verified: " + (", ".join(coverage["implemented"]) or "none"),
        "# Missing from generated code: " + (", ".join(coverage["missing"]) or "none"),
        "# Unsupported by selected template: " + (", ".join(plan["unsupported"]) or "none"),
        "# Automatic repair attempted: " + ("YES" if repair["attempted"] else "NO"),
        "# Automatic repair changed source: " + ("YES" if repair["repaired"] else "NO"),
        "# Repair attempts: " + str(repair["attempts"]),
        "# Unresolved supported features: " + (", ".join(repair["unresolved"]) or "none"),
        "# Completion: " + ("COMPLETE" if coverage["complete"] else "PARTIAL - review missing features"),
        "# Source checks are deterministic fingerprints, not a substitute for device testing.",
        "# App menu actions are filtered to the selected features; shared database code remains in the template.",
        "",
    ]
    generated += "\n".join(report)
    return generated
