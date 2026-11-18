import os, re, json, base64, sys

d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d:
        break
    d = p
BASE = d
print("Корень проекта: " + BASE)

# ПРАВКА 1. core/app.py — убрать смену пароля из белого списка.
ap = os.path.join(BASE, "core", "app.py")
src = open(ap, encoding="utf-8").read()
old = '"auth.change_password", "auth.do_change_password", "static"}'
if old in src:
    src = src.replace(old, '"static"}', 1)
    open(ap, "w", encoding="utf-8", newline="\n").write(src)
    print("  ~ core/app.py: смена пароля убрана из AUTH_WHITELIST")
elif '"auth.change_password"' not in src:
    print("  = core/app.py: смены пароля в белом списке уже нет")
else:
    print("  ! core/app.py: якорь не совпал — пришли мне строки 13-14")

# ПРАВКА 2. core/auth_routes.py — @login_required на GET change_password.
arp = os.path.join(BASE, "core", "auth_routes.py")
asrc = open(arp, encoding="utf-8").read()
eol2 = "\r\n" if "\r\n" in asrc else "\n"
lines = asrc.splitlines()
target = next((i for i, ln in enumerate(lines) if ln.strip() == "def change_password():"), None)
if target is None:
    print("  ! core/auth_routes.py: def change_password(): не найден")
elif any("login_required" in lines[j].strip() for j in range(max(0, target - 2), target)):
    print("  = core/auth_routes.py: @login_required на GET уже есть")
else:
    lines.insert(target, "@login_required")
    out = eol2.join(lines) + (eol2 if asrc.endswith(eol2) else "")
    open(arp, "w", encoding="utf-8", newline="\n").write(out)
    print("  ~ core/auth_routes.py: @login_required добавлен на GET change_password")

# ПРАВКА 3. core/auth.py — починить кракозябры в сообщении входа.
aup = os.path.join(BASE, "core", "auth.py")
if os.path.exists(aup):
    asrc3 = open(aup, encoding="utf-8").read()
    eol3 = "\r\n" if "\r\n" in asrc3 else "\n"
    good = 'login_manager.login_message = "Войдите в систему, чтобы продолжить."'
    if good in asrc3:
        print("  = core/auth.py: сообщение входа уже нормальное")
    else:
        ol, fixed = [], False
        for ln in asrc3.splitlines():
            if ln.strip().startswith("login_manager.login_message"):
                ol.append(good); fixed = True
            else:
                ol.append(ln)
        if fixed:
            open(aup, "w", encoding="utf-8", newline="\n").write(
                eol3.join(ol) + (eol3 if asrc3.endswith(eol3) else ""))
            print("  ~ core/auth.py: сообщение входа исправлено (были кракозябры)")
        else:
            print("  ! core/auth.py: строка login_message не найдена")
else:
    print("  ! core/auth.py не найден")

# ПРАВКА 4. history_seed.py (base64!) — релиз 0.12.9 + журнал.
hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
if not os.path.exists(hp):
    print("  ! history_seed.py не найден")
else:
    htxt = open(hp, encoding="utf-8").read()
    m = re.search(r'_B64\s*=\s*"([^"]*)"', htxt)
    if not m:
        print("  ! history_seed.py: не найден блок _B64 (файл не в base64?)")
    else:
        data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
        if any(r.get("version") == "0.12.9" for r in data["releases"]):
            print("  = history_seed.py: 0.12.9 уже есть")
        else:
            data["releases"].insert(0, {
                "version": "0.12.9", "release_date": "2026-11-18", "status": "released",
                "title": "Защита страницы смены пароля",
                "notes": "Страница смены пароля была в белом списке и без @login_required на GET — гость, открывший /auth/change-password напрямую, падал с AttributeError (AnonymousUserMixin не имеет auth_source). Убрали смену пароля из белого списка (цикл разрывает список исключений в guard) и поставили @login_required на GET. Попутно исправлено кракозябрное сообщение «Войдите в систему» в core/auth.py."})
            A = "синхронизация документации"
            data["changelog"].insert(0, {"date": "2026-11-18", "author": A, "change_type": "fixed", "module": "core", "ticket": "", "description": "Страница смены пароля защищена от гостей: убрана из AUTH_WHITELIST и получил @login_required на GET — прямой вход на /auth/change-password без авторизации больше не падает с AttributeError, а кидает на страницу входа."})
            data["changelog"].insert(1, {"date": "2026-11-18", "author": A, "change_type": "fixed", "module": "core", "ticket": "", "description": "Исправлено кракозябрное сообщение login_manager.login_message в core/auth.py (было UTF-8, прочитанное как другая кодировка)."})
            new_b64 = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
            htxt = htxt[:m.start(1)] + new_b64 + htxt[m.end(1):]
            open(hp, "w", encoding="utf-8", newline="\n").write(htxt)
            print("  + history_seed.py: релиз 0.12.9 и 2 записи журнала дописаны (base64 пересобран)")

print("")
print("=" * 60)
print("MARKER_END: страница смены пароля защищена, релиз 0.12.9 в Git")
print("=" * 60)
print("Commit + Push (можно с работы):")
print("  core/app.py, core/auth_routes.py, core/auth.py,")
print("  modules/versions/history_seed.py, tools/installers/install.py")
print("")
print("ВИРТУАЛКУ СЕЙЧАС НЕ ТРОГАЕМ — нет доступа. Всё дождётся дома.")