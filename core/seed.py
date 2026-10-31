"""Zasevka sistemyh roley, sid-admina i prav po umolchaniyu."""
import json
from core.app import db
from core.auth import hash_password
from core.models import Role, RolePermission, User
from modules.settings.models import Setting

# Kakie roli sozdavatsya avtomatom i kakie u nih 'nesnimaemye' prava.
# admin - superuser, yego prava proveryayutsya skvoz' iskuschenie, no
# immutable_perms strahuyut ot sluchainogo udaleniya klyuchevyh prav.
SYSTEM_ROLES = [
    ("admin",   "Administrator - polnyi dostup, nelzya udalit'", True,
     ["auth.manage_users", "auth.manage_roles", "auth.security"]),
    ("manager", "Rukovoditel - upravlyaet dannymi i spravkoi", True, []),
    ("staff",   "Sotrudnik - podaet zadachi, chitaet ostal'noe", True, []),
    ("viewer",  "Nablyudatel - tolko prosmotr", True, []),
]

# Prava po umolchaniyu dlya kazhdoi sistemoi roli (krome admin - on superuser).
# Etot spisok - tvoy start: mozhno menyat' v UI na Shage 2b.
DEFAULT_ROLE_PERMS = {
    "manager": [
        "feedback.view", "feedback.create", "feedback.set_status",
        "changelog.view", "changelog.manage",
        "versions.view", "versions.manage",
        "help.view", "help.manage",
        "settings.view", "settings.manage",
    ],
    "staff": [
        "feedback.view", "feedback.create",
        "changelog.view", "versions.view", "help.view", "settings.view",
    ],
    "viewer": [
        "feedback.view", "changelog.view", "versions.view", "help.view", "settings.view",
    ],
}

def run_seed():
    # 1) roli
    role_map = {}
    for name, desc, is_sys, imm in SYSTEM_ROLES:
        r = Role.query.filter_by(name=name).first()
        if not r:
            r = Role(name=name, description=desc, is_system=is_sys,
                     immutable_perms=json.dumps(imm, ensure_ascii=False))
            db.session.add(r)
            db.session.flush()
        role_map[name] = r

    # 2) sid-admin (tolko esli net)
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(
            username="admin", full_name="Administrator",
            password_hash=hash_password("admin123"),
            role_id=role_map["admin"].id, auth_source="local",
            is_active=True, must_change_password=True,
        )
        db.session.add(admin)
    db.session.commit()

    # 3) dozasev prav po umolchaniyu - ONE raz, zashisheno markerom,
    #    chtoby ne zateret' ruchnue nastroiki posle 2b.
    marker = Setting.query.get("role_defaults_seeded")
    if marker is None or marker.value != "1":
        for rolename, codes in DEFAULT_ROLE_PERMS.items():
            r = role_map.get(rolename)
            if not r:
                continue
            # stavim prava tolko esli u roli ih sychas net vovse
            if RolePermission.query.filter_by(role_id=r.id).count() == 0:
                for c in codes:
                    db.session.add(RolePermission(role_id=r.id, perm=c))
        db.session.add(Setting(key="role_defaults_seeded", value="1"))
    db.session.commit()
