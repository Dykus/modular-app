# ИСТОРИЯ ВЕРСИЙ И ЖУРНАЛА ИЗМЕНЕНИЙ — СТАТИЧЕСКИЙ КОД В GIT.
# Источник: sync-скрипты 0.6.0-0.12.5. НЕ генерируется из базы данных,
# поэтому одинаков на любой ОС (Windows/Linux/малina). Любой новый сервер
# получает полную историю при первом же старте.
#
# ДОБАВЛЕНИЕ НОВОЙ ВЕРСИИ: допиши объект в RELEASES и записи в CHANGELOG
# (или положи новый sync-скрипт и извлеки данные). apply() идемпотентен:
# существующее не перезаписывает, доливает только отсутствующее.
from datetime import datetime as _dt

_DATE_KEYS = ("released_at", "release_date", "date", "created_at", "updated_at", "ts")


def _date(v):
    if not isinstance(v, str) or not v:
        return None
    try:
        return _dt.fromisoformat(v.replace(" ", "T"))
    except Exception:
        return None


# --- РЕЛИЗЫ (версия, заголовок, что вошло, дата) ---
RELEASES = [
{"version": "0.6.0", "release_date": "2026-10-31", "status": "released",
 "title": "Авторизация, роли, пользователи, руководство",
 "notes": "Вход и пароли (хеш), роли и права с человеческими описаниями, экраны «Роли» и «Пользователи», журнал входов и аудит, блокировка подбора пароля, safety-switch, модуль «Руководство» с печатью, регламент документации."},
{"version": "0.7.0", "release_date": "2026-10-31", "status": "released",
 "title": "Хотелки: адресат и приватность",
 "notes": "Поля «Кто» и «Кому» с выпадающими списками пользователей (свободный ввод, если человека нет в списке); приватные записи, видимые только автору, адресату и админу; переключение видимости."},
{"version": "0.8.0", "release_date": "2026-10-31", "status": "released",
 "title": "Active Directory",
 "notes": "Вход доменными учётками с graceful-degradation, авто-provisioning с ролью по умолчанию, кнопка проверки связи из настроек, источник входа в журналах и профиле."},
{"version": "0.8.1", "release_date": "2026-10-31", "status": "released",
 "title": "Понятный журнал настроек",
 "notes": "Ключи и значения в журнале изменений настроек отображаются по-русски: названия настроек, включено/выключено, список модулей именами, темы и режимы защиты AD."},
{"version": "0.8.2", "release_date": "2026-10-31", "status": "released",
 "title": "Справка о совместимости",
 "notes": "В руководстве и справке появился раздел о совместимости простыми словами: какие ОС подходят для сервера, почему XP и Server 2003 не подходят, какие браузеры работают, что делать со старыми компьютерами."},
{"version": "0.9.0", "release_date": "2026-10-31", "status": "released",
 "title": "Plug-and-play модули",
 "notes": "Автопоиск модулей по паспорту module.json, шаблон modules/_template, безопасная регистрация сторонних модулей (битой модуль не роняет систему), версия и автор модуля в Настройках."},
{"version": "0.9.1", "release_date": "2026-11-01", "status": "released",
 "title": "Устойчивое меню",
 "notes": "Меню больше не падает, если у какого-то модуля не найден endpoint: такой пункт пропускается с предупреждением в консоли, остальные страницы работают."},
{"version": "0.9.2", "release_date": "2026-11-01", "status": "released",
 "title": "Корзина в модуле «Производство»",
 "notes": "Удалённые задачи перемещаются в корзину и хранятся 30 дней: можно восстановить или удалить навсегда. Автоочистка просроченных записей при открытии корзины."},
{"version": "0.10.0", "release_date": "2026-11-01", "status": "released",
 "title": "Конструктор таблиц",
 "notes": "Модуль «Таблицы»: свои таблицы-вкладки, колонки с типами, формулы-конструктор (арифметика, склейка, дни, ЕСЛИ, ссылки между таблицами), матрица прав «роль × колонка», история по клеткам, корзина на 30 дней, счётчики-карточки."},
{"version": "0.10.1", "release_date": "2026-11-01", "status": "released",
 "title": "Импорт Excel и русский конструктор",
 "notes": "В конструктор таблиц добавлен импорт .xlsx с сопоставлением колонок по заголовкам; типы колонок и формы полностью на русском."},
{"version": "0.11.0", "release_date": "2026-11-17", "status": "released",
 "title": "Inline-редактирование + привязка к модулям",
 "notes": "Конструктор таблиц: клик по своей клетке для быстрой правки (AJAX, без перезагрузки), цветовое различение своих/чужих/вычисляемых колонок, подсветка строк, изменённых за последние 5 минут, и поле module_key — таблица из конструктора становится вкладкой внутри выбранного модуля."},
{"version": "0.11.1", "release_date": "2026-11-17", "status": "released",
 "title": "Фикс чистого старта",
 "notes": "Приложение снова запускается на пустой базе: таблицы настроек создаются до засевки. Меню больше не падает из-за одного битого адреса модуля."},
{"version": "0.12.0", "release_date": "2026-11-17", "status": "released",
 "title": "Серверный пакет",
 "notes": "Работа на отдельном сервере: настройки в .env, отладка выключена, фиксированный порт, waitress, служба systemd, выкладка одной командой update.sh, автобэкапы."},
{"version": "0.12.1", "release_date": "2026-11-17", "status": "released",
 "title": "Тест обновления",
 "notes": "Проверка процесса обновления через установщик: тестовый модуль test_update, метка в заголовке."},
{"version": "0.12.2", "release_date": "2026-11-17", "status": "released",
 "title": "Полная история версий",
 "notes": "История релизов и журнала изменений стала частью кода: применяется при каждом старте. Любая новая установка (VM, малina) получает полную и одинаковую историю с первого запуска."},
{"version": "0.12.3", "release_date": "2026-11-17", "status": "released",
 "title": "Русский update.sh + принудительная история",
 "notes": "Скрипт update.sh полностью переписан по-русски. Добавлен отдельный шаг принудительного применения истории версий."},
{"version": "0.12.4", "release_date": "2026-11-17", "status": "released",
 "title": "Исправление генерации истории",
 "notes": "Генератор истории запускается только на разработочной машине (Windows), где полная база. На сервере история берётся готовой из Git."},
{"version": "0.12.5", "release_date": "2026-11-17", "status": "released",
 "title": "Полная история версий на сервере",
 "notes": "История релизов и журнала наконец применяется полностью на сервере: колонка «date» добавлена в список дат, транзакции разделены — autoflush больше не ломает сессию."},
]

