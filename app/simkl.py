"""SIMKL calendar helpers — no API key required."""
import logging
import requests
from datetime import datetime, timezone

log = logging.getLogger(__name__)

CALENDAR_URL = 'https://data.simkl.in/calendar/tv.json'

# In-process cache — keyed by today's date so it auto-refreshes each day
_cache = {'date': None, 'data': None}


def fetch_calendar():
    """Download SIMKL TV calendar and return {tmdb_id (int): air_date (YYYY-MM-DD)}.

    Covers the next 33 days, updated every 6 hours on SIMKL's CDN.
    Result is cached in memory for the lifetime of the process on a given day.
    Returns an empty dict on failure so callers can fall back gracefully.
    """
    today = datetime.now(timezone.utc).date()
    if _cache['date'] == today and _cache['data'] is not None:
        return _cache['data']

    try:
        r = requests.get(CALENDAR_URL, timeout=15)
        r.raise_for_status()
        result = {}
        for entry in r.json():
            tmdb_id = entry.get('ids', {}).get('tmdb')
            date_str = entry.get('date', '')
            if not tmdb_id or not date_str:
                continue
            air_date = date_str[:10]  # "2026-05-16T00:00:00-05:00" → "2026-05-16"
            # For shows with multiple entries keep the earliest upcoming date
            if tmdb_id not in result or air_date < result[tmdb_id]:
                result[int(tmdb_id)] = air_date
        _cache['date'] = today
        _cache['data'] = result
        log.info('SIMKL calendar loaded: %d shows', len(result))
        return result
    except Exception as e:
        log.warning('SIMKL calendar fetch failed: %s', e)
        return {}
