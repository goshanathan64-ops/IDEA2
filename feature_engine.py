"""Offline blueprint analysis and generated-feature verification for IDEA2APK V3."""
import ast
import re

ALIASES = {
    "customer profiles": "customer_profiles", "customer profile": "customer_profiles",
    "customer records": "customer_profiles", "client profiles": "customer_profiles",
    "contact details": "contact_details", "phone numbers": "contact_details",
    "phone and email": "contact_details", "customer contact information": "contact_details",
    "customer notes": "customer_notes", "notes for customers": "customer_notes",
    "follow ups": "follow_up_records", "follow-ups": "follow_up_records",
    "follow up records": "follow_up_records", "customer follow ups": "follow_up_records",
    "follow up tracking": "follow_up_tracking", "follow-up tracking": "follow_up_tracking",
    "follow up reminders": "follow_up_tracking", "customer follow up history": "follow_up_tracking",
    "search customers": "customer_search", "customer search": "customer_search",
    "tasks": "task_records", "task": "task_records", "task records": "task_records",
    "create tasks": "task_records", "add tasks": "task_records",
    "deadlines": "due_dates", "due date": "due_dates", "due dates": "due_dates", "task deadlines": "due_dates",
    "priority": "priority_levels", "priorities": "priority_levels", "task priorities": "priority_levels",
    "high medium low priority": "priority_levels",
    "completion": "completion_tracking", "completion tracking": "completion_tracking",
    "mark tasks complete": "completion_tracking", "task completion": "completion_tracking",
    "task categories": "task_categories", "categories for tasks": "task_categories",
    "task search": "task_search", "search tasks": "task_search",
    "bookings": "booking_records", "booking": "booking_records",
    "booking records": "booking_records", "make bookings": "booking_records",
    "appointments": "appointment_scheduling", "appointment scheduling": "appointment_scheduling",
    "schedule appointments": "appointment_scheduling", "appointment calendar": "appointment_scheduling",
    "customer details": "customer_details", "client details": "customer_details",
    "customer contact details": "customer_details",
    "booking status": "booking_status", "appointment status": "booking_status",
    "booking history": "booking_history", "appointment history": "booking_history",
    "upcoming appointments": "appointment_scheduling",
    "students": "student_records", "student records": "student_records", "student profiles": "student_records",
    "classes": "class_management", "class management": "class_management", "class records": "class_management",
    "attendance": "attendance_tracking", "attendance tracking": "attendance_tracking",
    "student attendance": "attendance_tracking", "exam results": "results_records",
    "student results": "results_records", "marks": "results_records", "results": "results_records",
    "income": "income_records", "income records": "income_records", "record income": "income_records",
    "transaction history": "transaction_history", "history": "transaction_history",
    "categories": "category_tracking", "category tracking": "category_tracking",
    "products": "product_catalogue", "product catalogue": "product_catalogue",
    "product catalog": "product_catalogue", "inventory": "stock_tracking",
    "stock": "stock_tracking", "stock management": "stock_tracking",
    "sales": "record_sales", "record sale": "record_sales",
    "customers": "customer_records", "customer management": "customer_records",
    "expenses": "expense_records", "expense tracking": "expense_records",
    "reports": "basic_reports", "business reports": "basic_reports",
    "offline": "local_sqlite_storage", "local storage": "local_sqlite_storage",
    "local data storage": "local_sqlite_storage",
    "usd and zig support": "currency_support", "usd/zig currency support": "currency_support",
    "separate currency transactions": "currency_support", "currency support": "currency_support",
    "cost price tracking": "cost_price_tracking", "product cost prices": "cost_price_tracking",
    "profit/loss summaries": "profit_loss_reports",
    "profit and loss summaries": "profit_loss_reports", "profit reports": "profit_loss_reports",
    # Plain-language requests commonly entered by first-time app builders.
    "add products": "product_catalogue", "manage products": "product_catalogue",
    "product list": "product_catalogue", "inventory tracking": "stock_tracking",
    "stock levels": "stock_tracking", "manage stock": "stock_tracking",
    "sell products": "record_sales", "sales recording": "record_sales",
    "sales history": "record_sales", "manage customers": "customer_records",
    "customer list": "customer_records", "record expenses": "expense_records",
    "daily reports": "basic_reports", "monthly reports": "basic_reports",
    "usd zig": "currency_support", "usd/zig": "currency_support",
    "usd and zig balances": "currency_support", "usd zig balances": "currency_support",
    "local database": "local_sqlite_storage",
    "admission numbers": "student_records", "class lists": "class_management",
    "record attendance": "attendance_tracking", "daily attendance": "attendance_tracking",
    "subject marks": "results_records", "exam marks": "results_records",
    "school summaries": "basic_reports", "track income": "income_records",
    "income tracking": "income_records", "expense categories": "category_tracking",
    "spending categories": "category_tracking", "account balance": "basic_reports",
    "appointment date and time": "appointment_scheduling",
    "appointment duration": "appointment_scheduling", "booking calendar": "appointment_scheduling",
    "booking status updates": "booking_status", "appointment history": "booking_history",
    "task title": "task_records", "task description": "task_records",
    "task deadline": "due_dates", "task priority": "priority_levels",
    "mark as completed": "completion_tracking", "mark completed": "completion_tracking",
    "search and filter tasks": "task_search",
    "phone and email contacts": "contact_details", "customer address": "contact_details",
    "follow up dates": "follow_up_records", "follow-up dates": "follow_up_records",
    "follow up status": "follow_up_tracking", "follow-up status": "follow_up_tracking",
    "search customer records": "customer_search",
}

