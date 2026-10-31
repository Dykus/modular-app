"""Reestr prav: sbiraet prava iz vseh moduley v odin obschiy spisok.

Pravo - eta metka vida "modul.deystvie", naprimer "feedback.create"
(umet sozdavat' zadachi) ili "auth.manage_users" (umet upravlyat' lyud'mi).
Sam po sebe pravo nichego ne delayot - eta prosto teGL na dveri. Rol' -
eto spisok takih teGLov, kotorye cheloveku razresheny.

Kazhdy modul peredachaet svoi prava v fayle modules/<imya>/perms.py
(spisok PERMISSIONS). My prohodim po vsem modulam iz registry.py,
chitaem ih PERMISSIONS i skladivaem v obshchie slovari:
  ALL_PERMS    = {kod_prava: (grappa_chelovechitayemaya, opisanie)}
  PERM_GROUPS  = [spisok grupp v poryadke dla UI]
  MODULE_PERMS = {kluch_modulea: [spiski ego prav]}
"""
import importlib

# eti tri slovara napolyayotsya pri zapuske (funkciy collect())
ALL_PERMS = {}
PERM_GROUPS = []
MODULE_PERMS = {}

# Sistemnye prava dostupa - oni ne prinadlezhat nikakomu modulyu-vkladke,
# no bez nih nelzya upravlyat' lyud'mi i rol'yami. Derzhim ih zdes'.
AUTH_PERMS = [
    ("auth.manage_users", "Доступ", "Создавать, редактировать и блокировать пользователей"),
    ("auth.manage_roles", "Доступ", "Создавать роли и назначать им права (галочки)"),
    ("auth.security",     "Доступ", "Менять безопасность: включать/выключать авторизацию, пороги блокировки"),
]

def collect():
    """Sobiraet vse prava. Vyzivaetsya ODN raz pri zapuske iz core/app.py."""
    global ALL_PERMS, PERM_GROUPS, MODULE_PERMS
    ALL_PERMS = {}
    PERM_GROUPS = []
    MODULE_PERMS = {}

    from core.registry import AVAILABLE_MODULES
    for m in AVAILABLE_MODULES:
        key = m["key"]
        codes = []
        # probuem importnut' modules/<key>/perms.py; esli fayla net - propuskaem
        try:
            mod = importlib.import_module("modules.%s.perms" % key)
        except ModuleNotFoundError:
            mod = None
        for code, group, desc in getattr(mod, "PERMISSIONS", []) if mod else []:
            if code not in ALL_PERMS:
                ALL_PERMS[code] = (group, desc)
            if group not in PERM_GROUPS:
                PERM_GROUPS.append(group)
            codes.append(code)
        MODULE_PERMS[key] = codes

    # dobavlyaem sistemnye prava dostupa v konez
    for code, group, desc in AUTH_PERMS:
        if code not in ALL_PERMS:
            ALL_PERMS[code] = (group, desc)
        if group not in PERM_GROUPS:
            PERM_GROUPS.append(group)
    MODULE_PERMS["auth"] = [c for c, _, _ in AUTH_PERMS]
