"""Offline advisory blueprint review. Deterministic; no paid API or network."""
import re

CORE_FIELDS = ("name", "description", "target", "template_id")
FIELD_LABELS = {"name": "App name", "description": "App description", "target": "Target users", "template_id": "App template"}

def _clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()

def analyze_blueprint_intelligence(data, feature_analysis=None):
    """Return completeness, confidence, missing info, issues, and suggestions."""
    data = data if isinstance(data, dict) else {}
    missing = [field for field in CORE_FIELDS if not _clean(data.get(field))]
    issues, recommendations, warnings = [], [], []
    if "name" in missing: recommendations.append("Give the app a short, recognizable name.")
    if "description" in missing: recommendations.append("Describe the app purpose and main workflow.")
    if "target" in missing: recommendations.append("Name the people who will use the app.")
    if "template_id" in missing: warnings.append("No template selected; the default may be used.")
    if feature_analysis:
        unsupported = list(feature_analysis.get("unsupported", []))
        if unsupported:
            issues.append({"type":"unsupported_features","severity":"warning","items":unsupported,"message":"Some requested features are not supported by this template yet."})
            recommendations.append("Review unsupported features and remove them or select a compatible template.")
        if not feature_analysis.get("ready", True):
            issues.append({"type":"unknown_template","severity":"error","items":[str(data.get("template_id") or "unknown"),],"message":"The selected template is not recognized by the current generator."})
    if _clean(data.get("description")) and not _clean(data.get("features")) and not data.get("feature_selection_locked"):
        issues.append({"type":"no_features_listed","severity":"info","items":[],"message":"No feature list; the engine may infer features from the description."})
        recommendations.append("List the key screens or actions for more predictable generation.")
    app_type, template = _clean(data.get("app_type")).lower(), _clean(data.get("template_id")).lower()
    hints = {"school":("school_records",),"education":("school_records",),"booking":("booking_appointments",),"appointment":("booking_appointments",),"task":("task_manager",),"customer":("customer_manager",),"expense":("expense_tracker",),"shop":("shop_inventory",),"business":("shop_inventory","expense_tracker","customer_manager")}
    hinted = hints.get(app_type)
    if hinted and template and template not in hinted:
        issues.append({"type":"app_type_template_mismatch","severity":"warning","items":[app_type,template],"message":"App type and template may not match; review this choice."})
        recommendations.append("Confirm that the selected template matches the app purpose.")
    weights = {"name":20,"description":35,"target":25,"template_id":20}
    completeness = sum(weight for field, weight in weights.items() if field not in missing)
    confidence = "HIGH" if completeness >= 90 and not any(i["severity"] == "error" for i in issues) else "MEDIUM" if completeness >= 60 else "LOW"
    return {"completeness":completeness,"confidence":confidence,"missing_fields":missing,"missing_labels":[FIELD_LABELS[f] for f in missing],"issues":issues,"recommendations":list(dict.fromkeys(recommendations)),"warnings":warnings,"ready_for_review":True,"note":"Offline advisory analysis; not a substitute for feature checks, APK builds, or device testing."}


def render_blueprint_intelligence_summary(report):
    """Format intelligence findings for the mobile blueprint-review panel."""
    report = report or {}
    lines = [
        "BLUEPRINT INTELLIGENCE — {}% COMPLETE / {} CONFIDENCE".format(
            report.get("completeness", 0), report.get("confidence", "LOW")
        ),
    ]
    missing = report.get("missing_labels", [])
    lines.append("MISSING: " + (", ".join(missing) if missing else "None"))
    for issue in report.get("issues", []):
        lines.append("{}: {}".format(issue.get("severity", "info").upper(), issue.get("message", "Review note")))
    for warning in report.get("warnings", []):
        lines.append("NOTE: " + warning)
    for suggestion in report.get("recommendations", []):
        lines.append("SUGGESTION: " + suggestion)
    return "\n".join(lines)


