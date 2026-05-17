"""TMDB API helpers."""
import json
import requests
from flask import current_app


def _get(path, **params):
    cfg = current_app.config
    params['api_key'] = cfg['TMDB_API_KEY']
    r = requests.get(f"{cfg['TMDB_BASE_URL']}{path}", params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def search(query, page=1):
    return _get('/search/multi', query=query, page=page, include_adult=False)


def get_details(tmdb_id, media_type):
    return _get(f'/{media_type}/{tmdb_id}', append_to_response='credits')


def get_watch_providers(tmdb_id, media_type):
    data = _get(f'/{media_type}/{tmdb_id}/watch/providers')
    results = data.get('results', {})
    us = results.get('US', {})
    providers = []
    for provider in us.get('flatrate', []):
        providers.append({
            'provider_id': provider['provider_id'],
            'name': provider['provider_name'],
            'logo': f"https://image.tmdb.org/t/p/original{provider['logo_path']}"
        })
    return providers


def get_all_providers():
    """Return combined unique provider list from TMDB (US, flatrate) for both movie and tv."""
    seen = {}
    for media_type in ('movie', 'tv'):
        data = _get(f'/watch/providers/{media_type}', watch_region='US', language='en-US')
        for p in data.get('results', []):
            pid = p['provider_id']
            if pid not in seen:
                seen[pid] = {
                    'provider_id': pid,
                    'name': p['provider_name'],
                    'logo': f"https://image.tmdb.org/t/p/original{p.get('logo_path', '')}",
                    'priority': p.get('display_priority', 999),
                }
    return sorted(seen.values(), key=lambda x: x['priority'])


def classify_title(media_type, genres, origin_countries):
    if media_type == 'tv':
        genre_names = [g.get('name', '') for g in genres]
        if 'Animation' in genre_names and 'JP' in (origin_countries or []):
            return 'Anime'
        return 'TV Show'
    return 'Movie'


def get_tv_next_episode(tmdb_id):
    """Return next episode air date string or None."""
    try:
        data = _get(f'/tv/{tmdb_id}')
        next_ep = data.get('next_episode_to_air')
        if next_ep:
            return next_ep.get('air_date')
        last_ep = data.get('last_episode_to_air')
        if last_ep:
            return last_ep.get('air_date')
    except Exception:
        pass
    return None


def poster_url(path, size='w342'):
    if not path:
        return None
    return f"https://image.tmdb.org/t/p/{size}{path}"


def backdrop_url(path, size='w1280'):
    if not path:
        return None
    return f"https://image.tmdb.org/t/p/{size}{path}"
