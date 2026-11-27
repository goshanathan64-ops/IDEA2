"""Offline blueprint analysis and generated-source validation for IDEA2APK V3.

This module is deliberately deterministic: it maps user wording to known
feature identifiers and reports unsupported requests without claiming to
generate them.
"""
import ast
import re

ALIASES = {
    "products": "product_catalogue",
    "product catalogue": "product_catalogue",
    "product catalog": "product_catalogue",
    "inventory": "stock_tracking",
    "stock": "stock_tracking",
    "stock management": "stock_tracking",
    "sales": "record_sales",
    "record sale": "record_sales",
    "customers": "customer_records",
    "customer management": "customer_records",
    "expenses": "expense_records",
    "expense tracking": "expense_records",
    "reports": "basic_reports",
    "business reports": "basic_reports",
    "offline": "local_sqlite_storage",
    "local storage": "local_sqlite_storage",
    "local data storage": "local_sqlite_storage",
    "usd and zig support": "currency_support",
    "usd/zig currency support": "currency_support",
    "separate currency transactions": "currency_support",
    "currency support": "currency_support",
    "cost price tracking": "cost_price_tracking",
    "product cost prices": "cost_price_tracking",
    "profit/loss summaries": "profit_loss_reports",
    "profit and loss summaries": "profit_loss_reports",
    "profit reports": "profit_loss_reports",
}

SHOP_SUPPORTED = {
    "product_catalogue",
    "stock_tracking",
    "record_sales",
    "customer_records",
    "expense_records",
    "basic_reports",
    "local_sqlite_storage",
    "currency_support",
    "cost_price_tracking",
    "profit_loss_reports",
}


def split_requested_features(value):
    """Accept comma/newline/bullet/semicolon-separated blueprint features."""
    if isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        raw_items = re.split(r"[,;\n]+", str(value or ""))
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
    """Return a transparent, deterministic feature plan for a project."""
    data = data if isinstance(data, dict) else {}
    requested = split_requested_features(data.get("features", []))
    canonical = []
    for item in requested:
        feature = canonical_feature(item)
        if feature not in canonical:
            canonical.append(feature)

    template_id = str(data.get("template_id") or "shop_inventory")
    supported_set = SHOP_SUPPORTED if template_id == "shop_inventory" else set()
    supported = [item for item in canonical if item in supported_set]
    unsupported = [item for item in canonical if item not in supported_set]
    return {
        "template_id": template_id,
        "requested": canonical,
        "supported": supported,
        "unsupported": unsupported,
        "ready": template_id == "shop_inventory",
    }


def validate_generated_source(source):
    """Compile generated Python and return structured validation results."""
    if not isinstance(source, str) or not source.strip():
        return {"valid": False, "errors": ["Generated source is empty."]}
    try:
        ast.parse(source)
    except SyntaxError as error:
        return {
            "valid": False,
            "errors": ["Python syntax error at line {}: {}".format(
                error.lineno, error.msg
            )],
        }
    return {"valid": True, "errors": []}
