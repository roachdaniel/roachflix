import json
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app.models import db, Title, WatchlistEntry, User
from . import import_bp

STATUS_MAP = {
    'completed':  'watched',
    'plantowatch': 'want',
    'watching':   'watching',
}

SKIP_STATUSES = {'notinteresting', 'hold', 'dropped'}


def _import_items(items, media_type, category, user_id):
    added = skipped = dupes = 0
    for item in items:
        raw = item.get('movie') or item.get('show') or {}
        status_key = item.get('status', '')

        if status_key in SKIP_STATUSES:
            skipped += 1
            continue
        status = STATUS_MAP.get(status_key)
        if not status:
            skipped += 1
            continue

        ids = raw.get('ids', {})
        tmdb_id = ids.get('tmdb')
        if not tmdb_id:
            skipped += 1
            continue
        tmdb_id = int(tmdb_id)

        year = str(raw.get('year', '')) or None
        release_date = f"{year}-01-01" if year else None

        title = Title.query.filter_by(tmdb_id=tmdb_id, media_type=media_type).first()
        if not title:
            title = Title(
                tmdb_id=tmdb_id,
                media_type=media_type,
                category=category,
                title=raw.get('title', ''),
                release_date=release_date,
            )
            db.session.add(title)
            db.session.flush()

        entry = WatchlistEntry.query.filter_by(user_id=user_id, title_id=title.id).first()
        if entry:
            dupes += 1
        else:
            db.session.add(WatchlistEntry(user_id=user_id, title_id=title.id, status=status))
            added += 1

    return added, skipped, dupes


@import_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'GET':
        users = User.query.all()
        return render_template('import_data/index.html', users=users)

    file = request.files.get('file')
    username = request.form.get('username', current_user.username)

    if not file or not file.filename.endswith('.json'):
        return render_template('import_data/index.html',
                               users=User.query.all(),
                               error='Please upload a SimklBackup.json file.')

    user = User.query.filter_by(username=username).first()
    if not user:
        return render_template('import_data/index.html',
                               users=User.query.all(),
                               error='Unknown user.')

    try:
        data = json.load(file)
    except Exception:
        return render_template('import_data/index.html',
                               users=User.query.all(),
                               error='Could not parse JSON file.')

    results = {}
    for key, media_type, category in [
        ('movies', 'movie', 'Movie'),
        ('shows',  'tv',    'TV Show'),
        ('anime',  'tv',    'Anime'),
    ]:
        items = data.get(key, [])
        added, skipped, dupes = _import_items(items, media_type, category, user.id)
        results[key] = {'total': len(items), 'added': added, 'skipped': skipped, 'dupes': dupes}

    db.session.commit()
    total_added = sum(r['added'] for r in results.values())
    return render_template('import_data/result.html', results=results,
                           total_added=total_added, username=username)
