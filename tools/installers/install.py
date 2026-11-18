import os, re, json, base64, sys

d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d:
        break
    d = p
BASE = d
print("Koren' proekta: " + BASE)

# =========================================================================
# 1. dark.css -> etalon + UNIVERSAL'NYJ kontrast (chinit notes v lyubom tege).
# =========================================================================
DARK = """/* Temnaya tema - primenyaetsya k body.dark */
body.dark { background:#15171c; color:#d7dae0; }
body.dark main { background:#1e2128; box-shadow:0 2px 6px rgba(0,0,0,.4); }
body.dark header { background:linear-gradient(135deg,#3b4270,#4a2f63); }
body.dark .welcome h2 { color:#8ea2ff; }
body.dark .welcome p, body.dark .card h3 { color:#9aa3b2; }
body.dark .card { background:#23262e; border-left-color:#8ea2ff; box-shadow:0 2px 4px rgba(0,0,0,.3); }
body.dark .card p { color:#e7eaf0; }
body.dark th { background:#23262e; color:#9aa3b2; border-bottom-color:#333844; }
body.dark td { border-bottom-color:#2a2e37; }
body.dark tr:hover td { background:#262a33; }
body.dark .form-row { background:#23262e; border-color:#3a3f4b; }
body.dark .form-row input, body.dark .form-row select,
body.dark .toolbar input[type=text] { background:#1a1d24; border-color:#3a3f4b; color:#e7eaf0; }
body.dark .btn.gray { background:#3a3f4b; } body.dark .btn.gray:hover { background:#4a5060; }
body.dark .info { background:#1c2733; border-left-color:#3b82f6; }
body.dark .info h3 { color:#60a5fa; }
body.dark .flash { background:#3a2f12; border-left-color:#f39c12; color:#ffd97a; }
body.dark .empty { color:#6b7280; }
body.dark .note { color:#6b7280; }
body.dark footer { color:#6b7280; }
body.dark .theme-btn { background:rgba(255,255,255,.12); color:#fff; }
.theme-btn { background:rgba(255,255,255,.2); color:#fff; border:none; border-radius:6px;
padding:6px 10px; cursor:pointer; font-size:16px; vertical-align:middle; margin-left:6px; }
.theme-btn:hover { background:rgba(255,255,255,.32); }
/* universal-kontrast: perekrashivaem LYUBOY tekst vnutri main (notes v
   versiyah, priglushonnyj tekst s inline-cvetom iz šablonov) nezavisimo ot
   tega. Akcenty zaščishcheny :not. !important protiv inline šablonov. */
body.dark main *:not(.badge):not(.btn):not([class*="b-"]):not(.info):not(.flash):not(.form-row):not(.toolbar):not(.stats):not(.uname):not(.theme-btn):not(header):not(nav):not(.userbox):not(h1):not(h2):not(h3):not(h4):not(a):not(input):not(select):not(textarea):not(button):not(.card){ color:#c4ccd8 !important; }
body.dark main a:not(.btn):not(.badge):not([class*="b-"]){ color:#8ea2ff !important; }
body.dark main a:not(.btn):not(.badge):not([class*="b-"]):hover{ color:#b3c2ff !important; }
body.dark main .card p{ color:#e7eaf0 !important; }
body.dark footer{ color:#9aa3b2 !important; }
"""
dp = os.path.join(BASE, "web", "static", "css", "dark.css")
if not os.path.exists(dp):
    dp = os.path.join(BASE, "static", "css", "dark.css")
open(dp, "w", encoding="utf-8", newline="\n").write(DARK)
print("  ~ dark.css: pere zapisan etalonon + universal'nyj kontrast")

