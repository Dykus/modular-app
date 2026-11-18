# -*- coding: utf-8 -*-
import os, re, json, base64
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d: break
    d = p
BASE = d
print("ROOT: " + BASE)

# 1. service.py: IF chitaet sravnenie iz if_op.
sp = os.path.join(BASE, "modules", "tables", "service.py")
s = open(sp, encoding="utf-8").read()
pat = re.compile(r'(val = str\(f\.get\("value"\) or ""\)\s*\n\s*)op = f\.get\("op"\)')
if 'f.get("if_op") or f.get("op")' in s:
    print("SKIP service.py: if_op already preferred")
elif pat.search(s):
    s = pat.sub(lambda m: m.group(1) + 'op = f.get("if_op") or f.get("op")', s, count=1)
    open(sp, "w", encoding="utf-8", newline="\n").write(s)
    print("PATCH service.py: IF reads comparison from if_op")
else:
    print("WARN service.py: if-branch anchor not found")

# 2. sheet_routes.py: /sample dlya prev'yu.
rp = os.path.join(BASE, "modules", "tables", "sheet_routes.py")
s = open(rp, encoding="utf-8").read()
if "fsample-v1" in s:
    print("SKIP sheet_routes.py: sample endpoint present")
else:
    s = s.rstrip("\n") + '''

# fsample-v1: syrye dannye pervyh strok dlya zhivogo prev'yu (tol'ko chtenie).
@tables_bp.route("/<int:tid>/sample")
@perm("tables.view")
def sample(tid):
    ensure()
    t, m, cols, cm = meta(tid)
    rows = TableRow.query.filter_by(table_id=tid, deleted_at=None).order_by(TableRow.id).limit(5).all()
    return jsonify({"rows": [{"id": r.id, "data": jload(r.data, {})} for r in rows],
                    "cols": [{"k": c.key, "t": c.title, "ty": c.col_type,
                              "op": jload(c.options, [])} for c in cols]})
'''
    open(rp, "w", encoding="utf-8", newline="\n").write(s)
    print("PATCH sheet_routes.py: /sample endpoint appended")

