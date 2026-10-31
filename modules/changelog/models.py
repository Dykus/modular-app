from core.app import db
from datetime import datetime

TYPE_LABELS = {"added": "Добавлено", "fixed": "Исправлено", "changed": "Изменено", "removed": "Удалено"}
TYPE_BADGE = {"added": "b-green", "fixed": "b-purple", "changed": "b-yellow", "removed": "b-red"}

class ChangelogEntry(db.Model):
    __tablename__ = "changelog_entry"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    author = db.Column(db.String(80), nullable=False)
    change_type = db.Column(db.String(20), default="added", nullable=False)
    module = db.Column(db.String(40), default="core", nullable=False)
    description = db.Column(db.Text, nullable=False)
    ticket = db.Column(db.String(120), default="")

def seed():
    if ChangelogEntry.query.count() > 0:
        return
    rows = [
        ("Создан каркас приложения: ядро Flask + SQLAlchemy, модульная архитектура.", "core", "added"),
        ("Модуль «Задачи отдела» (feedback): трекер хотелок со статусами и журналом.", "feedback", "added"),
        ("Модуль «Настройки»: включение/выключение модулей, тема, название, журнал изменений.", "settings", "added"),
        ("Настраиваемый порт в config.py + автоподбор свободного; абсолютный путь к БД.", "core", "changed"),
        ("Полный русский интерфейс в браузере.", "core", "changed"),
    ]
    for desc, mod, typ in rows:
        db.session.add(ChangelogEntry(author="система", change_type=typ, module=mod, description=desc))
    db.session.commit()
