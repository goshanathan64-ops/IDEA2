"""Independent offline Booking & Appointments app generator for IDEA2APK V3."""
import re

from feature_engine import analyze_blueprint, expand_template_features, validate_feature_coverage, validate_generated_source, run_self_healing_pipeline

BOOKING_FEATURES = [
    "booking_records", "appointment_scheduling", "customer_details",
    "booking_status", "booking_history", "basic_reports", "local_sqlite_storage",
]

TEMPLATE = r'''import os
import sqlite3
from datetime import datetime, date, timedelta

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
        self.db_path = os.path.join(self.user_data_dir, "bookings.db")
        self.db = sqlite3.connect(self.db_path)
        self.create_tables()
        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(7))
        root.add_widget(Label(text=APP_TITLE, size_hint_y=None, height=dp(44), font_size=sp(22)))
        root.add_widget(Label(text=APP_DESCRIPTION, size_hint_y=None, height=dp(42), font_size=sp(12)))
        self.summary_label = Label(text="", size_hint_y=None, height=dp(86), halign="left")
        root.add_widget(self.summary_label)
        scroll = ScrollView(do_scroll_x=False)
        menu = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(7))
        menu.bind(minimum_height=menu.setter("height"))
        actions = [
            ("booking_records", "NEW BOOKING", self.new_booking),
            ("booking_history", "BOOKING HISTORY", self.show_history),
            ("appointment_scheduling", "UPCOMING APPOINTMENTS", self.show_upcoming),
            ("booking_status", "UPDATE BOOKING STATUS", self.update_status),
            ("basic_reports", "BOOKING SUMMARY", self.show_summary),
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
        self.status = Label(text="Offline bookings are saved on this device.", size_hint_y=None, height=dp(30), font_size=sp(11))
        root.add_widget(self.status)
        self.refresh_dashboard()
        return root

    def create_tables(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                phone TEXT DEFAULT '',
                service TEXT NOT NULL,
                booking_date TEXT NOT NULL,
                booking_time TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL DEFAULT 60,
                notes TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'scheduled'
                    CHECK(status IN ('scheduled','completed','cancelled')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_bookings_datetime "
            "ON bookings(booking_date, booking_time)"
        )
        self.db.commit()

    def _save_booking(self, values):
        customer = str(values.get("customer_name", "")).strip()
        phone = str(values.get("phone", "")).strip()
        service = str(values.get("service", "")).strip()
        day = str(values.get("booking_date", "")).strip()
        clock = str(values.get("booking_time", "")).strip()
        notes = str(values.get("notes", "")).strip()
        try:
            duration = int(values.get("duration_minutes", 60) or 60)
            datetime.strptime(day, "%Y-%m-%d")
            datetime.strptime(clock, "%H:%M")
        except (TypeError, ValueError):
            raise ValueError("Use date YYYY-MM-DD, time HH:MM and a whole-number duration.")
        if not customer or not service:
            raise ValueError("Customer name and service are required.")
        if duration < 5 or duration > 720:
            raise ValueError("Duration must be between 5 and 720 minutes.")
        start = datetime.strptime(day + " " + clock, "%Y-%m-%d %H:%M")
        end = start + timedelta(minutes=duration)
        if end.date() != start.date():
            raise ValueError("A booking must finish on the same day.")
        rows = self.db.execute(
            "SELECT id,booking_time,duration_minutes FROM bookings "
            "WHERE booking_date=? AND service=? AND status!='cancelled'",
            (day, service)
        ).fetchall()
        for booking_id, existing_time, existing_duration in rows:
            existing_start = datetime.strptime(day + " " + existing_time, "%Y-%m-%d %H:%M")
            existing_end = existing_start + timedelta(minutes=existing_duration)
            if start < existing_end and existing_start < end:
                raise ValueError("This service already has a booking that overlaps that time.")
        self.db.execute(
            "INSERT INTO bookings(customer_name,phone,service,booking_date,booking_time,"
            "duration_minutes,notes) VALUES(?,?,?,?,?,?,?)",
            (customer, phone, service, day, clock, duration, notes)
        )
        self.db.commit()

    def _get_history(self, limit=200):
        return self.db.execute(
            "SELECT id,customer_name,phone,service,booking_date,booking_time,"
            "duration_minutes,status,notes FROM bookings "
            "ORDER BY booking_date DESC,booking_time DESC,id DESC LIMIT ?",
            (int(limit),)
        ).fetchall()

    def _get_upcoming(self, from_date=None, limit=100):
        day = from_date or date.today().isoformat()
        return self.db.execute(
            "SELECT id,customer_name,phone,service,booking_date,booking_time,"
            "duration_minutes,status FROM bookings "
            "WHERE booking_date>=? AND status='scheduled' "
            "ORDER BY booking_date,booking_time LIMIT ?",
            (day, int(limit))
        ).fetchall()

    def _update_booking_status(self, booking_id, status):
        try:
            identifier = int(booking_id)
        except (TypeError, ValueError):
            raise ValueError("Enter a valid booking ID.")
        state = str(status).strip().lower()
        if state not in ("scheduled", "completed", "cancelled"):
            raise ValueError("Status must be scheduled, completed or cancelled.")
        cursor = self.db.execute(
            "UPDATE bookings SET status=? WHERE id=?",
            (state, identifier)
        )
        if cursor.rowcount != 1:
            self.db.rollback()
            raise ValueError("Booking ID was not found.")
        self.db.commit()

    def _get_summary(self):
        total = self.db.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
        scheduled = self.db.execute(
            "SELECT COUNT(*) FROM bookings WHERE status='scheduled'"
        ).fetchone()[0]
        completed = self.db.execute(
            "SELECT COUNT(*) FROM bookings WHERE status='completed'"
        ).fetchone()[0]
        cancelled = self.db.execute(
            "SELECT COUNT(*) FROM bookings WHERE status='cancelled'"
        ).fetchone()[0]
        today = self.db.execute(
            "SELECT COUNT(*) FROM bookings WHERE booking_date=? AND status='scheduled'",
            (date.today().isoformat(),)
        ).fetchone()[0]
        return {
            "total": total, "scheduled": scheduled, "completed": completed,
            "cancelled": cancelled, "today": today,
        }

    def refresh_dashboard(self, *_args):
        summary = self._get_summary()
        self.summary_label.text = (
            "All bookings: {} | Scheduled: {}\n"
            "Completed: {} | Cancelled: {}\n"
            "Scheduled for today: {}"
        ).format(
            summary["total"], summary["scheduled"], summary["completed"],
            summary["cancelled"], summary["today"]
        )

    def new_booking(self, *_args):
        self.open_form("New Booking", [
            ("customer_name", "Customer full name"),
            ("phone", "Phone number (optional)"),
            ("service", "Service / staff member"),
            ("booking_date", "Date YYYY-MM-DD"),
            ("booking_time", "Time HH:MM (24-hour)"),
            ("duration_minutes", "Duration minutes (default 60)"),
            ("notes", "Notes (optional)"),
        ], self._after_booking_save)

    def _after_booking_save(self, values):
        self._save_booking(values)
        self.refresh_dashboard()

    def show_history(self, *_args):
        rows = self._get_history()
        message = "\n".join(
            "#{} | {} | {} | {} {} | {} min | {}".format(
                row[0], row[1], row[3], row[4], row[5], row[6], row[7]
            ) for row in rows
        ) or "No bookings recorded."
        self.popup_message("Booking History", message)

    def show_upcoming(self, *_args):
        rows = self._get_upcoming()
        message = "\n".join(
            "#{} | {} | {} | {} {} | {} min".format(
                row[0], row[1], row[3], row[4], row[5], row[6]
            ) for row in rows
        ) or "No upcoming scheduled appointments."
        self.popup_message("Upcoming Appointments", message)

    def update_status(self, *_args):
        self.open_form("Update Booking Status", [
            ("booking_id", "Booking ID"),
            ("status", "scheduled, completed or cancelled"),
        ], self._after_status_update)

    def _after_status_update(self, values):
        self._update_booking_status(values["booking_id"], values["status"])
        self.refresh_dashboard()

    def show_summary(self, *_args):
        summary = self._get_summary()
        self.popup_message(
            "Booking Summary",
            "All bookings: {}\nScheduled: {}\nCompleted: {}\nCancelled: {}\nToday: {}".format(
                summary["total"], summary["scheduled"], summary["completed"],
                summary["cancelled"], summary["today"]
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


def generate_booking_code(data):
    data = data if isinstance(data, dict) else {}
    plan = analyze_blueprint(data)
    name = str(data.get("name") or "My Booking Manager").strip() or "My Booking Manager"
    description = str(data.get("description") or "Offline booking and appointment manager").strip()
    requested = plan["requested"]
    selected = expand_template_features("booking_appointments", requested, BOOKING_FEATURES)

    generated = TEMPLATE.replace("__APP_TITLE__", repr(name))
    generated = generated.replace("__APP_DESCRIPTION__", repr(description))
    generated = generated.replace("__ENABLED_FEATURES__", repr(selected))
    pipeline = run_self_healing_pipeline(
        generated, selected, "booking_appointments", regenerate_callback=lambda: TEMPLATE.replace("__APP_TITLE__", repr(name)).replace("__APP_DESCRIPTION__", repr(description)).replace("__ENABLED_FEATURES__", repr(selected))
    )
    generated = pipeline["source"]
    coverage = pipeline["coverage"]
    generated += "\n".join([
        "",
        "# IDEA2APK V3 BLUEPRINT VERIFICATION",
        "# Template: booking_appointments",
        "# Requested: " + (", ".join(requested) or "none (template defaults)"),
        "# Selected for app UI: " + (", ".join(selected) or "none"),
        "# Actually generated and verified: " + (", ".join(coverage["implemented"]) or "none"),
        "# Missing from generated code: " + (", ".join(coverage["missing"]) or "none"),
        "# Unsupported by selected template: " + (", ".join(plan["unsupported"]) or "none"),
        "# Repair attempted: " + ("YES" if pipeline["repair"]["attempted"] else "NO"),
        "# Repair status: " + pipeline["repair"]["status"],
        "# Completion: " + ("COMPLETE" if coverage["complete"] and not plan["unsupported"] else "PARTIAL - review unsupported or missing features"),
        "# Source checks are deterministic fingerprints, not a substitute for device testing.",
        "",
    ])
    validation = validate_generated_source(generated)
    if not validation["valid"]:
        raise ValueError("Booking generator produced invalid Python: " + "; ".join(validation["errors"]))
    return generated