# Fingerprints must all be present before a requested feature is reported as generated.
FEATURE_SOURCE_CHECKS = {
    "product_catalogue": ("CREATE TABLE IF NOT EXISTS products", "def show_products"),
    "stock_tracking": ("quantity INTEGER", "def _save_sale", "quantity=quantity-?"),
    "record_sales": ("CREATE TABLE IF NOT EXISTS sales", "INSERT INTO sales", "def record_sale"),
    "customer_records": ("CREATE TABLE IF NOT EXISTS customers", "def _save_customer", "def show_customers"),
    "expense_records": ("CREATE TABLE IF NOT EXISTS expenses", "def _save_expense", "def show_expense_history"),
    "basic_reports": ("def show_reports", "def _get_period_totals"),
    "local_sqlite_storage": ("sqlite3.connect", "self.user_data_dir"),
    "currency_support": ("currency TEXT", "currency='USD'", '"ZIG"'),
    "cost_price_tracking": ("cost_price", "unit_cost"),
    "profit_loss_reports": ("gross_profit", "net_result_known_costs"),
}

EXPENSE_TRACKER_SOURCE_CHECKS = {
    "income_records": ("def add_income", "self._save_transaction('income', values)"),
    "expense_records": ("def add_expense", "self._save_transaction('expense', values)"),
    "category_tracking": ("category TEXT", '"category"'),
    "currency_support": ('"USD"', '"ZIG"', "currency TEXT"),
    "basic_reports": ("def _get_summary", "def show_summary"),
    "local_sqlite_storage": ("sqlite3.connect", "self.user_data_dir"),
    "transaction_history": ("def _get_history", "def show_history"),
}

SCHOOL_RECORDS_SOURCE_CHECKS = {
    "student_records": ("CREATE TABLE IF NOT EXISTS students", "def _save_student", "def _get_students"),
    "class_management": ("class_name TEXT", "SELECT COUNT(DISTINCT class_name)"),
    "attendance_tracking": ("CREATE TABLE IF NOT EXISTS attendance", "def _record_attendance", "def _get_attendance"),
    "results_records": ("CREATE TABLE IF NOT EXISTS results", "def _save_result", "def _get_results"),
    "basic_reports": ("def _get_school_summary", "def show_school_summary"),
    "local_sqlite_storage": ("sqlite3.connect", "self.user_data_dir"),
}

