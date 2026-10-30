from core.app import db
from datetime import datetime
import json

class Setting(db.Model):
    __tablename__ = "setting"
    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Text, default="")

class SettingLog(db.Model):
    __tablename__ = "setting_log"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), nullable=False)
    old_value = db.Column(db.Text, default="")
    new_value = db.Column(db.Text, default="")
    who = db.Column(db.String(80), default="")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

def get_setting(key, default=""):
    row = Setting.query.get(key)
    if row is None or row.value == "":
        return default
    return row.value

def get_bool(key, default=False):
    v = get_setting(key, "")
    if v == "":
        return default
    return str(v).lower() in ("1", "true", "yes", "on")

def set_setting(key, value, who="sistema"):
    row = Setting.query.get(key)
    old = row.value if row else ""
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False)
    if row:
        row.value = value
    else:
        db.session.add(Setting(key=key, value=value))
    if old != value:
        db.session.add(SettingLog(key=key, old_value=old, new_value=value, who=who))
    db.session.commit()
    return old, value
