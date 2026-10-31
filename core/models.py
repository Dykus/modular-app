"""Modeli BD: polzovateli, roli, prava, zhurnal vkhodov, audit"""
from core.app import db
from datetime import datetime

class Role(db.Model):
    __tablename__ = "role"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(200), default="")
    is_system = db.Column(db.Boolean, default=False, nullable=False)
    immutable_perms = db.Column(db.Text, default="")  # JSON-spisok prav, kotorye nelzya snyat
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    permissions = db.relationship("RolePermission", backref="role", cascade="all,delete", lazy="dynamic")
    users = db.relationship("User", backref="role_rel", lazy="dynamic")

class RolePermission(db.Model):
    __tablename__ = "role_permission"
    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=False)
    perm = db.Column(db.String(120), nullable=False)

class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(120), default="")
    email = db.Column(db.String(120), default="")
    password_hash = db.Column(db.String(256), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"))
    auth_source = db.Column(db.String(20), default="local")  # local / ad
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    must_change_password = db.Column(db.Boolean, default=False, nullable=False)
    failed_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_authenticated(self):
        return True
    @property
    def is_active_user(self):
        return bool(self.is_active)
    @property
    def is_anonymous(self):
        return False
    @property
    def is_superuser(self):
        return bool(self.role_rel and self.role_rel.name == "admin")
    def get_id(self):
        return str(self.id)
    @property
    def display_name(self):
        return self.full_name or self.username

class LoginLog(db.Model):
    __tablename__ = "login_log"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), default="")
    user_id = db.Column(db.Integer)
    success = db.Column(db.Boolean, default=False, nullable=False)
    ip = db.Column(db.String(64), default="")
    provider = db.Column(db.String(20), default="local")
    reason = db.Column(db.String(120), default="")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    __tablename__ = "audit_log"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    action = db.Column(db.String(100))
    table_name = db.Column(db.String(100))
    record_id = db.Column(db.Integer)
    changes = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", backref=db.backref("logs", lazy=True))