CUSTOMER_MANAGER_SOURCE_CHECKS = {
    "customer_profiles": ("CREATE TABLE IF NOT EXISTS customers", "def _save_customer", "def _get_customers"),
    "contact_details": ("phone TEXT DEFAULT ''", "email TEXT DEFAULT ''", "address TEXT DEFAULT ''"),
    "customer_notes": ("notes TEXT DEFAULT ''", "notes LIKE ?"),
    "follow_up_records": ("CREATE TABLE IF NOT EXISTS followups", "def _save_followup", "INSERT INTO followups"),
    "follow_up_tracking": ("def _get_followups", "def _complete_followup", "followup_date<=?"),
    "customer_search": ("def _get_customers", "phone LIKE ?", "email LIKE ?"),
    "basic_reports": ("def _get_summary", "def show_summary"),
    "local_sqlite_storage": ("sqlite3.connect", "self.user_data_dir"),
}

TASK_MANAGER_SOURCE_CHECKS = {
    "task_records": ("CREATE TABLE IF NOT EXISTS tasks", "def _save_task", "INSERT INTO tasks"),
    "due_dates": ("due_date TEXT DEFAULT ''", "def _get_due_tasks", "datetime.strptime(due_date, \"%Y-%m-%d\")"),
    "priority_levels": ("priority TEXT NOT NULL DEFAULT 'medium'", "CHECK(priority IN ('low','medium','high'))"),
    "completion_tracking": ("status TEXT NOT NULL DEFAULT 'pending'", "def _complete_task", "completed_at=CURRENT_TIMESTAMP"),
    "task_categories": ("category TEXT DEFAULT 'General'", "category LIKE ?"),
    "task_search": ("def _get_tasks", "title LIKE ?", "description LIKE ?"),
    "basic_reports": ("def _get_summary", "def show_summary"),
    "local_sqlite_storage": ("sqlite3.connect", "self.user_data_dir"),
}

BOOKING_APPOINTMENTS_SOURCE_CHECKS = {
    "booking_records": ("CREATE TABLE IF NOT EXISTS bookings", "def _save_booking", "INSERT INTO bookings"),
    "appointment_scheduling": ("booking_date TEXT NOT NULL", "def _get_upcoming", "datetime.strptime(day + \" \" + clock"),
    "customer_details": ("customer_name TEXT NOT NULL", "phone TEXT DEFAULT ''"),
    "booking_status": ("status TEXT NOT NULL DEFAULT 'scheduled'", "def _update_booking_status"),
    "booking_history": ("def _get_history", "def show_history"),
    "basic_reports": ("def _get_summary", "def show_summary"),
    "local_sqlite_storage": ("sqlite3.connect", "self.user_data_dir"),
}

TEMPLATE_FEATURE_CHECKS = {
    "shop_inventory": FEATURE_SOURCE_CHECKS,
    "expense_tracker": EXPENSE_TRACKER_SOURCE_CHECKS,
    "school_records": SCHOOL_RECORDS_SOURCE_CHECKS,
    "booking_appointments": BOOKING_APPOINTMENTS_SOURCE_CHECKS,
    "task_manager": TASK_MANAGER_SOURCE_CHECKS,
    "customer_manager": CUSTOMER_MANAGER_SOURCE_CHECKS,
}



def split_requested_features(value):
    """Accept comma/newline/bullet/semicolon-separated blueprint features."""
    raw_items = list(value) if isinstance(value, (list, tuple, set)) else re.split(r"[,;\n]+", str(value or ""))
    cleaned = []
    for item in raw_items:
        item = re.sub(r"^\s*[-*•\d.)]+\s*", "", str(item)).strip().lower()
        if item:
            cleaned.append(item)
    return cleaned


