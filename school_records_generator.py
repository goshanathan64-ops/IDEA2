"""Independent offline School Records app generator for IDEA2APK V3."""
import json
import math
import re

from feature_engine import analyze_blueprint, expand_template_features, validate_feature_coverage, validate_generated_source

SCHOOL_FEATURES = [
    "student_records", "class_management", "attendance_tracking",
    "results_records", "basic_reports", "local_sqlite_storage",
]

TEMPLATE = r'''import os
import math
import sqlite3
from datetime import date, datetime

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
        self.db_path = os.path.join(self.user_data_dir, "school_records.db")
        self.db = sqlite3.connect(self.db_path)
        self.create_tables()
        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(7))
        root.add_widget(Label(text=APP_TITLE, size_hint_y=None, height=dp(44), font_size=sp(22)))
        root.add_widget(Label(text=APP_DESCRIPTION, size_hint_y=None, height=dp(42), font_size=sp(12)))
        self.summary_label = Label(text="", size_hint_y=None, height=dp(92), halign="left")
        root.add_widget(self.summary_label)
        scroll = ScrollView(do_scroll_x=False)
        menu = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(7))
        menu.bind(minimum_height=menu.setter("height"))
        actions = [
            ("student_records", "ADD / UPDATE STUDENT", self.add_student),
            ("student_records", "STUDENT LIST / SEARCH", self.show_students),
            ("attendance_tracking", "RECORD ATTENDANCE", self.record_attendance),
            ("attendance_tracking", "ATTENDANCE HISTORY", self.show_attendance),
            ("results_records", "RECORD STUDENT RESULT", self.record_result),
            ("results_records", "VIEW RESULTS", self.show_results),
            ("basic_reports", "SCHOOL SUMMARY", self.show_school_summary),
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
        self.status = Label(text="Offline school records are saved on this device.", size_hint_y=None, height=dp(30), font_size=sp(11))
        root.add_widget(self.status)
        self.refresh_dashboard()
        return root

    def create_tables(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admission_no TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                class_name TEXT NOT NULL,
                guardian_name TEXT DEFAULT '',
                guardian_phone TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                attendance_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('present','absent','late')),
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
                UNIQUE(student_id, attendance_date)
            );
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                term TEXT NOT NULL,
                score REAL NOT NULL CHECK(score >= 0),
                max_score REAL NOT NULL CHECK(max_score > 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(attendance_date);
            CREATE INDEX IF NOT EXISTS idx_results_student ON results(student_id);
        """)
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.commit()

    def _save_student(self, values):
        admission = str(values.get("admission_no", "")).strip()
        name = str(values.get("name", "")).strip()
        class_name = str(values.get("class_name", "")).strip()
        guardian = str(values.get("guardian_name", "")).strip()
        phone = str(values.get("guardian_phone", "")).strip()
        if not admission or not name or not class_name:
            raise ValueError("Admission number, student name and class are required.")
        self.db.execute(
            "INSERT INTO students(admission_no,name,class_name,guardian_name,guardian_phone) "
            "VALUES(?,?,?,?,?) ON CONFLICT(admission_no) DO UPDATE SET "
            "name=excluded.name,class_name=excluded.class_name,"
            "guardian_name=excluded.guardian_name,guardian_phone=excluded.guardian_phone",
            (admission, name, class_name, guardian, phone)
        )
        self.db.commit()

    def _get_students(self, search=""):
        term = "%" + str(search).strip() + "%"
        return self.db.execute(
            "SELECT admission_no,name,class_name,guardian_name,guardian_phone "
            "FROM students WHERE admission_no LIKE ? OR name LIKE ? OR class_name LIKE ? "
            "ORDER BY class_name,name",
            (term, term, term)
        ).fetchall()

    def _record_attendance(self, admission_no, attendance_date, status):
        admission = str(admission_no).strip()
        day = str(attendance_date).strip()
        state = str(status).strip().lower()
        try:
            datetime.strptime(day, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must use YYYY-MM-DD.")
        if state not in ("present", "absent", "late"):
            raise ValueError("Status must be present, absent or late.")
        student = self.db.execute("SELECT id FROM students WHERE admission_no=?", (admission,)).fetchone()
        if student is None:
            raise ValueError("Student admission number was not found.")
        self.db.execute(
            "INSERT INTO attendance(student_id,attendance_date,status) VALUES(?,?,?) "
            "ON CONFLICT(student_id,attendance_date) DO UPDATE SET status=excluded.status",
            (student[0], day, state)
        )
        self.db.commit()

    def _get_attendance(self, limit=100):
        return self.db.execute(
            "SELECT s.admission_no,s.name,s.class_name,a.attendance_date,a.status "
            "FROM attendance a JOIN students s ON s.id=a.student_id "
            "ORDER BY a.attendance_date DESC,s.name LIMIT ?",
            (int(limit),)
        ).fetchall()

    def _save_result(self, admission_no, subject, term, score, max_score=100):
        admission = str(admission_no).strip()
        subject = str(subject).strip()
        term = str(term).strip()
        try:
            mark = float(score)
            maximum = float(max_score)
        except (TypeError, ValueError):
            raise ValueError("Enter valid numeric marks.")
        if not admission or not subject or not term:
            raise ValueError("Admission number, subject and term are required.")
        if not math.isfinite(mark) or not math.isfinite(maximum) or maximum <= 0 or mark < 0 or mark > maximum:
            raise ValueError("Marks must be between zero and the maximum score.")
        student = self.db.execute("SELECT id FROM students WHERE admission_no=?", (admission,)).fetchone()
        if student is None:
            raise ValueError("Student admission number was not found.")
        self.db.execute(
            "INSERT INTO results(student_id,subject,term,score,max_score) VALUES(?,?,?,?,?)",
            (student[0], subject, term, mark, maximum)
        )
        self.db.commit()

    def _get_results(self, admission_no=""):
        query = (
            "SELECT s.admission_no,s.name,s.class_name,r.subject,r.term,r.score,r.max_score "
            "FROM results r JOIN students s ON s.id=r.student_id"
        )
        params = ()
        if str(admission_no).strip():
            query += " WHERE s.admission_no=?"
            params = (str(admission_no).strip(),)
        query += " ORDER BY r.id DESC"
        return self.db.execute(query, params).fetchall()

    def _get_school_summary(self):
        students = self.db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        classes = self.db.execute("SELECT COUNT(DISTINCT class_name) FROM students").fetchone()[0]
        attendance = self.db.execute(
            "SELECT status,COUNT(*) FROM attendance GROUP BY status"
        ).fetchall()
        results = self.db.execute(
            "SELECT COUNT(*),COALESCE(AVG((score/max_score)*100),0) FROM results"
        ).fetchone()
        return {
            "students": students,
            "classes": classes,
            "attendance": dict(attendance),
            "results_count": results[0],
            "average_percentage": float(results[1]),
        }

    def refresh_dashboard(self, *_args):
        summary = self._get_school_summary()
        self.summary_label.text = (
            "Students: {} | Classes: {}\nAttendance entries: {}\n"
            "Results: {} | Average: {:.1f}%"
        ).format(
            summary["students"], summary["classes"],
            sum(summary["attendance"].values()),
            summary["results_count"], summary["average_percentage"]
        )

    def add_student(self, *_args):
        self.open_form("Add / Update Student", [
            ("admission_no", "Admission number"),
            ("name", "Student full name"),
            ("class_name", "Class / grade"),
            ("guardian_name", "Parent / guardian name"),
            ("guardian_phone", "Guardian phone"),
        ], lambda values: self._after_student_save(values))

    def _after_student_save(self, values):
        self._save_student(values)
        self.refresh_dashboard()

    def record_attendance(self, *_args):
        self.open_form("Record Attendance", [
            ("admission_no", "Student admission number"),
            ("attendance_date", "Date YYYY-MM-DD (e.g. 2026-11-27)"),
            ("status", "Status: present, absent or late"),
        ], self._after_attendance_save)

    def _after_attendance_save(self, values):
        self._record_attendance(values["admission_no"], values["attendance_date"], values["status"])
        self.refresh_dashboard()

    def record_result(self, *_args):
        self.open_form("Record Student Result", [
            ("admission_no", "Student admission number"),
            ("subject", "Subject"),
            ("term", "Term / examination"),
            ("score", "Mark scored"),
            ("max_score", "Maximum mark (default 100)"),
        ], self._after_result_save)

    def _after_result_save(self, values):
        self._save_result(
            values["admission_no"], values["subject"], values["term"],
            values["score"], values.get("max_score") or "100"
        )
        self.refresh_dashboard()

    def show_students(self, *_args):
        self.open_form("Search Students (leave blank for all)", [("search", "Name, admission number or class")], self._show_student_search)

    def _show_student_search(self, values):
        rows = self._get_students(values.get("search", ""))
        message = "\n".join("{} | {} | {} | {} | {}".format(*row) for row in rows) or "No students found."
        self.popup_message("Student Records", message)

    def show_attendance(self, *_args):
        rows = self._get_attendance()
        message = "\n".join("{} | {} | {} | {} | {}".format(*row) for row in rows) or "No attendance recorded."
        self.popup_message("Attendance History", message)

    def show_results(self, *_args):
        rows = self._get_results()
        message = "\n".join("{} | {} | {} | {} | {} | {}/{}".format(*row) for row in rows) or "No results recorded."
        self.popup_message("Student Results", message)

    def show_school_summary(self, *_args):
        summary = self._get_school_summary()
        message = (
            "Students: {}\nClasses: {}\nAttendance: {}\n"
            "Results: {}\nAverage mark: {:.1f}%"
        ).format(
            summary["students"], summary["classes"], summary["attendance"],
            summary["results_count"], summary["average_percentage"]
        )
        self.popup_message("School Summary", message)

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


def generate_school_records_code(data):
    data = data if isinstance(data, dict) else {}
    plan = analyze_blueprint(data)
    name = str(data.get("name") or "My School Records").strip() or "My School Records"
    description = str(data.get("description") or "Offline school records manager").strip()
    requested = plan["requested"]
    selected = expand_template_features("school_records", requested, SCHOOL_FEATURES)

    generated = TEMPLATE.replace("__APP_TITLE__", repr(name))
    generated = generated.replace("__APP_DESCRIPTION__", repr(description))
    generated = generated.replace("__ENABLED_FEATURES__", repr(selected))
    coverage = validate_feature_coverage(generated, selected, template_id="school_records")
    generated += "\n".join([
        "",
        "# IDEA2APK V3 BLUEPRINT VERIFICATION",
        "# Template: school_records",
        "# Requested: " + (", ".join(requested) or "none (template defaults)"),
        "# Selected for app UI: " + (", ".join(selected) or "none"),
        "# Actually generated and verified: " + (", ".join(coverage["implemented"]) or "none"),
        "# Missing from generated code: " + (", ".join(coverage["missing"]) or "none"),
        "# Unsupported by selected template: " + (", ".join(plan["unsupported"]) or "none"),
        "# Completion: " + ("COMPLETE" if coverage["complete"] and not plan["unsupported"] else "PARTIAL - review unsupported or missing features"),
        "# Source checks are deterministic fingerprints, not a substitute for device testing.",
        "",
    ])
    validation = validate_generated_source(generated)
    if not validation["valid"]:
        raise ValueError("School Records generator produced invalid Python: " + "; ".join(validation["errors"]))
    return generated
