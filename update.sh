#!/usr/bin/env bash
# ОДНА КОМАНДА ВЫКЛАДКИ: бэкап -> .env -> git pull -> зависимости ->
# установщик -> принудительное применение истории -> перезапуск службы -> проверка HTTP.
set -euo pipefail
cd "$(dirname "$0")"
PY=./venv/bin/python
if [ ! -x "$PY" ]; then
  echo "ОШИБКА: нет venv. Создайте: python3 -m venv venv && ./venv/bin/python -m pip install -r requirements.txt"
  exit 1
fi

echo "[1/7] Бэкап базы..."
./backup.sh

echo "[2/7] Файл .env..."
if [ ! -f .env ]; then
  cp .env.example .env
  KEY=$($PY -c "import secrets; print(secrets.token_hex(32))")
  sed -i "s|^APP_SECRET_KEY=.*|APP_SECRET_KEY=${KEY}|" .env
  echo "  создан .env со случайным секретным ключом"
else
  echo "  .env уже есть, не трогаем"
fi

echo "[3/7] git pull..."
git pull --ff-only

echo "[4/7] Зависимости..."
$PY -m pip install -q -r requirements.txt

echo "[5/7] Установщик (если пришёл новый)..."
if [ -f tools/installers/install.py ]; then
  cp tools/installers/install.py ./install.py
  $PY install.py < /dev/null
else
  echo "  нового установщика нет, пропуск"
fi

echo "[6/7] Применение истории версий..."
$PY -c "
import sys
sys.path.insert(0, '.')
from core.app import create_app, db
app = create_app()
with app.app_context():
    try:
        from modules.versions import history_seed as hs
        added_r, added_c = hs.apply()
        if added_r or added_c:
            print(f'  история: добавлено релизов {added_r}, записей журнала {added_c}')
        else:
            print('  история: всё уже есть')
    except Exception as e:
        print(f'  ПРЕДУПРЕЖДЕНИЕ: история не применена: {e}')
"

echo "[7/7] Перезапуск службы..."
if systemctl is-enabled modular-app >/dev/null 2>&1; then
  sudo systemctl restart modular-app
  sleep 3
  echo "  служба: $(systemctl is-active modular-app)"
else
  echo "  служба ещё не установлена."
  echo "  Поставьте один раз: ./deploy/install-service.sh"
fi

PORT=$($PY -c "import config; print(config.PORT)")
echo "Проверка HTTP на порту ${PORT}:"
curl -sS -o /dev/null -w "  HTTP %{http_code}\n" "http://127.0.0.1:${PORT}/" || echo "  сервер не ответил"
echo "Готово."
