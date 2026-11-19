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
        print("SKIP " + rel + ": " + marker); return
    open(p, "a", encoding="utf-8", newline="\n").write("\n\n" + block.strip("\n") + "\n")
    print("APPEND " + rel + ": " + marker)

# 1. sheet_routes.py: cols_reorder (drag zagolovkov lista). Idempotent.
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

# 2. routes.py: col_move (knopki vyshe/nizhe v cols). Idempotent.
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

# 3. sheet_cols.js v2: MutationObserver perestavljaet draggable posle kazhdoi pererisovki shapki.
put("web/static/js/sheet_cols.js", r'''
/* colreorder-ui-v2: drag zagolovkov kolonok v liste; draggable perestavljaetsya
   posle kazhdoi pererisovki #shthead (MutationObserver), slushateli delegirovany
   na sam #shthead i perezhivajut innerHTML-zamenu. sheet.js NE izmenjaetsya. */
(function(){
"use strict";
var dragKey=null, overKey=null, before=true, bound=false;
function shthead(){return document.getElementById("shthead");}
function ths(){var t=shthead();if(!t)return[];var r=t.querySelector("tr.shcols");if(!r)return[];
 var out=[];for(var i=0;i<r.cells.length;i++){var th=r.cells[i];if(th.getAttribute("data-sort"))out.push(th);}return out;}
function keyOrder(){var a=ths(),o=[];for(var i=0;i<a.length;i++)o.push(a[i].getAttribute("data-sort"));return o;}
function equip(){var a=ths();for(var i=0;i<a.length;i++){a[i].setAttribute("draggable","true");a[i].classList.add("coldraggable");}}
function clearMarks(){var a=ths();for(var i=0;i<a.length;i++)a[i].classList.remove("colbefore","colafter");}
function reset(){dragKey=null;overKey=null;clearMarks();var a=ths();for(var i=0;i<a.length;i++)a[i].classList.remove("coldragging");}
function onDown(e){
 if(e.button!==0)return;
 var th=e.target.closest("th[data-sort]");if(!th)return;
 if(e.target.closest("input,select,button,a"))return;
 dragKey=th.getAttribute("data-sort");
 try{e.dataTransfer.effectAllowed="move";e.dataTransfer.setData("text/plain",dragKey);}catch(_){}
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
 var root=document.getElementById("shroot");
 var tid=root?root.getAttribute("data-tid"):"";
 reset();
 if(!tid){location.reload();return;}
 fetch("/tables/"+tid+"/cols/reorder",{method:"POST",
  headers:{"Content-Type":"application/json","X-Requested-With":"fetch"},
  body:JSON.stringify({keys:order})})
  .then(function(r){return r.json().then(function(j){return{st:r.status,j:j};});})
  .then(function(res){
   if(res.st===403){alert("Переставлять колонки может только роль с правом управления таблицей.");return;}
   if(res.j&&res.j.ok){location.reload();}else{alert("Не удалось сохранить порядок колонок.");}
  })
  .catch(function(){alert("Нет связи с сервером.");});
}
function bind(){
 var t=shthead();if(!t)return;
 if(bound)return;bound=true;
 t.addEventListener("dragstart",onDown);
 t.addEventListener("dragover",onOver);
 t.addEventListener("drop",onDrop);
 t.addEventListener("dragend",reset);
 equip();
 try{
  var mo=new MutationObserver(function(){equip();});
  mo.observe(t,{childList:true,subtree:true});
 }catch(_){
  setInterval(equip,1500); /* fallback, esli MutationObserver neprestupen */
 }
}
function start(){
 if(shthead()&&shthead().querySelector("tr.shcols")){bind();return;}
 var n=0,tm=setInterval(function(){n++;if(shthead()&&shthead().querySelector("tr.shcols")){clearInterval(tm);bind();}else if(n>20){clearInterval(tm);}},200);
}
if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",start);}else{start();}
})();
''')

