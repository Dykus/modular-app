#!/usr/bin/env bash
# Odin raz: stavit sluzhbu systemd. Sam podstavlyaet tekushchego
# polzovatelya i put' k projektu (vazhno pri perenose na malinu).
set -euo pipefail
cd "$(dirname "$0")/.."
APPDIR=$(pwd)
RUNUSER=$(whoami)

if [ ! -x "${APPDIR}/venv/bin/python" ]; then
  echo "OSHIBKA: net venv v ${APPDIR}"
  exit 1
fi
if [ ! -f "${APPDIR}/.env" ]; then
  echo "OSHIBKA: net .env. Snachala zapustite ./update.sh"
  exit 1
fi

echo "Stavlyu sluzhbu modular-app:"
echo "  polzovatel: ${RUNUSER}"
echo "  papka:      ${APPDIR}"

sudo tee /etc/systemd/system/modular-app.service > /dev/null <<EOF
[Unit]
Description=Modular App (proizvodstvo)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${RUNUSER}
WorkingDirectory=${APPDIR}
ExecStart=${APPDIR}/venv/bin/python ${APPDIR}/run.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now modular-app
sleep 3
systemctl status modular-app --no-pager | head -n 12
echo ""
echo "Sluzhba ustanovlena i vklyuchena avtozapusk pri zagruzke."
echo "Logi:  journalctl -u modular-app -f"
