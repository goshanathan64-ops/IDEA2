
import os
import re
import json
import uuid
import zipfile
import shutil

from kivy.app import App
from kivy.metrics import dp, sp
from kivy.core.clipboard import Clipboard
from kivy.utils import platform
from kivy.clock import Clock

from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup


APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_FILE = os.path.join(APP_DIR, "idea2apk_projects.json")
EXPORT_DIR = os.path.join(APP_DIR, "exports")


class IDEA2APK(App):

    def build(self):
        self.title = "IDEA2APK"
        self.projects = self.load_projects()
        self.current_project = None
        self.generated_code = ""
        self.generated_is_app_code = False

        self.manager = ScreenManager()

        self.home_screen = Screen(name="home")
        self.planner_screen = Screen(name="planner")
        self.projects_screen = Screen(name="projects")
        self.result_screen = Screen(name="result")

        for screen in [
            self.home_screen,
            self.planner_screen,
            self.projects_screen,
            self.result_screen
        ]:
            self.manager.add_widget(screen)

        self.create_home_screen()
        self.create_planner_screen()
        self.create_projects_screen()
        self.create_result_screen()

        return self.manager

    def make_button(self, text, callback, height=48):
        btn = Button(
            text=text,
            size_hint_y=None,
            height=dp(height),
            font_size=sp(15)
        )
        btn.bind(on_release=callback)
        return btn

    def make_label(self, text, height=35, size=16):
        return Label(
            text=text,
            size_hint_y=None,
            height=dp(height),
            font_size=sp(size),
            halign="center",
            valign="middle"
        )

    def make_input(self, hint, height=48, multiline=False):
        return TextInput(
            hint_text=hint,
            size_hint_y=None,
            height=dp(height),
            multiline=multiline,
            font_size=sp(15),
            padding=dp(10)
        )

    # HOME SCREEN

    def create_home_screen(self):
        layout = BoxLayout(
            orientation="vertical",
            padding=dp(18),
            spacing=dp(12)
        )

        layout.add_widget(
            self.make_label("IDEA2APK", 65, 28)
        )

        layout.add_widget(
            self.make_label(
                "Turn your ideas into Android apps",
                45,
                16
            )
        )

        layout.add_widget(
            self.make_button(
                "SMART APP PLANNER",
                self.open_planner
            )
        )

        layout.add_widget(
            self.make_button(
                "MY PROJECTS",
                self.open_projects
            )
        )

        layout.add_widget(
            self.make_button(
                "ABOUT IDEA2APK",
                self.show_about
            )
        )

        self.home_screen.add_widget(layout)

    # PLANNER SCREEN

    def create_planner_screen(self):
        root = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(8)
        )

        root.add_widget(
            self.make_label("SMART APP PLANNER", 45, 22)
        )

        scroll = ScrollView()

        form = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            size_hint_y=None
        )

        form.bind(minimum_height=form.setter("height"))

        form.add_widget(self.make_label("App name"))

        self.name_input = self.make_input(
            "Example: My Business App"
        )
        form.add_widget(self.name_input)

        form.add_widget(self.make_label("App description"))

        self.description_input = self.make_input(
            "Describe what your app does",
            90,
            True
        )
        form.add_widget(self.description_input)

        form.add_widget(self.make_label("Target users"))

        self.target_input = self.make_input(
            "Example: Customers, students, farmers"
        )
        form.add_widget(self.target_input)

        form.add_widget(self.make_label("App type"))

        self.type_input = self.make_input(
            "Example: Business, education, shopping"
        )
        form.add_widget(self.type_input)

        form.add_widget(self.make_label("App features"))

        self.features_input = self.make_input(
            "Enter features separated by commas",
            100,
            True
        )
        form.add_widget(self.features_input)

        # Optional details that complete the 16-section app blueprint.
        self.extra_inputs = {}
        extra_fields = [
            ("logo_version", "Logo idea and app version", "Example: Blue and white logo; version 1.0"),
            ("user_accounts", "User accounts and permissions", "Example: Owner login, staff accounts, customer accounts"),
            ("screens", "Screens and navigation", "Example: Dashboard, products, sales, settings"),
            ("database", "Database and data to store", "Example: Products, prices, stock, customers, sales"),
            ("business_logic", "Business rules and workflows", "Example: Reduce stock automatically after each sale"),
            ("design", "Design and branding", "Example: Green theme, large buttons, simple layout"),
            ("notifications", "Notifications and reminders", "Example: Low-stock alerts and payment reminders"),
            ("reports", "Reports and analytics", "Example: Daily sales, monthly profit, stock reports"),
            ("connectivity", "Internet and offline requirements", "Example: Works offline; syncs when internet is available"),
            ("security", "Security and data protection", "Example: PIN login, role permissions, backups"),
            ("monetization", "Monetization and payments", "Example: Free app, subscriptions, mobile money"),
            ("platforms", "Target platforms", "Example: Android phone and tablet"),
            ("testing", "Testing and release requirements", "Example: Test adding products, sales, stock and reports")
        ]

        for key, heading, hint in extra_fields:
            form.add_widget(self.make_label(heading, 35, 15))
            field = self.make_input(hint, 72, True)
            self.extra_inputs[key] = field
            form.add_widget(field)

        form.add_widget(
            self.make_button(
                "GENERATE BLUEPRINT",
                self.generate_blueprint
            )
        )

        form.add_widget(
            self.make_button(
                "GENERATE APP CODE",
                self.generate_app_code
            )
        )

        form.add_widget(
            self.make_button(
                "SAVE PROJECT",
                self.save_current_project
            )
        )

        scroll.add_widget(form)
        root.add_widget(scroll)

        root.add_widget(            self.make_button("BACK HOME", self.go_home)
        )

        self.planner_screen.add_widget(root)

    # PROJECTS SCREEN

    def create_projects_screen(self):
        root = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(8)
        )

        root.add_widget(
            self.make_label("MY PROJECTS", 50, 22)
        )

        self.project_list = BoxLayout(
            orientation="vertical",
            spacing=dp(6),
            size_hint_y=None
        )

        self.project_list.bind(
            minimum_height=self.project_list.setter("height")
        )

        scroll = ScrollView()
        scroll.add_widget(self.project_list)
        root.add_widget(scroll)

        root.add_widget(
            self.make_button(
                "REFRESH PROJECTS",
                self.refresh_projects
            )
        )

        root.add_widget(
            self.make_button(
                "BACK HOME",
                self.go_home
            )
        )

        self.projects_screen.add_widget(root)

    # RESULT SCREEN

    def create_result_screen(self):
        root = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8)
        )

        root.add_widget(
            self.make_label(
                "GENERATED APP CODE",
                45,
                20
            )
        )

        self.result_text = TextInput(
            readonly=True,
            multiline=True,
            font_size=sp(12),
            size_hint_y=1
        )

        root.add_widget(self.result_text)

        root.add_widget(
            self.make_button(
                "EXPORT PROJECT ZIP",
                self.export_project_zip
            )
        )

        root.add_widget(
            self.make_button(
                "SHARE GENERATED CODE (COPY)",
                self.copy_generated_code
            )
        )

        root.add_widget(
            self.make_button(
                "BUILD APK (CREATE BUILD PACKAGE)",
                self.build_apk
            )
        )

        root.add_widget(
            self.make_button(
                "BACK TO PLANNER",
                self.open_planner
            )
        )

        self.result_screen.add_widget(root)

    # PROJECT DATA

    def get_project_data(self):
        name = self.name_input.text.strip()
        description = self.description_input.text.strip()

        if not name:
            self.message("Please enter an app name.")
            return None

        return {
            "id": (
                self.current_project["id"]
                if self.current_project
                else str(uuid.uuid4())
            ),
            "name": name,
            "description": description,
            "target": self.target_input.text.strip(),
            "app_type": self.type_input.text.strip(),
            "features": self.features_input.text.strip(),
            **{
                key: field.text.strip()
                for key, field in self.extra_inputs.items()
            }
        }

    # BLUEPRINT GENERATION

    def generate_blueprint(self, *args):
        data = self.get_project_data()

        if not data:
            return

        def value(key):
            return data.get(key, "").strip() or "Not specified"

        sections = [
            ("1. APP IDENTITY", "Name: " + value("name") + "\nDescription: " + value("description") + "\nLogo and version: " + value("logo_version")),
            ("2. TARGET USERS", value("target")),
            ("3. APP CATEGORY", value("app_type")),
            ("4. CORE FEATURES", value("features")),
            ("5. USER ACCOUNTS AND PERMISSIONS", value("user_accounts")),
            ("6. SCREENS AND NAVIGATION", value("screens")),
            ("7. DATABASE AND DATA STORAGE", value("database")),
            ("8. BUSINESS LOGIC AND WORKFLOWS", value("business_logic")),
            ("9. DESIGN AND BRANDING", value("design")),
            ("10. NOTIFICATIONS AND REMINDERS", value("notifications")),
            ("11. REPORTS AND ANALYTICS", value("reports")),
            ("12. INTERNET AND OFFLINE REQUIREMENTS", value("connectivity")),
            ("13. SECURITY AND DATA PROTECTION", value("security")),
            ("14. MONETIZATION AND PAYMENTS", value("monetization")),
            ("15. TARGET PLATFORMS", value("platforms")),
            ("16. TESTING AND RELEASE REQUIREMENTS", value("testing"))
        ]

        blueprint = "IDEA2APK COMPLETE APP BLUEPRINT\n"
        blueprint += "================================\n\n"
        for heading, details in sections:
            blueprint += heading + "\n" + details + "\n\n"
        blueprint += "NEXT STEP: Review this blueprint, then generate the application code."

        self.generated_code = blueprint
        self.generated_is_app_code = False
        self.current_project = data
        self.result_text.text = blueprint
        self.manager.current = "result"

    # APP CODE GENERATION

    def generate_app_code(self, *args):
        data = self.get_project_data()

        if not data:
            return

        app_name = re.sub(
            r"[^A-Za-z0-9_]",
            "",
            data["name"].replace(" ", "_")
        )
        if not app_name:
            app_name = "HardwareShopManager"

        # Stage 2: generate a working hardware-shop management app.
        # The generated app stores its records locally on the Android device.
        code = r'''import os
import json
from datetime import date, datetime

from kivy.app import App
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup


APP_TITLE = __APP_TITLE__
APP_DESCRIPTION = __APP_DESCRIPTION__


class GeneratedApp(App):

    def build(self):
        self.title = APP_TITLE
        self.data_file = os.path.join(
            self.user_data_dir, "hardware_shop_data.json"
        )
        self.data = self.load_data()

        root = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(7)
        )

        heading = Label(
            text=APP_TITLE,
            size_hint_y=None,
            height=dp(48),
            font_size=sp(22),
            bold=True
        )
        root.add_widget(heading)

        self.status = Label(
            text="Hardware Shop Manager",
            size_hint_y=None,
            height=dp(30),
            font_size=sp(13)
        )
        root.add_widget(self.status)

        scroll = ScrollView()        self.content = BoxLayout(
            orientation="vertical",
            spacing=dp(7),
            size_hint_y=None
        )
        self.content.bind(minimum_height=self.content.setter("height"))
        scroll.add_widget(self.content)
        root.add_widget(scroll)

        self.show_dashboard()
        return root

    def load_data(self):
        empty = {
            "products": [],
            "sales": [],
            "expenses": [],
            "customers": []
        }
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as handle:
                    saved = json.load(handle)
                for key in empty:
                    if not isinstance(saved.get(key), list):
                        saved[key] = []
                return saved
        except Exception:
            pass
        return empty

    def save_data(self):
        try:
            os.makedirs(self.user_data_dir, exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as handle:
                json.dump(self.data, handle, indent=2)
            self.status.text = "Saved on this device"
            return True
        except Exception as error:
            self.status.text = "Save error: " + str(error)
            return False

    def money(self, amount):
        return "$" + format(float(amount), ".2f")

    def add_label(self, text, height=38, size=15):
        label = Label(
            text=str(text),
            size_hint_y=None,
            height=dp(height),
            font_size=sp(size),
            halign="left",
            valign="middle"
        )
        label.bind(size=lambda obj, value: setattr(obj, "text_size", (value[0], None)))
        self.content.add_widget(label)

    def add_button(self, text, callback):
        button = Button(
            text=text,
            size_hint_y=None,
            height=dp(46),
            font_size=sp(14)
        )
        button.bind(on_release=lambda instance: callback())
        self.content.add_widget(button)

    def clear_content(self):
        self.content.clear_widgets()

    def navigation(self):
        self.add_button("DASHBOARD", self.show_dashboard)
        self.add_button("PRODUCTS AND STOCK", self.show_products)
        self.add_button("RECORD A SALE", self.show_sales)
        self.add_button("RECORD AN EXPENSE", self.show_expenses)
        self.add_button("CUSTOMERS", self.show_customers)
        self.add_button("DAILY AND MONTHLY REPORTS", self.show_reports)

    def show_dashboard(self):
        self.clear_content()
        self.add_label("BUSINESS DASHBOARD", 42, 19)
        stock_value = sum(
            float(p.get("price", 0)) * int(p.get("quantity", 0))
            for p in self.data["products"]
        )
        today = date.today().isoformat()
        today_sales = sum(
            float(s.get("total", 0))
            for s in self.data["sales"] if s.get("date") == today
        )
        today_expenses = sum(
            float(e.get("amount", 0))
            for e in self.data["expenses"] if e.get("date") == today
        )
        self.add_label("Products listed: " + str(len(self.data["products"])))
        self.add_label("Stock value at selling price: " + self.money(stock_value))
        self.add_label("Sales today: " + self.money(today_sales))
        self.add_label("Expenses today: " + self.money(today_expenses))
        self.add_label("Customers saved: " + str(len(self.data["customers"])))
        self.add_label("Records are saved locally on this device.", 48, 12)
        self.navigation()

    def show_products(self):
        self.clear_content()
        self.add_label("PRODUCTS AND STOCK", 42, 19)
        self.add_button("ADD NEW PRODUCT", self.add_product)
        if not self.data["products"]:
            self.add_label("No products yet. Add your first product.")
        for item in self.data["products"]:
            self.add_label(
                "{} | {} in stock | {}".format(
                    item.get("name", ""),
                    item.get("quantity", 0),
                    self.money(item.get("price", 0))
                ),
                44,
                13
            )
        self.navigation()

    def add_product(self):
        self.open_form(
            "Add product",
            ["Product name", "Selling price (USD)", "Opening quantity"],
            self.save_product
        )

    def save_product(self, values):
        try:
            name = values[0].strip()
            price = float(values[1])
            quantity = int(values[2])
            if not name or price < 0 or quantity < 0:
                raise ValueError()
        except Exception:
            self.show_message("Enter a product name, a valid price and a whole-number quantity.")
            return
        self.data["products"].append({
            "name": name,
            "price": price,
            "quantity": quantity
        })
        self.save_data()
        self.show_products()

    def show_sales(self):
        self.clear_content()
        self.add_label("SALES", 42, 19)
        self.add_label("Record a sale using the exact product name.")
        self.add_button("RECORD NEW SALE", self.add_sale)
        for sale in reversed(self.data["sales"][-20:]):
            self.add_label(
                "{} | {} x {} | {}".format(
                    sale.get("date", ""),
                    sale.get("quantity", 0),
                    sale.get("product", ""),
                    self.money(sale.get("total", 0))
                ),
                42,
                12
            )
        self.navigation()

    def add_sale(self):
        self.open_form(
            "Record sale",
            ["Exact product name", "Quantity sold"],
            self.save_sale
        )

    def save_sale(self, values):
        name = values[0].strip().lower()
        try:
            quantity = int(values[1])
            if not name or quantity <= 0:
                raise ValueError()
        except Exception:
            self.show_message("Enter a product name and a quantity greater than zero.")
            return

        product = next(
            (p for p in self.data["products"] if p.get("name", "").lower() == name),
            None
        )
        if product is None:
            self.show_message("That product was not found. Check its exact name.")
            return
        if int(product.get("quantity", 0)) < quantity:
            self.show_message("Not enough stock. Available: " + str(product.get("quantity", 0)))
            return

        total = float(product.get("price", 0)) * quantity
        product["quantity"] = int(product.get("quantity", 0)) - quantity
        self.data["sales"].append({
            "product": product["name"],
            "quantity": quantity,
            "unit_price": float(product.get("price", 0)),
            "total": total,
            "date": date.today().isoformat(),
            "time": datetime.now().strftime("%H:%M")
        })
        self.save_data()
        self.show_message("Sale saved. Total: " + self.money(total))
        self.show_sales()

    def show_expenses(self):
        self.clear_content()
        self.add_label("EXPENSES", 42, 19)
        self.add_button("ADD EXPENSE", self.add_expense)
        for expense in reversed(self.data["expenses"][-20:]):
            self.add_label(
                "{} | {} | {}".format(
                    expense.get("date", ""),
                    expense.get("description", ""),
                    self.money(expense.get("amount", 0))
                ),
                42,
                12
            )
        self.navigation()
    def add_expense(self):
        self.open_form(
            "Add expense",
            ["Expense description", "Amount (USD)"],
            self.save_expense
        )

    def save_expense(self, values):
        try:
            description = values[0].strip()
            amount = float(values[1])
            if not description or amount <= 0:
                raise ValueError()
        except Exception:
            self.show_message("Enter a description and an amount greater than zero.")
            return
        self.data["expenses"].append({
            "description": description,
            "amount": amount,
            "date": date.today().isoformat()
        })
        self.save_data()
        self.show_expenses()

    def show_customers(self):
        self.clear_content()
        self.add_label("CUSTOMERS", 42, 19)
        self.add_button("ADD CUSTOMER", self.add_customer)
        for customer in self.data["customers"]:
            self.add_label(
                "{} | {}".format(
                    customer.get("name", ""),
                    customer.get("phone", "")
                ),
                42,
                13
            )
        self.navigation()

    def add_customer(self):
        self.open_form(
            "Add customer",
            ["Customer name", "Phone number (optional)"],
            self.save_customer
        )

    def save_customer(self, values):
        name = values[0].strip()
        if not name:
            self.show_message("Enter the customer's name.")
            return
        self.data["customers"].append({
            "name": name,
            "phone": values[1].strip()
        })
        self.save_data()
        self.show_customers()

    def show_reports(self):
        self.clear_content()
        self.add_label("BUSINESS REPORTS", 42, 19)
        today = date.today().isoformat()
        month = date.today().strftime("%Y-%m")
        daily_sales = sum(float(s.get("total", 0)) for s in self.data["sales"] if s.get("date") == today)
        daily_expenses = sum(float(e.get("amount", 0)) for e in self.data["expenses"] if e.get("date") == today)
        monthly_sales = sum(float(s.get("total", 0)) for s in self.data["sales"] if str(s.get("date", "")).startswith(month))
        monthly_expenses = sum(float(e.get("amount", 0)) for e in self.data["expenses"] if str(e.get("date", "")).startswith(month))
        self.add_label("TODAY", 34, 16)
        self.add_label("Sales: " + self.money(daily_sales))
        self.add_label("Expenses: " + self.money(daily_expenses))
        self.add_label("Net before other costs: " + self.money(daily_sales - daily_expenses))
        self.add_label("THIS MONTH", 34, 16)
        self.add_label("Sales: " + self.money(monthly_sales))
        self.add_label("Expenses: " + self.money(monthly_expenses))
        self.add_label("Net before other costs: " + self.money(monthly_sales - monthly_expenses))
        self.add_label("Reports use the dates recorded on this device.", 46, 12)
        self.navigation()

    def open_form(self, title, prompts, callback):
        panel = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8)
        )
        fields = []
        for prompt in prompts:
            field = TextInput(
                hint_text=prompt,
                multiline=False,
                size_hint_y=None,
                height=dp(44),
                font_size=sp(14)
            )
            fields.append(field)
            panel.add_widget(field)

        controls = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(8)
        )
        popup = Popup(
            title=title,
            content=panel,
            size_hint=(0.9, None),
            height=dp(300)
        )
        save_button = Button(text="SAVE")
        cancel_button = Button(text="CANCEL")
        controls.add_widget(save_button)
        controls.add_widget(cancel_button)
        panel.add_widget(controls)

        def submit(instance):
            values = [field.text for field in fields]
            popup.dismiss()
            callback(values)

        save_button.bind(on_release=submit)
        cancel_button.bind(on_release=lambda instance: popup.dismiss())
        popup.open()

    def show_message(self, message):
        panel = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8)
        )
        panel.add_widget(Label(text=message))
        close_button = Button(text="OK", size_hint_y=None, height=dp(44))
        panel.add_widget(close_button)
        popup = Popup(title="Hardware Shop Manager", content=panel, size_hint=(0.85, 0.35))
        close_button.bind(on_release=popup.dismiss)
        popup.open()


if __name__ == "__main__":
    GeneratedApp().run()
'''
        code = code.replace("__APP_TITLE__", repr(app_name))
        code = code.replace("__APP_DESCRIPTION__", repr(data["description"]))
        self.generated_code = code
        self.generated_is_app_code = True
        self.current_project = data
        self.result_text.text = code
        self.manager.current = "result"

    # SAVE AND LOAD PROJECTS

    def load_projects(self):
        try:
            if os.path.exists(PROJECTS_FILE):
                with open(
                    PROJECTS_FILE,
                    "r",
                    encoding="utf-8"
                ) as file:
                    return json.load(file)
        except Exception:
            pass

        return []

    def save_projects(self):
        try:
            with open(
                PROJECTS_FILE,
                "w",
                encoding="utf-8"
            ) as file:
                json.dump(
                    self.projects,
                    file,
                    indent=4
                )

            return True

        except Exception as error:
            self.message("Save failed: " + str(error))
            return False

    def save_current_project(self, *args):
        data = self.get_project_data()

        if not data:
            return

        found = False

        for index, project in enumerate(self.projects):
            if project.get("id") == data["id"]:
                self.projects[index] = data
                found = True
                break

        if not found:
            self.projects.append(data)

        self.current_project = data

        if self.save_projects():
            self.message("Project saved successfully.")

    def open_projects(self, *args):
        self.refresh_projects()
        self.manager.current = "projects"

    def refresh_projects(self, *args):
        self.project_list.clear_widgets()

        if not self.projects:
            self.project_list.add_widget(
                self.make_label("No saved projects yet.", 50)
            )
            return

        for project in self.projects:
            name = project.get("name", "Unnamed project")
            row = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(145),
                spacing=dp(5)
            )

            row.add_widget(
                self.make_label(name, 35, 17)
            )

            row.add_widget(
                self.make_button(
                    "OPEN / EDIT",
                    lambda btn, p=project: self.edit_project(p),
                    38
                )
            )

            row.add_widget(
                self.make_button(
                    "DELETE",
                    lambda btn, p=project: self.delete_project(p),
                    38
                )
            )

            self.project_list.add_widget(row)

    def edit_project(self, project):
        self.current_project = project

        self.name_input.text = project.get("name", "")
        self.description_input.text = project.get("description", "")
        self.target_input.text = project.get("target", "")
        self.type_input.text = project.get("app_type", "")
        self.features_input.text = project.get("features", "")
        for key, field in self.extra_inputs.items():
            field.text = project.get(key, "")

        self.manager.current = "planner"

    def delete_project(self, project):
        self.projects = [
            item for item in self.projects
            if item.get("id") != project.get("id")
        ]

        self.save_projects()
        self.refresh_projects()
        self.message("Project deleted.")

    # BUILD SPEC GENERATOR

    def create_buildozer_spec(self, data):
        safe_title = re.sub(
            r"[\r\n]+",
            " ",
            data.get("name", "MyBusiness")
        ).strip()[:50] or "MyBusiness"

        package_name = re.sub(
            r"[^a-z0-9]",
            "",
            safe_title.lower()
        )

        if not package_name:
            package_name = "mybusiness"
        if not package_name[0].isalpha():
            package_name = "app" + package_name
        package_name = package_name[:50]

        return """[app]
title = {title}
package.name = {package}
package.domain = com.nexgen

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,txt

version = 0.1

requirements = python3==3.11.5,hostpython3==3.11.5,kivy==2.3.0

orientation = portrait
fullscreen = 0

android.api = 34
android.minapi = 21
android.ndk = 28c
p4a.commit = 0382d27de2f7315ed98e74884bafb30365decdee
android.build_tools_version = 34.0.0
android.accept_sdk_license = True

android.archs = arm64-v8a, armeabi-v7a

# Use Android's system file picker; no broad storage permission is needed.
android.permissions = INTERNET

[buildozer]
log_level = 2
warn_on_root = 1
""".format(
            title=safe_title,
            package=package_name
        )

    # STAGE 5: ZIP EXPORT

    def create_github_workflow(self):
        return """name: Build Android APK

on:
  workflow_dispatch:
  push:
    branches:
      - main

jobs:
  build:
    runs-on: ubuntu-22.04
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"

      - name: Set up Java
        uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "17"

      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y git zip unzip autoconf automake libtool pkg-config zlib1g-dev libncurses5-dev libffi-dev libssl-dev libltdl-dev cmake

      - name: Install Buildozer
        run: |
          python -m pip install --upgrade pip setuptools wheel
          python -m pip install -r requirements.txt

      - name: Build Android APK
        run: buildozer -v android debug

      - name: Upload APK
        uses: actions/upload-artifact@v4
        with:
          name: Generated-Android-APK
          path: bin/*.apk
          if-no-files-found: error
"""

    def create_requirements_txt(self):
        return (
            "buildozer==1.5.0\n"
            "cython==0.29.33\n"
            "virtualenv\n"
        )

    def export_project_zip(self, *args):
        if not self.generated_code:
            self.message("Generate app code first.")
            return

        try:
            os.makedirs(EXPORT_DIR, exist_ok=True)

            data = self.current_project or {
                "name": "MyBusiness",
                "description": "Generated application"
            }

            folder_name = re.sub(
                r"[^A-Za-z0-9_-]",
                "_",
                data["name"]
            )

            if not folder_name:
                folder_name = "MyBusiness"

            zip_path = os.path.join(
                EXPORT_DIR,
                folder_name + ".zip"
            )

            with zipfile.ZipFile(
                zip_path,
                "w",
                zipfile.ZIP_DEFLATED
            ) as archive:

                archive.writestr(
                    "main.py",
                    self.generated_code
                )

                archive.writestr(
                    "README.md",
                    "# " + data["name"] + "\n\n"
                    + data.get("description", "") + "\n\n"
                    + "## Build the Android APK\n"
                    + "This ZIP is a build package, not the APK itself.\n\n"
                    + "1. Create a GitHub repository.\n"
                    + "2. Extract this ZIP and upload all files, including the hidden .github folder.\n"
                    + "3. Commit the files to the main branch.\n"
                    + "4. Open the repository Actions tab.\n"
                    + "5. Select Build Android APK, then choose Run workflow.\n"
                    + "6. Wait for the build to finish successfully.\n"
                    + "7. Open the completed run and download Generated-Android-APK.\n"
                    + "8. Extract the downloaded artifact and install the APK on Android.\n\n"
                    + "Security: do not put passwords, API keys or private information in this project.\n"
                    + "On a public repository, uploaded source code is visible to everyone.\n"
                )
