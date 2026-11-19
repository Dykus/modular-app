# -*- coding: utf-8 -*-
import os, re, json, base64
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d: break
    d = p
BASE = d
print("ROOT: " + BASE)

NEW_BLOCK = r'''
# texpimp-v1: jeksport/v Import tablicy kak fajla (.json) meždu mašinami.
TABLE_EXPORT_FORMAT = "modular-table-export/1"

@tables_bp.route("/<int:tid>/export")
@perm("tables.view")
def table_export(tid):
    from flask import Response
    t = CustomTable.query.get_or_404(tid)
    m = user_access(tid, current_user)
    if not m["view"]:
        abort(403)
    cols = cols_of(tid)
    widths = {}
    try:
        from modules.tables.sheet_routes import ColWidth
        for w in ColWidth.query.filter_by(table_id=tid).all():
            if w.width_px and w.width_px > 0:
                widths[w.column_key] = int(w.width_px)
    except Exception:
        pass
    acc = []
    for r in Role.query.order_by(Role.name).all():
        ra = role_access(tid, r.id)
        if not (ra["view"] or ra["create"] or ra["delete"] or ra["edit"]):
            continue
        modes = [mo for mo in ("view", "create", "delete") if ra[mo]]
        acc.append({"role_name": r.name, "modes": modes, "edits": sorted(ra["edit"])})
    rows = []
    for r in TableRow.query.filter_by(table_id=tid).order_by(TableRow.id).all():
        rows.append({"id": r.id, "data": jload(r.data, {}), "created_by": r.created_by or "",
                     "deleted_at": r.deleted_at.isoformat() if r.deleted_at else None,
                     "deleted_by": r.deleted_by or ""})
    doc = {"format": TABLE_EXPORT_FORMAT,
           "table": {"key": t.key, "title": t.title, "counters": jload(t.counters, [])},
           "columns": [{"key": c.key, "title": c.title, "col_type": c.col_type, "grp": c.grp or "",
                        "options": jload(c.options, []), "formula": jload(c.formula, {}),
                        "order": c.order if c.order is not None else 0} for c in cols],
           "widths": widths, "access": acc, "rows": rows}
    body = json.dumps(doc, ensure_ascii=False, indent=1)
    fname = "%s_%s.json" % (re.sub(r"[^A-Za-z0-9_.-]", "_", t.key),
                            datetime.datetime.utcnow().strftime("%Y%m%d"))
    return Response(body, mimetype="application/json",
                    headers={"Content-Disposition": 'attachment; filename="%s"' % fname})

def _texp_tmp_dir():
    bdir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "data", "tmp")
    os.makedirs(bdir, exist_ok=True)
    return bdir

def _texp_cleanup_old(max_age_s=3600):
    """Udaljaet starejšie vremennye dokumenty importa (techenie chasa)."""
    now = datetime.datetime.utcnow().timestamp()
    try:
        for fn in os.listdir(_texp_tmp_dir()):
            if not fn.startswith("texp_") or not fn.endswith(".json"):
                continue
            fp = os.path.join(_texp_tmp_dir(), fn)
            try:
                if now - os.path.getmtime(fp) > max_age_s:
                    os.remove(fp)
            except OSError:
                pass
    except FileNotFoundError:
        pass

def _texp_summarize(doc):
    fmt = str(doc.get("format") or "")
    tb = doc.get("table") or {}
    cols = doc.get("columns") or []
    rows = doc.get("rows") or []
    live = [r for r in rows if not r.get("deleted_at")]
    dead = [r for r in rows if r.get("deleted_at")]
    have, missing = [], []
    names = {r.name for r in Role.query.all()}
    for a in (doc.get("access") or []):
        rn = str(a.get("role_name") or "")
        if rn in names:
            have.append(rn)
        elif rn:
            missing.append(rn)
    conflict = None
    key = str(tb.get("key") or "").strip()
    if key and CustomTable.query.filter_by(key=key).first():
        conflict = key
    size_kb = len(json.dumps(doc, ensure_ascii=False)) // 1024
    return {"fmt": fmt, "ok_fmt": fmt.startswith("modular-table-export/"),
            "key": key, "title": str(tb.get("title") or ""),
            "ncols": len(cols), "nlive": len(live), "ndead": len(dead),
            "nacc": len(doc.get("access") or []), "have_roles": have,
            "missing_roles": missing, "conflict": conflict, "size_kb": size_kb}

@tables_bp.route("/import-json", methods=["GET", "POST"])
@perm("tables.manage")
def import_json():
    """Ekran importa .json tablicy: svodka -> režim -> primenenie v odnoj tranzakcii."""
    _texp_cleanup_old()
    if request.method != "POST":
        return render_template("tables/import_table.html", step="pick", summ=None, done=None)

    act = request.form.get("act") or "preview"
    if act == "preview":
        f = request.files.get("file")
        if f is None or not f.filename:
            flash("Выберите файл .json таблицы.")
            return redirect(url_for("tables.import_json"))
        raw_bytes = f.stream.read()
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            flash("Файл должен быть текстовым JSON в UTF-8.")
            return redirect(url_for("tables.import_json"))
        try:
            doc = json.loads(text)
        except Exception as e:
            flash("Не удалось прочитать JSON: " + str(e)[:200])
            return redirect(url_for("tables.import_json"))
        summ = _texp_summarize(doc)
        if not summ["ok_fmt"]:
            flash("Файл не похож на экспорт таблицы (нет format modular-table-export/…).")
            return redirect(url_for("tables.import_json"))
        # Dokument idët NA DISK, ne v sesiju/kuku.
        tmpname = "texp_" + uuid.uuid4().hex + ".json"
        tmppath = os.path.join(_texp_tmp_dir(), tmpname)
        with open(tmppath, "w", encoding="utf-8") as tf:
            tf.write(text)
        request.session["texp_file"] = tmpname
        return render_template("tables/import_table.html", step="confirm", summ=summ, done=None)

    # Shag 2: primenenie.
    mode = request.form.get("mode") or "new"
    tmpname = request.session.pop("texp_file", None)
    if not tmpname:
        flash("Сессия истекла — загрузите файл заново.")
        return redirect(url_for("tables.import_json"))
    tmppath = os.path.join(_texp_tmp_dir(), tmpname)
    try:
        with open(tmppath, "r", encoding="utf-8") as tf:
            doc = json.load(tf)
    except Exception as e:
        flash("Ошибка чтения сохранённого файла: " + str(e)[:200])
        return redirect(url_for("tables.import_json"))
    finally:
        try:
            os.remove(tmppath)
        except OSError:
            pass
    summ = _texp_summarize(doc)
    newkey = (request.form.get("newkey") or "").strip()
    target_key = newkey or summ["key"]
    if not target_key:
        flash("У таблицы нет ключа в файле — импорт невозможен.")
        return redirect(url_for("tables.import_json"))
    existing = CustomTable.query.filter_by(key=target_key).first()
    if mode == "new" and existing:
        flash("Ключ «%s» занят. Выберите «Обновить существующую», «Только структура» или задайте другой ключ." % target_key)
        # Vozvrat na ekran podtverzhdenija s novym session-file (poprosite fajl znova).
        return redirect(url_for("tables.import_json"))

    report = {"mode": mode, "cols_added": 0, "cols_updated": 0, "cols_removed": 0,
              "rows_created": 0, "rows_updated": 0, "trash_restored": 0,
              "roles_skipped": [], "backup": "", "errors": []}
    try:
        cols_doc = doc.get("columns") or []
        rows_doc = doc.get("rows") or []
        acc_doc = doc.get("access") or []
        wid_doc = doc.get("widths") or {}
        ctr_doc = (doc.get("table") or {}).get("counters") or []
        role_by_name = {r.name: r for r in Role.query.all()}

        if mode == "new":
            mx = db.session.query(db.func.max(CustomTable.order)).scalar() or 0
            t = CustomTable(key=target_key, title=str((doc.get("table") or {}).get("title") or target_key),
                            order=mx + 1, created_by=who() + " (импорт)")
            db.session.add(t); db.session.flush()
            report["backup"] = "(новая таблица — резервная копия не требуется)"
        else:
            t = existing
            bdir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                "data", "backups")
            os.makedirs(bdir, exist_ok=True)
            stamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            bpath = os.path.join(bdir, "pre_import_%s_%s.json" % (target_key, stamp))
            with open(bpath, "w", encoding="utf-8") as bf:
                cur_cols = [{"key": c.key, "title": c.title, "col_type": c.col_type, "grp": c.grp or "",
                             "options": jload(c.options, []), "formula": jload(c.formula, {}),
                             "order": c.order if c.order is not None else 0} for c in cols_of(t.id)]
                cur_rows = [{"id": r.id, "data": jload(r.data, {}), "created_by": r.created_by or "",
                             "deleted_at": r.deleted_at.isoformat() if r.deleted_at else None,
                             "deleted_by": r.deleted_by or ""}
                            for r in TableRow.query.filter_by(table_id=t.id).all()]
                json.dump({"reason": "pre-import", "table": {"key": t.key, "title": t.title,
                         "counters": jload(t.counters, [])}, "columns": cur_cols, "rows": cur_rows},
                          bf, ensure_ascii=False, indent=1)
            report["backup"] = "data/backups/" + os.path.basename(bpath)

        # Kolonki.
        if mode == "new":
            for cd in cols_doc:
                db.session.add(TableColumn(table_id=t.id, key=str(cd.get("key")), title=str(cd.get("title") or cd.get("key")),
                                           col_type=str(cd.get("col_type") or "text"), grp=str(cd.get("grp") or ""),
                                           options=json.dumps(cd.get("options") or [], ensure_ascii=False),
                                           formula=json.dumps(cd.get("formula") or {}, ensure_ascii=False),
                                           order=int(cd.get("order") or 0)))
                report["cols_added"] += 1
            db.session.flush()
        else:
            cur = {c.key: c for c in cols_of(t.id)}
            wanted = {str(cd.get("key")): cd for cd in cols_doc}
            for k, cd in wanted.items():
                c = cur.get(k)
                if c is None:
                    db.session.add(TableColumn(table_id=t.id, key=k, title=str(cd.get("title") or k),
                                               col_type=str(cd.get("col_type") or "text"), grp=str(cd.get("grp") or ""),
                                               options=json.dumps(cd.get("options") or [], ensure_ascii=False),
                                               formula=json.dumps(cd.get("formula") or {}, ensure_ascii=False),
                                               order=int(cd.get("order") or 0)))
                    report["cols_added"] += 1
                else:
                    c.title = str(cd.get("title") or c.title); c.col_type = str(cd.get("col_type") or c.col_type)
                    c.grp = str(cd.get("grp") or ""); c.options = json.dumps(cd.get("options") or [], ensure_ascii=False)
                    c.formula = json.dumps(cd.get("formula") or {}, ensure_ascii=False)
                    c.order = int(cd.get("order") or c.order or 0)
                    report["cols_updated"] += 1
            for k, c in cur.items():
                if k not in wanted:
                    db.session.delete(c); report["cols_removed"] += 1
            db.session.flush()

        # Stroki (ne pri "structure only").
        if mode != "structure":
            cur_ids = {r.id for r in TableRow.query.filter_by(table_id=t.id).all()}
            for rd in rows_doc:
                rid = rd.get("id")
                dat = json.dumps(rd.get("data") or {}, ensure_ascii=False)
                cb = str(rd.get("created_by") or "")
                da = rd.get("deleted_at")
                dbt = datetime.datetime.fromisoformat(da) if da else None
                if rid in cur_ids:
                    row = TableRow.query.get(rid)
                    if row is not None and row.table_id == t.id:
                        row.data = dat
                        row.updated_at = datetime.datetime.utcnow()
                        if dbt is not None:
                            row.deleted_at = dbt; row.deleted_by = str(rd.get("deleted_by") or "")
                            report["trash_restored"] += 1
                        report["rows_updated"] += 1
                else:
                    nr = TableRow(table_id=t.id, data=dat, created_by=cb,
                                  updated_at=datetime.datetime.utcnow(),
                                  deleted_at=dbt, deleted_by=str(rd.get("deleted_by") or ""))
                    db.session.add(nr); db.session.flush()
                    if dbt is not None:
                        report["trash_restored"] += 1
                    report["rows_created"] += 1

        # Širina.
        try:
            from modules.tables.sheet_routes import ColWidth
            for k, px in (wid_doc or {}).items():
                try:
                    pv = int(px)
                except Exception:
                    pv = 0
                if pv <= 0:
                    continue
                cw = ColWidth.query.filter_by(table_id=t.id, column_key=str(k)).first()
                if cw is None:
                    db.session.add(ColWidth(table_id=t.id, column_key=str(k), width_px=pv))
                else:
                    cw.width_px = pv
        except Exception as e:
            report["errors"].append("ширина: " + str(e)[:120])

        # Dostup po imeni roli.
        TableAccess.query.filter_by(table_id=t.id).delete()
        for a in acc_doc:
            rn = str(a.get("role_name") or "")
            r = role_by_name.get(rn)
            if r is None:
                if rn:
                    report["roles_skipped"].append(rn)
                continue
            for mo in (a.get("modes") or []):
                if mo in ("view", "create", "delete"):
                    db.session.add(TableAccess(table_id=t.id, role_id=r.id, column_key="", mode=mo))
            for ek in (a.get("edits") or []):
                db.session.add(TableAccess(table_id=t.id, role_id=r.id, column_key=str(ek), mode="edit"))

        t.counters = json.dumps(ctr_doc, ensure_ascii=False)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        report["errors"].append(str(e)[:300])
        flash("Импорт отменён (rollback), база не изменена: " + str(e)[:200])
        return redirect(url_for("tables.import_json"))

    return render_template("tables/import_table.html", step="done", summ=summ, done=report)
'''

