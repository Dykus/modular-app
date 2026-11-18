# -*- coding: utf-8 -*-
import os, re, json, base64, sys

d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d:
        break
    d = p
BASE = d
print("ROOT: " + BASE)
sys.path.insert(0, BASE)
from core.app import create_app, db
app = create_app()

URGENT = "⚠ СРОЧНО"
EQ_TYPES = ["Станок", "Пресс", "Конвейер", "Электро"]
AREAS = ["Цех A", "Цех B", "Склад"]
PRIOS = ["Низкий", "Средний", "Высокий", "Критичный"]
STATS = ["Новая", "В работе", "Выполнено", "Отклонено"]

with app.app_context():
    from modules.tables.models import CustomTable, TableColumn, TableRow, TableAccess
    from core.models import Role

    if CustomTable.query.filter_by(key="demo_requests").first():
        print("SKIP: demo tables already exist")
    else:
        # --- probe formula kinds via real compute_value ---
        cost_kind = days_kind = if_kind = if_op = None
        try:
            from modules.tables.service import compute_value
            def mk(f):
                return TableColumn(table_id=0, key="probe", title="probe",
                                   col_type="computed",
                                   formula=json.dumps(f, ensure_ascii=False))
            def num_ok(g, want):
                try:
                    return abs(float(str(g).replace(",", "."))) == want
                except Exception:
                    return False
            for k in ("arith", "math", "calc"):
                try:
                    g = compute_value(mk({"kind": k, "op": "*", "a": "h", "b": "r"}),
                                      {"h": "3", "r": "100"}, lambda rt: [])
                    if num_ok(g, 300):
                        cost_kind = k; break
                except Exception:
                    pass
            for k in ("days", "diff", "date_diff", "between"):
                try:
                    g = compute_value(mk({"kind": k, "a": "p", "b": "f"}),
                                      {"p": "01.11.2026", "f": "05.11.2026"}, lambda rt: [])
                    if num_ok(g, 4):
                        days_kind = k; break
                except Exception:
                    pass
            for k in ("if", "cond", "condition"):
                for op in ("=", "==", "eq"):
                    try:
                        g = compute_value(mk({"kind": k, "col": "pr", "if_op": op,
                                              "value": "Критичный", "then": URGENT, "else": ""}),
                                          {"pr": "Критичный"}, lambda rt: [])
                        if str(g).strip() == URGENT:
                            if_kind, if_op = k, op; break
                    except Exception:
                        pass
                if if_kind:
                    break
            print("PROBE: cost=%s days=%s if=%s op=%s" % (cost_kind, days_kind, if_kind, if_op))
        except Exception as e:
            print("WARN: service import failed (%s); computed columns skipped" % e)

        def add_table(key, title, order):
            t = CustomTable(key=key, title=title, order=order, created_by="demo_seed")
            db.session.add(t); db.session.flush(); return t

        def add_col(t, key, title, ctype, order, options=None, formula=None):
            c = TableColumn(table_id=t.id, key=key, title=title, col_type=ctype, order=order,
                            options=json.dumps(options or [], ensure_ascii=False),
                            formula=json.dumps(formula or {}, ensure_ascii=False))
            db.session.add(c); db.session.flush(); return c

        eq = add_table("demo_equipment", "Оборудование (демо)", 900)
        for i, (k, ti, ct, op) in enumerate([
                ("inv", "Инв. номер", "text", None),
                ("name", "Название", "text", None),
                ("eqtype", "Тип", "list", EQ_TYPES),
                ("area", "Участок", "list", AREAS)]):
            add_col(eq, k, ti, ct, i + 1, options=op)
        eq_rows = [
            {"inv": "101", "name": "Токарный станок 16К20", "eqtype": "Станок", "area": "Цех A"},
            {"inv": "102", "name": "Пресс П6324", "eqtype": "Пресс", "area": "Цех A"},
            {"inv": "103", "name": "Конвейер ЛК-4", "eqtype": "Конвейер", "area": "Цех B"},
        ]
        for r in eq_rows:
            db.session.add(TableRow(table_id=eq.id, data=json.dumps(r, ensure_ascii=False),
                                    created_by="demo_seed"))
        db.session.flush()

        rq = add_table("demo_requests", "Заявки на ремонт (демо)", 901)
        keys = []
        def col(k, ti, ct, options=None, formula=None):
            add_col(rq, k, ti, ct, len(keys) + 1, options=options, formula=formula)
            keys.append(k)
        col("rdate", "Дата заявки", "date")
        col("inv", "Инв. номер", "text")
        col("equip", "Оборудование", "ref",
            formula={"kind": "ref", "ref_table": eq.id, "match_local": "inv",
                     "match_remote": "inv", "show": "name"})
        col("descr", "Описание", "text")
        col("prio", "Приоритет", "list", options=PRIOS)
        col("stat", "Статус", "list", options=STATS)
        col("plan", "Плановая дата", "date")
        col("fact", "Факт. дата", "date")
        col("hours", "Часы работы", "number")
        col("rate", "Ставка", "number")
        if cost_kind:
            col("cost", "Стоимость", "computed",
                formula={"kind": cost_kind, "op": "*", "a": "hours", "b": "rate"})
        if days_kind:
            col("late", "Просрочка, дн", "computed",
                formula={"kind": days_kind, "a": "plan", "b": "fact"})
        if if_kind:
            col("urgent", "Срочно?", "computed",
                formula={"kind": if_kind, "col": "prio", "if_op": if_op,
                         "value": "Критичный", "then": URGENT, "else": ""})

        counters = [{"title": "Всего заявок", "func": "count", "col": "inv", "wcol": "", "wval": ""},
                    {"title": "В работе", "func": "count", "col": "inv", "wcol": "stat", "wval": "В работе"},
                    {"title": "Критичные", "func": "count", "col": "inv", "wcol": "prio", "wval": "Критичный"}]
        if cost_kind:
            counters.insert(1, {"title": "Сумма затрат", "func": "sum", "col": "cost", "wcol": "", "wval": ""})
        rq.counters = json.dumps(counters, ensure_ascii=False)

        rows = [
            {"rdate": "10.11.2026", "inv": "101", "descr": "Шпиндель не крутит", "prio": "Высокий",
             "stat": "Выполнено", "plan": "12.11.2026", "fact": "15.11.2026", "hours": "6", "rate": "800"},
            {"rdate": "14.11.2026", "inv": "102", "descr": "Течь масла", "prio": "Критичный",
             "stat": "В работе", "plan": "16.11.2026", "fact": "", "hours": "2", "rate": "900"},
            {"rdate": "15.11.2026", "inv": "103", "descr": "Замена ленты", "prio": "Средний",
             "stat": "Новая", "plan": "20.11.2026", "fact": "", "hours": "", "rate": "700"},
            {"rdate": "16.11.2026", "inv": "101", "descr": "Профилактика", "prio": "Низкий",
             "stat": "Выполнено", "plan": "17.11.2026", "fact": "17.11.2026", "hours": "3", "rate": "800"},
        ]
        for r in rows:
            db.session.add(TableRow(table_id=rq.id, data=json.dumps(r, ensure_ascii=False),
                                    created_by="demo_seed"))

        editable = [k for k in keys if k not in ("equip", "cost", "late", "urgent")]
        def grant(rname, modes, edits):
            role = Role.query.filter_by(name=rname).first()
            if not role:
                return
            for m in modes:
                db.session.add(TableAccess(table_id=rq.id, role_id=role.id, column_key="*", mode=m))
            for k in edits:
                db.session.add(TableAccess(table_id=rq.id, role_id=role.id, column_key=k, mode="edit"))
        grant("manager", ["view", "create", "delete"], editable)
        grant("staff", ["view", "create"], ["descr", "prio", "hours"])
        grant("viewer", ["view"], [])
        db.session.commit()
        print("CREATED: demo_equipment + demo_requests, cols=%d, rows=%d" % (len(keys), len(rows)))

    # --- release 0.12.18 + changelog (base64, idempotent) ---
    hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
    htxt = open(hp, encoding="utf-8").read()
    m = re.search(r'_B64\s*=\s*"([^"]*)"', htxt)
    data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
    if not any(r.get("version") == "0.12.18" for r in data["releases"]):
        data["releases"].insert(0, {
            "version": "0.12.18", "release_date": "2026-11-18", "status": "released",
            "title": "Демо-таблицы конструктора",
            "notes": "Установщик создаёт две демо-таблицы: справочник оборудования и заявки на ремонт "
                     "со ссылкой-ВПР, вычисляемой стоимостью, просрочкой и сигналом «Срочно?», "
                     "счётчиками-карточками и матрицей прав ролей. Виды формул проверяются на месте "
                     "через compute_value, неподдержанные колонки пропускаются. Повторный запуск "
                     "не трогает существующие таблицы."})
        data["changelog"].insert(0, {
            "date": "2026-11-18", "author": "синхронизация документации", "change_type": "added",
            "module": "tables", "ticket": "",
            "description": "Добавлены демо-таблицы конструктора (оборудование + заявки на ремонт): "
                           "ссылка-ВПР, формулы стоимости/просрочки/сигнала, счётчики и матрица прав; "
                           "повторный запуск установщика не дублирует данные."})
        nb = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
        htxt = htxt[:m.start(1)] + nb + htxt[m.end(1):]
        open(hp, "w", encoding="utf-8", newline="\n").write(htxt)
        print("PATCH history_seed.py: release 0.12.18")
    else:
        print("SKIP history_seed.py: 0.12.18 already present")

print("=" * 60)
print("MARKER_END: demo tables + release 0.12.18")
print("=" * 60)
print("Commit + Push:")
print("  tools/installers/install.py")
print("  modules/versions/history_seed.py")