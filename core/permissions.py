"""Reestr prav: sbiraet prava iz vseh moduley v odin obschiy spisok.

Pravo - metka vida "modul.deystvie". Kazhdy modul ob'yavlyaet svoi prava
v fayle modules/<imya>/perms.py (spisok PERMISSIONS). Funkciya collect()
prohodit po vsem modulam iz registry.py i skladivaet vse v slovari:
  ALL_PERMS    = {kod: (gruppa, chelovecheskoe opisanie)}
  PERM_GROUPS  = [gruppy v poryadke dlya UI]
  MODULE_PERMS = {kluch modulya: [kody ego prav]}
"""
import importlib

ALL_PERMS = {}
PERM_GROUPS = []
MODULE_PERMS = {}

# Sistemnye prava dostupa: ne prinadlezhat modulym-vkladkam, no bez nih
# nelzya upravlyat' lyud'mi, rolyami i bezopasnostyu.
AUTH_PERMS = [
    ("auth.manage_users", "Доступ",
     "Создавать, редактировать и блокировать пользователей"),
    ("auth.manage_roles", "Доступ",
     "Создавать роли и назначать им права (галочки)"),
    ("auth.security", "Доступ",
     "Менять безопасность: включать/выключать авторизацию, пороги блокировки"),
]

def collect():
    """Sobiraet vse prava. Vyzivaetsya odin raz pri zapuske iz core/app.py."""
    global ALL_PERMS, PERM_GROUPS, MODULE_PERMS
    ALL_PERMS = {}
    PERM_GROUPS = []
    MODULE_PERMS = {}

    from core.registry import AVAILABLE_MODULES
    for m in AVAILABLE_MODULES:
        key = m["key"]
        codes = []
        try:
            mod = importlib.import_module("modules.%s.perms" % key)
        except ModuleNotFoundError:
            mod = None
        except Exception as e:
            # Zashchita: bitoy perms.py odnogo modulya ne valit vse prilozhenie.
            print("PREDUPREZHDENIE: ne smog prochitat' modules/%s/perms.py: %s" % (key, e))
            print("  Modul poluchit pustoi nabor prav, poka fayl ne pochinyat.")
            mod = None
        for code, group, desc in (getattr(mod, "PERMISSIONS", []) if mod else []):
            if code not in ALL_PERMS:
                ALL_PERMS[code] = (group, desc)
            if group not in PERM_GROUPS:
                PERM_GROUPS.append(group)
            codes.append(code)
        MODULE_PERMS[key] = codes

    for code, group, desc in AUTH_PERMS:
        if code not in ALL_PERMS:
            ALL_PERMS[code] = (group, desc)
        if group not in PERM_GROUPS:
            PERM_GROUPS.append(group)
    MODULE_PERMS["auth"] = [c for c, _, _ in AUTH_PERMS]