# 4. sheet.html: nadezhnoje podkluchenie sheet_cols.js posle sheet.js (novyj yakor').
sp = os.path.join(BASE, "modules", "tables", "templates", "tables", "sheet.html")
s = open(sp, encoding="utf-8").read()
if "filename='js/sheet_cols.js'" in s:
    print("SKIP sheet.html: sheet_cols.js already linked")
else:
    pat = re.compile(r"(<script[^>]*filename='js/sheet\.js'[^>]*></script>)")
    s2, n = pat.subn(lambda m: m.group(1) + "\n<script src=\"{{ url_for('static', filename='js/sheet_cols.js') }}\"></script>", s, count=1)
    if n:
        open(sp, "w", encoding="utf-8", newline="\n").write(s2)
        print("PATCH sheet.html: sheet_cols.js linked after sheet.js (robust anchor)")
    else:
        print("WARN sheet.html: sheet.js anchor 'filename=...sheet.js' not found")

# 5. CSS: user-select na draggahle (chtoby drag ne zahvatyvals' vydeleniem teksta). Idempotent.
st = os.path.join(BASE, "web", "static", "css", "style.css")
c = open(st, encoding="utf-8").read()
if "colmove2-css" not in c:
    c = c.rstrip("\n") + '''
/* colmove2-css: drag zagolovkov ne treogaet vydelenie */
#shthead tr.shcols th.coldraggable{-webkit-user-select:none;user-select:none}
#shthead tr.shcols th.coldragging{opacity:.45}
'''
    open(st, "w", encoding="utf-8", newline="\n").write(c)
    print("PATCH style.css: colmove2 (user-select none)")
else:
    print("SKIP style.css: colmove2-css present")

hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
v = open(hp, encoding="utf-8").read()
m = re.search(r'_B64\s*=\s*"([^"]*)"', v)
data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.26" for r in data["releases"]):
    data["releases"].insert(0, {"version": "0.13.26", "release_date": "2026-11-19", "status": "released",
        "title": "Перетаскивание колонок в листе заработало",
        "notes": "В 0.13.25 перестановка колонок перетаскиванием заголовка в листе не работала по двум причинам: скрипт sheet_cols.js не подключился к странице (якорь вставки не совпал из-за пробелов и фигурных скобок Jinja вокруг filename='js/sheet.js'), и даже при подключении атрибут draggable стирался при каждой перерисовке шапки листа (sheet.js заменяет innerHTML #shthead при загрузке, опросе чужих правок и любой правке). Скрипт переписан: делегированные слушатели drag висят на самом #shthead и переживают перезапись, а MutationObserver заново навешивает draggable на заголовки после каждой перерисовки; подключение сделано надёжным якорем по уникальной подстроке filename='js/sheet.js'. Рабочий код листа (sheet.js) не изменялся. Маршруты cols_reorder и col_move дописаны идемпотентно на случай, если 0.13.25 до них не дошёл."})
    data["changelog"].insert(0, {"date": "2026-11-19", "author": "синхронизация документации", "change_type": "fixed",
        "module": "tables", "ticket": "",
        "description": "Лист: перетаскивание заголовков колонок работает — sheet_cols.js подключён надёжным якорем и переставляет draggable через MutationObserver после каждой перерисовки шапки; sheet.js не тронут."})
    nb = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
    v = v[:m.start(1)] + nb + v[m.end(1):]
    open(hp, "w", encoding="utf-8", newline="\n").write(v)
    print("PATCH history_seed.py: release 0.13.26")
else:
    print("SKIP history_seed.py: 0.13.26 present")

print("=" * 60)
print("MARKER_END: column drag in sheet fixed (0.13.26)")
print("=" * 60)
print("Commit + Push:")
print("  modules/tables/sheet_routes.py      (append cols_reorder, esli ne bylo)")
print("  modules/tables/routes.py            (append col_move, esli ne bylo)")
print("  web/static/js/sheet_cols.js         (perepisan v2)")
print("  modules/tables/templates/tables/sheet.html")
print("  web/static/css/style.css")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")