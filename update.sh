#!/usr/bin/env bash
# ODNA KOMANDA VYKLADKI: bekap -> .env -> git pull -> zavisimosti ->
# ustanovshchik -> restart sluzhby -> proverka HTTP.
set -euo pipefail
cd "$(dirname "$0")"
PY=./venv/bin/python
if [ ! -x "$PY" ]; then
  echo "OSHIBKA: net venv. Sozdayte: python3 -m venv venv && ./venv/bin/python -m pip install -r requirements.txt"
  exit 1
fi

echo "[1/6] Bekap bazy..."
./backup.sh

echo "[2/6] Fayl .env..."
if [ ! -f .env ]; then
  cp .env.example .env
  KEY=$($PY -c "import secrets; print(secrets.token_hex(32))")
  sed -i "s|^APP_SECRET_KEY=.*|APP_SECRET_KEY=${KEY}|" .env
  echo "  sozdan .env so sluchaynym sekretnym klyuchom"
else
  echo "  .env uzhe est, ne trogaem"
fi

echo "[3/6] git pull..."
git pull --ff-only

echo "[4/6] Zavisimosti..."
$PY -m pip install -q -r requirements.txt

echo "[5/6] Ustanovshchik (esli prishel novyy)..."
if [ -f tools/installers/install.py ]; then
  cp tools/installers/install.py ./install.py
  $PY install.py < /dev/null
else
  echo "  novogo ustanovshchika net, propusk"
fi

echo "[6/6] Perezaпуск sluzhby..."
if systemctl is-enabled modular-app >/dev/null 2>&1; then
  sudo systemctl restart modular-app
  sleep 3
  echo "  sluzhba: $(systemctl is-active modular-app)"
else
  echo "  sluzhba eshe ne ustanovlena."
  echo "  Postavte odin raz: ./deploy/install-service.sh"
fi

PORT=$($PY -c "import config; print(config.PORT)")
echo "Proverka HTTP na portu ${PORT}:"
curl -sS -o /dev/null -w "  HTTP %{http_code}\n" "http://127.0.0.1:${PORT}/" || echo "  server ne otvetil"
echo "Gotovo."
