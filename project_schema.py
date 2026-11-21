"""Versioned project data and validation for IDEA2APK V3.

The schema deliberately accepts the legacy V2 keys so existing saved projects
can be loaded and upgraded without discarding user data.
"""
import copy

SCHEMA_VERSION = 1

LEGACY_REQUIRED_FIELDS = ("id", "name", "description", "target", "app_type", "features")


def normalize_project(project):
    if not isinstance(project, dict):
        raise TypeError("Project must be a dictionary.")

    result = copy.deepcopy(project)
    for key in LEGACY_REQUIRED_FIELDS:
        result.setdefault(key, "")

    result["schema_version"] = SCHEMA_VERSION
    result.setdefault("category", result.get("app_type", "business") or "business")
    result.setdefault("template_id", "shop_inventory")
    result.setdefault("build_status", "not_built")
    return result


def validate_project(project):
    """Return (errors, warnings); warnings never silently imply support."""
    errors = []
    warnings = []

    if not isinstance(project, dict):
        return ["Project data must be an object."], []

    name = str(project.get("name", "")).strip()
    if not name:
        errors.append("Enter an app name.")
    elif len(name) > 40:
        errors.append("App name must be 40 characters or fewer.")

    description = str(project.get("description", "")).strip()
    if len(description) > 1000:
        errors.append("Description must be 1,000 characters or fewer.")

    if not str(project.get("id", "")).strip():
        errors.append("Project ID is missing.")

    if not str(project.get("app_type", project.get("category", ""))).strip():
        warnings.append("App category has not been selected.")

    if not str(project.get("features", "")).strip():
        warnings.append("No requested features have been listed.")

    return errors, warnings
