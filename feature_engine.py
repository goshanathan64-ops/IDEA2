"""Offline blueprint analysis and generated-feature verification for IDEA2APK V3."""
import ast
import re

ALIASES = {
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
    available = set(FEATURE_SOURCE_CHECKS) if template_id == "shop_inventory" else set()
    return {
        "template_id": template_id,
        "requested": requested,
        "available": [item for item in requested if item in available],
        "unsupported": [item for item in requested if item not in available],
        "ready": template_id == "shop_inventory",
    }


def validate_feature_coverage(source, requested_features):
    """Verify requested features by checking their implementation fingerprints."""
    implemented, missing = [], []
    for feature in requested_features:
        checks = FEATURE_SOURCE_CHECKS.get(feature)
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
