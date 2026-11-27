"""Independent offline Customer Manager app generator for IDEA2APK V3."""
from feature_engine import analyze_blueprint, validate_feature_coverage, validate_generated_source

CUSTOMER_FEATURES = [
    "customer_profiles", "contact_details", "customer_notes", "follow_up_records",
    "follow_up_tracking", "customer_search", "basic_reports", "local_sqlite_storage",
]

TEMPLATE = r'''import os
import sqlite3
from datetime import datetime, date

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
        self.db_path = os.path.join(self.user_data_dir, "customers.db")
        self.db = sqlite3.connect(self.db_path)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.create_tables()
        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(7))
        root.add_widget(Label(text=APP_TITLE, size_hint_y=None, height=dp(44), font_size=sp(22)))
        root.add_widget(Label(text=APP_DESCRIPTION, size_hint_y=None, height=dp(38), font_size=sp(12)))
        self.summary_label = Label(text="", size_hint_y=None, height=dp(82), halign="left")
        root.add_widget(self.summary_label)
        scroll = ScrollView(do_scroll_x=False)
        menu = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(7))
        menu.bind(minimum_height=menu.setter("height"))
        actions = [
            ("customer_profiles", "ADD / UPDATE CUSTOMER", self.add_customer),
            ("customer_search", "CUSTOMER LIST / SEARCH", self.search_customers),
            ("follow_up_records", "ADD FOLLOW-UP", self.add_followup),
            ("follow_up_tracking", "FOLLOW-UP HISTORY / DUE", self.show_followups),
            ("basic_reports", "CUSTOMER SUMMARY", self.show_summary),
        ]
        for feature, caption, callback in actions:
            if feature in ENABLED_FEATURES:
                button = Button(text=caption, size_hint_y=None, height=dp(48))
                button.bind(on_release=callback)
                menu.add_widget(button)
        scroll.add_widget(menu)
        root.add_widget(scroll)
        refresh = Button(text="HOME / REFRESH", size_hint_y=None, height=dp(44))
        refresh.bind(on_release=self.refresh_dashboard)
        root.add_widget(refresh)
        self.status = Label(text="Customer records are stored offline on this device.", size_hint_y=None, height=dp(30), font_size=sp(11))
        root.add_widget(self.status)
        self.refresh_dashboard()
        return root

    def create_tables(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT DEFAULT '',
                email TEXT DEFAULT '',
                address TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS followups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                followup_date TEXT NOT NULL,
                note TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending','completed')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT DEFAULT '',
                FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
            )
        """)
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_followups_date ON followups(followup_date)")
        self.db.commit()

    def _save_customer(self, values):
        name = str(values.get("name", "")).strip()
        phone = str(values.get("phone", "")).strip()
        email = str(values.get("email", "")).strip()
        address = str(values.get("address", "")).strip()
        notes = str(values.get("notes", "")).strip()
        customer_id = str(values.get("customer_id", "")).strip()
        if not name:
            raise ValueError("Customer name is required.")
        if email and ("@" not in email or "." not in email.split("@")[-1]):
            raise ValueError("Enter a valid email address.")
        if customer_id:
            try:
                identifier = int(customer_id)
            except ValueError:
                raise ValueError("Customer ID must be a number.")
            cursor = self.db.execute(
                "UPDATE customers SET name=?,phone=?,email=?,address=?,notes=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (name, phone, email, address, notes, identifier)
            )
            if cursor.rowcount != 1:
                self.db.rollback()
                raise ValueError("Customer ID was not found.")
        else:
            self.db.execute(
                "INSERT INTO customers(name,phone,email,address,notes) VALUES(?,?,?,?,?)",
                (name, phone, email, address, notes)
            )
        self.db.commit()

    def _get_customers(self, search="", limit=300):
        query = (
            "SELECT id,name,phone,email,address,notes,created_at FROM customers "
            "WHERE 1=1"
        )
        params = []
        if search:
            pattern = "%" + str(search).strip() + "%"
            query += " AND (name LIKE ? OR phone LIKE ? OR email LIKE ? OR address LIKE ? OR notes LIKE ?)"
            params.extend([pattern] * 5)
        query += " ORDER BY name COLLATE NOCASE,id DESC LIMIT ?"
        params.append(int(limit))
        return self.db.execute(query, params).fetchall()

    def _save_followup(self, values):
        try:
            customer_id = int(values.get("customer_id", ""))
        except (TypeError, ValueError):
            raise ValueError("Enter a valid customer ID.")
        followup_date = str(values.get("followup_date", "")).strip()
        note = str(values.get("note", "")).strip()
        if not followup_date:
            raise ValueError("Follow-up date is required.")
        try:
            datetime.strptime(followup_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Follow-up date must use YYYY-MM-DD.")
        if not note:
            raise ValueError("Follow-up note is required.")
        customer = self.db.execute("SELECT id FROM customers WHERE id=?", (customer_id,)).fetchone()
        if not customer:
            raise ValueError("Customer ID was not found.")
        self.db.execute(
            "INSERT INTO followups(customer_id,followup_date,note) VALUES(?,?,?)",
            (customer_id, followup_date, note)
        )
        self.db.commit()

    def _get_followups(self, status="all", through_date=None, limit=300):
        query = (
            "SELECT f.id,f.customer_id,c.name,f.followup_date,f.note,f.status "
            "FROM followups f JOIN customers c ON c.id=f.customer_id WHERE 1=1"
        )
        params = []
        if status in ("pending", "completed"):
            query += " AND f.status=?"
            params.append(status)
        if through_date:
            query += " AND f.followup_date<=?"
            params.append(through_date)
        query += " ORDER BY f.followup_date,f.id LIMIT ?"
        params.append(int(limit))
        return self.db.execute(query, params).fetchall()

    def _complete_followup(self, followup_id):
        try:
            identifier = int(followup_id)
        except (TypeError, ValueError):
            raise ValueError("Enter a valid follow-up ID.")
        cursor = self.db.execute(
            "UPDATE followups SET status='completed',completed_at=CURRENT_TIMESTAMP "
            "WHERE id=? AND status='pending'", (identifier,)
        )
        if cursor.rowcount != 1:
            self.db.rollback()
            raise ValueError("Pending follow-up ID was not found.")
        self.db.commit()

    def _get_summary(self):
        customers = self.db.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        with_phone = self.db.execute("SELECT COUNT(*) FROM customers WHERE phone!=''").fetchone()[0]
        pending = self.db.execute("SELECT COUNT(*) FROM followups WHERE status='pending'").fetchone()[0]
        completed = self.db.execute("SELECT COUNT(*) FROM followups WHERE status='completed'").fetchone()[0]
        due = self.db.execute(
            "SELECT COUNT(*) FROM followups WHERE status='pending' AND followup_date<=?",
            (date.today().isoformat(),)
        ).fetchone()[0]
        return {"customers": customers, "with_phone": with_phone, "pending": pending,
                "completed": completed, "due": due}

    def refresh_dashboard(self, *_args):
        summary = self._get_summary()
        self.summary_label.text = (
            "Customers: {} | With phone: {}\n"
            "Follow-ups pending: {} | Completed: {} | Due: {}"
        ).format(summary["customers"], summary["with_phone"], summary["pending"],
                 summary["completed"], summary["due"])

    def add_customer(self, *_args):
        self.open_form("Add / Update Customer", [
            ("customer_id", "Customer ID to update (leave blank for new)"),
            ("name", "Customer name"),
            ("phone", "Phone number"),
            ("email", "Email (optional)"),
            ("address", "Address (optional)"),
            ("notes", "Notes (optional)"),
        ], self._after_customer_save)

    def _after_customer_save(self, values):
        self._save_customer(values)
        self.refresh_dashboard()

    def search_customers(self, *_args):
        self.open_form("Search Customers", [("search", "Name, phone, email or notes")],
                       lambda values: self._show_customers(values.get("search", "")))

    def _show_customers(self, search):
        rows = self._get_customers(search)
        message = "\n".join(
            "#{} | {} | {} | {}".format(row[0], row[1], row[2] or "No phone", row[3] or "No email")
            for row in rows
        ) or "No matching customers."
        self.popup_message("Customer List", message)

    def add_followup(self, *_args):
        self.open_form("Add Follow-up", [
            ("customer_id", "Customer ID"),
            ("followup_date", "Date YYYY-MM-DD"),
            ("note", "Follow-up note"),
        ], self._after_followup_save)

    def _after_followup_save(self, values):
        self._save_followup(values)
        self.refresh_dashboard()

    def show_followups(self, *_args):
        rows = self._get_followups("pending")
        message = "\n".join(
            "#{} | {} | {} | {}".format(row[0], row[2], row[3], row[4])
            for row in rows
        ) or "No pending follow-ups."
        self.popup_message("Pending Follow-ups", message)
        self.open_form("Complete Follow-up", [("followup_id", "Follow-up ID")],
                       self._after_followup_complete)

    def _after_followup_complete(self, values):
        self._complete_followup(values.get("followup_id"))
        self.refresh_dashboard()

    def show_summary(self, *_args):
        summary = self._get_summary()
        self.popup_message(
            "Customer Summary",
            "Customers: {}\nWith phone: {}\nPending follow-ups: {}\n"
            "Completed follow-ups: {}\nDue follow-ups: {}".format(
                summary["customers"], summary["with_phone"], summary["pending"],
                summary["completed"], summary["due"]
            )
        )

    def open_form(self, title, field_specs, save_callback):
        body = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(7))
        fields = {}
        for key, hint in field_specs:
            field = TextInput(hint_text=hint, multiline=False, size_hint_y=None, height=dp(44))
            fields[key] = field
            body.add_widget(field)
        buttons = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(7))
        save = Button(text="SAVE")
        cancel = Button(text="CANCEL")
        buttons.add_widget(save)
        buttons.add_widget(cancel)
        body.add_widget(buttons)
        popup = Popup(title=title, content=body, size_hint=(0.92, 0.88))
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
        body = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(7))
        scroll = ScrollView()
        label = Label(text=message, size_hint_y=None, halign="left", valign="top")
        label.bind(texture_size=lambda obj, size: setattr(obj, "height", size[1] + dp(18)))
        scroll.add_widget(label)
        body.add_widget(scroll)
        close = Button(text="CLOSE", size_hint_y=None, height=dp(42))
        body.add_widget(close)
        popup = Popup(title=title, content=body, size_hint=(0.92, 0.82))
        close.bind(on_release=popup.dismiss)
        popup.open()
'''


