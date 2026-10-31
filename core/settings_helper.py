"""Pomoshchniki dlya chislovyh nastroek (zdes', chtoby ne tashchit' krug importov)"""
from modules.settings.models import get_setting

def get_int(key, default=0):
    v = get_setting(key, "")
    try:
        return int(v)
    except (TypeError, ValueError):
        return default
