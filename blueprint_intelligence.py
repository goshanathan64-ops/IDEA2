"""Offline advisory blueprint review. Deterministic; no paid API or network."""
import re

CORE_FIELDS = ("name", "description", "target", "template_id")
FIELD_LABELS = {"name": "App name", "description": "App description", "target": "Target users", "template_id": "App template"}

def _clean(value):
    return re.sub(r"\\s+", " ", str(value or "")).strip()

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