# Template-aware, offline suggestions. These never alter a user's blueprint.
IMPROVEMENT_PRIORITIES = {
    "shop_inventory": ["product_catalogue", "stock_tracking", "record_sales", "basic_reports", "local_sqlite_storage"],
    "school_records": ["student_records", "attendance_tracking", "results_records", "basic_reports", "local_sqlite_storage"],
    "expense_tracker": ["income_records", "expense_records", "currency_support", "transaction_history", "basic_reports"],
    "booking_appointments": ["booking_records", "appointment_scheduling", "booking_status", "booking_history", "local_sqlite_storage"],
    "task_manager": ["task_records", "due_dates", "priority_levels", "completion_tracking", "task_search"],
    "customer_manager": ["customer_profiles", "contact_details", "follow_up_records", "customer_search", "local_sqlite_storage"],
}

IMPROVEMENT_REASONS = {
    "product_catalogue": "Keep product names and details in one catalogue.",
    "stock_tracking": "Track quantities and reduce stock when sales are recorded.",
    "record_sales": "Record each sale so business activity can be reviewed.",
    "basic_reports": "Summarize records for quicker decisions.",
    "local_sqlite_storage": "Keep app records locally on the device for offline use.",
    "student_records": "Keep student profiles and admission details together.",
    "attendance_tracking": "Record daily attendance for each student.",
    "results_records": "Store marks and review student performance.",
    "income_records": "Record money received as well as money spent.",
    "expense_records": "Track spending to understand where money goes.",
    "currency_support": "Separate supported USD and ZiG transaction totals.",
    "transaction_history": "Review past income and expense entries.",
    "booking_records": "Keep a saved record of each booking.",
    "appointment_scheduling": "Set appointment dates and times.",
    "booking_status": "Track whether bookings are scheduled or completed.",
    "booking_history": "Review previous bookings.",
    "task_records": "Create and save individual tasks.",
    "due_dates": "Give tasks deadlines to help organize work.",
    "priority_levels": "Mark important tasks as high, medium, or low priority.",
    "completion_tracking": "Mark tasks complete and distinguish them from pending work.",
    "task_search": "Find saved tasks more quickly.",
    "customer_profiles": "Keep each customer's details in a dedicated profile.",
    "contact_details": "Store useful phone, email, and address details.",
    "follow_up_records": "Save planned customer follow-ups.",
    "customer_search": "Find customer records by their details.",
}


def recommend_blueprint_improvements(data, feature_analysis=None, limit=3):
    """Suggest useful, supported features without changing the user's selections."""
    data = data if isinstance(data, dict) else {}
    template_id = _clean(data.get("template_id")).lower()
    priorities = IMPROVEMENT_PRIORITIES.get(template_id, [])
    if not priorities:
        return []
    try:
        from feature_engine import canonical_feature, split_requested_features
        raw = data.get("features", [])
        existing = {canonical_feature(item) for item in split_requested_features(raw)}
        if feature_analysis:
            existing.update(canonical_feature(item) for item in feature_analysis.get("requested", []))
        from template_catalog import get_template
        template = get_template(template_id)
        supported = set(template.get("supported_features", [])) if template else set()
    except Exception:
        return []
    suggestions = []
    for feature in priorities:
        if feature in supported and feature not in existing:
            suggestions.append({
                "feature": feature,
                "reason": IMPROVEMENT_REASONS.get(feature, "This feature may improve the app workflow."),
            })
        if len(suggestions) >= max(0, int(limit)):
            break
    return suggestions


def render_blueprint_improvements(suggestions):
    """Format optional improvements for the blueprint-review screen."""
    if not suggestions:
        return "OPTIONAL IMPROVEMENTS: No additional template recommendations."
    lines = ["OPTIONAL IMPROVEMENTS — REVIEW BEFORE ADDING"]
    for item in suggestions:
        lines.append("+ " + item["feature"] + ": " + item["reason"])
    return "\\n".join(lines)
