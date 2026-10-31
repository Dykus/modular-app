"""Zasevka sistemyh roley, sid-admina, prav po umolchaniyu i testovogo chitatelya."""
import json
from core.app import db
from core.auth import hash_password
from core.models import Role, RolePermission, User
from modules.settings.models import Setting

SYSTEM_ROLES = [
    ("admin",   "Администратор — полный доступ, нельзя удалить", True,
     ["auth.manage_users", "auth.manage_roles", "auth.security"]),
    ("manager", "Руководитель — управляет данными и справкой", True, []),
    ("staff",   "Сотрудник — подаёт задачи, читает остальное", True, []),
    ("viewer",  "Наблюдатель — только просмотр", True, []),
]

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
    role_map = {}
    for name, desc, is_sys, imm in SYSTEM_ROLES:
        r = Role.query.filter_by(name=name).first()
        if not r:
            r = Role(name=name, description=desc, is_system=is_sys,
                     immutable_perms=json.dumps(imm, ensure_ascii=False))
            db.session.add(r)
            db.session.flush()
        role_map[name] = r

    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(
            username="admin", full_name="Администратор",
            password_hash=hash_password("admin123"),
            role_id=role_map["admin"].id, auth_source="local",
            is_active=True, must_change_password=True,
        )
        db.session.add(admin)
    db.session.commit()

    marker = Setting.query.get("role_defaults_seeded")
    if marker is None or marker.value != "1":
        for rolename, codes in DEFAULT_ROLE_PERMS.items():
            r = role_map.get(rolename)
            if not r:
                continue
            if RolePermission.query.filter_by(role_id=r.id).count() == 0:
                for c in codes:
                    db.session.add(RolePermission(role_id=r.id, perm=c))
        db.session.add(Setting(key="role_defaults_seeded", value="1"))
    db.session.commit()

    tv = User.query.filter_by(username="test_viewer").first()
    if not tv:
        tv = User(
            username="test_viewer", full_name="Тестовый наблюдатель",
            password_hash=hash_password("test1234"),
            role_id=role_map["viewer"].id, auth_source="local",
            is_active=True, must_change_password=False,
        )
        db.session.add(tv)
        db.session.commit()
