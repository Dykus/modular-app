# -*- coding: utf-8 -*-
import os, re, json, base64
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d: break
    d = p
BASE = d
print("ROOT: " + BASE)

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

V3 = r'''
<script>
/* fprev-v3 */
(function(){
var SAMPLE="{{ url_for('tables.sample', tid=t.id) }}";
var SPREFIX="{{ url_for('tables.index') }}";
var ATABLES={ {% for x in all_tables %}{{ x.id|tojson }}:{{ x.title|tojson }},{% endfor %} };
function boot(){
try{
var old=document.getElementById('fprev');if(old&&old.parentNode)old.parentNode.removeChild(old);
var kind=document.querySelector('[name="kind"]');
if(!kind||!kind.form)return;
var form=kind.form;
var ctype=form.querySelector('[name="col_type"]');
function el(n){return form.querySelector('[name="'+n+'"]');}
var F={op:el('op'),a:el('a'),b:el('b'),ifcol:el('if_col'),ifop:el('if_op'),ifval:el('if_val'),
 thenv:el('then_v'),elsev:el('else_v'),reftable:el('ref_table'),mloc:el('match_local'),
 mrem:el('match_remote'),show:el('show'),opts:el('options')};
function head(){var d=document.createElement('div');d.className='ghead';return d;}
var hA=head(),hI=head(),hR=head();
if(F.op&&F.op.parentNode)F.op.parentNode.insertBefore(hA,F.op);
if(F.ifcol&&F.ifcol.parentNode)F.ifcol.parentNode.insertBefore(hI,F.ifcol);
if(F.reftable&&F.reftable.parentNode)F.reftable.parentNode.insertBefore(hR,F.reftable);
var box=document.createElement('div');box.id='fprev';box.className='fprev';box.style.display='none';
box.innerHTML='<h3>Живой пример: что посчитает формула</h3><div class="fprev-sum" id="fprevsum"></div><div id="fprevrows"></div><div class="note" id="fprevnote"></div>';
var fs=kind.closest('fieldset')||kind.closest('.form-row')||kind.parentNode;
fs.parentNode.insertBefore(box,fs.nextSibling);
function vis(e,on){if(e)e.style.display=on?"":"none";}
function regroup(){
 var ty=ctype?ctype.value:"text";
 var isList=(ty==="list"),isCalc=(ty==="computed"),isRef=(ty==="ref");
 vis(F.opts,isList);
 if(F.opts){var hd=F.opts.previousElementSibling;
  if(hd&&/Варианты списка/.test(hd.textContent||""))vis(hd,isList);}
 var fset=kind.closest('fieldset');if(fset)vis(fset,isCalc||isRef);
 var k=kind.value||"arith";
 vis(kind,isCalc);
 var showAB=isCalc&&(k==="arith"||k==="concat"||k==="days");
 vis(F.op,isCalc&&k==="arith");vis(F.a,showAB);vis(F.b,showAB);vis(hA,showAB);
 if(k==="arith")hA.textContent="Выражение над колонками (или числами)";
 else if(k==="concat")hA.textContent="Что склеиваем: сначала A, потом B";
 else hA.textContent="Между какими датами считаем дни (B пусто — до сегодня)";
 var showIf=isCalc&&k==="if";
 vis(F.ifcol,showIf);vis(F.ifop,showIf);vis(F.ifval,showIf);vis(F.thenv,showIf);vis(F.elsev,showIf);vis(hI,showIf);
 hI.textContent="Условие: если колонка … сравнение … значение … то ТО иначе ИНАЧЕ";
 var showRef=isRef;
 vis(F.reftable,showRef);vis(F.mloc,showRef);vis(F.mrem,showRef);vis(F.show,showRef);vis(hR,showRef);
 hR.textContent="Ссылка (как ВПР): найди строку в другой таблице по совпадению ключа и покажи её колонку";
}
var sample=null,remotes={};
function val(n){var e=el(n);return e?e.value:"";}
function num(v){v=String(v==null?"":v).replace(/\s/g,"").replace(",",".");var n=parseFloat(v);return isNaN(n)?null:n;}
function dparse(v){v=String(v||"").trim();var m=v.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);if(m)return new Date(+m[3],+m[2]-1,+m[1]);var m2=v.match(/^(\d{4})-(\d{2})-(\d{2})$/);if(m2)return new Date(+m2[1],+m2[2]-1,+m2[3]);return null;}
function fnum(x){if(x===null||x===undefined)return "";if(x===Math.round(x))return String(x);return String(Math.round(x*100)/100);}
function tok(t,dd){t=String(t==null?"":t).trim();if(Object.prototype.hasOwnProperty.call(dd,t))return String(dd[t]==null?"":dd[t]);return t;}
function colTitle(k){if(sample){for(var i=0;i<sample.cols.length;i++)if(sample.cols[i].k===k)return sample.cols[i].t;}return k;}
function isCol(k){if(sample){for(var i=0;i<sample.cols.length;i++)if(sample.cols[i].k===k)return true;}return false;}
function lit(k){k=String(k==null?"":k).trim();if(!k)return "…";return isCol(k)?("«"+colTitle(k)+"»"):("«"+k+"» (литерал)");}
function readF(){return {kind:val('kind'),op:val('op'),a:val('a'),b:val('b'),col:val('if_col'),if_op:val('if_op'),value:val('if_val'),then:val('then_v'),else:val('else_v'),ref_table:val('ref_table'),match_local:val('match_local'),match_remote:val('match_remote'),show:val('show')};}
function missing(f,ty){
 if(ty==="ref"){var n=[];if(!+f.ref_table)n.push("таблицу");if(!String(f.match_local||"").trim())n.push("наш ключ");if(!String(f.match_remote||"").trim())n.push("ключ там");if(!String(f.show||"").trim())n.push("что показать");return n;}
 if(f.kind==="arith"){var m=[];if(!String(f.a||"").trim())m.push("A");if(!String(f.b||"").trim())m.push("B");return m;}
 if(f.kind==="days")return String(f.a||"").trim()?[]:["A"];
 if(f.kind==="if")return String(f.col||"").trim()?[]:["колонку условия"];
 return [];
}
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
 if(ty==="ref")return 'Из таблицы «'+(ATABLES[+f.ref_table]||"…")+'»: где её «'+(f.match_remote||"…")+'» равно нашей «'+(f.match_local||"…")+'», показать «'+(f.show||"…")+'»';
 if(f.kind==="arith")return lit(f.a)+" "+(SYM[f.op]||"…")+" "+lit(f.b);
 if(f.kind==="concat")return "склейка: "+lit(f.a)+" + "+lit(f.b);
 if(f.kind==="days")return "дней между "+lit(f.a)+" и "+(String(f.b||"").trim()?lit(f.b):"сегодня");
 if(f.kind==="if")return "если «"+(f.col||"…")+"» "+(OW[f.if_op||f.op]||"…")+" «"+(f.value||"…")+"» то «"+(f.then||"…")+"» иначе «"+(f.else||"…")+"»";
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
 var note=document.getElementById('fprevnote');
 if(!sample){note.textContent="Загружаю строки для примера…";return;}
 var f=readF();
 var miss=missing(f,ty);
 var rt=+f.ref_table||0;
 if(ty==="ref")ensureRemote(rt);
 var remote=(ty==="ref"&&remotes[rt])?remotes[rt].rows:[];
 document.getElementById('fprevsum').textContent=summary(ty,f);
 var rows=sample.rows;
 if(!rows.length){document.getElementById('fprevrows').innerHTML='<div class="note">Строк пока нет — пример появится с первой строкой.</div>';note.textContent="";return;}
 var h='<table><tr><th>Строка</th><th>Результат</th></tr>';
 for(var i=0;i<rows.length;i++){
  var lab=[];for(var j=0;j<Math.min(2,sample.cols.length);j++){var k=sample.cols[j].k;var v=rows[i].data[k];if(v)lab.push(String(v));}
  var res=miss.length?"…":(compute(ty,f,rows[i].data,remote)||"—");
  h+='<tr><td>'+(lab.join(" · ")||("№"+rows[i].id))+'</td><td class="res">'+res+'</td></tr>';
 }
 document.getElementById('fprevrows').innerHTML=h+"</table>";
 note.textContent=miss.length?("Не хватает: "+miss.join(", ")+". Заполните — и пример посчитается сразу.")
  :"Пример пересчитывается при каждом изменении полей и НЕ сохраняется до «Сохранить колонку».";
}
fetch(SAMPLE).then(function(r){return r.json();}).then(function(j){sample=j;update();}).catch(function(){
 box.style.display="";document.getElementById('fprevnote').textContent="Не удалось загрузить строки для примера (эндпоинт /sample).";});
form.addEventListener("input",function(){regroup();update();});
form.addEventListener("change",function(){regroup();update();});
regroup();update();
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
if "fprev-v2" in s:
    s2 = re.sub(r'<script>\s*/\* fprev-v2 \*/[\s\S]*?</script>\s*', '', s, count=1)
    if s2 != s:
        s = s2
        print("PATCH cols.html: v2 preview script removed")
if "fprev-v3" in s:
    print("SKIP cols.html: fprev-v3 present")
else:
    idx = s.rfind("{% endblock %}")
    if idx != -1:
        s = s[:idx] + V3.strip("\n") + "\n" + s[idx:]
        open(cp, "w", encoding="utf-8", newline="\n").write(s)
        print("PATCH cols.html: human formula constructor (v3) injected")
    else:
        print("WARN cols.html: endblock not found")

st = os.path.join(BASE, "web", "static", "css", "style.css")
c = open(st, encoding="utf-8").read()
if "ghead-css" not in c:
    c = c.rstrip("\n") + '''
