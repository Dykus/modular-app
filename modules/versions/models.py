from core.app import db
from datetime import datetime

STATUS_LABELS = {"released": "Выпущен", "planned": "План", "deprecated": "Устарел"}
STATUS_BADGE = {"released": "b-green", "planned": "b-purple", "deprecated": "b-gray"}

class Release(db.Model):
    __tablename__ = "release"
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(40), nullable=False)
    release_date = db.Column(db.Date, default=datetime.utcnow)
    title = db.Column(db.String(200), default="")
    notes = db.Column(db.Text, default="")
    status = db.Column(db.String(20), default="released", nullable=False)
    is_current = db.Column(db.Boolean, default=False, nullable=False)

def seed():
    if Release.query.count() > 0:
        return
    rows = [
        ("0.1.0", "Первый каркас", "Flask + SQLAlchemy, модульная структура папок.", "released", False),
        ("0.2.0", "Модуль Задачи отдела", "Трекер хотелок со статусами и журналом изменений.", "released", False),
        ("0.3.0", "Модуль Настройки", "Включение/выключение модулей, тема, название.", "released", False),
        ("0.4.0", "Порт и БД", "Настраиваемый порт + автоподбор; абсолютный путь к БД; русский интерфейс.", "released", False),
        ("0.5.0", "Журнал, Версии, Справка", "Добавлены модули changelog, versions, help; версия в футере; обновлён README.", "released", True),
    ]
    for ver, title, notes, status, cur in rows:
        db.session.add(Release(version=ver, title=title, notes=notes, status=status, is_current=cur))
    db.session.commit()
