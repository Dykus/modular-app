from core.app import db
from datetime import datetime

class CustomTable(db.Model):
    __tablename__ = "custom_table"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(60), unique=True, nullable=False)
    title = db.Column(db.String(120), nullable=False)
    order = db.Column(db.Integer, default=0)
    counters = db.Column(db.Text, default="[]")
    created_by = db.Column(db.String(80), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TableColumn(db.Model):
    __tablename__ = "table_column"
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey("custom_table.id"), nullable=False)
    key = db.Column(db.String(60), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    col_type = db.Column(db.String(20), default="text")   # text number date list computed ref
    grp = db.Column(db.String(60), default="")            # grupa-vladelec (dlya shapki)
    options = db.Column(db.Text, default="[]")            # dlya list: ["a","b"]
    formula = db.Column(db.Text, default="{}")            # dlya computed/ref
    order = db.Column(db.Integer, default=0)

class TableRow(db.Model):
    __tablename__ = "table_row"
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey("custom_table.id"), nullable=False)
    data = db.Column(db.Text, default="{}")
    created_by = db.Column(db.String(80), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.String(80), default="")

class TableAccess(db.Model):
    __tablename__ = "table_access"
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey("custom_table.id"), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=False)
    column_key = db.Column(db.String(60), default="*")    # "*" = dostup k tablice
    mode = db.Column(db.String(10), default="view")       # view create delete edit

class CellLog(db.Model):
    __tablename__ = "table_cell_log"
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, nullable=False)
    row_id = db.Column(db.Integer, nullable=False)
    column_key = db.Column(db.String(60), default="")
    old_value = db.Column(db.Text, default="")
    new_value = db.Column(db.Text, default="")
    who = db.Column(db.String(80), default="")
    ts = db.Column(db.DateTime, default=datetime.utcnow)
