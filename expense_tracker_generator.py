"""Independent offline Expense Tracker app generator for IDEA2APK V3."""
import json
import re

from feature_engine import (
    analyze_blueprint,
    validate_feature_coverage,
    validate_generated_source,
)

EXPENSE_FEATURES = [
    "income_records",
    "expense_records",
    "category_tracking",
    "currency_support",
    "basic_reports",
    "local_sqlite_storage",
    "transaction_history",
]

TEMPLATE = r'''import os
import math
import sqlite3
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


class GeneratedApp(App):
    def build(self):
        self.title = APP_TITLE
        self.db_path = os.path.join(self.user_data_dir, "expense_tracker.db")
        self.db = sqlite3.connect(self.db_path)
        self.create_tables()

        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        root.add_widget(Label(text=APP_TITLE, size_hint_y=None, height=dp(44), font_size=sp(23)))
        root.add_widget(Label(text=APP_DESCRIPTION, size_hint_y=None, height=dp(42), font_size=sp(12)))
        self.summary_label = Label(text="Loading summary...", size_hint_y=None, height=dp(100))
        root.add_widget(self.summary_label)

        scroll = ScrollView(do_scroll_x=False)
        menu = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
        menu.bind(minimum_height=menu.setter("height"))
        actions = [
            ("income_records", "ADD INCOME", self.add_income),
            ("expense_records", "ADD EXPENSE", self.add_expense),
            ("transaction_history", "TRANSACTION HISTORY", self.show_history),
            ("basic_reports", "INCOME / EXPENSE SUMMARY", self.show_summary),
        ]
        for feature, caption, callback in actions:
            if feature in ENABLED_FEATURES:
                button = Button(text=caption, size_hint_y=None, height=dp(52))
                button.bind(on_release=callback)
                menu.add_widget(button)
        scroll.add_widget(menu)
        root.add_widget(scroll)

        refresh = Button(text="HOME / REFRESH", size_hint_y=None, height=dp(46))
        refresh.bind(on_release=self.refresh_summary)
        root.add_widget(refresh)
        self.status = Label(text="Offline records are saved on this device.", size_hint_y=None, height=dp(30), font_size=sp(11))
        root.add_widget(self.status)
        self.refresh_summary()
        return root

    def create_tables(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL CHECK(kind IN ('income', 'expense')),
                description TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'General',
                amount REAL NOT NULL CHECK(amount > 0),
                currency TEXT NOT NULL CHECK(currency IN ('USD', 'ZIG')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(created_at)")
        self.db.commit()

    def _save_transaction(self, kind, values):
        description = str(values.get("description", "")).strip()
        category = str(values.get("category", "General")).strip() or "General"
        amount = float(values.get("amount", 0))
        currency = str(values.get("currency", "USD")).strip().upper()
        if kind not in ("income", "expense"):
            raise ValueError("Transaction type is not supported.")
        if not description:
            raise ValueError("Enter a description.")
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Amount must be a positive number.")
        if currency not in ("USD", "ZIG"):
            raise ValueError("Currency must be USD or ZiG.")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.db.execute(
                "INSERT INTO transactions(kind, description, category, amount, currency) VALUES(?,?,?,?,?)",
                (kind, description, category, amount, currency)
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return amount, currency

    def add_income(self, *_args):
        self.open_transaction_form("Record Income", self._save_income)

    def add_expense(self, *_args):
        self.open_transaction_form("Record Expense", self._save_expense)

    def _save_income(self, values):
        result = self._save_transaction('income', values)
        self.refresh_summary()
        return result

    def _save_expense(self, values):
        result = self._save_transaction('expense', values)
        self.refresh_summary()
        return result

    def _get_history(self, limit=100):
        return self.db.execute(
            "SELECT kind, description, category, amount, currency, created_at "
            "FROM transactions ORDER BY id DESC LIMIT ?",
            (int(limit),)
        ).fetchall()

    def _get_summary(self):
        result = {}
        for currency in ("USD", "ZIG"):
            income = self.db.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE kind='income' AND currency=?",
                (currency,)
            ).fetchone()[0]
            expenses = self.db.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE kind='expense' AND currency=?",
                (currency,)
            ).fetchone()[0]
            result[currency] = {
                "income": float(income),
                "expenses": float(expenses),
                "balance": float(income - expenses),
            }
        return result

    def refresh_summary(self, *_args):
        totals = self._get_summary()
        self.summary_label.text = (
            "USD  Income: {:.2f} | Expenses: {:.2f} | Balance: {:.2f}\n"
            "ZiG  Income: {:.2f} | Expenses: {:.2f} | Balance: {:.2f}"
        ).format(
            totals["USD"]["income"], totals["USD"]["expenses"], totals["USD"]["balance"],
            totals["ZIG"]["income"], totals["ZIG"]["expenses"], totals["ZIG"]["balance"]
        )

    def show_summary(self, *_args):
        totals = self._get_summary()
        message = []
        for currency in ("USD", "ZIG"):
            row = totals[currency]
            message.append(
                "{}\nIncome: {:.2f}\nExpenses: {:.2f}\nBalance: {:.2f}".format(
                    currency, row["income"], row["expenses"], row["balance"]
                )
            )
        self.popup_message("Financial Summary", "\n\n".join(message))

    def show_history(self, *_args):
        rows = self._get_history()
        if not rows:
            message = "No transactions recorded yet."
        else:
            message = "\n".join(
                "{} | {} | {} | {:.2f} {} | {}".format(*row)
                for row in rows
            )
        self.popup_message("Transaction History", message)

    def open_transaction_form(self, title, save_callback):
        body = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(7))
        fields = {}
        for key, hint in [
            ("description", "Description"),
            ("category", "Category (e.g. sales, food, transport)"),
            ("amount", "Amount"),
            ("currency", "Currency: USD or ZIG"),
        ]:
            field = TextInput(hint_text=hint, multiline=False, size_hint_y=None, height=dp(46))
            fields[key] = field
            body.add_widget(field)
        buttons = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        save = Button(text="SAVE")
        cancel = Button(text="CANCEL")
        buttons.add_widget(save)
        buttons.add_widget(cancel)
        body.add_widget(buttons)
        popup = Popup(title=title, content=body, size_hint=(0.92, 0.86))

        def submit(_button):
            values = {key: field.text.strip() for key, field in fields.items()}
            try:
                save_callback(values)
                popup.dismiss()
                self.status.text = title + " saved."
            except Exception as error:
                self.popup_message("Check your entries", str(error))

        save.bind(on_release=submit)
        cancel.bind(on_release=popup.dismiss)
        popup.open()

    def popup_message(self, title, message):
        body = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        scroll = ScrollView()
        label = Label(text=message, size_hint_y=None, halign="left", valign="top")
        label.bind(texture_size=lambda obj, size: setattr(obj, "height", size[1] + dp(18)))
        scroll.add_widget(label)
        body.add_widget(scroll)
        close = Button(text="CLOSE", size_hint_y=None, height=dp(44))
        body.add_widget(close)
        popup = Popup(title=title, content=body, size_hint=(0.92, 0.82))
        close.bind(on_release=popup.dismiss)
        popup.open()
'''


