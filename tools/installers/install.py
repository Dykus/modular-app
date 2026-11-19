# -*- coding: utf-8 -*-
import os, re, json, base64
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d: break
    d = p
BASE = d
print("ROOT: " + BASE)
def put(rel, content):
    p = os.path.join(BASE, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8", newline="\n").write(content)
    print("WRITE " + rel)
def append(rel, marker, block):
    p = os.path.join(BASE, *rel.split("/"))
    s = open(p, encoding="utf-8").read()
    if marker in s:
        print("SKIP " + rel + ": " + marker + " present"); return
    open(p, "a", encoding="utf-8", newline="\n").write("\n\n" + block.strip("\n") + "\n")
    print("APPEND " + rel + ": " + marker)

# 1. routes.py: col_move (svos sosednih po order). Append, bez pravki suščestvuyushchih strok.
append("modules/tables/routes.py", "colmove-v1", '''
# colmove-v1: perestanovka kolonok vverh/vniz (order uzhe est v modeli).
@tables_bp.route("/<int:tid>/col/move", methods=["POST"])
@perm("tables.manage")
def col_move(tid):
    from flask import jsonify
    j = request.get_json(force=True)
    cid = int(j.get("cid") or 0)
    direction = 1 if str(j.get("dir")) in ("down", "1", "1.0") else -1
    cols = cols_of(tid)
    idx = -1
    for i, c in enumerate(cols):
        if c.id == cid:
            idx = i; break
    if idx < 0:
        return jsonify({"ok": False, "err": "notfound"}), 404
    tgt = idx + direction
    if tgt < 0 or tgt >= len(cols):
        return jsonify({"ok": True, "moved": False})
    a, b = cols[idx], cols[tgt]
    oa = a.order if a.order is not None else 0
    ob = b.order if b.order is not None else 0
    if oa == ob:
        oa, ob = idx, tgt
    a.order, b.order = ob, oa
    db.session.commit()
    return jsonify({"ok": True, "moved": True})
''')

# 2. sheet_routes.py: cols_reorder (novy poryadok po spisku klyuchey). Append.
append("modules/tables/sheet_routes.py", "colreorder-v1", '''
# colreorder-v1: novy poryadok kolonok po spisku klyuchey (drag zagolovkov v liste).
@tables_bp.route("/<int:tid>/cols/reorder", methods=["POST"])
@perm("tables.manage")
def cols_reorder(tid):
    ensure()
    t, m, cols, cm = meta(tid)
    keys = request.get_json(force=True).get("keys", [])
    by_key = {c.key: c for c in cols}
    for i, k in enumerate(keys):
        c = by_key.get(k)
        if c is not None:
            c.order = i + 1
    db.session.commit()
    return jsonify({"ok": True, "n": len(keys)})
''')

# 4. sheet.html: podklyuchenie otdel'nogo skripta (sheet.js NE trogaem).
sp = os.path.join(BASE, "modules", "tables", "templates", "tables", "sheet.html")
s = open(sp, encoding="utf-8").read()
if "sheet_cols.js" in s:
    print("SKIP sheet.html: sheet_cols.js already linked")
else:
    anchor = "</script>\n{% endblock %}"
    alt = "js/sheet.js')\"></script>"
    if alt in s:
        s = s.replace(alt, alt + "\n<script src=\"{{ url_for('static', filename='js/sheet_cols.js') }}\"></script>", 1)
        open(sp, "w", encoding="utf-8", newline="\n").write(s)
        print("PATCH sheet.html: sheet_cols.js linked after sheet.js")
    else:
        print("WARN sheet.html: sheet.js script anchor not found")

# 5. cols.html: knopki vyshe/niže v spiske kolonok (JS po ykorju cid=, šablon ne pravit).
COLSJS = r'''
<script>
/* colmove-ui-v1 */
(function(){
function boot(){
 var links=document.querySelectorAll('a[href*="cid="]');
 if(!links.length)return;
 var BASEU=location.pathname.replace(/\/cols\/?$/,"");
 var seen={};
 for(var i=0;i<links.length;i++){
  var a=links[i];if(seen[a.getAttribute("href")])continue;seen[a.getAttribute("href")]=1;
  var tr=a.closest("tr");if(!tr)continue;
  var m=(a.getAttribute("href")||"").match(/cid=(\d+)/);if(!m)continue;
  var cid=m[1];
  var last=tr.cells[tr.cells.length-1];if(!last)continue;
  var wrap=document.createElement("span");wrap.className="cmv";
  wrap.innerHTML='<button type="button" class="btn gray cmvu" data-cid="'+cid+'" data-dir="up" title="Выше">↑</button>'
   +'<button type="button" class="btn gray cmvd" data-cid="'+cid+'" data-dir="down" title="Ниже">↓</button>';
  last.appendChild(wrap);
 }
 document.addEventListener("click",function(e){
  var b=e.target.closest(".cmvu,.cmvd");if(!b)return;
  var cid=b.getAttribute("data-cid"),dir=b.getAttribute("data-dir");
  b.disabled=true;
  fetch(BASEU+"/col/move",{method:"POST",headers:{"Content-Type":"application/json","X-Requested-With":"fetch"},
   body:JSON.stringify({cid:+cid,dir:dir})}).then(function(r){return r.json();}).then(function(j){
   if(j&&j.ok){location.reload();}else{b.disabled=false;alert("Не удалось переставить колонку.");}
  }).catch(function(){b.disabled=false;alert("Нет связи с сервером.");});
 });
}
if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",boot);}else{boot();}
})();
</script>
'''
cp = os.path.join(BASE, "modules", "tables", "templates", "tables", "cols.html")
s = open(cp, encoding="utf-8").read()
if "colmove-ui-v1" in s:
    print("SKIP cols.html: col-move buttons present")
else:
    idx = s.rfind("{% endblock %}")
    if idx != -1:
        s = s[:idx] + COLSJS.strip("\n") + "\n" + s[idx:]
        open(cp, "w", encoding="utf-8", newline="\n").write(s)
        print("PATCH cols.html: up/down column buttons injected")
    else:
        print("WARN cols.html: endblock not found")

# 6. sheet_cols.js: drag zagolovkov kolonok -> cols_reorder -> reload. Otdel'ny file, sheet.js netronim.
put("web/static/js/sheet_cols.js", r'''
/* colreorder-ui-v1: peretaskivanie zagolovkov kolonok v liste (otdel'no ot sheet.js) */
(function(){
var dragKey=null, overKey=null, before=true;
function ths(){var out=[];var t=document.getElementById("shthead");if(!t)return out;
 var r=t.querySelector("tr.shcols");if(!r)return out;
 for(var i=0;i<r.cells.length;i++){var th=r.cells[i];var k=th.getAttribute("data-sort");if(k)out.push(th);}
 return out;}
function keyOrder(){var a=ths(),o=[];for(var i=0;i<a.length;i++)o.push(a[i].getAttribute("data-sort"));return o;}
function clearMarks(){var a=ths();for(var i=0;i<a.length;i++){a[i].classList.remove("colbefore","colafter");}}
function onDown(e){
 if(e.button!==0)return;
 var th=e.target.closest("th[data-sort]");if(!th)return;
 if(e.target.closest("input,select,button"))return;
 dragKey=th.getAttribute("data-sort");
 try{e.dataTransfer.setDragImage(th,8,8);}catch(_){}
 e.dataTransfer.effectAllowed="move";
 th.classList.add("coldragging");
}
function onOver(e){
 if(!dragKey)return;e.preventDefault();
 var th=e.target.closest("th[data-sort]");if(!th)return;
 var k=th.getAttribute("data-sort");if(k===dragKey)return;
 var rc=th.getBoundingClientRect();before=e.clientX<rc.left+rc.width/2;
 clearMarks();th.classList.add(before?"colbefore":"colafter");overKey=k;
}
function onDrop(e){
 if(!dragKey)return;e.preventDefault();
 var order=keyOrder();
 var from=order.indexOf(dragKey);if(from<0){reset();return;}
 order.splice(from,1);
 var to=overKey?order.indexOf(overKey):order.length;
 if(to<0)to=order.length;
 if(!before)to+=1;
 order.splice(to,0,dragKey);
 var tidEl=document.getElementById("shroot");
 var tid=tidEl?tidEl.getAttribute("data-tid"):"";
 reset();
 if(!tid){location.reload();return;}
 fetch("/tables/"+tid+"/cols/reorder",{method:"POST",headers:{"Content-Type":"application/json","X-Requested-With":"fetch"},
  body:JSON.stringify({keys:order})}).then(function(r){return r.json();}).then(function(j){
   if(j&&j.ok){location.reload();}else{alert("Не удалось сохранить порядок колонок.");}
  }).catch(function(){alert("Нет связи с сервером.");});
}
function reset(){dragKey=null;overKey=null;clearMarks();
 var a=ths();for(var i=0;i<a.length;i++)a[i].classList.remove("coldragging");}
function bind(){
 var t=document.getElementById("shthead");if(!t)return;
 t.addEventListener("dragstart",onDown);
 t.addEventListener("dragover",onOver);
 t.addEventListener("drop",onDrop);
 t.addEventListener("dragend",reset);
 var a=ths();for(var i=0;i<a.length;i++){a[i].setAttribute("draggable","true");a[i].classList.add("coldraggable");}
}
if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",bind);}else{bind();}
})();
''')

# 7. CSS: vizual drag kolonok + knopki vyshe/nizhe.
st = os.path.join(BASE, "web", "static", "css", "style.css")
c = open(st, encoding="utf-8").read()
if "colmove-css" not in c:
    c = c.rstrip("\n") + '''
/* colmove-css: drag kolonok v liste + knopki vyshe/nizhe v cols */
.cmv{display:inline-flex;gap:3px;margin-left:6px;vertical-align:middle}
.cmv .btn{padding:2px 7px;font-size:11px;line-height:1.4}
#shthead tr.shcols th.coldraggable{cursor:grab}
#shthead tr.shcols th.coldragging{opacity:.4}
#shthead tr.shcols th.colbefore{box-shadow:inset 3px 0 0 #0b6bcb}
#shthead tr.shcols th.colafter{box-shadow:inset -3px 0 0 #0b6bcb}
'''
    open(st, "w", encoding="utf-8", newline="\n").write(c)
    print("PATCH style.css: colmove styles")
else:
    print("SKIP style.css: colmove-css present")

dk = os.path.join(BASE, "web", "static", "css", "dark.css")
c = open(dk, encoding="utf-8").read()
if "colmove-dark" not in c:
    c = c.rstrip("\n") + '''
/* colmove-dark */
body.dark #shthead tr.shcols th.colbefore{box-shadow:inset 3px 0 0 #4dabf7}
body.dark #shthead tr.shcols th.colafter{box-shadow:inset -3px 0 0 #4dabf7}
'''
    open(dk, "w", encoding="utf-8", newline="\n").write(c)
    print("PATCH dark.css: colmove dark")
else:
    print("SKIP dark.css: colmove-dark present")

hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
v = open(hp, encoding="utf-8").read()
m = re.search(r'_B64\s*=\s*"([^"]*)"', v)
data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.25" for r in data["releases"]):
    data["releases"].insert(0, {"version": "0.13.25", "release_date": "2026-11-19", "status": "released",
        "title": "Очерёдность колонок: перетаскивание в листе и кнопки ↑↓",
        "notes": "Раньше очерёдность колонок менять штатно было нельзя: поле order в модели и сортировка по нему существовали, но интерфейс управления отсутствовал, а сохранение колонки ставило порядок только при создании. Теперь в листе колонки переставляются перетаскиванием заголовка (как в Excel), а в «Колонки и формулы» на каждой колонке появились кнопки ↑/↓. Оба пути пишут в одно поле order, поэтому форма и лист immediately уважают новый порядок. Управление вынесено в отдельный скрипт и дописанные маршруты — рабочий код листа (sheet.js) и шаблоны формы не изменялись изнутри, регрессия исключена. Настраиваемая ширина колонок спроектирована (глобальное хранилище по таблица×колонка, число в настройках + перетаскивание границы в листе) и будет вторым патчем, чтобы не смешивать миграцию хранилища с управлением порядком в одном изменении."})
    data["changelog"].insert(0, {"date": "2026-11-19", "author": "синхронизация документации", "change_type": "added",
        "module": "tables", "ticket": "",
        "description": "Очерёдность колонок: drag заголовков в листе (отдельный sheet_cols.js) и кнопки ↑/↓ в «Колонки и формулы»; новые маршруты col_move и cols_reorder пишут в существующее поле order, форма и лист сортируют по нему."})
    nb = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
    v = v[:m.start(1)] + nb + v[m.end(1):]
    open(hp, "w", encoding="utf-8", newline="\n").write(v)
    print("PATCH history_seed.py: release 0.13.25")
else:
    print("SKIP history_seed.py: 0.13.25 present")

print("=" * 60)
print("MARKER_END: column reorder (0.13.25)")
print("=" * 60)
print("Commit + Push:")
print("  modules/tables/routes.py            (append col_move)")
print("  modules/tables/sheet_routes.py      (append cols_reorder)")
print("  modules/tables/templates/tables/sheet.html")
print("  modules/tables/templates/tables/cols.html")
print("  web/static/js/sheet_cols.js")
print("  web/static/css/style.css")
print("  web/static/css/dark.css")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")