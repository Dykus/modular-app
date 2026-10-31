"""Reestr dostupnyh moduley."""

AVAILABLE_MODULES = [
    {"key": "feedback",   "name": "Задачи отдела",
     "endpoint": "feedback.list_items",
     "import_path": "modules.feedback.routes",   "bp_attr": "feedback_bp"},
    {"key": "production", "name": "Производство",
     "endpoint": "production.index",
     "import_path": "modules.production.routes", "bp_attr": "production_bp"},
    {"key": "changelog",  "name": "Журнал изменений",
     "endpoint": "changelog.list_entries",
     "import_path": "modules.changelog.routes",  "bp_attr": "changelog_bp"},
    {"key": "versions",   "name": "Версии",
     "endpoint": "versions.list_releases",
     "import_path": "modules.versions.routes",   "bp_attr": "versions_bp"},
    {"key": "help",       "name": "Справка",
     "endpoint": "help.index_articles",
     "import_path": "modules.help.routes",       "bp_attr": "help_bp"},
]
SYSTEM_MODULE_KEYS = ["settings"]
