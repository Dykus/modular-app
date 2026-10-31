"""Active Directory provayder: proverka parolya, provisioning, diagnostika.

Graceful-degradation: esli AD vyklyuchen/nedostupen - vozvraschaem None/False,
prilozhenie prodolžaet rabotat na lokalnyh parolyah (esli razreshen fallback).
"""

from modules.settings.models import get_setting, get_bool

def ldap3_available():
    try:
        import ldap3  # noqa
        return True
    except Exception:
        return False

def _get_config():
    return {
        "enabled":    get_bool("ad_enabled", False),
        "host":       get_setting("ad_host", "").strip(),
        "port":       int(get_setting("ad_port", "389") or "389"),
        "security":   get_setting("ad_security", "none"),
        "base_dn":    get_setting("ad_base_dn", "").strip(),
        "bind_tmpl":  get_setting("ad_bind_template", "").strip(),
        "search_flt": get_setting("ad_search_filter", "(sAMAccountName=%s)"),
        "def_role":   get_setting("ad_default_role", "staff"),
        "fn_attr":    get_setting("ad_provision_fullname_attr", "displayName"),
        "mail_attr":  get_setting("ad_provision_email_attr", "mail"),
        "fallback":   get_bool("ad_allow_fallback_local", True),
    }

def _server_and_tls(cfg):
    import ldap3, ssl
    use_ssl = (cfg["security"] == "ldaps")
    tls = ldap3.Tls(validate=ssl.CERT_NONE) if cfg["security"] in ("starttls", "ldaps") else None
    server = ldap3.Server(cfg["host"], port=cfg["port"], use_ssl=use_ssl, tls=tls,
                          get_info=ldap3.NONE, connect_timeout=5)
    return server, use_ssl

def _search_dn(conn, cfg, username):
    """Ishchet DN polzovatelya po base_dn + filtr. Vozvraschaet (dn, attrs)."""
    import ldap3
    flt = cfg["search_flt"].replace("%s", ldap3.utils.conv.escape_filter_chars(username))
    conn.search(cfg["base_dn"], flt, attributes=[cfg["fn_attr"], cfg["mail_attr"], "sAMAccountName"])
    if not conn.entries:
        return None, {}
    e = conn.entries[0]
    attrs = {
        "fullname": str(e[cfg["fn_attr"]].value) if cfg["fn_attr"] in e else "",
        "email":    str(e[cfg["mail_attr"]].value) if cfg["mail_attr"] in e else "",
    }
    return str(e.entry_dn), attrs

def verify_ad_password(username, password):
    """Glavnaya funkciya dlya core.auth.
    Vozvraschaet (True, attrs) / (False, reason) / (None, reason-AD-nedostupen)."""
    if not ldap3_available():
        return None, "библиотека ldap3 не установлена"
    cfg = _get_config()
    if not cfg["enabled"] or not cfg["host"]:
        return None, "AD выключен или не настроен"
    import ldap3
    try:
        server, use_ssl = _server_and_tls(cfg)
    except Exception as e:
        return None, "не удалось создать соединение: " + str(e)[:120]

    bind_identity = None
    user_dn = None
    attrs = {}
    if cfg["bind_tmpl"] and "%s" in cfg["bind_tmpl"]:
        bind_identity = cfg["bind_tmpl"] % username
    else:
        # poisk DN: nuzhen anonimonnyi bind; esli on zapreshchen - prosim shablon
        try:
            probe = ldap3.Connection(server, auto_bind=False)
            probe.open()
            if cfg["security"] == "starttls":
                probe.start_tls()
            if not probe.bind():
                return None, "анонимный bind отклонён — укажите шаблон входа в настройках AD"
            user_dn, attrs = _search_dn(probe, cfg, username)
            try: probe.unbind()
            except Exception: pass
        except Exception as e:
            return None, "AD недоступен (поиск DN): " + str(e)[:120]
        if not user_dn:
            return False, "пользователь не найден в AD"

    who = bind_identity if bind_identity else user_dn
    try:
        conn = ldap3.Connection(server, user=who, password=password,
                                authentication=ldap3.SIMPLE, auto_bind=False)
        conn.open()
        if cfg["security"] == "starttls":
            conn.start_tls()
        if not conn.bind():
            return False, "неверный пароль AD"
        if not attrs and cfg["base_dn"]:
            try:
                _, attrs = _search_dn(conn, cfg, username)
            except Exception:
                attrs = {}
        try: conn.unbind()
        except Exception: pass
        return True, attrs
    except ldap3.core.exceptions.LDAPInvalidCredentialsResult:
        return False, "неверный пароль AD"
    except Exception as e:
        return None, "AD недоступен (bind): " + str(e)[:120]