rp = os.path.join(BASE, "modules", "tables", "routes.py")
s = open(rp, encoding="utf-8").read()
if "texpimp-v2" in s:
    print("SKIP routes.py: texpimp-v2 present")
else:
    pat = re.compile(r'# texpimp-v1:[^\n]*\n(?:[\s\S]*?)\Z')
    m = pat.search(s)
    if m:
        head = s[:m.start()]
        new_block = NEW_BLOCK.replace("# texpimp-v1:", "# texpimp-v2:")
        open(rp, "w", encoding="utf-8", newline="\n").write(head + new_block.lstrip("\n"))
        print("PATCH routes.py: texpimp block replaced (session->disk temp file)")
    else:
        print("WARN routes.py: texpimp-v1 block not found at tail")

ip = os.path.join(BASE, "modules", "tables", "templates", "tables", "import_table.html")
si = open(ip, encoding="utf-8").read()
if "size_kb" not in si:
    si = si.replace('<p class="note">Экспорт делается кнопкой «⬇ Экспорт (.json)» в шапке формы или листа нужной таблицы.</p>',
                    '<p class="note">Экспорт делается кнопкой «⬇ Экспорт (.json)» в шапке формы или листа нужной таблицы. Размер файла показан в сводке; больших таблиц ограничение куки больше не касается — документ лежит во временном файле.</p>')
    si = si.replace('<p>Колонок: <b>{{ summ.ncols }}</b> · строк живых: <b>{{ summ.nlive }}</b> · в корзине: <b>{{ summ.ndead }}</b> · правил доступа: <b>{{ summ.nacc }}</b></p>',
                    '<p>Колонок: <b>{{ summ.ncols }}</b> · строк живых: <b>{{ summ.nlive }}</b> · в корзине: <b>{{ summ.ndead }}</b> · правил доступа: <b>{{ summ.nacc }}</b> · размер: <b>{{ summ.size_kb }} КБ</b></p>')
    open(ip, "w", encoding="utf-8", newline="\n").write(si)
    print("PATCH import_table.html: size shown + note about disk temp")
