#!/bin/bash
set -e

REMOTE="pi@192.168.1.8"
REMOTE_DIR="/home/pi/roachflix"

echo "==> Deploying RoachFlix to PinkiPi..."

ssh "$REMOTE" "
  cd $REMOTE_DIR || { git clone https://github.com/roachdaniel/roachflix.git $REMOTE_DIR && cd $REMOTE_DIR; }
  git pull
  source venv/bin/activate
  pip install -q -r requirements.txt
  flask db upgrade
  sudo systemctl restart roachflix
  echo 'Done.'
"

echo "==> RoachFlix deployed."
