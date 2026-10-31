"""Russkie nazvaniya nastroek i chelovecheskie znacheniya dlya zhurnalov."""
import json

SETTING_LABELS = {
    "app_title": "Название приложения (в шапке)",
    "app_footer": "Подпись в подвале страниц",
    "theme": "Тема интерфейса по умолчанию",
    "enabled_modules": "Список включённых модулей",
    "auth_enabled": "Авторизация: главный выключатель входа",
    "lock_threshold": "Неудачных входов подряд до блокировки",
    "lock_minutes": "Время блокировки после неудачных попыток",
    "feedback_require_comment_on_reject": "Требовать причину при отказе «Не нужно»",
    "ad_enabled": "Вход через Active Directory (домен)",
    "ad_host": "Адрес сервера Active Directory",
    "ad_port": "Порт сервера Active Directory",
    "ad_security": "Защита соединения с AD (шифрование)",
    "ad_base_dn": "Корень поиска пользователей в AD (Base DN)",
    "ad_bind_template": "Шаблон входа в AD (логин через домен)",
    "ad_search_filter": "Фильтр поиска пользователя в AD",
    "ad_default_role": "Роль для новых пользователей из AD",
    "ad_allow_fallback_local": "Запасной вход локальным паролем, если AD недоступен",
    "role_defaults_seeded": "Служебное: системные роли созданы",
}

BOOL_KEYS = {"auth_enabled", "ad_enabled", "feedback_require_comment_on_reject",
             "ad_allow_fallback_local"}

MODULE_NAMES = {
    "feedback": "Задачи отдела",
    "production": "Производство",
    "changelog": "Журнал изменений",
    "versions": "Версии",
    "help": "Справка",
    "manual": "Руководство",
    "settings": "Настройки",
}

def setting_label(key):
    """Russkoe nazvanie nastroiki; esli neizvestna - sam kod."""
    return SETTING_LABELS.get(key, key)

def format_setting_value(key, raw):
    """Prevraschaet tehnicheskoe znachenie v ponyatnoe."""
    if raw is None or raw == "":
        return "(не задано — значение по умолчанию)"
    if key in BOOL_KEYS:
        return "включено" if str(raw).lower() in ("1", "true", "yes", "on") else "выключено"
    if key == "enabled_modules":
        try:
            codes = json.loads(raw)
        except Exception:
            return raw
        names = dict(MODULE_NAMES)
        try:
            from core.registry import AVAILABLE_MODULES
            names.update({m["key"]: m["name"] for m in AVAILABLE_MODULES})
        except Exception:
            pass
        return ", ".join(names.get(c, c) for c in codes) if codes else "(модули выключены)"
    if key == "theme":
        return {"light": "светлая", "dark": "тёмная"}.get(raw, raw)
    if key == "ad_security":
        return {"none": "без шифрования (порт 389)",
                "starttls": "StartTLS (шифрование после соединения)",
                "ldaps": "LDAPS/SSL (шифрование сразу, порт 636)"}.get(raw, raw)
    if key == "lock_threshold":
        return str(raw) + " попыток"
    if key == "lock_minutes":
        return str(raw) + " минут"
    return raw
