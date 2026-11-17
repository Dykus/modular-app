import os, sys

d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d:
        break
    d = p
BASE = d
print("Корень проекта: " + BASE)

# =========================================================================
# ПАТЧ 1. routes.py — сортировка по номеру версии, а не по id/дате.
# =========================================================================
rp = os.path.join(BASE, "modules", "versions", "routes.py")
src = open(rp, encoding="utf-8").read()
changed = False

HELPER = '''

def _ver_key(v):
    # "0.12.7" -> (0, 12, 7); нечисловые хвосты -> 0. Не зависит от ОС и БД.
    parts = []
    for chunk in (v or "0").split("."):
        num = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(num) if num else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def _sorted_releases(rows):
    # Наибольшая версия первая; внутри равных версий — по дате, затем по id.
    return sorted(
        rows,
        key=lambda r: (_ver_key(r.version),
                       r.release_date or datetime.min.date(),
                       r.id),
        reverse=True,
    )
'''

anchor_import = "from modules.versions.models import Release, STATUS_LABELS, STATUS_BADGE"
if "_sorted_releases" not in src:
    if anchor_import in src:
        src = src.replace(anchor_import, anchor_import + HELPER, 1)
        changed = True
        print("  + routes.py: helper _sorted_releases вставлен")
    else:
        print("  ! routes.py: якорь импорта не найден — сообщи мне")

old_list = "releases = Release.query.order_by(Release.release_date.desc(), Release.id.desc()).all()"
new_list = "releases = _sorted_releases(Release.query.all())"
if old_list in src:
    src = src.replace(old_list, new_list, 1)
    changed = True
    print("  ~ routes.py: список версий сортируется по номеру")
elif new_list in src:
    print("  = routes.py: список уже починен")
else:
    print("  ! routes.py: строка сортировки списка не найдена — сообщи мне")

old_about = "releases = Release.query.order_by(Release.release_date.desc(), Release.id.desc()).limit(10).all()"
new_about = "releases = _sorted_releases(Release.query.all())[:10]"
if old_about in src:
    src = src.replace(old_about, new_about, 1)
    changed = True
    print("  ~ routes.py: «последние релизы» на «О программе» тоже починены")
elif new_about in src:
    print("  = routes.py: «О программе» уже починена")
else:
    print("  ! routes.py: строка сортировки about не найдена — сообщи мне")

if changed:
    open(rp, "w", encoding="utf-8", newline="\n").write(src)

# =========================================================================
# ПАТЧ 2. history_seed.py — релиз 0.12.7 в статический файл (едет через Git).
# Никаких sync_*.py в корне: они в .gitignore и на сервер не приедут.
# =========================================================================
hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
hsrc = open(hp, encoding="utf-8").read()
if '"0.12.7"' not in hsrc:
    rel_block = (
        'RELEASES = [\n'
        '{"version": "0.12.7", "release_date": "2026-11-17", "status": "released",\n'
        ' "title": "Семантическая сортировка версий",\n'
        ' "notes": "Список релизов и «последние релизы» на «О программе» сортируются по номеру версии (0.12.7 > 0.11.0), а не по id вставки или дате. Работает одинаково на Windows, Linux и малине — это код в Git, не генерация из базы."},\n'
    )
    hsrc = hsrc.replace("RELEASES = [\n", rel_block, 1)

    cl_block = (
        'CHANGELOG = [\n'
        '{"date": "2026-11-17", "author": "синхронизация документации", "change_type": "fixed", "module": "versions", "ticket": "", "description": "Сортировка списка релизов и блока «последние релизы» переведена на семантический номер версии: порядок больше не зависит от id вставки и одинаков на любой ОС."},\n'
        '{"date": "2026-11-17", "author": "синхронизация документации", "change_type": "added", "module": "versions", "ticket": "", "description": "Релиз 0.12.7 добавлен в статический history_seed.py — приезжает на сервер через Git, без sync-скрипта в корне."},\n'
    )
    hsrc = hsrc.replace("CHANGELOG = [\n", cl_block, 1)
    open(hp, "w", encoding="utf-8", newline="\n").write(hsrc)
    print("  + history_seed.py: релиз 0.12.7 и записи журнала дописаны (в Git)")
else:
    print("  = history_seed.py: 0.12.7 уже есть")

print("")
print("=" * 60)
print("MARKER_END: сортировка версий починена, релиз 0.12.7 в Git")
print("=" * 60)
print("Commit + Push:")
print("  modules/versions/routes.py        (сортировка по номеру версии)")
print("  modules/versions/history_seed.py  (релиз 0.12.7)")
print("  tools/installers/install.py")
print("")
print("Затем на VM: ./update.sh  (git pull привезёт сортировку,")
print("история дольёт 0.12.7, служба перезапустится)")