# -*- coding: utf-8 -*-
import os, re, json, base64
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d: break
    d = p
BASE = d
print("ROOT: " + BASE)

NEWSCRIPT = r'''<script>
/* cbuild-v3 */
(function(){
function JP(s){try{var v=JSON.parse(s);return Array.isArray(v)?v:[];}catch(e){return [];}}
function escq(s){return String(s==null?"":s).replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/</g,"&lt;");}
function boot(){
var box=document.getElementById("cbrows");
var ta=document.querySelector('textarea[name="counters"]');
var add=document.getElementById("cbadd");
if(!box||!ta){return;}
try{
var CCOLS=[{% for c in cols %}{k:{{ c.key|tojson }},t:{{ c.title|tojson }},ty:{{ c.col_type|tojson }},op:JP({{ c.options|tojson }})},{% endfor %}];
function colByKey(k){for(var i=0;i<CCOLS.length;i++){if(CCOLS[i].k===k)return CCOLS[i];}return null;}
function parse(){var out=[];var lines=ta.value.split("\n");
for(var i=0;i<lines.length;i++){var p=lines[i].split("|");
if(p.length>=3&&p[0].trim()&&p[2].trim()){out.push({title:p[0].trim(),func:(p[1]||"count").trim(),col:p[2].trim(),wcol:(p[3]||"").trim(),wval:(p[4]||"").trim()});}}
return out;}
var data=parse();
function colOpts(sel){var h="";for(var i=0;i<CCOLS.length;i++){var c=CCOLS[i];h+='<option value="'+c.k+'"'+(c.k===sel?" selected":"")+'>'+escq(c.t)+'</option>';}return h;}
function wcolOpts(sel){var h='<option value="">— без условия —</option>';for(var i=0;i<CCOLS.length;i++){var c=CCOLS[i];h+='<option value="'+c.k+'"'+(c.k===sel?" selected":"")+'>'+escq(c.t)+'</option>';}return h;}
function valField(r){var c=colByKey(r.wcol);
if(c&&c.ty==="list"){var h='<select class="cb-val"><option value="">—</option>';var ops=c.op||[];for(var i=0;i<ops.length;i++){h+='<option'+(ops[i]===r.wval?" selected":"")+'>'+escq(ops[i])+'</option>';}return h+'</select>';}
return '<input type="text" class="cb-val" value="'+escq(r.wval)+'" placeholder="значение">';}
function render(){
if(!data.length){box.innerHTML='<div class="note">Счётчиков пока нет — нажми «＋ Добавить счётчик».</div>';return;}
var h="";
for(var i=0;i<data.length;i++){var r=data[i];
h+='<div class="cb-row" data-i="'+i+'">'
+'<input type="text" class="cb-title" value="'+escq(r.title)+'" placeholder="Название карточки">'
+'<select class="cb-func"><option value="count"'+(r.func==="count"?" selected":"")+'>сколько строк</option><option value="sum"'+(r.func==="sum"?" selected":"")+'>сумма чисел</option></select>'
+'<select class="cb-col">'+colOpts(r.col)+'</select>'
+'<select class="cb-wcol">'+wcolOpts(r.wcol)+'</select>'
+valField(r)
+'<button type="button" class="btn red cb-del" title="Убрать счётчик">✕</button></div>';}
box.innerHTML=h;}
function sync(){var out=[];for(var i=0;i<data.length;i++){var r=data[i];out.push([r.title,r.func,r.col,r.wcol,r.wval].join("|"));}ta.value=out.join("\n");}
box.addEventListener("input",function(e){var row=e.target.closest(".cb-row");if(!row)return;var r=data[+row.getAttribute("data-i")];if(!r)return;
if(e.target.classList.contains("cb-title")){r.title=e.target.value;}
else if(e.target.classList.contains("cb-val")){r.wval=e.target.value;}
sync();});
box.addEventListener("change",function(e){var row=e.target.closest(".cb-row");if(!row)return;var r=data[+row.getAttribute("data-i")];if(!r)return;
if(e.target.classList.contains("cb-func")){r.func=e.target.value;}
else if(e.target.classList.contains("cb-col")){r.col=e.target.value;}
else if(e.target.classList.contains("cb-wcol")){r.wcol=e.target.value;r.wval="";render();}
else if(e.target.classList.contains("cb-val")){r.wval=e.target.value;}
sync();});
box.addEventListener("click",function(e){var b=e.target.closest(".cb-del");if(!b)return;var row=b.closest(".cb-row");if(!row)return;
data.splice(+row.getAttribute("data-i"),1);render();sync();});
if(add){add.addEventListener("click",function(){data.push({title:"",func:"count",col:CCOLS.length?CCOLS[0].k:"",wcol:"",wval:""});render();sync();});}
if(!ta.closest("details")){var det=document.createElement("details");det.className="cb-raw";
var sum=document.createElement("summary");sum.textContent="Технический формат (строки через |) — заполняется сам";
ta.parentNode.insertBefore(det,ta);det.appendChild(sum);det.appendChild(ta);}
render();sync();
}catch(err){
box.innerHTML='<div class="note" style="color:#c0392b;font-weight:600">Конструктор не запустился: '+escq(err&&err.message?err.message:err)+'. Техническое поле ниже работает по-прежнему.</div>';
}
}
if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",boot);}else{boot();}
})();
</script>'''

