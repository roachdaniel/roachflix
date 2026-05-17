#!/bin/bash
set -e

REMOTE="pi@192.168.1.8"
REMOTE_DIR="/home/pi/roachflix"

echo "==> Deploying RoachFlix to PinkiPi..."

ssh "$REMOTE" bash <<'ENDSSH'
set -e
REMOTE_DIR="/home/pi/roachflix"

# Clone if first deploy
if [ ! -d "$REMOTE_DIR/.git" ]; then
  git clone https://github.com/roachdaniel/roachflix.git "$REMOTE_DIR"
fi

cd "$REMOTE_DIR"
git pull

# Create venv if missing
if [ ! -f venv/bin/activate ]; then
  python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

# Init DB if first deploy
if [ ! -f instance/roachflix.db ]; then
  mkdir -p instance
  flask db init 2>/dev/null || true
  flask db migrate -m "initial" 2>/dev/null || true
fi
flask db upgrade

# Install and enable service if missing
if [ ! -f /etc/systemd/system/roachflix.service ]; then
  sudo cp roachflix.service /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable roachflix
fi

sudo systemctl restart roachflix
echo "==> RoachFlix deployed and running."
ENDSSH
