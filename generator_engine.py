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
                quantity INTEGER NOT NULL DEFAULT 0
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
                FOREIGN KEY(product_id) REFERENCES products(id)
            );
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.db.commit()

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
        popup = Popup(title=title, content=body, size_hint=(0.92, 0.65))
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
            price = float(values["price"])
            quantity = int(values["quantity"])
            if not name or price < 0 or quantity < 0:
                raise ValueError("Enter a product name and valid non-negative price and quantity.")
            self.db.execute(
                "INSERT INTO products(name, price, quantity) VALUES(?,?,?) "
                "ON CONFLICT(name) DO UPDATE SET price=excluded.price, quantity=excluded.quantity",
                (name, price, quantity)
            )
            self.db.commit()
            self.show_products()
        self.open_form("Add / Update Product", [
            ("name", "Product name"),
            ("price", "Selling price"),
            ("quantity", "Opening stock quantity")
        ], save)

    def show_products(self, *_args):
        rows = self.db.execute("SELECT name, price, quantity FROM products ORDER BY name").fetchall()
        if not rows:
            text = "No products yet. Use Add Product to create your first item."
        else:
            text = "PRODUCT                 PRICE       STOCK\n"
            text += "\n".join("{}                 {:.2f}       {}".format(*row) for row in rows)
        self.popup_message("Products and Inventory", text)

    def record_sale(self, *_args):
        def save(values):
            product_name = values["product"].strip()
            quantity = int(values["quantity"])
            customer = values["customer"].strip()
            if not product_name or quantity <= 0:
                raise ValueError("Enter a product name and a quantity greater than zero.")
            row = self.db.execute(
                "SELECT id, price, quantity FROM products WHERE name=? COLLATE NOCASE",
                (product_name,)
            ).fetchone()
            if row is None:
                raise ValueError("Product not found. Add it first using Add Product.")
            product_id, price, stock = row
            if quantity > stock:
                raise ValueError("Not enough stock. Available quantity: {}".format(stock))
            self.db.execute(
                "INSERT INTO sales(product_id, quantity, unit_price, customer) VALUES(?,?,?,?)",
                (product_id, quantity, price, customer)
            )
            self.db.execute(
                "UPDATE products SET quantity=quantity-? WHERE id=?",
                (quantity, product_id)
            )
            self.db.commit()
            self.status.text = "Sale saved. Total: {:.2f}".format(price * quantity)
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
            if not description or amount <= 0:
                raise ValueError("Enter an expense description and amount greater than zero.")
            self.db.execute(
                "INSERT INTO expenses(description, amount) VALUES(?,?)",
                (description, amount)
            )
            self.db.commit()
        self.open_form("Record Expense", [
            ("description", "Expense description"),
            ("amount", "Amount")
        ], save)

    def show_reports(self, *_args):
        sales = self.db.execute(
            "SELECT COALESCE(SUM(quantity * unit_price), 0), COUNT(*) FROM sales"
        ).fetchone()
        expenses = self.db.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses").fetchone()[0]
        stock = self.db.execute("SELECT COALESCE(SUM(quantity), 0) FROM products").fetchone()[0]
        products = self.db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        customers = self.db.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        revenue = sales[0]
        report = (
            "BUSINESS REPORT\n\n"
            "Products: {}\n"
            "Units currently in stock: {}\n"
            "Customers: {}\n"
            "Sales transactions: {}\n"
            "Total sales revenue: {:.2f}\n"
            "Total expenses: {:.2f}\n"
            "Revenue minus expenses: {:.2f}\n\n"
            "Note: This is a basic cash summary, not a full accounting profit calculation."
        ).format(products, stock, customers, sales[1], revenue, expenses, revenue - expenses)
        self.popup_message("Business Reports", report)

    def show_dashboard(self, *_args):
        products = self.db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        stock = self.db.execute("SELECT COALESCE(SUM(quantity),0) FROM products").fetchone()[0]
        sales = self.db.execute("SELECT COALESCE(SUM(quantity * unit_price),0) FROM sales").fetchone()[0]
        self.status.text = "Products: {} | Stock units: {} | Sales: {:.2f}".format(products, stock, sales)

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
