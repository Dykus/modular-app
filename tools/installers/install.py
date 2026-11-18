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
# ПРАВКА 1. core/app.py — убрать смену пароля из белого списка.
# Страница смены пароля должна требовать входа; guard разрывает цикл
# своим списком исключений, поэтому белый список ей не нужен.
# =========================================================================
ap = os.path.join(BASE, "core", "app.py")
src = open(ap, encoding="utf-8").read()
changed = False
old = '"auth.change_password", "auth.do_change_password", "static"}'
new = '"static"}'
if old in src:
    src = src.replace(old, new, 1)
    changed = True
    print("  ~ core/app.py: смена пароля убрана из AUTH_WHITELIST")
elif new in src and '"auth.change_password"' not in src:
    print("  = core/app.py: смены пароля в белом списке уже нет")
else:
    print("  ! core/app.py: якорь белого списка не совпал — пришли мне строки 13-14")
if changed:
    open(ap, "w", encoding="utf-8", newline="\n").write(src)

# =========================================================================
# ПРАВКА 2. core/auth_routes.py — @login_required на GET change_password.
# Идемпотентно: если декоратор уже есть над def change_password(): — пропуск.
# =========================================================================
arp = os.path.join(BASE, "core", "auth_routes.py")
asrc = open(arp, encoding="utf-8").read()
eol = "\r\n" if "\r\n" in asrc else "\n"
lines = asrc.splitlines()
target = None
for i, ln in enumerate(lines):
    if ln.strip() == "def change_password():":
        target = i
        break
if target is None:
    print("  ! core/auth_routes.py: def change_password(): не найден")
else:
    has_lr = any("login_required" in lines[j].strip() for j in range(max(0, target - 2), target))
    if has_lr:
        print("  = core/auth_routes.py: @login_required на GET уже есть")
    else:
        lines.insert(target, "@login_required")
        out = eol.join(lines)
        if asrc.endswith(eol):
            out += eol
        open(arp, "w", encoding="utf-8", newline="\n").write(out)
        print("  ~ core/auth_routes.py: @login_required добавлен на GET change_password")

# =========================================================================
# ПРАВКА 3. core/auth.py — починить кракозябры в сообщении входа.
# После правки 1 гость, попавший на смену пароля, редиректится на вход и
# увидит это сообщение — значит его надо сделать читаемым.
# =========================================================================
aup = os.path.join(BASE, "core", "auth.py")
if os.path.exists(aup):
    asrc2 = open(aup, encoding="utf-8").read()
    good = 'login_manager.login_message = "Войдите в систему, чтобы продолжить."'
    if good in asrc2:
        print("  = core/auth.py: сообщение входа уже нормальное")
    else:
        out_lines = []
        fixed = False
        for ln in asrc2.splitlines():
            if ln.strip().startswith("login_manager.login_message"):
                out_lines.append(good)
                fixed = True
            else:
                out_lines.append(ln)
        if fixed:
            res = eol.join(out_lines)
            if asrc2.endswith(eol):
                res += eol
            open(aup, "w", encoding="utf-8", newline="\n").write(res)
            print("  ~ core/auth.py: сообщение входа исправлено (были кракозябры)")
        else:
            print("  ! core/auth.py: строка login_message не найдена")
else:
    print("  ! core/auth.py не найден")

# =========================================================================
# ПРАВКА 4. history_seed.py — релиз 0.12.9 + журнал (едет через Git).
# =========================================================================
hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
if os.path.exists(hp):
    hsrc = open(hp, encoding="utf-8").read()
    if '"0.12.9"' not in hsrc:
        rel_block = (
            'RELEASES = [\n'
            '{"version": "0.12.9", "release_date": "2026-11-18", "status": "released",\n'
            ' "title": "Защита страницы смены пароля",\n'
            ' "notes": "Страница смены пароля была в белом списке и без @login_required на GET — гость, открывший /auth/change-password напрямую, падал с AttributeError (AnonymousUserMixin не имеет auth_source). Убрали смену пароля из белого списка (цикл разрывает список исключений в guard) и поставили @login_required на GET. Попутно исправлено кракозябрное сообщение «Войдите в систему» в core/auth.py."},\n'
        )
        hsrc = hsrc.replace("RELEASES = [\n", rel_block, 1)
        cl_block = (
            'CHANGELOG = [\n'
            '{"date": "2026-11-18", "author": "синхронизация документации", "change_type": "fixed", "module": "core", "ticket": "", "description": "Страница смены пароля защищена от гостей: убрана из AUTH_WHITELIST и получил @login_required на GET — прямой вход на /auth/change-password без авторизации больше не падает с AttributeError, а кидает на страницу входа."},\n'
            '{"date": "2026-11-18", "author": "синхронизация документации", "change_type": "fixed", "module": "core", "ticket": "", "description": "Исправлено кракозябрное сообщение login_manager.login_message в core/auth.py (было UTF-8, прочитанное как другая кодировка)."},\n'
        )
        hsrc = hsrc.replace("CHANGELOG = [\n", cl_block, 1)
        open(hp, "w", encoding="utf-8", newline="\n").write(hsrc)
        print("  + history_seed.py: релиз 0.12.9 и 2 записи журнала дописаны (в Git)")
    else:
        print("  = history_seed.py: 0.12.9 уже есть")
else:
    print("  ! history_seed.py не найден")

print("")
print("=" * 60)
print("MARKER_END: страница смены пароля защищена, релиз 0.12.9 в Git")
print("=" * 60)
print("Commit + Push:")
print("  core/app.py          (смена пароля убрана из белого списка)")
print("  core/auth_routes.py  (@login_required на GET смены пароля)")
print("  core/auth.py         (сообщение входа починено)")
print("  modules/versions/history_seed.py (релиз 0.12.9)")
print("  tools/installers/install.py")