def test_connection(test_user="", test_password=""):
    """Poshagovaya diagnostika dlya knopki 'Proverit svyaz'.
    Vozvraschaet spisok (ok: True/False, tekst). Ostanavlivaetsya na pervom False."""
    steps = []
    def add(ok, text):
        steps.append((ok, text))
        return ok
    if not ldap3_available():
        add(False, "Шаг 1. Библиотека ldap3 не установлена: python -m pip install ldap3")
        return steps
    add(True, "Шаг 1. Библиотека ldap3 установлена")
    cfg = _get_config()
    if not cfg["host"]:
        add(False, "Шаг 2. Не указан хост контроллера домена")
        return steps
    add(True, "Шаг 2. Хост: %s:%d, защита: %s" % (cfg["host"], cfg["port"], cfg["security"]))
    import ldap3
    try:
        server, use_ssl = _server_and_tls(cfg)
        conn = ldap3.Connection(server, auto_bind=False)
        conn.open()
    except Exception as e:
        add(False, "Шаг 3. TCP-соединение не открылось: " + str(e)[:160])
        return steps
    add(True, "Шаг 3. TCP-соединение открыто")
    if cfg["security"] == "starttls":
        try:
            conn.start_tls()
            add(True, "Шаг 4. StartTLS поднят")
        except Exception as e:
            add(False, "Шаг 4. StartTLS не поднялся: " + str(e)[:160])
            try: conn.unbind()
            except Exception: pass
            return steps
    else:
        add(True, "Шаг 4. TLS не требуется (выбран режим без него)")

    if test_user and test_password:
        who = (cfg["bind_tmpl"] % test_user) if (cfg["bind_tmpl"] and "%s" in cfg["bind_tmpl"]) else test_user
        try:
            c2 = ldap3.Connection(server, user=who, password=test_password,
                                  authentication=ldap3.SIMPLE, auto_bind=False)
            c2.open()
            if cfg["security"] == "starttls":
                c2.start_tls()
            if c2.bind():
                add(True, "Шаг 5. Проверочный вход (bind) успешен: " + who)
                if cfg["base_dn"]:
                    try:
                        dn, _ = _search_dn(c2, cfg, test_user)
                        if dn:
                            add(True, "Шаг 6. Поиск в Base DN нашёл пользователя: " + dn)
                        else:
                            add(False, "Шаг 6. Поиск в Base DN не нашёл пользователя — проверьте Base DN и фильтр")
                    except Exception as e:
                        add(False, "Шаг 6. Поиск не выполнился: " + str(e)[:160])
                else:
                    add(True, "Шаг 6. Base DN не задан — поиск пропущен (работает вход по шаблону)")
                try: c2.unbind()
                except Exception: pass
            else:
                add(False, "Шаг 5. Bind отклонён (неверный пароль/учётка заблокирована): " + str(c2.result)[:120])
                try: c2.unbind()
                except Exception: pass
        except Exception as e:
            add(False, "Шаг 5. Bind не выполнился: " + str(e)[:160])
    else:
        try:
            if conn.bind():
                add(True, "Шаг 5. Анонимный bind выполнен (проверочный логин не указан)")
                if cfg["base_dn"]:
                    try:
                        conn.search(cfg["base_dn"], "(objectClass=user)", attributes=["cn"], size_limit=5)
                        add(True, "Шаг 6. Поиск в Base DN вернул записей: %d" % len(conn.entries))
                    except Exception as e:
                        add(False, "Шаг 6. Поиск в Base DN не выполнился: " + str(e)[:160])
            else:
                add(False, "Шаг 5. Анонимный bind отклонён: укажите проверочный логин и пароль")
        except Exception as e:
            add(False, "Шаг 5. Bind не выполнился: " + str(e)[:160])
    try: conn.unbind()
    except Exception: pass
    return steps
