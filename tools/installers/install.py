# -*- coding: utf-8 -*-
import os, re, json, base64
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d: break
    d = p
BASE = d
print("ROOT: " + BASE)

# 1. base.html: sbtoast zhimet dol'she, zamiraet pod kursorom, klik - skryt'.
bp = os.path.join(BASE, "web", "templates", "base.html")
s = open(bp, encoding="utf-8").read()
OLD = ('setTimeout(function(){t.style.opacity="0";t.style.transition=".4s";\n'
       '        setTimeout(function(){if(t.parentNode)t.remove();},450);},6000);}}')
NEW = ('t.title="Клик — скрыть";t.style.cursor="pointer"; /* sbtoast-hover-v1 */\n'
       '      var ttl=10000,left=ttl,t0=0,tmr=null;\n'
       '      function kill(){t.style.opacity="0";t.style.transition=".4s";setTimeout(function(){if(t.parentNode)t.remove();},450);}\n'
       '      function go(){t0=Date.now();tmr=setTimeout(kill,left);}\n'
       '      t.addEventListener("mouseenter",function(){clearTimeout(tmr);left-=Date.now()-t0;});\n'
       '      t.addEventListener("mouseleave",go);\n'
       '      t.addEventListener("click",kill);\n'
       '      go();}}')
if "sbtoast-hover-v1" in s:
    print("SKIP base.html: sbtoast hover-pause present")
elif OLD in s:
    s = s.replace(OLD, NEW, 1)
    open(bp, "w", encoding="utf-8", newline="\n").write(s)
    print("PATCH base.html: result toast 10s + hover-pause + click-to-close")
else:
    print("WARN base.html: sbtoast timer anchor not found")

# 2. sheet.js: tosty lista - to zhe povedenie.
jp = os.path.join(BASE, "web", "static", "js", "sheet.js")
s = open(jp, encoding="utf-8").read()
OLDJ = ('$("shtoasts").appendChild(t);setTimeout(function(){t.style.opacity="0";t.style.transition=".3s";setTimeout(function(){t.remove();},320);},action?8000:4200);}')
NEWJ = ('$("shtoasts").appendChild(t);\n'
        ' t.title="Клик — скрыть";t.style.cursor="pointer"; /* toast-hover-v1 */\n'
        ' var ttl=action?12000:8000,left=ttl,t0=0,tmr=null;\n'
        ' function kill(){if(!t.parentNode)return;t.style.opacity="0";t.style.transition=".3s";setTimeout(function(){if(t.parentNode)t.remove();},320);}\n'
        ' function go(){t0=Date.now();tmr=setTimeout(kill,left);}\n'
        ' t.addEventListener("mouseenter",function(){clearTimeout(tmr);left-=Date.now()-t0;});\n'
        ' t.addEventListener("mouseleave",go);\n'
        ' t.addEventListener("click",function(e){if(e.target.tagName!=="BUTTON")kill();});\n'
        ' go();}')
if "toast-hover-v1" in s:
    print("SKIP sheet.js: toast hover-pause present")
elif OLDJ in s:
    s = s.replace(OLDJ, NEWJ, 1)
    open(jp, "w", encoding="utf-8", newline="\n").write(s)
    print("PATCH sheet.js: sheet toasts 8s/12s + hover-pause + click-to-close")
else:
    print("WARN sheet.js: toast timer anchor not found")

hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
v = open(hp, encoding="utf-8").read()
m = re.search(r'_B64\s*=\s*"([^"]*)"', v)
data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.22" for r in data["releases"]):
    data["releases"].insert(0, {"version": "0.13.22", "release_date": "2026-11-19", "status": "released",
        "title": "Тосты не исчезают, пока их читают",
        "notes": "Тост результата («Строка сохранена.») жил 6 секунд и таял посреди чтения, тосты листа — ещё меньше. Теперь тост результата живёт 10 секунд, тосты листа 8 секунд (12 с кнопкой действия), таймер замирает, пока курсор наведён на тост, а клик по тосту закрывает его сразу. Кнопка действия внутри тоста работает как раньше."})
    data["changelog"].insert(0, {"date": "2026-11-19", "author": "синхронизация документации", "change_type": "changed",
        "module": "web", "ticket": "",
        "description": "Тосты (результат действия и листовые): увеличено время жизни, таймер замирает при наведении курсора, клик закрывает сразу — сообщение можно дочитать спокойно."})
    nb = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
    v = v[:m.start(1)] + nb + v[m.end(1):]
    open(hp, "w", encoding="utf-8", newline="\n").write(v)
    print("PATCH history_seed.py: release 0.13.22")
else:
    print("SKIP history_seed.py: 0.13.22 present")

print("=" * 60)
print("MARKER_END: toasts wait for the reader (0.13.22)")
print("=" * 60)
print("Commit + Push:")
print("  web/templates/base.html")
print("  web/static/js/sheet.js")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")