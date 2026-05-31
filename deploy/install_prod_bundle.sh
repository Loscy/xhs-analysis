#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR=/opt/xhs-analysis
UPLOAD_DIR=${1:-/tmp/xhs-analysis-upload}

if [ ! -d "$UPLOAD_DIR/backend" ] || [ ! -d "$UPLOAD_DIR/frontend-dist" ]; then
  echo "missing bundle contents in $UPLOAD_DIR" >&2
  exit 1
fi

apt update
apt install -y python3 python3-venv python3-pip nginx android-tools-adb

mkdir -p "$PROJECT_DIR"
if [ -f "$PROJECT_DIR/backend/.env" ]; then
  cp "$PROJECT_DIR/backend/.env" /tmp/xhs-analysis-backend.env
fi
rm -rf "$PROJECT_DIR/backend" "$PROJECT_DIR/frontend" "$PROJECT_DIR/deploy"
mkdir -p "$PROJECT_DIR/frontend"

cp -a "$UPLOAD_DIR/backend" "$PROJECT_DIR/backend"
cp -a "$UPLOAD_DIR/deploy" "$PROJECT_DIR/deploy"
cp -a "$UPLOAD_DIR/frontend-dist" "$PROJECT_DIR/frontend/dist"
if [ ! -f "$PROJECT_DIR/backend/.env" ] && [ -f /tmp/xhs-analysis-backend.env ]; then
  cp /tmp/xhs-analysis-backend.env "$PROJECT_DIR/backend/.env"
fi
if [ ! -f "$PROJECT_DIR/backend/.env" ]; then
  cp "$PROJECT_DIR/backend/.env.example" "$PROJECT_DIR/backend/.env"
fi

cd "$PROJECT_DIR/backend"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

mkdir -p /tmp/xhs-ui-tags

cp "$PROJECT_DIR/deploy/xhs-analysis-api.service" /etc/systemd/system/xhs-analysis-api.service
cp "$PROJECT_DIR/deploy/nginx-xhs-analysis.conf" /etc/nginx/sites-available/xhs-analysis.conf
ln -sf /etc/nginx/sites-available/xhs-analysis.conf /etc/nginx/sites-enabled/xhs-analysis.conf
rm -f /etc/nginx/sites-enabled/default

systemctl daemon-reload
systemctl enable xhs-analysis-api
systemctl restart xhs-analysis-api
nginx -t
systemctl restart nginx

echo
echo "xhs-analysis deployed"
systemctl --no-pager --full status xhs-analysis-api
