"""Shared Telegram config for RoachFlix — mirrors the tradebot pattern."""
import os


def _load_token():
    try:
        import json
        with open('/home/pi/.openclaw/openclaw.json') as f:
            return json.load(f)['channels']['telegram']['botToken']
    except Exception:
        pass
    return os.environ.get('TELEGRAM_BOT_TOKEN', '')


TELEGRAM_BOT_TOKEN = _load_token()
TELEGRAM_CHAT_ID = '-1003891903734'
TELEGRAM_THREAD_ID = 1234  # T.V. topic