else:
    print("SKIP import_table.html: size already present")

hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
v = open(hp, encoding="utf-8").read()
m = re.search(r'_B64\s*=\s*"([^"]*)"', v)
data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.31" for r in data["releases"]):
    data["releases"].insert(0, {"version": "0.13.31", "release_date": "2026-11-19", "status": "released",
        "title": "Импорт таблицы (.json): снято ограничение размера файла",
        "notes": "В 0.13.29–0.13.30 импорт таблицы падал с сообщением «файл слишком велик для предпросмотра в сессии» на любых таблицах тяжелее нескольких десятков строк: я клал весь JSON-документ в сессию Flask, которая по умолчанию хранится в cookie и ограничена примерно 4 КБ после подписи. Теперь документ при предпросмотре пишется во временный файл data/tmp/texp_<uuid>.json, в сессию уходит только его имя (~50 байт), при применении читается с диска и удаляется; старые файлы старше часа подчищаются автоматически. В сводке добавлен размер файла в килобайтах. Импорт теперь работает для таблиц любого разумного объёма, включая корзину и все строки разом."})
    data["changelog"].insert(0, {"date": "2026-11-19", "author": "синхронизация документации", "change_type": "fixed",
        "module": "tables", "ticket": "",
        "description": "Импорт таблицы (.json): документ перенесён из cookie-сессии во временный файл data/tmp/, снят лимит ~4 КБ; в сводке показан размер файла; автоочистка старых временных документов."})
    nb = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
    v = v[:m.start(1)] + nb + v[m.end(1):]
    open(hp, "w", encoding="utf-8", newline="\n").write(v)
    print("PATCH history_seed.py: release 0.13.31")
else:
    print("SKIP history_seed.py: 0.13.31 present")

print("=" * 60)
print("MARKER_END: import via disk temp file, no cookie limit (0.13.31)")
print("=" * 60)
print("Commit + Push:")
print("  modules/tables/routes.py")
print("  modules/tables/templates/tables/import_table.html")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")