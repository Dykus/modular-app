# -*- coding: utf-8 -*-
import os, sys, json
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d: break
    d = p
BASE = d
print("ROOT: " + BASE)
sys.path.insert(0, BASE)
from core.app import create_app, db
app = create_app()
with app.app_context():
    from modules.tables.models import CustomTable, TableColumn, TableRow, TableAccess
    from core.models import Role
    if CustomTable.query.filter_by(key="demo_orders").first():
        print("SKIP: demo_orders already exists in this database")
    else:
        t = CustomTable(key="demo_orders", title="Заказы (демо-макет)", order=902, created_by="demo_seed")
        db.session.add(t); db.session.flush()
        COLS = [
            ("num", "№ заказа", "text", "Продажи", None),
            ("client", "Клиент", "text", "Продажи", None),
            ("sum", "Сумма, руб", "number", "Продажи", None),
            ("odate", "Дата заказа", "date", "Продажи", None),
            ("due", "Срок к", "date", "Продажи", None),
            ("status", "Статус производства", "list", "Производство", ["Не начато", "В производстве", "На контроле", "Готово"]),
            ("rdate", "Дата готовности", "date", "Производство", None),
            ("shop", "Цех / линия", "list", "Производство", ["Цех 1", "Цех 2", "Цех 3", "Линия А", "Линия Б"]),
            ("pnote", "Примечание производства", "text", "Производство", None),
            ("shipped", "Отгружено", "list", "Склад", ["Нет", "Частично", "Да"]),
            ("sdate", "Дата отгрузки", "date", "Склад", None),
            ("wnote", "Примечание склада", "text", "Склад", None),
        ]
        keys = []
        for i, (k, ti, ct, g, op) in enumerate(COLS):
            db.session.add(TableColumn(table_id=t.id, key=k, title=ti, col_type=ct, grp=g, order=i + 1,
                                       options=json.dumps(op or [], ensure_ascii=False), formula="{}"))
            keys.append(k)
        ROWS = [
            {"num": "001", "client": "ООО «Ромашка»", "sum": "50000", "odate": "01.11.2026", "due": "20.11.2026",
             "status": "В производстве", "rdate": "", "shop": "Цех 2", "pnote": "ждём металл", "shipped": "Нет", "sdate": "", "wnote": ""},
            {"num": "002", "client": "ИП Василёк", "sum": "50000", "odate": "02.11.2026", "due": "25.11.2026",
             "status": "Не начато", "rdate": "", "shop": "", "pnote": "", "shipped": "Нет", "sdate": "", "wnote": ""},
            {"num": "003", "client": "АО «Колос»", "sum": "120000", "odate": "28.10.2026", "due": "15.11.2026",
             "status": "На контроле", "rdate": "14.11.2026", "shop": "Цех 1", "pnote": "ОТК проверяет", "shipped": "Нет", "sdate": "", "wnote": ""},
            {"num": "004", "client": "ООО «Штиль»", "sum": "30000", "odate": "20.10.2026", "due": "05.11.2026",
             "status": "Готово", "rdate": "03.11.2026", "shop": "Цех 2", "pnote": "упаковано", "shipped": "Да", "sdate": "05.11.2026", "wnote": "ТТ-4821"},
            {"num": "005", "client": "ООО «Ромашка»", "sum": "75000", "odate": "03.11.2026", "due": "30.11.2026",
             "status": "Не начато", "rdate": "", "shop": "", "pnote": "", "shipped": "Нет", "sdate": "", "wnote": ""},
            {"num": "006", "client": "АО «Колос»", "sum": "12000", "odate": "15.10.2026", "due": "25.10.2026",
             "status": "Готово", "rdate": "24.10.2026", "shop": "Цех 1", "pnote": "", "shipped": "Частично", "sdate": "30.10.2026", "wnote": "ждём машину"},
        ]
        for r in ROWS:
            db.session.add(TableRow(table_id=t.id, data=json.dumps(r, ensure_ascii=False), created_by="demo_seed"))
        t.counters = json.dumps([
            {"title": "Всего заказов", "func": "count", "col": "num", "wcol": "", "wval": ""},
            {"title": "Сумма заказов", "func": "sum", "col": "sum", "wcol": "", "wval": ""},
            {"title": "В производстве", "func": "count", "col": "num", "wcol": "status", "wval": "В производстве"},
            {"title": "Отгружено", "func": "count", "col": "num", "wcol": "shipped", "wval": "Да"},
        ], ensure_ascii=False)
        def grant(rname, modes, edits):
            role = Role.query.filter_by(name=rname).first()
            if not role: return
            for m in modes:
                db.session.add(TableAccess(table_id=t.id, role_id=role.id, column_key="*", mode=m))
            for k in edits:
                db.session.add(TableAccess(table_id=t.id, role_id=role.id, column_key=k, mode="edit"))
        grant("manager", ["view", "create", "delete"], keys)
        grant("staff", ["view", "create"], ["num", "client", "sum", "odate", "due"])
        grant("viewer", ["view"], [])
        db.session.commit()
        print("CREATED demo_orders: 12 cols, 6 rows, 3 groups, 4 counters, access matrix")

print("=" * 60)
print("MARKER_END: demo_orders seed (idempotent, per-database)")
print("=" * 60)
print("Commit + Push:")
print("  tools/installers/install.py")