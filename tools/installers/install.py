import os, subprocess, sys
from sqlalchemy import text

d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d:
        break
    d = p
BASE = d
print("Корень проекта: " + BASE)

# =========================================================================
# ШАГ A. Миграция данных: у локального admin выставить must_change_password=1,
# если он 0/NULL (колонка добавилась позже и SQLite дал 0 старым строкам).
# Идемпотентно: повторный запуск трогает 0 строк.
# =========================================================================
print("")
print("Миграция флага смены пароля...")
print("-" * 50)
sys.path.insert(0, BASE)
from core.app import create_app, db
app = create_app()
with app.app_context():
    res = db.session.execute(text(
        "UPDATE user SET must_change_password=1 "
        "WHERE username='admin' AND (must_change_password=0 OR must_change_password IS NULL)"
    ))
    db.session.commit()
    n = res.rowcount or 0
    print("  admin: флаг выставлен, затронутых строк = %d" % n)
    if n == 0:
        print("  (уже был 1 — ничего не меняли; если смены всё равно нет, виновник перехват, не данные)")
print("-" * 50)

# =========================================================================
# ШАГ B. Релиз 0.12.9 + журнал — в СТАТИЧЕСКИЙ history_seed.py (едет через Git).
# Никаких sync_*.py в корне: они в .gitignore и на сервер не приедут.
# =========================================================================
hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
if os.path.exists(hp):
    hsrc = open(hp, encoding="utf-8").read()
    if '"0.12.9"' not in hsrc:
        rel_block = (
            'RELEASES = [\n'
            '{"version": "0.12.9", "release_date": "2026-11-18", "status": "released",\n'
            ' "title": "Принудительная смена пароля работает на старых базах",\n'
            ' "notes": "Колонка must_change_password добавлялась в модель позже, чем на мастерской/сервере уже жил admin, и SQLite подставил старым строкам 0 (False) — из-за этого система не требовала сменить пароль при первом входе, хотя код перехвата был верен. Разовая идемпотентная миграция выставляет флаг admin=1 на существующих базах; на чистых базаг seed и так ставит 1. Попутно исправлено сообщение про занятый порт (вместо %d теперь реальное число)."},\n'
        )
        hsrc = hsrc.replace("RELEASES = [\n", rel_block, 1)
        cl_block = (
            'CHANGELOG = [\n'
            '{"date": "2026-11-18", "author": "синхронизация документации", "change_type": "fixed", "module": "core", "ticket": "", "description": "Принудительная смена пароля при первом входе заработала на существующих базах: разовая миграция выставляет must_change_password=1 для admin, которому колонка, добавленная позже модели, досталась со значением 0."},\n'
            '{"date": "2026-11-18", "author": "синхронизация документации", "change_type": "fixed", "module": "core", "ticket": "", "description": "В сообщении про занятый порт в серверном режиме вместо литерала %d теперь подставляется реальный номер порта."},\n'
        )
        hsrc = hsrc.replace("CHANGELOG = [\n", cl_block, 1)
        open(hp, "w", encoding="utf-8", newline="\n").write(hsrc)
        print("  + history_seed.py: релиз 0.12.9 и 2 записи журнала дописаны (в Git)")
    else:
        print("  = history_seed.py: 0.12.9 уже есть")
else:
    print("  ! history_seed.py не найден — сначала примени установщик 0.12.6+")

# =========================================================================
# ШАГ C. Мелкий фикс run.py: %d -> реальное число порта (f-строка).
# =========================================================================
rp = os.path.join(BASE, "run.py")
if os.path.exists(rp):
    src = open(rp, encoding="utf-8").read()
    old = '"OSHIBKA: port %d zanat. Osvobodite ego ili izmenite APP_PORT v .env"'
    new = 'f"OSHIBKA: port {config.PORT} zanat. Osvobodite ego ili izmenite APP_PORT v .env"'
    if old in src:
        src = src.replace(old, new, 1)
        open(rp, "w", encoding="utf-8", newline="\n").write(src)
        print("  ~ run.py: сообщение про занятый порт починено (%d -> число)")
    elif new in src:
        print("  = run.py: сообщение уже починено")
    else:
        print("  ! run.py: строка про порт не найдена — не страшно, это косметика")

print("")
print("=" * 60)
print("MARKER_END: миграция флага + релиз 0.12.9 в Git")
print("=" * 60)
print("Commit + Push:")
print("  modules/versions/history_seed.py   (релиз 0.12.9)")
print("  run.py                             (фикс %d)")
print("  tools/installers/install.py")
print("(миграция флага уже применена к ЭТОЙ базе прямо сейчас)")
print("")
print("Затем на VM: ./update.sh  (привезёт релиз и применит миграцию к боевой базе)")