# --- ЖУРНАЛ ИЗМЕНЕНИЙ (тип, модуль, описание, дата релиза) ---
_A = "синхронизация документации"
CHANGELOG = [
# 0.6.0
{"date": "2026-10-31", "author": _A, "change_type": "added", "module": "core", "ticket": "", "description": "Авторизация: вход и выход, профиль, принудительная смена пароля, блокировка после неудачных попыток, журнал входов, safety-switch."},
{"date": "2026-10-31", "author": _A, "change_type": "added", "module": "core", "ticket": "", "description": "Реестр прав: модули объявляют права в perms.py; страница отказа 403 объясняет, какого права не хватает и что оно даёт."},
{"date": "2026-10-31", "author": _A, "change_type": "added", "module": "core", "ticket": "", "description": "Замки прав на всех страницах модулей: прямая ссылка без права даёт понятный отказ, а не чужие данные."},
{"date": "2026-10-31", "author": _A, "change_type": "added", "module": "core", "ticket": "", "description": "Экран «Роли»: создание ролей галочками прав с описаниями, защищённые права admin, защиты от самоблокировки."},
{"date": "2026-10-31", "author": _A, "change_type": "added", "module": "core", "ticket": "", "description": "Экран «Пользователи»: создание, назначение ролей, блокировка, сброс пароля, аудит действий над людьми."},
{"date": "2026-10-31", "author": _A, "change_type": "added", "module": "manual", "ticket": "", "description": "Модуль «Руководство»: разделы эксплуатации, версия для печати, печать без меню и кнопок, правка разделов."},
{"date": "2026-10-31", "author": _A, "change_type": "changed", "module": "web", "ticket": "", "description": "Меню фильтруется по правам роли; текущая версия показывается в футере из базы данных."},
{"date": "2026-10-31", "author": _A, "change_type": "changed", "module": "docs", "ticket": "", "description": "Синхронизация документации: справки обновлены под авторизацию, добавлен регламент документации."},
# 0.7.0
{"date": "2026-10-31", "author": _A, "change_type": "added", "module": "feedback", "ticket": "", "description": "Хотелки: поле «Кому» (адресат) с выпадающим списком пользователей и свободным вводом."},
{"date": "2026-10-31", "author": _A, "change_type": "added", "module": "feedback", "ticket": "", "description": "Приватные хотелки: видны только автору, адресату и администратору; значок замка в списке."},
{"date": "2026-10-31", "author": _A, "change_type": "changed", "module": "feedback", "ticket": "", "description": "Поле «Кто» теперь выпадающий список пользователей (можно вписать своё)."},
# 0.8.0
{"date": "2026-10-31", "author": _A, "change_type": "added", "module": "core", "ticket": "", "description": "Active Directory: провайдер входа с graceful-degradation и авто-provisioning доменных пользователей."},
{"date": "2026-10-31", "author": _A, "change_type": "added", "module": "settings", "ticket": "", "description": "Кнопка «Проверить связь» для AD: пошаговая диагностика (библиотека, хост, TCP, TLS, bind, поиск)."},
{"date": "2026-10-31", "author": _A, "change_type": "changed", "module": "auth", "ticket": "", "description": "Журнал входов и профиль показывают источник пароля: локальный или AD."},
{"date": "2026-10-31", "author": _A, "change_type": "changed", "module": "auth", "ticket": "", "description": "У пользователей появился признак источника входа; доменные пароли локально не хранятся."},
# 0.8.1
{"date": "2026-10-31", "author": _A, "change_type": "changed", "module": "settings", "ticket": "", "description": "Журнал изменений настроек показывает названия и значения понятным русским языком; технический код ключа остаётся мелким шрифтом."},
# 0.8.2
{"date": "2026-10-31", "author": _A, "change_type": "added", "module": "manual", "ticket": "", "description": "Новый раздел руководства «Совместимость: какие компьютеры и браузеры подходят» — простыми словами, с частыми вопросами."},
{"date": "2026-10-31", "author": _A, "change_type": "added", "module": "help", "ticket": "", "description": "Статья справки «Какие компьютеры и браузеры подходят» (выжимка раздела совместимости)."},
# 0.9.0
{"date": "2026-10-31", "author": _A, "change_type": "added", "module": "core", "ticket": "", "description": "Модули с паспортом module.json обнаруживаются автоматически: достаточно положить папку в modules/ и перезапустить сервер."},
{"date": "2026-10-31", "author": _A, "change_type": "added", "module": "core", "ticket": "", "description": "Битой сторонний модуль больше не роняет запуск: пропускается с предупреждением, остальная система работает."},
{"date": "2026-10-31", "author": _A, "change_type": "added", "module": "docs", "ticket": "", "description": "Шаблон модуля modules/_template и пошаговая инструкция «Как подключить новый модуль» в руководстве и справке."},
# 0.9.1
{"date": "2026-11-01", "author": _A, "change_type": "changed", "module": "core", "ticket": "", "description": "Меню стало устойчивым: если у модуля не найден endpoint, пункт пропускается с предупреждением в консоли, а остальные страницы работают."},
# 0.9.2
{"date": "2026-11-01", "author": _A, "change_type": "added", "module": "production", "ticket": "", "description": "Корзина: удалённые задачи не исчезают, а хранятся 30 дней с возможностью восстановления или удаления навсегда."},
{"date": "2026-11-01", "author": _A, "change_type": "changed", "module": "production", "ticket": "", "description": "Кнопка «Удалить» теперь перемещает задачу в корзину вместо мгновенного уничтожения; автоочистка корзины старше 30 дней."},
# 0.10.0
{"date": "2026-11-01", "author": _A, "change_type": "added", "module": "tables", "ticket": "", "description": "Новый модуль «Таблицы (конструктор)»: свои таблицы-вкладки, колонки с типами, вычисляемые колонки-формулы через визуальный конструктор, ссылки между таблицами (аналог ВПР)."},
{"date": "2026-11-01", "author": _A, "change_type": "added", "module": "tables", "ticket": "", "description": "Права на клетки: матрица «роль × колонка» (видеть/создавать/удалять/менять колонку), свои колонки ✎, чужие 🔒."},
{"date": "2026-11-01", "author": _A, "change_type": "added", "module": "tables", "ticket": "", "description": "История изменений по клеткам, корзина строк на 30 дней с восстановлением, счётчики-карточки, резервная копия при удалении таблицы."},
# 0.10.1
{"date": "2026-11-01", "author": _A, "change_type": "added", "module": "tables", "ticket": "", "description": "Импорт Excel (.xlsx) в таблицу конструктора: сопоставление колонок по заголовкам, автосоздание недостающих, пропуск пустых строк, отметка в истории."},
{"date": "2026-11-01", "author": _A, "change_type": "changed", "module": "tables", "ticket": "", "description": "Конструктор полностью по‑русски: типы колонок в списках и таблице показаны подписями; форма правки колонки подставляет сохранённую формулу."},
# 0.11.0
{"date": "2026-11-17", "author": _A, "change_type": "added", "module": "tables", "ticket": "", "description": "Inline-редактирование: клик по своей клетке открывает поле ввода, Enter сохраняет через AJAX без перезагрузки страницы."},
{"date": "2026-11-17", "author": _A, "change_type": "changed", "module": "tables", "ticket": "", "description": "Цветовое различение колонок: свои ✎ белые, чужие 🔒 серые, вычисляемые ⚙ голубые."},
{"date": "2026-11-17", "author": _A, "change_type": "added", "module": "tables", "ticket": "", "description": "Подсветка недавно изменённого: зелёная полоса слева и мягкий фон на 5 минут после правки."},
{"date": "2026-11-17", "author": _A, "change_type": "added", "module": "tables", "ticket": "", "description": "Привязка таблицы к модулю (module_key): таблица из конструктора становится вкладкой внутри выбранного модуля."},
# 0.11.1
{"date": "2026-11-17", "author": _A, "change_type": "fixed", "module": "core", "ticket": "", "description": "Чистый старт: модели системного модуля «Настройки» импортируются до create_all — на пустой базе таблицы setting/setting_log создаются, seed не падает."},
{"date": "2026-11-17", "author": _A, "change_type": "changed", "module": "core", "ticket": "", "description": "Меню устойчиво к битым endpoint: пункт пропускается с предупреждением в консоли вместо падения всех страниц."},
# 0.12.0
{"date": "2026-11-17", "author": _A, "change_type": "added", "module": "core", "ticket": "", "description": "Серверный режим: настройки через .env, отладка выключена, порт фиксированный, WSGI-сервер waitress."},
{"date": "2026-11-17", "author": _A, "change_type": "added", "module": "deploy", "ticket": "", "description": "Служба systemd и скрипт её установки: автозапуск при загрузке и подъём после сбоя."},
{"date": "2026-11-17", "author": _A, "change_type": "added", "module": "deploy", "ticket": "", "description": "update.sh — выкладка обновления одной командой; backup.sh — горячие копии базы с хранением 14 дней."},
{"date": "2026-11-17", "author": _A, "change_type": "changed", "module": "docs", "ticket": "", "description": "Установщики переехали в tools/installers/ — теперь они приезжают на сервер через Git вместе с кодом."},
# 0.12.1
{"date": "2026-11-17", "author": _A, "change_type": "added", "module": "test_update", "ticket": "", "description": "Тестовый модуль для проверки процесса обновления через установщик."},
{"date": "2026-11-17", "author": _A, "change_type": "changed", "module": "web", "ticket": "", "description": "Тестовая метка [TEST-UPDATE] в заголовке страниц для проверки обновления."},
# 0.12.2
{"date": "2026-11-17", "author": _A, "change_type": "added", "module": "versions", "ticket": "", "description": "Полная история релизов и журнала изменений стала частью кода: применяется при каждом старте приложения. Любая новая машина (VM, малina) с первого запуска получает полную и одинаковую историю."},
{"date": "2026-11-17", "author": _A, "change_type": "added", "module": "tools", "ticket": "", "description": "Скрипт tools/export_history.py для регенерации history_seed.py после каждого нового релиза."},
{"date": "2026-11-17", "author": _A, "change_type": "fixed", "module": "versions", "ticket": "", "description": "Автоматическое применение истории: обработка дат (release_date) и откат сессии при ошибках."},
{"date": "2026-11-17", "author": _A, "change_type": "removed", "module": "test_update", "ticket": "", "description": "Тестовый модуль для проверки обновления удалён после успешного теста."},
{"date": "2026-11-17", "author": _A, "change_type": "changed", "module": "web", "ticket": "", "description": "Тестовая метка [TEST-UPDATE] убрана из заголовков страниц."},
# 0.12.3
{"date": "2026-11-17", "author": _A, "change_type": "changed", "module": "deploy", "ticket": "", "description": "update.sh полностью на русском языке: все шаги, сообщения и проверки читаются по-русски."},
{"date": "2026-11-17", "author": _A, "change_type": "added", "module": "deploy", "ticket": "", "description": "Принудительное применение истории версий при каждом update.sh: история дольётся даже если автоприменение при старте не сработало."},
{"date": "2026-11-17", "author": _A, "change_type": "fixed", "module": "versions", "ticket": "", "description": "Гарантированное применение истории: отдельный шаг в update.sh, независимый от автоприменения при старте."},
# 0.12.4
{"date": "2026-11-17", "author": _A, "change_type": "fixed", "module": "tools", "ticket": "", "description": "export_history.py теперь запускается ТОЛЬКО на разработочной машине (Windows), где полная база. На сервере (Linux) история берётся готовой из Git, а не генерируется из неполной локальной базы."},
{"date": "2026-11-17", "author": _A, "change_type": "added", "module": "tools", "ticket": "", "description": "Проверка платформы: генератор истории автоматически определяет Windows/Linux и на сервере не запускается."},
# 0.12.5
{"date": "2026-11-17", "author": _A, "change_type": "fixed", "module": "versions", "ticket": "", "description": "История версий наконец применяется полностью: колонка «date» в таблице changelog_entry добавлена в список дат, транзакции разделены (релизы и журнал коммитятся отдельно) — autoflush больше не ломает сессию."},
]


