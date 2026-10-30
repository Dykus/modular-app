"""Konfiguraciya. Menyay znacheniyu zdes."""
import os

# Absolyutnye puti - chtooby SQLite na Windows TOCHNO videl papku data
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Put' k baze sobiraem ABSOLYUTNYM, pryamymi sleshami (format dlya Windows)
DATABASE = "sqlite:///" + os.path.join(DATA_DIR, "database.db").replace("\\", "/")

PORT = 5000          # esli zanato - programma vozmets sleduyushchiy svobodnyy
HOST = "0.0.0.0"     # 0.0.0.0 = dostupno po lokalnoy seti vsem
SECRET_KEY = "change-me-in-production"
