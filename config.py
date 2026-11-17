"""Konfiguraciya. Znacheniya berutsya iz .env (ili iz okruzheniya)."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

def _load_dotenv():
    p = os.path.join(BASE_DIR, ".env")
    if not os.path.isfile(p):
        return
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

_load_dotenv()

PORT = int(os.environ.get("APP_PORT", "5000"))
HOST = os.environ.get("APP_HOST", "0.0.0.0")
SECRET_KEY = os.environ.get("APP_SECRET_KEY", "change-me-in-production")
DEBUG = os.environ.get("APP_DEBUG", "0").lower() in ("1", "true", "yes", "on")
DATABASE = "sqlite:///" + os.path.join(DATA_DIR, "database.db").replace("\\", "/")
