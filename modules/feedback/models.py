from core.app import db
from datetime import datetime

STATUS_LABELS = {"new": "Новая", "work": "В работе", "done": "Сделано", "reject": "Не нужно"}
STATUS_BADGE = {"new": "b-purple", "work": "b-yellow", "done": "b-green", "reject": "b-gray"}

class FeedbackItem(db.Model):
    __tablename__ = "feedback_item"
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(80), nullable=False)
    text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="new", nullable=False)
    comment = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    logs = db.relationship("FeedbackLog", backref="item", cascade="all,delete",
                           order_by="FeedbackLog.timestamp.desc()")

class FeedbackLog(db.Model):
    __tablename__ = "feedback_log"
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("feedback_item.id"), nullable=False)
    who = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(40), nullable=False)
    old_status = db.Column(db.String(20), default="")
    new_status = db.Column(db.String(20), default="")
    comment = db.Column(db.Text, default="")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
