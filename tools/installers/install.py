# -*- coding: utf-8 -*-
import os, re, json, base64
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d: break
    d = p
BASE = d
print("ROOT: " + BASE)

# 1. base.html: knopka "naverh" na vseh stranitsah.
bp = os.path.join(BASE, "web", "templates", "base.html")
s = open(bp, encoding="utf-8").read()
TOTOP = '''<button id="totop" title="Наверх" aria-label="Наверх">↑</button>
<script>
/* totop-v1 */
(function(){var b=document.getElementById("totop");if(!b)return;
function upd(){b.style.display=(window.scrollY>600)?"block":"none";}
window.addEventListener("scroll",upd,{passive:true});upd();
b.addEventListener("click",function(){window.scrollTo({top:0,behavior:"smooth"});});})();
</script>
'''
if "totop-v1" in s:
    print("SKIP base.html: totop present")
elif "</body>" in s:
    s = s.replace("</body>", TOTOP + "</body>", 1)
    open(bp, "w", encoding="utf-8", newline="\n").write(s)
    print("PATCH base.html: back-to-top button added")
else:
    print("WARN base.html: </body> not found")

st = os.path.join(BASE, "web", "static", "css", "style.css")
c = open(st, encoding="utf-8").read()
if "totop-css" not in c:
    c = c.rstrip("\n") + '''
/* totop-css: kruglaya knopka naverh */
#totop{position:fixed;right:18px;bottom:74px;z-index:70;width:44px;height:44px;border-radius:50%;
 border:none;cursor:pointer;display:none;font-size:20px;font-weight:700;color:#fff;
 background:linear-gradient(135deg,#667eea,#764ba2);box-shadow:0 8px 20px rgba(40,50,90,.35);
 transition:.15s}
#totop:hover{transform:translateY(-3px);box-shadow:0 12px 26px rgba(40,50,90,.45)}
@media print{#totop{display:none!important}}
'''
    open(st, "w", encoding="utf-8", newline="\n").write(c)
    print("PATCH style.css: totop styles")
else:
    print("SKIP style.css: totop-css present")

dk = os.path.join(BASE, "web", "static", "css", "dark.css")
c = open(dk, encoding="utf-8").read()
if "totop-dark" not in c:
    c = c.rstrip("\n") + '''
/* totop-dark */
body.dark #totop{background:linear-gradient(135deg,#3b4270,#4a2f63);color:#e7eaf0;box-shadow:0 8px 20px rgba(0,0,0,.5)}
'''
    open(dk, "w", encoding="utf-8", newline="\n").write(c)
    print("PATCH dark.css: totop dark styles")
else:
    print("SKIP dark.css: totop-dark present")

# 2. Diagnostika modulya manual: marshruty, shablony, stroka knopki pechati.
lines = []
mp = os.path.join(BASE, "modules", "manual")
if os.path.isdir(mp):
    rp = os.path.join(mp, "routes.py")
    if os.path.exists(rp):
        rt = open(rp, encoding="utf-8").read()
        lines.append("=== manual/routes.py: routes ===")
        for m in re.finditer(r"@[\w.]+\.route\(([^)]*)\)", rt):
            lines.append("ROUTE: " + m.group(1).strip())
        lines.append("=== manual/routes.py: print-related lines ===")
        for i, ln in enumerate(rt.splitlines(), 1):
            if "print" in ln.lower() or "pechat" in ln.lower():
                lines.append("%d: %s" % (i, ln.strip()))
    else:
        lines.append("WARN: modules/manual/routes.py not found")
    lines.append("=== manual templates ===")
    for root, dirs, files in os.walk(os.path.join(mp, "templates")):
        for f in files:
            lines.append(os.path.join(root, f).replace(BASE, ""))
    lines.append("=== button markup lines ===")
    for root, dirs, files in os.walk(os.path.join(mp, "templates")):
        for f in files:
            if not f.endswith(".html"):
                continue
            fp = os.path.join(root, f)
            tx = open(fp, encoding="utf-8").read()
            for i, ln in enumerate(tx.splitlines(), 1):
                if "печат" in ln or "print" in ln.lower():
                    lines.append("%s:%d: %s" % (f, i, ln.strip()))
else:
    lines.append("WARN: modules/manual dir not found")
rep = os.path.join(BASE, "_diag_manual.txt")
open(rep, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("DIAG written: " + rep)
for ln in lines:
    print("  | " + ln)

hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
v = open(hp, encoding="utf-8").read()
m = re.search(r'_B64\s*=\s*"([^"]*)"', v)
data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.18" for r in data["releases"]):
    data["releases"].insert(0, {"version": "0.13.18", "release_date": "2026-11-19", "status": "released",
        "title": "Кнопка «наверх» на всех страницах",
        "notes": "На длинных страницах (руководство, журнал, справки) снизу приходилось долго мотать к началу. Добавлена круглая кнопка «↑» справа внизу: появляется после прокрутки около 600 пикселей и плавно поднимает к началу страницы; на коротких страницах и в печати скрыта. Работает во всех модулях сразу, так как встроена в базовый шаблон."})
    data["changelog"].insert(0, {"date": "2026-11-19", "author": "синхронизация документации", "change_type": "added",
        "module": "web", "ticket": "",
        "description": "Глобальная кнопка «наверх» в базовом шаблоне: появляется после прокрутки 600px, плавный подъём, скрыта в печати и на коротких страницах."})
    nb = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
    v = v[:m.start(1)] + nb + v[m.end(1):]
    open(hp, "w", encoding="utf-8", newline="\n").write(v)
    print("PATCH history_seed.py: release 0.13.18")
else:
    print("SKIP history_seed.py: 0.13.18 present")

print("=" * 60)
print("MARKER_END: back-to-top button + manual diagnostics (0.13.18)")
print("=" * 60)
print("Commit + Push:")
print("  web/templates/base.html")
print("  web/static/css/style.css")
print("  web/static/css/dark.css")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")
print("  (_diag_manual.txt NE kommitim: on v .gitignore)")