def canonical_feature(value):
    """Normalize a feature phrase and map common natural-language synonyms."""
    text = str(value or "").strip().lower()
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"[\t\r\n]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^[\W_]+|[\W_]+$", "", text)
    if text in ALIASES:
        return ALIASES[text]
    # Treat harmless punctuation variants consistently without guessing intent.
    compact = re.sub(r"[^a-z0-9 ]+", " ", text)
    compact = re.sub(r"\s+", " ", compact).strip()
    # Keep the user's original punctuation in unknown feature labels for clear diagnostics.
    return ALIASES.get(compact, text.replace(" ", "_"))


DESCRIPTION_FEATURE_HINTS = {
    "shop_inventory": [
        ("products", "product_catalogue"), ("inventory", "stock_tracking"),
        ("stock", "stock_tracking"), ("sales", "record_sales"),
        ("customers", "customer_records"), ("expenses", "expense_records"),
        ("reports", "basic_reports"), ("offline", "local_sqlite_storage"),
        ("usd and zig", "currency_support"), ("usd/zig", "currency_support"),
        ("cost price", "cost_price_tracking"), ("profit and loss", "profit_loss_reports"),
    ],
    "school_records": [
        ("students", "student_records"), ("admission numbers", "student_records"),
        ("classes", "class_management"), ("attendance", "attendance_tracking"),
        ("marks", "results_records"), ("exam results", "results_records"),
        ("school reports", "basic_reports"), ("offline", "local_sqlite_storage"),
    ],
    "expense_tracker": [
        ("income", "income_records"), ("expenses", "expense_records"),
        ("categories", "category_tracking"), ("transactions", "transaction_history"),
        ("transaction history", "transaction_history"), ("usd", "currency_support"),
        ("zig", "currency_support"), ("balance", "basic_reports"),
        ("reports", "basic_reports"), ("offline", "local_sqlite_storage"),
    ],
    "booking_appointments": [
        ("bookings", "booking_records"), ("appointments", "appointment_scheduling"),
        ("appointment date", "appointment_scheduling"), ("customer details", "customer_details"),
        ("booking status", "booking_status"), ("booking history", "booking_history"),
        ("reports", "basic_reports"), ("offline", "local_sqlite_storage"),
    ],
    "task_manager": [
        ("tasks", "task_records"), ("deadlines", "due_dates"),
        ("due dates", "due_dates"), ("priority", "priority_levels"),
        ("completed", "completion_tracking"), ("categories", "task_categories"),
        ("search", "task_search"), ("reports", "basic_reports"),
        ("offline", "local_sqlite_storage"),
    ],
    "customer_manager": [
        ("customers", "customer_profiles"), ("phone", "contact_details"),
        ("email", "contact_details"), ("address", "contact_details"),
        ("notes", "customer_notes"), ("follow up", "follow_up_records"),
        ("follow-up", "follow_up_records"), ("search", "customer_search"),
        ("reports", "basic_reports"), ("offline", "local_sqlite_storage"),
    ],
}


def infer_features_from_description(description, template_id):
    """Conservatively infer only known template features from explicit keywords."""
    text = re.sub(r"\\s+", " ", str(description or "").lower())
    inferred = []
    for phrase, feature in DESCRIPTION_FEATURE_HINTS.get(template_id, []):
        pattern = r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])"
        if re.search(pattern, text) and feature not in inferred:
            inferred.append(feature)
    return inferred