# =========================================================================
# 2. history_seed.py -> polnyj peresbor base64 (relizy 0.6.0-0.12.15 + zhurnal).
# =========================================================================
REL = [
("0.6.0","2026-10-31","Авторизация, роли, пользователи, руководство","Вход и пароли (хеш), роли и права с человеческими описаниями, экраны «Роли» и «Пользователи», журнал входов и аудит, блокировка подбора пароля, safety-switch, модуль «Руководство» с печатью, регламент документации."),
("0.7.0","2026-10-31","Хотелки: адресат и приватность","Поля «Кто» и «Кому» с выпадающими списками пользователей (свободный ввод, если человека нет в списке); приватные записи, видимые только автору, адресату и админу; переключение видимости."),
("0.8.0","2026-10-31","Active Directory","Вход доменными учётками с graceful-degradation, авто-provisioning с ролью по умолчанию, кнопка проверки связи из настроек, источник входа в журналах и профиле."),
("0.8.1","2026-10-31","Понятный журнал настроек","Ключи и значения в журнале изменений настроек отображаются по-русски: названия настроек, включено/выключено, список модулей именами, темы и режимы защиты AD."),
("0.8.2","2026-10-31","Справка о совместимости","В руководстве и справке появился раздел о совместимости простыми словами: какие ОС подходят для сервера, почему XP и Server 2003 не подходят, какие браузеры работают, что делать со старыми компьютерами."),
("0.9.0","2026-11-01","Plug-and-play модули","Автопоиск модулей по паспорту module.json, шаблон modules/_template, безопасная регистрация сторонних модулей (битой модуль не роняет систему), версия и автор модуля в Настройках."),
("0.9.1","2026-11-01","Устойчивое меню","Меню больше не падает, если у какого-то модуля не найден endpoint: такой пункт пропускается с предупреждением в консоли, остальные страницы работают."),
("0.9.2","2026-11-01","Корзина в модуле «Производство»","Удалённые задачи перемещаются в корзину и хранятся 30 дней: можно восстановить или удалить навсегда. Автоочистка просроченных записей при открытии корзины."),
("0.10.0","2026-11-01","Конструктор таблиц","Модуль «Таблицы»: свои таблицы-вкладки, колонки с типами, формулы-конструктор (арифметика, склейка, дни, ЕСЛИ, ссылки между таблицами), матрица прав «роль × колонка», история по клеткам, корзина на 30 дней, счётчики-карточки."),
("0.10.1","2026-11-01","Импорт Excel и русский конструктор","В конструктор таблиц добавлен импорт .xlsx с сопоставлением колонок по заголовкам; типы колонок и формы полностью на русском."),
("0.11.0","2026-11-17","Inline-редактирование + привязка к модулям","Конструктор таблиц: клик по своей клетке для быстрой правки (AJAX, без перезагрузки), цветовое различение своих/чужих/вычисляемых колонок, подсветка строк, изменённых за последние 5 минут, и поле module_key — таблица из конструктора становится вкладкой внутри выбранного модуля."),
("0.11.1","2026-11-17","Фикс чистого старта","Приложение снова запускается на пустой базе: таблицы настроек создаются до засевки. Меню больше не падает из-за одного битого адреса модуля."),
("0.12.0","2026-11-17","Серверный пакет","Работа на отдельном сервере: настройки в .env, отладка выключена, фиксированный порт, waitress, служба systemd, выкладка одной командой update.sh, автобэкапы."),
("0.12.1","2026-11-17","Тест обновления","Проверка процесса обновления через установщик: тестовый модуль test_update, метка в заголовке."),
("0.12.2","2026-11-17","Полная история версий","История релизов и журнала изменений стала частью кода: применяется при каждом старте. Любая новая установка (VM, малина) получает полную и одинаковую историю с первого запуска."),
("0.12.3","2026-11-17","Русский update.sh + принудительная история","Скрипт update.sh полностью переписан по-русски. Добавлен отдельный шаг принудительного применения истории версий."),
("0.12.4","2026-11-17","Исправление генерации истории","Генератор истории запускается только на разработочной машине (Windows), где полная база. На сервере история берётся готовой из Git."),
("0.12.5","2026-11-17","Полная история версий на сервере","История релизов и журнала наконец применяется полностью на сервере: колонка «date» добавлена в список дат, транзакции разделены — autoflush больше не ломает сессию."),
("0.12.6","2026-11-18","История версий — статический код в Git","История релизов и журнала изменений больше не зависит от операционной системы: это статический файл modules/versions/history_seed.py в Git, собранный из sync-скриптов. Генерация из базы Windows удалена. Любой новый сервер получает полную и одинаковую историю при первом же запуске."),
("0.12.7","2026-11-18","Семантическая сортировка версий","Список релизов и «последние релизы» на «О программе» сортируются по номеру версии (0.12.7 > 0.11.0), а не по id вставки или дате. Работает одинаково на Windows, Linux и малине — это код в Git, не генерация из базы."),
("0.12.8","2026-11-18","Справка и руководство — код в Git","Все тела статей справки (17) и разделов руководства (6) вынесены в статический modules/versions/docs_seed.py и применяются при каждом старте. Справка и руководство больше не зависят от ОС: любой новый сервер получает полную и одинаковую документацию с первого запуска. Ручные правки в UI временные; постоянные — через docs_seed + commit."),
("0.12.9","2026-11-18","Принудительная смена пароля работает на старых базах","Колонка must_change_password добавлялась в модель позже, чем на мастерской/сервере уже жил admin, и SQLite подставил старым строкам 0 (False) — из-за этого система не требовала сменить пароль при первом входе, хотя код перехвата был верен. Разовая идемпотентная миграция выставляет флаг admin=1 на существующих базах; на чистых базаг seed и так ставит 1. Попутно исправлено сообщение про занятый порт (вместо %d теперь реальное число)."),
("0.12.15","2026-11-18","Контраст тёмной темы (финал) + полная пересборка истории","Тёмная тема: универсальное переопределение цвета текста внутри main через !important с защитой акцентов — чинит нечитаемые notes в карточках релизов и любой приглушённый текст с inline-цветом из шаблонов, без зависимости от конкретного тега. История релизов и журнала пересобрана целиком из sync-скриптов (полный список 0.6.0–0.12.15 в base64): любая чистая база получает всю историю с первого запуска. В except-блоках автоприменения добавлен db.session.rollback() — ошибка одного применения больше не блокирует следующее. Подсветка активного пункта меню починена для производства."),
]
CL = [
("2026-10-31","added","core","Авторизация: вход и выход, профиль, принудительная смена пароля, блокировка после неудачных попыток, журнал входов, safety-switch."),
("2026-10-31","added","core","Реестр прав: модули объявляют права в perms.py; страница отказа 403 объясняет, какого права не хватает и что оно даёт."),
("2026-10-31","added","core","Замки прав на всех страницах модулей: прямая ссылка без права даёт понятный отказ, а не чужие данные."),
("2026-10-31","added","core","Экран «Роли»: создание ролей галочками прав с описаниями, защищённые права admin, защиты от самоблокировки."),
("2026-10-31","added","core","Экран «Пользователи»: создание, назначение ролей, блокировка, сброс пароля, аудит действий над людьми."),
("2026-10-31","added","manual","Модуль «Руководство»: разделы эксплуатации, версия для печати, печать без меню и кнопок, правка разделов."),
("2026-10-31","changed","web","Меню фильтруется по правам роли; текущая версия показывается в футере из базы данных."),
("2026-10-31","changed","docs","Синхронизация документации: справки обновлены под авторизацию, добавлен регламент документации."),
("2026-10-31","added","feedback","Хотелки: поле «Кому» (адресат) с выпадающим списком пользователей и свободным вводом."),
("2026-10-31","added","feedback","Приватные хотелки: видны только автору, адресату и администратору; значок замка в списке."),
("2026-10-31","changed","feedback","Поле «Кто» теперь выпадающий список пользователей (можно вписать своё)."),
("2026-10-31","added","core","Active Directory: провайдер входа с graceful-degradation и авто-provisioning доменных пользователей."),
("2026-10-31","added","settings","Кнопка «Проверить связь» для AD: пошаговая диагностика (библиотека, хост, TCP, TLS, bind, поиск)."),
("2026-10-31","changed","auth","Журнал входов и профиль показывают источник пароля: локальный или AD."),
("2026-10-31","changed","auth","У пользователей появился признак источника входа; доменные пароли локально не хранятся."),
("2026-10-31","changed","settings","Журнал изменений настроек показывает названия и значения понятным русским языком; технический код ключа остаётся мелким шрифтом."),
("2026-10-31","added","manual","Новый раздел руководства «Совместимость: какие компьютеры и браузеры подходят» — простыми словами, с частыми вопросами."),
("2026-10-31","added","help","Статья справки «Какие компьютеры и браузеры подходят» (выжимка раздела совместимости)."),
("2026-11-01","added","core","Модули с паспортом module.json обнаруживаются автоматически: достаточно положить папку в modules/ и перезапустить сервер."),
("2026-11-01","added","core","Битой сторонний модуль больше не роняет запуск: пропускается с предупреждением, остальная система работает."),
("2026-11-01","added","docs","Шаблон модуля modules/_template и пошаговая инструкция «Как подключить новый модуль» в руководстве и справке."),
("2026-11-01","changed","core","Меню стало устойчивым: если у модуля не найден endpoint, пункт пропускается с предупреждением в консоли, а остальные страницы работают."),
("2026-11-01","added","production","Корзина: удалённые задачи не исчезают, а хранятся 30 дней с возможностью восстановления или удаления навсегда."),
("2026-11-01","changed","production","Кнопка «Удалить» теперь перемещает задачу в корзину вместо мгновенного уничтожения; автоочистка корзины старше 30 дней."),
("2026-11-01","added","tables","Новый модуль «Таблицы (конструктор)»: свои таблицы-вкладки, колонки с типами, вычисляемые колонки-формулы через визуальный конструктор, ссылки между таблицами (аналог ВПР)."),
("2026-11-01","added","tables","Права на клетки: матрица «роль × колонка» (видеть/создавать/удалять/менять колонку), свои колонки ✎, чужие 🔒."),
("2026-11-01","added","tables","История изменений по клеткам, корзина строк на 30 дней с восстановлением, счётчики-карточки, резервная копия при удалении таблицы."),
("2026-11-01","added","tables","Импорт Excel (.xlsx) в таблицу конструктора: сопоставление колонок по заголовкам, автосоздание недостающих, пропуск пустых строк, отметка в истории."),
("2026-11-01","changed","tables","Конструктор полностью по‑русски: типы колонок в списках и таблице показаны подписями; форма правки колонки подставляет сохранённую формулу."),
("2026-11-17","added","tables","Inline-редактирование: клик по своей клетке открывает поле ввода, Enter сохраняет через AJAX без перезагрузки страницы."),
("2026-11-17","changed","tables","Цветовое различение колонок: свои ✎ белые, чужие 🔒 серые, вычисляемые ⚙ голубые."),
("2026-11-17","added","tables","Подсветка недавно изменённого: зелёная полоса слева и мягкий фон на 5 минут после правки."),
("2026-11-17","added","tables","Привязка таблицы к модулю (module_key): таблица из конструктора становится вкладкой внутри выбранного модуля."),
("2026-11-17","fixed","core","Чистый старт: модели системного модуля «Настройки» импортируются до create_all — на пустой базе таблицы setting/setting_log создаются, seed не падает."),
("2026-11-17","changed","core","Меню устойчиво к битым endpoint: пункт пропускается с предупреждением в консоли вместо падения всех страниц."),
("2026-11-17","added","core","Серверный режим: настройки через .env, отладка выключена, порт фиксированный, WSGI-сервер waitress."),
("2026-11-17","added","deploy","Служба systemd и скрипт её установки: автозапуск при загрузке и подъём после сбоя."),
("2026-11-17","added","deploy","update.sh — выкладка обновления одной командой; backup.sh — горячие копии базы с хранением 14 дней."),
("2026-11-17","changed","docs","Установщики переехали в tools/installers/ — теперь они приезжают на сервер через Git вместе с кодом."),
("2026-11-17","added","test_update","Тестовый модуль для проверки процесса обновления через установщик."),
("2026-11-17","changed","web","Тестовая метка [TEST-UPDATE] в заголовке страниц для проверки обновления."),
("2026-11-17","added","versions","Полная история релизов и журнала изменений стала частью кода: применяется при каждом старте приложения. Любая новая машина (VM, малина) с первого запуска получает полную и одинаковую историю."),
("2026-11-17","added","tools","Скрипт tools/export_history.py для регенерации history_seed.py после каждого нового релиза."),
("2026-11-17","fixed","versions","Автоматическое применение истории: обработка дат (release_date) и откат сессии при ошибках."),
("2026-11-17","removed","test_update","Тестовый модуль для проверки обновления удалён после успешного теста."),
("2026-11-17","changed","web","Тестовая метка [TEST-UPDATE] убрана из заголовков страниц."),
("2026-11-17","changed","deploy","update.sh полностью на русском языке: все шаги, сообщения и проверки читаются по-русски."),
("2026-11-17","added","deploy","Принудительное применение истории версий при каждом update.sh: история дольётся даже если автоприменение при старте не сработало."),
("2026-11-17","fixed","versions","Гарантированное применение истории: отдельный шаг в update.sh, независимый от автоприменения при старте."),
("2026-11-17","fixed","tools","export_history.py теперь запускается ТОЛЬКО на разработочной машине (Windows), где полная база. На сервере (Linux) история берётся готовой из Git, а не генерируется из неполной локальной базы."),
("2026-11-17","added","tools","Проверка платформы: генератор истории автоматически определяет Windows/Linux и на сервере не запускается."),
("2026-11-17","fixed","versions","История версий наконец применяется полностью: колонка «date» в таблице changelog_entry добавлена в список дат, транзакции разделены (релизы и журнал коммитятся отдельно) — autoflush больше не ломает сессию."),
("2026-11-18","changed","versions","История релизов и журнала изменений стала СТАТИЧЕСКИМ кодом в Git (modules/versions/history_seed.py), собранным из sync-скриптов. Больше не генерируется из базы Windows — одинакова на любой ОС, любой новый сервер получает полную историю при первом старте."),
("2026-11-18","removed","tools","tools/export_history.py удалён: генерация истории из локальной базы больше не нужна и была источником зависимости от Windows и обрезания истории на сервере."),
("2026-11-18","fixed","versions","Сортировка списка релизов и блока «последние релизы» переведена на семантический номер версии: порядок больше не зависит от id вставки и одинаков на любой ОС."),
("2026-11-18","added","versions","Релиз 0.12.7 добавлен в статический history_seed.py — приезжает на сервер через Git, без sync-скрипта в корне."),
("2026-11-18","added","docs","Справка и руководство стали статическим кодом в Git (modules/versions/docs_seed.py): 17 статей и 6 разделов применяются при каждом старте, идентичны на Windows, Linux и малине."),
("2026-11-18","changed","core","create_app() вызывает docs_seed.apply() после run_seed(): документация доливается/приводится к эталону автоматически, без sync-скриптов в корне."),
("2026-11-18","fixed","core","Принудительная смена пароля при первом входе заработала на существующих базах: разовая миграция выставляет must_change_password=1 для admin, которому колонка, добавленная позже модели, досталась со значением 0."),
("2026-11-18","fixed","core","В сообщении про занятый порт в серверном режиме вместо литерала %d теперь подставляется реальный номер порта."),
("2026-11-18","fixed","web","Тёмная тема: финальный контраст — универсальное переопределение цвета текста внутри main через !important с защитой акцентов (бейджи, кнопки, ссылки, заголовки категорий, цифры статистики); чинит нечитаемые notes в карточках релизов и любой приглушённый текст с inline-цветом из шаблонов, без зависимости от конкретного тега."),
("2026-11-18","fixed","core","В except-блоках автоприменения истории/документации добавлен db.session.rollback(): ошибка одного применения больше не оставляет сессию «грязной» и не блокирует следующее (чинит каскад PendingRollback, из-за которого релизы 0.12.10+ не доливались)."),
("2026-11-18","added","versions","history_seed.py пересобран целиком из sync-скриптов: полный список релизов 0.6.0–0.12.15 и журнал в base64; любая чистая база (малина) получает всю историю с первого запуска."),
("2026-11-18","fixed","web","Подсветка активного пункта меню: добавлено обратное совпадение префикса URL, чтобы «Производство» (/production/index → /production/) выделялся; работает и на вложенных страницах."),
]
releases = [{"version":v,"release_date":dt,"status":"released","title":ti,"notes":no} for (v,dt,ti,no) in REL]
A = "синхронizatsiya dokumentacii"
changelog = [{"date":dt,"author":A,"change_type":ty,"module":md,"ticket":"","description":de} for (dt,ty,md,de) in CL]
data = {"releases":releases, "changelog":changelog}
b64 = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")

