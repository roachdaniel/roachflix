from flask import render_template, request
from flask_login import login_required
from app import tmdb
from . import search_bp


@search_bp.route('/')
@login_required
def index():
    query        = request.args.get('q', '').strip()
    media_filter = request.args.get('type', 'all')
    if media_filter not in ('all', 'movie', 'tv'):
        media_filter = 'all'
    results = []
    error   = None
    if query:
        try:
            data = tmdb.search(query, media_type=media_filter)
            for item in data.get('results', []):
                mt = item.get('media_type')
                if mt not in ('movie', 'tv'):
                    continue
                results.append({
                    'tmdb_id':    item['id'],
                    'media_type': mt,
                    'title':      item.get('title') or item.get('name', ''),
                    'overview':   item.get('overview', ''),
                    'poster':     tmdb.poster_url(item.get('poster_path'), 'w342'),
                    'year':       (item.get('release_date') or item.get('first_air_date') or '')[:4],
                    'rating':     item.get('vote_average'),
                })
        except Exception as e:
            error = str(e)

    return render_template('search/index.html', query=query, results=results,
                           error=error, media_filter=media_filter)
