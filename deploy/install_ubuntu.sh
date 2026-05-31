#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR=/opt/xhs-analysis

apt update
apt install -y python3 python3-venv python3-pip nodejs npm nginx android-tools-adb

cd "$PROJECT_DIR/backend"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cd "$PROJECT_DIR/frontend"
npm install
npm run build

cp "$PROJECT_DIR/deploy/xhs-analysis-api.service" /etc/systemd/system/xhs-analysis-api.service
cp "$PROJECT_DIR/deploy/nginx-xhs-analysis.conf" /etc/nginx/sites-available/xhs-analysis.conf
ln -sf /etc/nginx/sites-available/xhs-analysis.conf /etc/nginx/sites-enabled/xhs-analysis.conf

systemctl daemon-reload
systemctl enable xhs-analysis-api
systemctl restart xhs-analysis-api
nginx -t
systemctl restart nginx

systemctl --no-pager --full status xhs-analysis-api
