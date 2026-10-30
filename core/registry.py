"""Reestr dostupnyh moduley."""

AVAILABLE_MODULES = [
    {"key": "feedback",   "name": "Задачи отдела",
     "endpoint": "feedback.list_items",
     "import_path": "modules.feedback.routes",   "bp_attr": "feedback_bp"},
    {"key": "production", "name": "Производство",
     "endpoint": "production.index",
     "import_path": "modules.production.routes", "bp_attr": "production_bp"},
]
SYSTEM_MODULE_KEYS = ["settings"]
