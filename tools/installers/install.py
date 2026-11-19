# -*- coding: utf-8 -*-
import os, re, json, base64
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d: break
    d = p
BASE = d
print("ROOT: " + BASE)

V2 = r'''
<script>
/* colwidth-ui-v2: pole "Širina, px" vo VSEH formah kolonok (novaja i pravka),
   vstavljaetsya PERED knopkami, sohranjaet čerez POST /width (0 = avto). */
(function(){
function boot(){
 var m=location.pathname.match(/\/tables\/(\d+)/);if(!m)return;
 var tid=m[1];
 var forms=document.querySelectorAll("form");
 var made=0;
 for(var fi=0;fi<forms.length;fi++){
  var form=forms[fi];
  var keyIn=form.querySelector('[name="key"]');
  var titleIn=form.querySelector('[name="title"]');
  if(!keyIn||!titleIn)continue;
  if(form.querySelector(".cw-field"))continue; /* guard ot dublej */
  var uid="cw"+fi;
  var row=document.createElement("div");
  row.className="form-row cw-field";
  row.style.cssText="margin-top:10px;padding:10px 12px;background:#f4f8ff;border:1px solid #cfe0f7;border-left:4px solid #2196f3;border-radius:8px;display:flex;gap:10px;align-items:center;flex-wrap:wrap";
  row.innerHTML='<label style="display:inline-flex;gap:8px;align-items:center;font-size:13px;font-weight:700;color:#1565c0">'
   +'↔ Ширина, px'
   +'<input type="number" min="0" max="1200" step="1" id="'+uid+'" class="cw-in" value="0" style="width:80px;padding:6px 8px;border:1px solid #90caf9;border-radius:7px;font-weight:700">'
   +'<span class="note" style="margin:0;font-weight:400">0 = авто · тяни границу в листе · видят все</span></label>'
   +'<button type="button" class="btn cw-save" data-uid="'+uid+'">💾 Ширина</button>'
   +'<span class="note cw-msg" id="'+uid+'msg" style="margin:0"></span>';
  /* vstavka pered blokami knopok, esli naideny; inache v konec formy */
  var saveBtn=null, btns=form.querySelectorAll("button");
  for(var bi=0;bi<btns.length;bi++){ if(/сохран/i.test(btns[bi].textContent||"")){saveBtn=btns[bi];break;} }
  if(saveBtn){
   var host=(saveBtn.parentNode&&saveBtn.parentNode!==form)?saveBtn.parentNode:saveBtn;
   form.insertBefore(row,host);
  } else { form.appendChild(row); }
  made++;
  (function(form,keyIn,uid){
   var inp=form.querySelector("#"+uid);
   var msg=form.querySelector("#"+uid+"msg");
   function curKey(){return (keyIn.value||"").trim();}
   function load(){
    var k=curKey(); if(!k){inp.value="0";return;}
    fetch("/tables/"+tid+"/widths").then(function(r){return r.json();}).then(function(j){
     inp.value=(j.widths&&j.widths[k])?j.widths[k]:"0";
    }).catch(function(){});
   }
   keyIn.addEventListener("change",load);
   form.querySelector(".cw-save").addEventListener("click",function(){
    var k=curKey(); if(!k){msg.textContent="сначала укажите ключ колонки";msg.style.color="#c0392b";return;}
    var w=parseInt(inp.value,10)||0;
    fetch("/tables/"+tid+"/width",{method:"POST",
     headers:{"Content-Type":"application/json","X-Requested-With":"fetch"},
     body:JSON.stringify({key:k,width:w})})
     .then(function(r){return r.json();})
     .then(function(j){
      if(j&&j.ok){msg.textContent=w>0?("ширина "+w+" px сохранена"):"сброшено на авто";msg.style.color="#27ae60";}
      else{msg.textContent="нет права управлять колонками";msg.style.color="#c0392b";}
     }).catch(function(){msg.textContent="нет связи";msg.style.color="#c0392b";});
   });
   load();
  })(form,keyIn,uid);
 }
 if(!made){var n=document.querySelector(".cw-note");if(!n){n=document.createElement("div");n.className="note cw-note";n.textContent="Поле ширины появится в форме колонки (создание/правка).";var eb=document.querySelector("form");if(eb&&eb.parentNode)eb.parentNode.insertBefore(n,eb);}}
}
if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",boot);}else{boot();}
})();
</script>
'''