def apply():
    """Добавляет в базу только НЕДОСТАЮЩИЕ релизы и записи журнала.
    Ничего существующего не перезаписывает. Идемпотентен."""
    from core.app import db
    from modules.versions.models import Release
    from modules.changelog.models import ChangelogEntry
    cols_r = set(Release.__table__.columns.keys())
    cols_c = set(ChangelogEntry.__table__.columns.keys())

    # РЕЛИЗЫ — отдельная транзакция.
    have_r = {r.version for r in Release.query.all()}
    added_r = 0
    for rec in RELEASES:
        if rec.get("version") in have_r:
            continue
        kw = {k: (_date(v) if k in _DATE_KEYS else v)
              for k, v in rec.items() if k in cols_r and k != "id"}
        kw.setdefault("is_current", False)
        db.session.add(Release(**kw))
        added_r += 1
    if added_r:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    # ЖУРНАЛ — отдельная транзакция.
    have_c = {(c.module, c.description) for c in ChangelogEntry.query.all()}
    added_c = 0
    for rec in CHANGELOG:
        if (rec.get("module"), rec.get("description")) in have_c:
            continue
        kw = {k: (_date(v) if k in _DATE_KEYS else v)
              for k, v in rec.items() if k in cols_c and k != "id"}
        db.session.add(ChangelogEntry(**kw))
        added_c += 1
    if added_c:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    # Гарантируем, что хоть один релиз помечен текущим.
    if not Release.query.filter_by(is_current=True).first():
        top = Release.query.order_by(Release.id.desc()).first()
        if top:
            top.is_current = True
            db.session.commit()

    return added_r, added_c
