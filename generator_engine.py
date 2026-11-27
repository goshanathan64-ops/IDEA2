"""IDEA2APK Generator Engine V2.

Generates a functional SQLite-backed shop-management starter app.
The generated app uses Kivy and Python's standard-library sqlite3 module.
"""
import json
import re

from feature_engine import analyze_blueprint, validate_generated_source


def generate_app_code(data):
    template_id = str(data.get("template_id") or "shop_inventory")
    if template_id != "shop_inventory":
        raise ValueError("The selected template is not ready to generate apps yet: " + template_id)

    name = (data.get("name") or "My Shop").strip()
    description = (data.get("description") or "Shop management application").strip()
    safe_title = re.sub(r"[^A-Za-z0-9 _-]", "", name) or "My Shop"

    template = r'''import os
import sqlite3

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


class GeneratedApp(App):
    def build(self):
        self.title = APP_TITLE
        self.db_path = os.path.join(self.user_data_dir, "my_shop.db")
        self.db = sqlite3.connect(self.db_path)
        self.db.execute("PRAGMA foreign_keys = ON")
        self.create_tables()

        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        root.add_widget(Label(text=APP_TITLE, font_size=sp(24), size_hint_y=None, height=dp(48)))
        root.add_widget(Label(text=APP_DESCRIPTION, font_size=sp(13), size_hint_y=None, height=dp(48)))

        actions = [
            ("Dashboard", self.show_dashboard),
            ("Products / Inventory", self.show_products),
            ("Add Product", self.add_product),
            ("Record Sale", self.record_sale),
            ("Customers", self.add_customer),
            ("Expenses", self.add_expense),
            ("Reports", self.show_reports),
        ]
        for caption, callback in actions:
            button = Button(text=caption, size_hint_y=None, height=dp(46))
            button.bind(on_release=callback)
            root.add_widget(button)

        self.status = Label(text="Ready. Your records are stored on this device.", font_size=sp(12))
        root.add_widget(self.status)
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

    def record_sale(self, *_args):
        def save(values):
            product_name = values["product"].strip()
            quantity = int(values["quantity"])
            customer = values["customer"].strip()
            if not product_name or quantity <= 0:
                raise ValueError("Enter a product name and a quantity greater than zero.")
            row = self.db.execute(
                "SELECT id, selling_price, quantity, cost_price, currency FROM products WHERE name=? COLLATE NOCASE",
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
            self.db.execute(
                "UPDATE products SET quantity=quantity-? WHERE id=?",
                (quantity, product_id)
            )
            self.db.commit()
            self.status.text = "Sale saved. Total: {:.2f} {}".format(price * quantity, currency)
        self.open_form("Record Sale", [
            ("product", "Exact product name"),
            ("quantity", "Quantity sold"),
            ("customer", "Customer name (optional)")
        ], save)

    def add_customer(self, *_args):
        def save(values):
            if not values["name"]:
                raise ValueError("Customer name is required.")
            self.db.execute(
                "INSERT INTO customers(name, phone) VALUES(?,?)",
                (values["name"], values["phone"])
            )
            self.db.commit()
            rows = self.db.execute("SELECT name, phone FROM customers ORDER BY id DESC").fetchall()
            self.popup_message("Customers", "\n".join("{}  {}".format(*row) for row in rows))
        self.open_form("Add Customer", [
            ("name", "Customer name"),
            ("phone", "Phone number (optional)")
        ], save)

    def add_expense(self, *_args):
        def save(values):
            description = values["description"]
            amount = float(values["amount"])
            currency = values["currency"].upper()
            if currency not in ("USD", "ZIG"):
                raise ValueError("Currency must be USD or ZiG.")
            if not description or amount <= 0:
                raise ValueError("Enter an expense description and amount greater than zero.")
            self.db.execute(
                "INSERT INTO expenses(description, amount, currency) VALUES(?,?,?)",
                (description, amount, currency)
            )
            self.db.commit()
        self.open_form("Record Expense", [
            ("description", "Expense description"),
            ("amount", "Amount"),
            ("currency", "Currency: USD or ZIG")
        ], save)

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
        self.popup_message("Business Reports", "\n".join(lines))

    def show_dashboard(self, *_args):
        products = self.db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        stock = self.db.execute("SELECT COALESCE(SUM(quantity),0) FROM products").fetchone()[0]
        usd_sales = self.db.execute("SELECT COALESCE(SUM(quantity * unit_price),0) FROM sales WHERE currency='USD'").fetchone()[0]
        zig_sales = self.db.execute("SELECT COALESCE(SUM(quantity * unit_price),0) FROM sales WHERE currency='ZIG'").fetchone()[0]
        low_stock = self.db.execute("SELECT COUNT(*) FROM products WHERE quantity <= low_stock_threshold").fetchone()[0]
        self.status.text = "Products: {} | Stock: {} | Low stock: {} | USD sales: {:.2f} | ZiG sales: {:.2f}".format(products, stock, low_stock, usd_sales, zig_sales)

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
    )

    # Keep the analysis visible in exported source so users can see which
    # requested features the current offline template does not yet implement.
    plan = analyze_blueprint(data)
    report = [
        "",
        "# IDEA2APK V3 BLUEPRINT ANALYSIS",
        "# Supported by this template: " + (
            ", ".join(plan["supported"]) or "none"
        ),
        "# Not yet generated: " + (
            ", ".join(plan["unsupported"]) or "none"
        ),
        "# This report is informational; unsupported features are not implemented.",
        "",
    ]
    generated += "\n".join(report)
    validation = validate_generated_source(generated)
    if not validation["valid"]:
        raise ValueError("; ".join(validation["errors"]))
    return generated