TPL = '''# ISTORIYA RELIZOV I ZHURNALA - STATICHESKIJ KOD V GIT (base64).
# Polnyj peresbor 0.6.0-0.12.15. apply() idempotenten: dolivaet_tolko_otsutstvuyushhee.
import base64 as _b64
import json as _json
from datetime import datetime as _dt

_B64 = "%s"
_DATA = _json.loads(_b64.b64decode(_B64).decode("utf-8"))

_DATE_KEYS = ("released_at", "release_date", "date", "created_at", "updated_at", "ts")

def _date(v):
    if not isinstance(v, str) or not v:
        return None
    try:
        return _dt.fromisoformat(v.replace(" ", "T"))
    except Exception:
        return None

def apply():
    from core.app import db
    from modules.versions.models import Release
    from modules.changelog.models import ChangelogEntry
    cols_r = set(Release.__table__.columns.keys())
    cols_c = set(ChangelogEntry.__table__.columns.keys())
    have_r = {r.version for r in Release.query.all()}
    added_r = 0
    for rec in _DATA["releases"]:
        if rec.get("version") in have_r:
            continue
        kw = {k: (_date(v) if k in _DATE_KEYS else v) for k, v in rec.items() if k in cols_r and k != "id"}
        kw.setdefault("is_current", False)
        db.session.add(Release(**kw)); added_r += 1
    if added_r:
        try: db.session.commit()
        except Exception: db.session.rollback(); raise
    have_c = {(c.module, c.description) for c in ChangelogEntry.query.all()}
    added_c = 0
    for rec in _DATA["changelog"]:
        if (rec.get("module"), rec.get("description")) in have_c:
            continue
        kw = {k: (_date(v) if k in _DATE_KEYS else v) for k, v in rec.items() if k in cols_c and k != "id"}
        db.session.add(ChangelogEntry(**kw)); added_c += 1
    if added_c:
        try: db.session.commit()
        except Exception: db.session.rollback(); raise
    if not Release.query.filter_by(is_current=True).first():
        top = Release.query.order_by(Release.id.desc()).first()
        if top:
            top.is_current = True
            try: db.session.commit()
            except Exception: db.session.rollback(); raise
    return added_r, added_c
''' % b64
hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
os.makedirs(os.path.dirname(hp), exist_ok=True)
open(hp, "w", encoding="utf-8", newline="\n").write(TPL)
print("  + history_seed.py: polnyj peresbor base64 (relizov=%d, zhurnala=%d)" % (len(releases), len(changelog)))

