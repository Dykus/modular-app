"""Sinhronizaciya dokumentacii dlya shaga 3b (AD), releiz 0.8.0."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime
from core.app import create_app, db

HELP_AD_TITLE = "Вход через Active Directory: настройка и проверка"
HELP_AD_BODY = """Active Directory подключается как дополнительный провайдер входа: при его недоступности программа падает на локальные пароли (если включён fallback), никто не оказывается заблокирован из-за проблем с доменом.

Настройка (Настройки → Active Directory, нужно право auth.security):
1. Хост контроллера домена (имя или IP) и порт: 389 для «Без TLS» и «StartTLS», 636 для «LDAPS/SSL».
2. Для самоподписанных сертификатов внутренних AD выбирайте StartTLS или LDAPS — проверка сертификата отключена намеренно.
3. Base DN: корень поиска, например DC=company,DC=local.
4. Шаблон входа: для домена COMPANY пишите COMPANY\\%s, для почтового UPN — %s@company.local. Если оставить пустым, будет поиск по Base DN (требует разрешённый анонимный поиск либо проверочные данные).
5. Роль по умолчанию для автоматически создаваемых доменных учёток.
6. Кнопка «Проверить связь» проходит шаги: библиотека → хост → TCP → TLS → bind → поиск, и останавливается на первой ошибке с пояснением.

Поведение при входе: доменная учётка проверяется только в AD; локальная — у нас, но при совпадении с AD-паролем автоматически переводится на AD. Новый доменный пользователь создаётся автоматически с ролью по умолчанию, имя и email подтягиваются из AD. Доменные пароли у нас не хранятся вообще.

Аварийный режим: если AD недоступен, локальные пользователи входят как раньше; доменные учётки до восстановления AD войти не могут — это осознанное поведение, чтобы не подменять доменный пароль локальным."""

HELP_LOGIN_TITLE = "Вход, пароль и блокировки"
HELP_LOGIN_BODY = """Вход: страница входа, логин и пароль. Источник пароля зависит от учётки: локальные проверяются у нас, доменные — в Active Directory (значок 🌐 в профиле и в журнале входов).

При первом входе локальная учётка обязана сменить пароль. Доменные пароли меняются в самом AD (Ctrl+Alt+Del → «Сменить пароль»).

Блокировка подбора: после N неудачных входов подряд вход замирает на M минут (N и M задаются в Настройках). Журнал входов покажет серию отказов, IP и источник (local/ad).

Если включён AD: доменные пользователи входят учётками Windows; при первом входе учётка создаётся автоматически с ролью по умолчанию. Если AD недоступен и включён fallback — локальные пароли продолжают работать.

Забыли пароль: локальный сбрасывает администратор в «Пользователи»; доменный меняется в AD. Админ забыл пароль: выключите авторизацию флажком в Настройках, войдите, сбросьте пароль, включите обратно."""

MANUAL_AD_CODE = "ad"
MANUAL_AD_TITLE = "Active Directory: вход доменными учётками"
MANUAL_AD_BODY = """Active Directory подключается как дополнительный провайдер входа: ядро от него не зависит и при недоступности домена падает на локальные пароли (если включён fallback).

Настройка (Настройки → Active Directory, нужно право auth.security): хост и порт контроллера домена; защита соединения (без TLS / StartTLS / LDAPS); Base DN вида DC=company,DC=local; шаблон входа (ДОМЕН + обратный слэш + логин, либо %s@домен); фильтр поиска; роль по умолчанию для автосоздаваемых учёток.

Кнопка «Проверить связь» выполняет пошаговую диагностику: библиотека ldap3 → хост → TCP-соединение → TLS → bind (проверочным логином или анонимно) → поиск в Base DN. Останавливается на первом шаге с ошибкой и пишет пояснение. Проверочные логин и пароль нигде не сохраняются.

Поведение при входе: доменная учётка проверяется только в AD; локальная — локально, но при совпадении пароля с AD автоматически переводится на доменный источник. Новый доменный пользователь создаётся автоматически (provisioning) с ролью по умолчанию; имя и email подтягиваются из AD; роль потом можно поменять в «Пользователи».

Аварийный режим: при недоступности AD локальные пользователи входят как раньше; доменные — не могут до восстановления связи. Это осознанное поведение: доменный пароль никогда не подменяется локальным."""

CHANGELOG_BATCH = [
("added", "core", "Active Directory: провайдер входа с graceful-degradation и авто-provisioning доменных пользователей."),
("added", "settings", "Кнопка «Проверить связь» для AD: пошаговая диагностика (библиотека, хост, TCP, TLS, bind, поиск)."),
("changed", "auth", "Журнал входов и профиль показывают источник пароля: локальный или AD."),
("changed", "auth", "У пользователей появился признак источника входа; доменные пароли локально не хранятся."),
]

def sync():
    from modules.help.models import HelpArticle
    from modules.manual.models import ManualSection
    from modules.changelog.models import ChangelogEntry
    from modules.versions.models import Release
    from modules.settings.models import Setting

    def upsert_help(title, cat, order, body):
        a = HelpArticle.query.filter_by(title=title).first()
        if not a:
            a = HelpArticle(title=title, category=cat, order=order, body=body,
                            edited_by="синхронизация документации")
            db.session.add(a)
        else:
            a.category = cat; a.order = order; a.body = body
            a.edited_by = "синхронизация документации"; a.updated_at = datetime.utcnow()

    upsert_help(HELP_AD_TITLE, "Техническое", 1, HELP_AD_BODY)
    upsert_help(HELP_LOGIN_TITLE, "Основы", 2, HELP_LOGIN_BODY)

    s = ManualSection.query.filter_by(code=MANUAL_AD_CODE).first()
    if not s:
        s = ManualSection(code=MANUAL_AD_CODE, title=MANUAL_AD_TITLE, order=75,
                          body=MANUAL_AD_BODY, updated_by="синхронизация документации")
        db.session.add(s)
    else:
        s.title = MANUAL_AD_TITLE; s.order = 75; s.body = MANUAL_AD_BODY
        s.updated_by = "синхронизация документации"; s.updated_at = datetime.utcnow()
    db.session.commit()
    print("  docs: spravka (2 statyi) i rukovodstvo (razdel AD) obnovleny")

    marker = Setting.query.get("docs_sync_v080") if hasattr(Setting.query, "get") else db.session.get(Setting, "docs_sync_v080")
    if marker is None or marker.value != "1":
        for typ, mod, desc in CHANGELOG_BATCH:
            db.session.add(ChangelogEntry(author="синхронизация документации",
                                          change_type=typ, module=mod, description=desc))
        db.session.add(Setting(key="docs_sync_v080", value="1"))
        db.session.commit()
        print("  changelog: zapisey dobavleno = %d" % len(CHANGELOG_BATCH))
    else:
        print("  changelog: partiya 0.8.0 uzhe dobavlena, propusk")

    if not Release.query.filter_by(version="0.8.0").first():
        Release.query.update({"is_current": False})
        db.session.add(Release(version="0.8.0",
            title="Active Directory",
            notes="Вход доменными учётками с graceful-degradation, авто-provisioning с ролью по умолчанию, кнопка проверки связи из настроек, источник входа в журналах и профиле.",
            status="released", is_current=True))
        db.session.commit()
        print("  versions: releiz 0.8.0 sozdan i pomachen tekushchim")
    else:
        print("  versions: releiz 0.8.0 uzhe est")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        sync()
    print("Sinhronizaciya 0.8.0 zavershena.")
