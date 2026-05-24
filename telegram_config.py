"""Shared Telegram config for Couch Potato — mirrors the tradebot pattern."""
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
TELEGRAM_CHAT_ID   = '-1003891903734'

# Topic (thread) IDs — update here if supergroup is recreated
TOPIC_TV     = 1234
TOPIC_ALERTS = 10

# Legacy alias used by app/telegram.py
TELEGRAM_THREAD_ID = TOPIC_TV