def analyze_blueprint(data):
    """Return explicit and description-inferred features without hiding unsupported requests."""
    data = data if isinstance(data, dict) else {}
    explicit = []
    for item in split_requested_features(data.get("features", [])):
        feature = canonical_feature(item)
        if feature not in explicit:
            explicit.append(feature)
    template_id = str(data.get("template_id") or "shop_inventory")
    inferred = [
        feature for feature in infer_features_from_description(
            data.get("description", ""), template_id
        )
        if feature not in explicit
    ]
    requested = explicit + inferred
    available = set(TEMPLATE_FEATURE_CHECKS.get(template_id, {}))
    supported = [item for item in requested if item in available]
    unsupported = [item for item in requested if item not in available]
    return {
        "template_id": template_id,
        "requested": requested,
        "explicit": explicit,
        "inferred": inferred,
        "available": supported,
        "unsupported": unsupported,
        "feature_status": [
            {
                "feature": item,
                "source": "description" if item in inferred else "features",
                "status": "available" if item in available else "unsupported",
                "reason": (
                    "Recognized for the selected template; verify it matches your intention."
                    if item in inferred else
                    "This feature has a generator check for the selected template."
                    if item in available else
                    "This feature is not currently implemented for the selected template."
                ),
            }
            for item in requested
        ],
        "ready": template_id in TEMPLATE_FEATURE_CHECKS,
    }


FEATURE_DEPENDENCIES = {
    "stock_tracking": ("product_catalogue",),
    "record_sales": ("product_catalogue", "stock_tracking"),
}


def select_generated_features(requested_features):
    """Expand required dependencies and default to the complete ready template."""
    requested = list(dict.fromkeys(requested_features or []))
    if not requested:
        return list(FEATURE_SOURCE_CHECKS)
    selected = list(requested)
    changed = True
    while changed:
        changed = False
        for feature in list(selected):
            for dependency in FEATURE_DEPENDENCIES.get(feature, ()):
                if dependency not in selected:
                    selected.append(dependency)
                    changed = True
    return [feature for feature in FEATURE_SOURCE_CHECKS if feature in selected]


def validate_feature_coverage(source, requested_features, template_id="shop_inventory"):
    """Verify requested features against the selected template fingerprints."""
    implemented, missing = [], []
    checks_by_feature = TEMPLATE_FEATURE_CHECKS.get(template_id, {})
    for feature in requested_features:
        checks = checks_by_feature.get(feature)
        if checks and all(check in source for check in checks):
            implemented.append(feature)
        else:
            missing.append(feature)
    return {"implemented": implemented, "missing": missing, "complete": not missing}


def repair_generated_source(source, requested_features, regenerate_callback=None):
    """Attempt one safe regeneration, then report verified and unresolved features."""
    initial_validation = validate_generated_source(source)
    initial_coverage = validate_feature_coverage(source, requested_features)
    needs_repair = (not initial_validation["valid"]) or bool(initial_coverage["missing"])
    result_source = source
    validation = initial_validation
    coverage = initial_coverage
    attempted = False
    repaired = False
    errors = []

    if needs_repair and callable(regenerate_callback):
        attempted = True
        try:
            candidate = regenerate_callback()
            candidate_validation = validate_generated_source(candidate)
            candidate_coverage = validate_feature_coverage(candidate, requested_features)
            improves_coverage = (
                len(candidate_coverage["implemented"]) >= len(initial_coverage["implemented"])
                and len(candidate_coverage["missing"]) <= len(initial_coverage["missing"])
            )
            if candidate_validation["valid"] and (not initial_validation["valid"] or improves_coverage):
                result_source = candidate
                validation = candidate_validation
                coverage = candidate_coverage
                repaired = candidate != source
            else:
                errors.extend(candidate_validation["errors"])
        except Exception as error:
            errors.append("Regeneration failed: {}".format(error))

    return {
        "source": result_source,
        "attempted": attempted,
        "attempts": 1 if attempted else 0,
        "repaired": repaired,
        "validation": validation,
        "coverage": coverage,
        "unresolved": list(coverage["missing"]),
        "errors": errors,
    }


def validate_generated_source(source):
    """Compile generated Python and return structured validation results."""
    if not isinstance(source, str) or not source.strip():
        return {"valid": False, "errors": ["Generated source is empty."]}
    try:
        ast.parse(source)
    except SyntaxError as error:
        return {"valid": False, "errors": ["Python syntax error at line {}: {}".format(error.lineno, error.msg)]}
    return {"valid": True, "errors": []}