cp = os.path.join(BASE, "modules", "tables", "templates", "tables", "cols.html")
s = open(cp, encoding="utf-8").read()
chg = 0
# 1. Vyrezat' mertvyj v1 (doписан posle {% endblock %}).
dead = re.search(r'<script>\s*/\* colwidth-ui-v1 \*/[\s\S]*?</script>\s*', s)
if dead:
    s = s[:dead.start()] + s[dead.end():]
    chg += 1
    print("PATCH cols.html: dead colwidth-ui-v1 (after endblock) removed")
elif "colwidth-ui-v1" in s:
    print("WARN cols.html: v1 marker present but no <script> block matched")
else:
    print("SKIP cols.html: no dead v1 block")
# 2. Vstavit' živoj v2 PERED {% endblock %} (kak colmove/grpui).
if "colwidth-ui-v2" in s:
    print("SKIP cols.html: colwidth-ui-v2 already present")
else:
    idx = s.rfind("{% endblock %}")
    if idx != -1:
        s = s[:idx] + V2.strip("\n") + "\n" + s[idx:]
        chg += 1
        print("PATCH cols.html: colwidth-ui-v2 inserted before endblock (live)")
    else:
        print("WARN cols.html: {% endblock %} anchor not found — v2 NOT inserted")
if chg:
    open(cp, "w", encoding="utf-8", newline="\n").write(s)
else:
    print("NOTE cols.html: nothing changed")

# 3. history_seed: reliz 0.13.28.
hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
v = open(hp, encoding="utf-8").read()
m = re.search(r'_B64\s*=\s*"([^"]*)"', v)
data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.28" for r in data["releases"]):
    data["releases"].insert(0, {"version": "0.13.28", "release_date": "2026-11-19", "status": "released",
        "title": "Поле ширины в форме колонки заработало (было дописано после endblock)",
        "notes": "В 0.13.27 поле «Ширина, px» в экране «Колонки и формулы» не появлялось, хотя перетаскивание границы в листе работало: скрипт был дописан в конец файла cols.html, то есть после тега {% endblock %}, и Jinja его не рендерила (в отличие от работающих кнопок ↑↓ и панели групп, которые вставлены перед endblock). Мёртвый блок удалён, живой переписан: поле ширины добавляется во все формы колонки (создание и правка) с уникальными id и защитой от дублей, вставляется перед кнопками «Сохранить/Сброс» с заметным оформлением, сохраняет через отдельный POST /width (0 = авто, право tables.manage). Лист, форма и рабочие маршруты не изменялись."})
    data["changelog"].insert(0, {"date": "2026-11-19", "author": "синхронизация документации", "change_type": "fixed",
        "module": "tables", "ticket": "",
        "description": "Колонки и формулы: поле «Ширина, px» в форме колонки починено — скрипт перенесён с конца файла (после endblock, мёртв) на вставку перед endblock; добавлен во все формы колонки, вставляется перед кнопками, сохраняет через POST /width."})
    nb = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
    v = v[:m.start(1)] + nb + v[m.end(1):]
    open(hp, "w", encoding="utf-8", newline="\n").write(v)
    print("PATCH history_seed.py: release 0.13.28")
else:
    print("SKIP history_seed.py: 0.13.28 present")

print("=" * 60)
print("MARKER_END: column width field in cols.html fixed (0.13.28)")
print("=" * 60)
print("Commit + Push:")
print("  modules/tables/templates/tables/cols.html")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")