# 3. cols.html: ubirat' bituyu v1-vstavku, postavit' v2-skript (panel' sozdayot sam).
V2 = r'''
<script>
/* fprev-v2 */
(function(){
var SAMPLE="{{ url_for('tables.sample', tid=t.id) }}";
var SPREFIX="{{ url_for('tables.index') }}";
var ATABLES={ {% for x in all_tables %}{{ x.id|tojson }}:{{ x.title|tojson }},{% endfor %} };
function boot(){
try{
var old=document.getElementById('fprev');
if(old&&old.parentNode)old.parentNode.removeChild(old);
var kind=document.querySelector('[name="kind"]');
if(!kind||!kind.form)return;
var form=kind.form;
var box=document.createElement('div');box.id='fprev';box.className='fprev';box.style.display='none';
box.innerHTML='<h3>Живой пример: что посчитает формула</h3><div class="fprev-sum" id="fprevsum"></div><div id="fprevrows"></div><div class="note" id="fprevnote">Пример пересчитывается при каждом изменении полей и НЕ сохраняется до «Сохранить колонку».</div>';
var host=kind.closest('fieldset')||kind.closest('.form-row')||kind.parentNode;
host.parentNode.insertBefore(box,host.nextSibling);
var ctype=form.querySelector('[name="col_type"]');
var sample=null,remotes={};
function val(n){var e=form.querySelector('[name="'+n+'"]');return e?e.value:"";}
function num(v){v=String(v==null?"":v).replace(/\s/g,"").replace(",",".");var n=parseFloat(v);return isNaN(n)?null:n;}
function dparse(v){v=String(v||"").trim();var m=v.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);if(m)return new Date(+m[3],+m[2]-1,+m[1]);var m2=v.match(/^(\d{4})-(\d{2})-(\d{2})$/);if(m2)return new Date(+m2[1],+m2[2]-1,+m2[3]);return null;}
function fnum(x){if(x===null||x===undefined)return "";if(x===Math.round(x))return String(x);return String(Math.round(x*100)/100);}
function tok(t,dd){t=String(t==null?"":t).trim();if(Object.prototype.hasOwnProperty.call(dd,t))return String(dd[t]==null?"":dd[t]);return t;}
function colTitle(k){if(sample){for(var i=0;i<sample.cols.length;i++)if(sample.cols[i].k===k)return sample.cols[i].t;}return k;}
function isCol(k){if(sample){for(var i=0;i<sample.cols.length;i++)if(sample.cols[i].k===k)return true;}return false;}
function lit(k){return isCol(k)?("«"+colTitle(k)+"»"):("«"+k+"» (литерал)");}
function readF(){return {kind:val('kind'),op:val('op'),a:val('a'),b:val('b'),col:val('if_col'),if_op:val('if_op'),value:val('if_val'),then:val('then_v'),else:val('else_v'),ref_table:val('ref_table'),match_local:val('match_local'),match_remote:val('match_remote'),show:val('show')};}
function compute(ty,f,dd,remote){
 try{
  if(ty==="ref"){var want=String(dd[f.match_local]==null?"":dd[f.match_local]);if(!want)return "";
   for(var i=0;i<remote.length;i++){if(String(remote[i][f.match_remote]==null?"":remote[i][f.match_remote])===want)return String(remote[i][f.show]==null?"":remote[i][f.show]);}
   return "";}
  if(f.kind==="arith"){var a=num(tok(f.a,dd)),b=num(tok(f.b,dd));if(a===null||b===null)return "";var r;
   if(f.op==="add")r=a+b;else if(f.op==="sub")r=a-b;else if(f.op==="mul")r=a*b;else if(f.op==="div"){if(b===0)return "";r=a/b;}else return "";
   return fnum(r);}
  if(f.kind==="concat")return (tok(f.a,dd)+" "+tok(f.b,dd)).trim();
  if(f.kind==="days"){var da=dparse(tok(f.a,dd));var bt=String(f.b||"").trim();var db=bt?dparse(tok(bt,dd)):new Date();if(!da||!db)return "";return String(Math.round((da-db)/86400000));}
  if(f.kind==="if"){var base=String(dd[f.col]==null?"":dd[f.col]);var vv=String(f.value||"");var op=f.if_op||f.op;var na=num(base),nv=num(vv);var ok=false;
   if(op==="eq")ok=base===vv;else if(op==="ne")ok=base!==vv;else if(op==="contains")ok=vv&&base.indexOf(vv)>=0;else if(op==="gt")ok=(na!==null&&nv!==null&&na>nv);else if(op==="lt")ok=(na!==null&&nv!==null&&na<nv);
   return String(ok?(f.then||""):(f.else||""));}
  return "";
 }catch(e){return "";}
}
function summary(ty,f){
 var SYM={add:"+",sub:"−",mul:"×",div:"÷"};
 var OW={eq:"=",ne:"≠",contains:"содержит",gt:">",lt:"<"};
 if(ty==="ref")return 'Из таблицы «'+(ATABLES[+f.ref_table]||("№"+f.ref_table))+'»: где её «'+(f.match_remote||"?")+'» равно нашей «'+(f.match_local||"?")+'», показать «'+(f.show||"?")+'»';
 if(f.kind==="arith")return lit(f.a)+" "+(SYM[f.op]||f.op||"?")+" "+lit(f.b);
 if(f.kind==="concat")return "склейка: "+lit(f.a)+" + "+lit(f.b);
 if(f.kind==="days")return "дней между "+lit(f.a)+" и "+(String(f.b||"").trim()?lit(f.b):"сегодня");
 if(f.kind==="if")return "если «"+(f.col||"?")+"» "+(OW[f.if_op||f.op]||"?")+" «"+(f.value||"")+"» то «"+(f.then||"")+"» иначе «"+(f.else||"")+"»";
 return "выберите вид формулы";
}
function ensureRemote(rt){
 if(!rt||remotes[rt])return;
 remotes[rt]={rows:[],cols:[]};
 fetch(SPREFIX+rt+"/sample").then(function(r){return r.json();}).then(function(j){remotes[rt]=j;update();}).catch(function(){});
}
function update(){
 var ty=ctype?ctype.value:"";
 if(ty!=="computed"&&ty!=="ref"){box.style.display="none";return;}
 box.style.display="";
 if(!sample){document.getElementById('fprevnote').textContent="Загружаю строки для примера…";return;}
 var f=readF();
 var rt=+f.ref_table||0;
 if(ty==="ref")ensureRemote(rt);
 var remote=(ty==="ref"&&remotes[rt])?remotes[rt].rows:[];
 document.getElementById('fprevsum').textContent=summary(ty,f);
 var rows=sample.rows;
 if(!rows.length){document.getElementById('fprevrows').innerHTML='<div class="note">Строк пока нет — пример появится с первой строкой.</div>';return;}
 var h='<table><tr><th>Строка</th><th>Результат</th></tr>';
 for(var i=0;i<rows.length;i++){
  var lab=[];for(var j=0;j<Math.min(2,sample.cols.length);j++){var k=sample.cols[j].k;var v=rows[i].data[k];if(v)lab.push(String(v));}
  h+='<tr><td>'+(lab.join(" · ")||("№"+rows[i].id))+'</td><td class="res">'+(compute(ty,f,rows[i].data,remote)||"∅")+'</td></tr>';
 }
 document.getElementById('fprevrows').innerHTML=h+"</table>";
}
fetch(SAMPLE).then(function(r){return r.json();}).then(function(j){sample=j;update();}).catch(function(){
 box.style.display="";document.getElementById('fprevnote').textContent="Не удалось загрузить строки для примера (эндпоинт /sample).";});
form.addEventListener("input",update);
form.addEventListener("change",update);
update();
}catch(err){
 var b2=document.createElement('div');b2.className='fprev';b2.style.display='';
 b2.innerHTML='<div class="note" style="color:#c0392b;font-weight:600">Превью не стартовало: '+String(err&&err.message?err.message:err)+'</div>';
 var h2=document.querySelector('[name="kind"]');
 if(h2){var hs=h2.closest('fieldset')||h2.closest('.form-row')||h2.parentNode;hs.parentNode.insertBefore(b2,hs.nextSibling);}
}
}
if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",boot);}else{boot();}
})();
</script>
'''
cp = os.path.join(BASE, "modules", "tables", "templates", "tables", "cols.html")
s = open(cp, encoding="utf-8").read()
if "fprev-v1" in s:
    s2 = re.sub(r'<div id="fprev"[\s\S]*?</script>\s*', '', s, count=1)
    if s2 != s:
        s = s2
        print("PATCH cols.html: broken v1 preview block removed")
