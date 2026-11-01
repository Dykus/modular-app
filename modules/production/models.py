from core.app import db
from datetime import datetime

STATUS_LABELS = {
    "new": "Новая",
    "in_progress": "В работе",
    "done": "Выполнено",
    "cancelled": "Отменено"
}

STATUS_BADGES = {
    "new": "b-purple",
    "in_progress": "b-yellow",
    "done": "b-green",
    "cancelled": "b-gray"
}

class ProductionTask(db.Model):
    """Задача производства"""
    __tablename__ = "production_task"

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="new", nullable=False)
    assignee = db.Column(db.String(100), default="")
    priority = db.Column(db.String(20), default="normal")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(100), default="")
    comment = db.Column(db.Text, default="")

    # Korzina: deleted_at IS NULL = zadacha aktivna;
    # deleted_at NOT NULL = zadacha v korzine.
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.String(100), default="")

    def to_dict(self):
        return {
            "id": self.id,
            "number": self.number,
            "description": self.description,
            "status": self.status,
            "status_label": STATUS_LABELS.get(self.status, self.status),
            "assignee": self.assignee,
            "priority": self.priority,
            "created_at": self.created_at.strftime("%d.%m.%Y %H:%M") if self.created_at else "",
            "updated_at": self.updated_at.strftime("%d.%m.%Y %H:%M") if self.updated_at else "",
            "created_by": self.created_by,
            "comment": self.comment,
            "in_trash": self.deleted_at is not None,
            "deleted_by": self.deleted_by or "",
        }
