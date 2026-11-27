"""Offline blueprint analysis and generated-feature verification for IDEA2APK V3."""
import ast
import re

ALIASES = {
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

TEMPLATE_FEATURE_CHECKS = {
    "shop_inventory": FEATURE_SOURCE_CHECKS,
    "expense_tracker": EXPENSE_TRACKER_SOURCE_CHECKS,
    "school_records": SCHOOL_RECORDS_SOURCE_CHECKS,
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
    text = re.sub(r"\s+", " ", str(value or "").strip().lower())
    text = text.replace("_", " ").replace("-", " ")
    return ALIASES.get(text, text.replace(" ", "_"))


def analyze_blueprint(data):
    """Return requested features and template candidates, not completion claims."""
    data = data if isinstance(data, dict) else {}
    requested = []
    for item in split_requested_features(data.get("features", [])):
        feature = canonical_feature(item)
        if feature not in requested:
            requested.append(feature)
    template_id = str(data.get("template_id") or "shop_inventory")
    available = set(TEMPLATE_FEATURE_CHECKS.get(template_id, {}))
    return {
        "template_id": template_id,
        "requested": requested,
        "available": [item for item in requested if item in available],
        "unsupported": [item for item in requested if item not in available],
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
