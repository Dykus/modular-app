"""Sinhronizaciya dokumentacii dlya izmeneniy modulea Hotelki (0.7.0)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime
from core.app import create_app, db

HELP_TITLE = "Как работать с Хотелками"
HELP_BODY = """Раздел «Задачи отдела» — доска потребностей: сотрудники пишут, что нужно, и указывают адресата; руководитель ведёт статусы.

Подать хотелку: «Кто» (по умолчанию вы, можно выбрать из списка или вписать), «Кому» (адресат: выберите пользователя из выпадающего списка или впишите своё, например должность), текст → «Отправить».

Приватность: галочка «приватно» делает запись видимой только автору, адресату и администратору; в списке она помечена замком. Кнопка «Сделать приватной/открытой» есть у автора, адресата и админа. Чужие приватные записи не видны ни в списке, ни в истории, ни в счётчиках.

Статусы: Новая, В работе, Сделано, Не нужно; менять может роль с правом «менять статус». При включённом требовании причины отказ «Не нужно» невозможен без комментария.

Кнопка «История» показывает, кто и когда менял статусы (только доступные вам записи). Поиск и фильтры — над таблицей."""

MANUAL_CODE = "hotelki"
MANUAL_BODY = """Раздел собирает потребности отдела и учитывает их выполнение. Хотелка — это служебная записка с адресатом: «кто → кому → что нужно».

Подача: «Кто» — выпадающий список пользователей (по умолчанию вы); «Кому» — такой же список, а если нужного человека в нём нет, впишите имя или должность вручную; затем текст и «Отправить».

Приватность: галочка «приватно» ограничивает видимость автором, адресатом и администратором. Это для случаев вроде «начальник отдела просит добавить функцию в программу» — зачем это видеть всему отделу? Приватные записи помечены замком, не попадают в чужие списки, историю и счётчики. Переключать видимость могут автор, адресат и админ.

Статусы: Новая, В работе, Сделано, Не нужно. Менять статус может роль с соответствующим правом (обычно руководитель). Отказ «Не нужно» при включённой настройке требует комментария с причиной.

История и поиск работают с учётом приватности: чужие закрытые записи не показываются вообще."""

CHANGELOG_BATCH = [
("added", "feedback", "Хотелки: поле «Кому» (адресат) с выпадающим списком пользователей и свободным вводом."),
("added", "feedback", "Приватные хотелки: видны только автору, адресату и администратору; значок замка в списке."),
("changed", "feedback", "Поле «Кто» теперь выпадающий список пользователей (можно вписать своё)."),
]

def sync():
    from modules.help.models import HelpArticle, CATEGORIES
    from modules.manual.models import ManualSection
    from modules.changelog.models import ChangelogEntry
    from modules.versions.models import Release
    from modules.settings.models import Setting

    a = HelpArticle.query.filter_by(title=HELP_TITLE).first()
    if not a:
        a = HelpArticle(title=HELP_TITLE, category="Модули", order=0, body=HELP_BODY,
                        edited_by="синхронизация документации")
        db.session.add(a)
    else:
        a.body = HELP_BODY; a.edited_by = "синхронизация документации"
        a.updated_at = datetime.utcnow()
    s = ManualSection.query.filter_by(code=MANUAL_CODE).first()
    if s:
        s.body = MANUAL_BODY; s.updated_by = "синхронизация документации"
        s.updated_at = datetime.utcnow()
    db.session.commit()
    print("  docs: spravka i rukovodstvo pro hotelki obnovleny")

    marker = Setting.query.get("docs_sync_v070")
    if marker is None or marker.value != "1":
        for typ, mod, desc in CHANGELOG_BATCH:
            db.session.add(ChangelogEntry(author="синхронизация документации",
                                          change_type=typ, module=mod, description=desc))
        db.session.add(Setting(key="docs_sync_v070", value="1"))
        db.session.commit()
        print("  changelog: zapisey dobavleno = %d" % len(CHANGELOG_BATCH))
    else:
        print("  changelog: partiya 0.7.0 uzhe dobavlena, propusk")

    if not Release.query.filter_by(version="0.7.0").first():
        Release.query.update({"is_current": False})
        db.session.add(Release(version="0.7.0",
                               title="Хотелки: адресат и приватность",
                               notes="Поля «Кто» и «Кому» с выпадающими списками пользователей (свободный ввод, если человека нет в списке); приватные записи, видимые только автору, адресату и админу; переключение видимости.",
                               status="released", is_current=True))
        db.session.commit()
        print("  versions: releiz 0.7.0 sozdan i pomachen tekushchim")
    else:
        print("  versions: releiz 0.7.0 uzhe est")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        sync()
    print("Sinhronizaciya 0.7.0 zavershena.")