if "fprev-v2" in s:
    print("SKIP cols.html: fprev-v2 present")
else:
    idx = s.rfind("{% endblock %}")
    if idx != -1:
        s = s[:idx] + V2.strip("\n") + "\n" + s[idx:]
        open(cp, "w", encoding="utf-8", newline="\n").write(s)
        print("PATCH cols.html: self-building live preview script injected")
    else:
        print("WARN cols.html: endblock not found")

st = os.path.join(BASE, "web", "static", "css", "style.css")
c = open(st, encoding="utf-8").read()
if "fprev-css" not in c:
    c = c.rstrip("\n") + '''
/* fprev-css: panel' zhivogo primera formuly */
.fprev{margin:14px 0;padding:14px 16px;background:#f4f8ff;border:1px solid #cfe0f7;border-left:4px solid #2196f3;border-radius:8px}
.fprev h3{color:#1976d2;font-size:13px;text-transform:uppercase;letter-spacing:.3px;margin-bottom:8px}
.fprev-sum{font-size:14px;font-weight:600;margin-bottom:8px}
.fprev table{font-size:13px;width:auto}
.fprev td,.fprev th{padding:5px 10px}
.fprev .res{font-weight:700;color:#1976d2}
'''
    open(st, "w", encoding="utf-8", newline="\n").write(c)
    print("PATCH style.css: fprev styles")
else:
    print("SKIP style.css: fprev-css present")

dk = os.path.join(BASE, "web", "static", "css", "dark.css")
c = open(dk, encoding="utf-8").read()
if "fprev-dark" not in c:
    c = c.rstrip("\n") + '''
/* fprev-dark */
body.dark .fprev{background:#1c2733;border-color:#2b3646;border-left-color:#3b82f6}
body.dark .fprev h3{color:#60a5fa}
body.dark .fprev .res{color:#60a5fa}
'''
    open(dk, "w", encoding="utf-8", newline="\n").write(c)
    print("PATCH dark.css: fprev dark styles")
else:
    print("SKIP dark.css: fprev-dark present")

hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
v = open(hp, encoding="utf-8").read()
m = re.search(r'_B64\s*=\s*"([^"]*)"', v)
data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.14" for r in data["releases"]):
    data["releases"].insert(0, {"version": "0.13.14", "release_date": "2026-11-18", "status": "released",
        "title": "Живой пример формулы заработал (панель создаёт себя сама)",
        "notes": "Первая версия живого примера не появлялась: строка со списком таблиц собиралась в JavaScript без фигурных скобок, скрипт падал с синтаксической ошибкой ещё до старта. Теперь панель примера создаётся самим скриптом и встаёт сразу после блока «Конструктор формулы», старая битая вставка удаляется, а при любом сбое панель показывает текст своей ошибки. Пример пересчитывает арифметику, склейку, дни и ЕСЛИ на первых пяти строках до сохранения; сравнение в «ЕСЛИ» читается из if_op."})
    data["changelog"].insert(0, {"date": "2026-11-18", "author": "синхронизация документации", "change_type": "fixed",
        "module": "tables", "ticket": "",
        "description": "Живой пример формулы: панель создаётся скриптом после блока «Конструктор формулы» (исправлена синтаксическая ошибка сборки списка таблиц), при сбое показывает текст ошибки на странице."})
    nb = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
    v = v[:m.start(1)] + nb + v[m.end(1):]
    open(hp, "w", encoding="utf-8", newline="\n").write(v)
    print("PATCH history_seed.py: release 0.13.14")
else:
    print("SKIP history_seed.py: 0.13.14 present")

print("=" * 60)
print("MARKER_END: self-building formula preview (0.13.14)")
print("=" * 60)
print("Commit + Push:")
print("  modules/tables/service.py")
print("  modules/tables/sheet_routes.py")
print("  modules/tables/templates/tables/cols.html")
print("  web/static/css/style.css")
print("  web/static/css/dark.css")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")