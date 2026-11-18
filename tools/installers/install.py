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
# Страница смены пароля должна требовать входа; в белом списке ей делать нечего.
# =========================================================================
ap = os.path.join(BASE, "core", "app.py")
src = open(ap, encoding="utf-8").read()
changed_app = False

if '"auth.change_password"' in src:
    # основной якорь (две записи одной строкой, как в findstr)
    old = '"auth.change_password", "auth.do_change_password", "static"}'
    new = '"static"}'
    if old in src:
        src = src.replace(old, new, 1)
        changed_app = True
        print("  ~ core/app.py: смена пароля убрана из AUTH_WHITELIST (якорь 1)")
    else:
        # запасной якорь: убрать две записи с хвостовой запятой
        old2 = '"auth.change_password", "auth.do_change_password", '
        if old2 in src:
            src = src.replace(old2, "", 1)
            changed_app = True
            print("  ~ core/app.py: смена пароля убрана из AUTH_WHITELIST (якорь 2)")
        else:
            print("  ! core/app.py: записи смены пароля найдены, но якорь не совпал — пришли мне строки 10-20")
else:
    print("  = core/app.py: смены пароля в белом списке уже нет")

if changed_app:
    open(ap, "w", encoding="utf-8", newline="\n").write(src)

# =========================================================================
# ПРАВКА 2. core/auth_routes.py — @login_required на GET change_password.
# Вставляем декоратор непосредственно перед def change_password():,
# если его там ещё нет (идемпотентно). Стиль как у POST-версии.
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
    print("  ! core/auth_routes.py: def change_password(): не найден — пришли мне строки 190-215")
else:
    # есть ли @login_required в двух строках выше?
    has_lr = any("login_required" in lines[j].strip()
                 for j in range(max(0, target - 2), target))
    if has_lr:
        print("  = core/auth_routes.py: @login_required на GET change_password уже есть")
    else:
        lines.insert(target, "@login_required")
        out = eol.join(lines)
        if asrc.endswith(eol):
            out += eol
        open(arp, "w", encoding="utf-8", newline="\n").write(out)
        print("  ~ core/auth_routes.py: @login_required добавлен на GET change_password")

print("")
print("=" * 60)
print("MARKER_END: страница смены пароля защищена от гостей")
print("=" * 60)
print("Commit + Push:")
print("  core/app.py          (смена пароля убрана из белого списка)")
print("  core/auth_routes.py  (@login_required на GET смены пароля)")
print("  tools/installers/install.py")
print("")
print("Затем на VM: ./update.sh")
print("ПОСЛЕ этого — тест: инкогнито, войти как admin, смотреть, кидает ли на смену.")
print("Релиз 0.12.9 добавлю отдельным шагом, когда тест подтвердит фикс.")