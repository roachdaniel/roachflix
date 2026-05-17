"""Telegram notification helper for RoachFlix."""
import requests
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from telegram_config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_THREAD_ID


def send_alert(message):
    if not TELEGRAM_BOT_TOKEN:
        return False
    try:
        r = requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage',
            json={
                'chat_id': TELEGRAM_CHAT_ID,
                'message_thread_id': TELEGRAM_THREAD_ID,
                'text': message,
                'parse_mode': 'HTML',
            },
            timeout=10,
        )
        return r.ok
    except Exception:
        return False