# =========================================================================
# 3. core/app.py -> rollback v except (chinit kas'kad PendingRollback).
# =========================================================================
cp = os.path.join(BASE, "core", "app.py")
src = open(cp, encoding="utf-8").read()
chg = False
for marker in ['print("PREDUPREZHDENIE: документация не применена: %s" % _e)',
               'print("PREDUPREZHDENIE: istoriya relizov ne primenena: %s" % _e)']:
    if marker in src and "db.session.rollback()" not in src[max(0,src.find(marker)-160):src.find(marker)]:
        src = src.replace(marker, "db.session.rollback()\n            " + marker, 1)
        chg = True
        print("  ~ core/app.py: rollback dobavlen pered '%s'" % marker[:42])
if chg:
    open(cp, "w", encoding="utf-8", newline="\n").write(src)
else:
    print("  = core/app.py: rollback uzhe est (ili yaкорь ne naiden)")

# =========================================================================
# 4. base.html -> podsvetka proizvodstva (idempotentno).
# =========================================================================
bp = os.path.join(BASE, "web", "templates", "base.html")
if not os.path.exists(bp):
    bp = os.path.join(BASE, "templates", "base.html")
bsrc = open(bp, encoding="utf-8").read()
if "hh.indexOf(path+'/')" in bsrc:
    print("  = base.html: podsvetka proizvodstva uzhe est")
