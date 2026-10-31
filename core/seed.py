"""Zasevka sistemnyh roley i sid-admina (vyzyvaetsya iz create_app)"""
import json
from core.app import db
from core.auth import hash_password
from core.models import Role, RolePermission, User

SYSTEM_ROLES = [
    ("admin", "Administrator - polnyy dostup, nelzya udalit", True,
     ["auth.manage_users", "auth.manage_roles", "auth.security"]),
    ("manager", "Rukovoditel - upravlyaet dannymi i spravkoy", True, []),
    ("staff", "Sotrudnik - podayet zadachi, chitaet ostalnoe", True, []),
    ("viewer", "Nablyudatel - tolko prosmotr", True, []),
]

def run_seed():
    # roli
    role_map = {}
    for name, desc, is_sys, imm in SYSTEM_ROLES:
        r = Role.query.filter_by(name=name).first()
        if not r:
            r = Role(name=name, description=desc, is_system=is_sys,
                     immutable_perms=json.dumps(imm, ensure_ascii=False))
            db.session.add(r)
            db.session.flush()
        role_map[name] = r
    # sid-admin
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(
            username="admin",
            full_name="Administrator",
            password_hash=hash_password("admin123"),
            role_id=role_map["admin"].id,
            auth_source="local",
            is_active=True,
            must_change_password=True,
        )
        db.session.add(admin)
    db.session.commit()
