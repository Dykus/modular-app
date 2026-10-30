from core.app import db
from core.models import AuditLog
def log_action(user_id, action, table_name, record_id, changes=None):
    log = AuditLog(user_id=user_id, action=action, table_name=table_name,
                   record_id=record_id, changes=str(changes) if changes else None)
    db.session.add(log)
    db.session.commit()
