"""Transparent starter-template catalogue for IDEA2APK V3.

Only templates that have a working generator are marked ready.
"""
TEMPLATES = [
    {
        "id": "shop_inventory",
        "name": "Shop & Inventory",
        "category": "business",
        "status": "ready",
        "description": "Products, stock, sales, customers, expenses and basic reports.",
        "supported_features": [
            "product_catalogue", "stock_tracking", "record_sales",
            "customer_records", "expense_records", "basic_reports",
            "local_sqlite_storage"
        ],
        "unsupported_features": [
            "online_payments", "cloud_sync", "multi_user_login",
            "live_delivery_tracking"
        ],
    },
    {
        "id": "school_records",
        "name": "School Records",
        "category": "education",
        "status": "planned",
        "description": "Student profiles, attendance, classes and results.",
        "supported_features": [],
        "unsupported_features": [],
    },
    {
        "id": "expense_tracker",
        "name": "Expense Tracker",
        "category": "finance",
        "status": "ready",
        "description": "Offline income and expense records, categories, USD/ZiG totals, transaction history and balance summaries.",
        "supported_features": [
            "income_records", "expense_records", "category_tracking",
            "currency_support", "basic_reports", "local_sqlite_storage",
            "transaction_history"
        ],
        "unsupported_features": [
            "budgets", "recurring_transactions", "cloud_sync",
            "bank_connections", "multi_user_login"
        ],
    },
    {
        "id": "booking_appointments",
        "name": "Booking & Appointments",
        "category": "services",
        "status": "planned",
        "description": "Bookings, schedules, customer details and reminders.",
        "supported_features": [],
        "unsupported_features": [],
    },
    {
        "id": "task_manager",
        "name": "Task Manager",
        "category": "productivity",
        "status": "planned",
        "description": "Tasks, due dates, priorities and completion tracking.",
        "supported_features": [],
        "unsupported_features": [],
    },
    {
        "id": "customer_manager",
        "name": "Customer Manager",
        "category": "business",
        "status": "planned",
        "description": "Customer profiles, contact details and follow-ups.",
        "supported_features": [],
        "unsupported_features": [],
    },
]


def list_templates():
    return [dict(item) for item in TEMPLATES]


def get_template(template_id):
    for item in TEMPLATES:
        if item["id"] == template_id:
            return dict(item)
    return None


def template_support_report(template_id, requested_features=None):
    template = get_template(template_id)
    if template is None:
        return {
            "known_template": False,
            "ready": False,
            "supported": [],
            "unsupported": list(requested_features or []),
        }

    requested = [str(item).strip().lower() for item in (requested_features or [])]
    supported_set = set(template["supported_features"])
    supported = [item for item in requested if item in supported_set]
    unsupported = [item for item in requested if item not in supported_set]
    return {
        "known_template": True,
        "ready": template["status"] == "ready",
        "supported": supported,
        "unsupported": unsupported,
    }



def blueprint_support_report(data):
    """Summarize the selected template's real feature support for blueprint review."""
    from feature_engine import analyze_blueprint

    plan = analyze_blueprint(data)
    template = get_template(plan["template_id"])
    return {
        "template_name": template["name"] if template else plan["template_id"],
        "readiness": "READY" if plan["ready"] else "NOT READY",
        "requested": list(plan["requested"]),
        "supported": list(plan["available"]),
        "unsupported": list(plan["unsupported"]),
    }
