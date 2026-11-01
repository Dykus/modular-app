"""Reestr moduley: bazovye + avtonaidennye po pasportu module.json.

Mehanizm plug-and-play: lyubaya papka v modules/, v kotoroy lezhit
module.json, avtomaticheski stanovitsya modulem. Pravki yadra ne nuzhny.
Papki, nachinayushchiesya s podcherkivaniya (naprimer _template), ignoriruyutsya.
"""
import os, json

BASE_MODULES = [
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
    {"key": "manual",     "name": "Руководство",
     "endpoint": "manual.index",
     "import_path": "modules.manual.routes",     "bp_attr": "manual_bp"},
]

def _scan_passports():
    """Prohodit po modules/ i chitaet module.json u kazhdoy papki."""
    found = []
    mdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "modules")
    if not os.path.isdir(mdir):
        return found
    for name in sorted(os.listdir(mdir)):
        if name.startswith("_"):
            continue
        p = os.path.join(mdir, name, "module.json")
        if not os.path.isfile(p):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            key = (d.get("key") or name).strip()
            found.append({
                "key": key,
                "name": d.get("name") or key,
                "endpoint": d.get("endpoint") or (key + ".index"),
                "import_path": d.get("import_path") or ("modules." + key + ".routes"),
                "bp_attr": d.get("bp_attr") or (key + "_bp"),
                "passport": d,
            })
        except Exception as e:
            print("PREDUPREZHDENIE: module.json v papke %s ne prochitan: %s" % (name, e))
    return found

def get_available_modules():
    mods = [dict(m) for m in BASE_MODULES]
    keys = {m["key"] for m in mods}
    for m in _scan_passports():
        if m["key"] not in keys:
            mods.append(m)
            keys.add(m["key"])
    return mods

AVAILABLE_MODULES = get_available_modules()
SYSTEM_MODULE_KEYS = ["settings"]
