"""Shared Telegram config for RoachFlix — mirrors the tradebot pattern."""
import os


def _load_token():
    env_paths = ['/home/pi/.env', '/home/father/.env']
    for path in env_paths:
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('TELEGRAM_BOT_TOKEN='):
                        return line.split('=', 1)[1]
        except Exception:
            pass
    return os.environ.get('TELEGRAM_BOT_TOKEN', '')


TELEGRAM_BOT_TOKEN = _load_token()
TELEGRAM_CHAT_ID = '-1003891903734'
TELEGRAM_THREAD_ID = 10  # Alerts topic