/* ghead-css: chelovecheskie podzagolovki grupp formuly */
.ghead{font-size:11px;text-transform:uppercase;letter-spacing:.4px;color:#5a6b85;margin:12px 0 4px;font-weight:700;width:100%}
.fprev .res{font-weight:700;color:#1976d2}
.fprev td,.fprev th{padding:5px 10px}
'''
    open(st, "w", encoding="utf-8", newline="\n").write(c)
    print("PATCH style.css: ghead styles")
else:
    print("SKIP style.css: ghead-css present")

dk = os.path.join(BASE, "web", "static", "css", "dark.css")
c = open(dk, encoding="utf-8").read()
if "ghead-dark" not in c:
    c = c.rstrip("\n") + '''
/* ghead-dark */
body.dark .ghead{color:#9aa3b2}
body.dark .fprev .res{color:#60a5fa}
'''
    open(dk, "w", encoding="utf-8", newline="\n").write(c)
    print("PATCH dark.css: ghead dark styles")
else:
    print("SKIP dark.css: ghead-dark present")

hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
v = open(hp, encoding="utf-8").read()
m = re.search(r'_B64\s*=\s*"([^"]*)"', v)
data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.15" for r in data["releases"]):
    data["releases"].insert(0, {"version": "0.13.15", "release_date": "2026-11-18", "status": "released",
        "title": "Конструктор формулы по-человечески: только нужные поля",
        "notes": "Раньше конструктор формулы показывал все поля сразу (арифметика, ЕСЛИ и ссылка друг под другом), а живой пример на пустых полях писал «» (литерал) и ∅ — это запутывало. Теперь видны только поля выбранного вида формулы, над группами появились человеческие подзаголовки («Выражение над колонками», «Условие: если…», «Ссылка (как ВПР)…»), блок «Варианты списка» показывается только для типа «Список», а живой пример вместо ∅ подсказывает, чего не хватает («Не хватает: A, B — заполните, и пример посчитается сразу»)."})
    data["changelog"].insert(0, {"date": "2026-11-18", "author": "синхронизация документации", "change_type": "changed",
        "module": "tables", "ticket": "",
        "description": "Конструктор формулы показывает только поля выбранного вида с человеческими подзаголовками; живой пример подсказывает недостающие поля вместо ∅; «Варианты списка» видны только для типа «Список»."})
    nb = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
    v = v[:m.start(1)] + nb + v[m.end(1):]
    open(hp, "w", encoding="utf-8", newline="\n").write(v)
    print("PATCH history_seed.py: release 0.13.15")
else:
    print("SKIP history_seed.py: 0.13.15 present")

print("=" * 60)
print("MARKER_END: human formula constructor (0.13.15)")
print("=" * 60)
print("Commit + Push:")
print("  modules/tables/service.py")
print("  modules/tables/sheet_routes.py")
print("  modules/tables/templates/tables/cols.html")
print("  web/static/css/style.css")
print("  web/static/css/dark.css")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")