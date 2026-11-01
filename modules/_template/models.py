from core.app import db

class PrimerNote(db.Model):
    __tablename__ = "primer_note"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), default="")

def seed():
    if PrimerNote.query.count() == 0:
        db.session.add(PrimerNote(text="Модуль подключён и работает."))
        db.session.commit()