def generate_expense_tracker_code(data):
    data = data if isinstance(data, dict) else {}
    plan = analyze_blueprint(data)
    name = str(data.get("name") or "My Expense Tracker").strip() or "My Expense Tracker"
    description = str(data.get("description") or "Offline income and expense tracker").strip()
    requested = plan["requested"]
    selected = [feature for feature in EXPENSE_FEATURES if feature in requested]
    if not requested:
        selected = list(EXPENSE_FEATURES)

    generated = TEMPLATE.replace("__APP_TITLE__", repr(name))
    generated = generated.replace("__APP_DESCRIPTION__", repr(description))
    generated = generated.replace("__ENABLED_FEATURES__", repr(selected))

    coverage = validate_feature_coverage(generated, selected)
    validation = validate_generated_source(generated)
    report = [
        "",
        "# IDEA2APK V3 BLUEPRINT VERIFICATION",
        "# Template: expense_tracker",
        "# Requested: " + (", ".join(requested) or "none (template defaults)"),
        "# Selected for app UI: " + (", ".join(selected) or "none"),
        "# Actually generated and verified: " + (", ".join(coverage["implemented"]) or "none"),
        "# Missing from generated code: " + (", ".join(coverage["missing"]) or "none"),
        "# Unsupported by selected template: " + (", ".join(plan["unsupported"]) or "none"),
        "# Completion: " + ("COMPLETE" if coverage["complete"] and not plan["unsupported"] else "PARTIAL - review unsupported or missing features"),
        "# Source checks are deterministic fingerprints, not a substitute for device testing.",
        "",
    ]
    generated += "\n".join(report)
    validation = validate_generated_source(generated)
    if not validation["valid"]:
        raise ValueError("Expense Tracker generator produced invalid Python: " + "; ".join(validation["errors"]))
    return generated