else:
    SCRIPT = ("<script>\n/* menu-active */\n(function(){\n"
      "  var path=location.pathname.replace(/\\/+$/,'');var links=document.querySelectorAll('nav a');\n"
      "  for(var i=0;i<links.length;i++){var a=links[i];var href=(a.getAttribute('href')||'').split('?')[0].split('#')[0];\n"
      "    var hh=href.replace(/\\/+$/,'');var ok=false;\n"
      "    if(hh===''){ok=(path==='');}else if(path===hh){ok=true;}else if(path.indexOf(hh+'/')===0){ok=true;}\n"
      "    else if(path!==''&&hh.indexOf(path+'/')===0){ok=true;}\n"
      "    if(ok)a.classList.add('active');}\n})();\n</script>")
    if "</body>" in bsrc:
        bsrc = bsrc.replace("</body>", SCRIPT + "\n</body>", 1)
        open(bp, "w", encoding="utf-8", newline="\n").write(bsrc)
        print("  + base.html: podsvetka proizvodstva vstavlena")
    else:
        print("  ! base.html: net </body> — prišli base.html FAJLOM")

print("")
print("=" * 60)
print("MARKER_END: kontrast(final)+polnââ istoriâ 0.6.0-0.12.15+kas'kad(0.12.15)")
print("=" * 60)
print("Commit + Push:")
print("  web/static/css/dark.css            (universal'nyj kontrast)")
print("  modules/versions/history_seed.py   (polnyj peresbor base64)")
print("  core/app.py                        (rollback v except)")
print("  web/templates/base.html            (podsvetka proizvodstva)")
print("  tools/installers/install.py")
print("")
print("VM SEGODNYA NE TROGAEM (net dostupa) — doeedet domoy cheres ./update.sh")