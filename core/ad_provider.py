"""Active Directory provayder: proverka parolya i avtoprovisioning.

Rabotaet v rezhime graceful-degradation:
  - esli AD vyklyuchen v Nastroikah - srazu vozvraschaem 'net'
  - esli AD vklyuchen, no svyaz ne podnyalas - vozvraschaem 'net' i log 'AD nedostupen'
  - esli biblioteka ldap3 ne ustanovlena - to zhe samoe

Bezopasnost:
  - Nikogda ne logiruem sam parol
  - TLS-nastrroyki berem iz BD, po umolchaniyu - bez TLS (na 389)
  - StartTLS i LDAPS podderzhivaemsya otdelno
"""

from modules.settings.models import get_setting, get_bool

def ldap3_available():
    """True, esli biblioteka ldap3 ustanovlena i importiruetsya."""
    try:
        import ldap3  # noqa
        return True
    except Exception:
        return False

def _get_config():
    """Sobiraem nastroiki AD iz BD v odin slovar."""
    return {
        "enabled":     get_bool("ad_enabled", False),
        "host":        get_setting("ad_host", "").strip(),
        "port":        int(get_setting("ad_port", "389") or "389"),
        "security":    get_setting("ad_security", "none"),
        "base_dn":     get_setting("ad_base_dn", "").strip(),
        "bind_tmpl":   get_setting("ad_bind_template", "").strip(),
        "search_flt":  get_setting("ad_search_filter", "(sAMAccountName=%s)"),
        "def_role":    get_setting("ad_default_role", "staff"),
        "fn_attr":     get_setting("ad_provision_fullname_attr", "displayName"),
        "mail_attr":   get_setting("ad_provision_email_attr", "mail"),
        "fallback":    get_bool("ad_allow_fallback_local", True),
    }

def try_ad_auth(username, log_fn=None):
    """Proveryaet parol v AD. Vozvraschaet dict:
      {"ok": True, "attrs": {"fullname": ..., "email": ...}}   - uspeh
      {"ok": False, "reason": "..."}                           - otkaz
      {"ok": None, "reason": "..."}                            - AD nedostupen / vyklyuchen

    Parol peredayotsya otdelno, v log NE popadaet.
    """
    if not ldap3_available():
        return {"ok": None, "reason": "библиотека ldap3 не установлена"}

    cfg = _get_config()
    if not cfg["enabled"] or not cfg["host"]:
        return {"ok": None, "reason": "AD выключен или не настроен"}

    import ldap3
    import ssl

    # 1) Soedinenie s serverom (bez bind poka)
    use_ssl = (cfg["security"] == "ldaps")
    tls_cfg = None
    if cfg["security"] == "starttls":
        # cert_reqs=CERT_NONE - dlya samopodpisannyh certifikatov vnutrennih AD
        tls_cfg = ldap3.Tls(validate=ssl.CERT_NONE)
    elif use_ssl:
        tls_cfg = ldap3.Tls(validate=ssl.CERT_NONE)

    try:
        server = ldap3.Server(cfg["host"], port=cfg["port"],
                              use_ssl=use_ssl, tls=tls_cfg,
                              get_info=ldap3.NONE, connect_timeout=5)
    except Exception as e:
        return {"ok": None, "reason": "не удалось создать соединение: " + str(e)[:120]}

    # 2) Poisk DN polzovatelya cherez anonimnyi bind (esli razresheno)
    #    libo prosto sobiraem DN po shablonu, esli on zadan.
    user_dn = None
    if cfg["bind_tmpl"] and "%s" in cfg["bind_tmpl"]:
        # Shablon vida COMPANY\user ili user@company.local - eto UPN, ne DN,
        # no ldap3 prinimaet obe formy kak "user" pri SIMPLE bind.
        bind_identity = cfg["bind_tmpl"] % username
    else:
        # Ishchem v base_dn po search_filter
        bind_identity = None
        try:
            anon = ldap3.Connection(server, auto_bind=False)
            anon.open()
            if cfg["security"] == "starttls":
                anon.start_tls()
            flt = cfg["search_flt"].replace("%s", ldap3.utils.conv.escape_filter_chars(username))
            anon.search(cfg["base_dn"], flt,
                        attributes=[cfg["fn_attr"], cfg["mail_attr"], "sAMAccountName"])
            if anon.entries:
                user_dn = str(anon.entries[0].entry_dn)
            anon.unbind()
        except Exception as e:
            if log_fn:
                log_fn("AD: poisk DN upal: " + str(e)[:120])
            return {"ok": None, "reason": "AD недоступен (поиск DN)"}

    if not bind_identity and not user_dn:
        return {"ok": False, "reason": "пользователь не найден в AD"}

    # 3) PROVERKA PAROLYA: SIMPLE bind ot imeni polzovatelya.
    #    Eto i est moment autentifikacii - esli parol neveren, bind upadet.
    who = bind_identity if bind_identity else user_dn
    # parol berem iz argumenta vnizu, no funkciu vyzyvaet do_login,
    # poetomu peredayom ego cherez zamikanie.
    def _bind(password):
        try:
            conn = ldap3.Connection(server, user=who, password=password,
                                    authentication=ldap3.SIMPLE, auto_bind=False)
            conn.open()
            if cfg["security"] == "starttls":
                conn.start_tls()
            if not conn.bind():
                return False, None
            # 4) Esli OK - sobiraem atributy (dlya provisioningu)
            attrs = {}
            if user_dn:
                try:
                    conn.search(user_dn, "(objectClass=*)", attributes=[cfg["fn_attr"], cfg["mail_attr"]])
                    if conn.entries:
                        e = conn.entries[0]
                        attrs["fullname"] = str(e[cfg["fn_attr"]].value) if cfg["fn_attr"] in e else ""
                        attrs["email"]  = str(e[cfg["mail_attr"]].value) if cfg["mail_attr"] in e else ""
                except Exception:
                    pass
            else:
                # Poisk posle uspeshnogo binda
                try:
                    flt = cfg["search_flt"].replace("%s", ldap3.utils.conv.escape_filter_chars(username))
                    conn.search(cfg["base_dn"], flt, attributes=[cfg["fn_attr"], cfg["mail_attr"]])
                    if conn.entries:
                        e = conn.entries[0]
                        attrs["fullname"] = str(e[cfg["fn_attr"]].value) if cfg["fn_attr"] in e else ""
                        attrs["email"]  = str(e[cfg["mail_attr"]].value) if cfg["mail_attr"] in e else ""
                except Exception:
                    pass
            try:
                conn.unbind()
            except Exception:
                pass
            return True, attrs
        except ldap3.core.exceptions.LDAPInvalidCredentialsResult:
            return False, None
        except Exception as e:
            return None, str(e)[:120]
    return {"_bind": _bind, "who": who, "ok": True}  # marker: 'proverit parol nuzhno otdelno'

def verify_ad_password(username, password):
    """Verhneurovnevaya funkciya dlya core.auth: True/False/None (None = AD nedostupen).
    Vozvraschaet kornež (rezultat, attrs_ili_reason).
    """
    r = try_ad_auth(username)
    if r["ok"] is None:
        return None, r.get("reason", "")
    if r["ok"] is False:
        return False, r.get("reason", "")
    ok, attrs = r["_bind"](password)
    if ok is None:
        return None, attrs  # zdes attrs - eto reason
    return ok, (attrs if ok else "неверный пароль AD")