def generate_customer_manager_code(data):
    data = data if isinstance(data, dict) else {}
    plan = analyze_blueprint(dict(data, template_id="customer_manager"))
    name = str(data.get("name") or "My Customer Manager").strip() or "My Customer Manager"
    description = str(data.get("description") or "Offline customer and follow-up manager").strip()
    requested = plan["requested"]
    selected = [feature for feature in CUSTOMER_FEATURES if feature in requested]
    if not requested:
        selected = list(CUSTOMER_FEATURES)
    generated = TEMPLATE.replace("__APP_TITLE__", repr(name))
    generated = generated.replace("__APP_DESCRIPTION__", repr(description))
    generated = generated.replace("__ENABLED_FEATURES__", repr(selected))
    checks = validate_feature_coverage(generated, selected, template_id="customer_manager")
    generated += "\n".join([
        "",
        "# IDEA2APK V3 BLUEPRINT VERIFICATION",
        "# Template: customer_manager",
        "# Requested: " + (", ".join(requested) or "none (template defaults)"),
        "# Selected for app UI: " + (", ".join(selected) or "none"),
        "# Actually generated and verified: " + (", ".join(checks["implemented"]) or "none"),
        "# Missing from generated code: " + (", ".join(checks["missing"]) or "none"),
        "# Unsupported by selected template: " + (", ".join(plan["unsupported"]) or "none"),
        "# Completion: " + ("COMPLETE" if checks["complete"] and not plan["unsupported"] else "PARTIAL - review unsupported or missing features"),
        "# Source checks are deterministic fingerprints, not a substitute for device testing.",
        "",
    ])
    validation = validate_generated_source(generated)
    if not validation["valid"]:
        raise ValueError("Customer Manager generator produced invalid Python: " + "; ".join(validation["errors"]))
    return generated