cp = os.path.join(BASE, "modules", "tables", "templates", "tables", "cols.html")
s = open(cp, encoding="utf-8").read()
if "cbuild-v3" in s:
    print("SKIP cols.html: cbuild-v3 script present")
else:
    pat = re.compile(r'(<div id="cbuilder"[\s\S]*?</div>\s*)<script>[\s\S]*?</script>')
    s2, n = pat.subn(lambda m: m.group(1) + NEWSCRIPT, s, count=1)
    if n:
        open(cp, "w", encoding="utf-8", newline="\n").write(s2)
        print("PATCH cols.html: counter builder script rewritten (cbuild-v3, self-diagnosing)")
    else:
        print("WARN cols.html: cbuilder div+script block not found")

hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
v = open(hp, encoding="utf-8").read()
m = re.search(r'_B64\s*=\s*"([^"]*)"', v)
data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.12" for r in data["releases"]):
    data["releases"].insert(0, {"version": "0.13.12", "release_date": "2026-11-18", "status": "released",
        "title": "Конструктор счётчиков переписан начисто и сам показывает ошибки",
        "notes": "Скрипт визуального конструктора счётчиков переписан одним цельным блоком вместо накопленных точечных заплат: инициализация по готовности DOM, безопасный разбор опций колонок, обработчики добавления/удаления/правки строк-счётчиков внутри защищённого блока. Если конструктор всё же не сможет стартовать, он пишет текст своей ошибки красным прямо в блок счётчиков, а техническое поле продолжает работать — диагностика больше не требует консоли."})
    data["changelog"].insert(0, {"date": "2026-11-18", "author": "синхронизация документации", "change_type": "fixed",
        "module": "tables", "ticket": "",
        "description": "Конструктор счётчиков: скрипт переписан начисто (cbuild-v3) с самодиагностикой — ошибка старта видна на странице красным текстом, кнопка «＋ Добавить счётчик» и строки-счётчики работают внутри защищённой инициализации."})
    nb = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
    v = v[:m.start(1)] + nb + v[m.end(1):]
    open(hp, "w", encoding="utf-8", newline="\n").write(v)
    print("PATCH history_seed.py: release 0.13.12")
else:
    print("SKIP history_seed.py: 0.13.12 present")

print("=" * 60)
print("MARKER_END: counter builder rewritten self-diagnosing (0.13.12)")
print("=" * 60)
print("Commit + Push:")
print("  modules/tables/templates/tables/cols.html")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")