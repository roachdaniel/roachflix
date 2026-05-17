import json
from datetime import datetime, timezone
from flask import render_template, redirect, url_for, request, jsonify, abort, flash
from flask_login import login_required, current_user
from app.models import db, Title, WatchlistEntry, User, SubscribedService
from app import tmdb
from . import watchlist_bp


def _subscribed_ids():
    return {s.provider_id for s in SubscribedService.query.all()}


def _filter_providers(providers, subscribed_ids):
    if not subscribed_ids:
        return providers
    return [p for p in providers if p.get('provider_id') in subscribed_ids]


@watchlist_bp.route('/')
@login_required
def index():
    tab = request.args.get('tab', 'Movie')
    status = request.args.get('status', 'want')
    user_filter = request.args.get('user', 'all')

    valid_tabs = ('Movie', 'TV Show', 'Anime')
    valid_statuses = ('want', 'watching', 'uptodate', 'watched', 'dropped')
    if tab not in valid_tabs:
        tab = 'Movie'
    if status not in valid_statuses:
        status = 'want'

    query = (WatchlistEntry.query
             .join(Title)
             .filter(WatchlistEntry.status == status))

    if user_filter == 'all':
        pass
    else:
        user_obj = User.query.filter_by(username=user_filter).first()
        if user_obj:
            query = query.filter(WatchlistEntry.user_id == user_obj.id)

    all_entries = query.order_by(WatchlistEntry.added_at.desc()).all()

    entries = [e for e in all_entries if e.effective_category == tab]

    sub_ids = _subscribed_ids()
    for e in entries:
        raw = json.loads(e.title.providers_json) if e.title.providers_json else []
        e.title._providers = _filter_providers(raw, sub_ids)

    users = User.query.all()
    return render_template(
        'watchlist/index.html',
        entries=entries,
        tab=tab,
        status=status,
        user_filter=user_filter,
        users=users,
        tabs=valid_tabs,
    )


@watchlist_bp.route('/title/<int:title_id>')
@login_required
def detail(title_id):
    title = Title.query.get_or_404(title_id)
    entry = WatchlistEntry.query.filter_by(
        user_id=current_user.id, title_id=title_id
    ).first()

    # Lazy TMDB enrichment for titles imported without full details
    if not title.poster_path or (title.media_type == 'tv' and not title.tmdb_status):
        try:
            details = tmdb.get_details(title.tmdb_id, title.media_type)
            title.poster_path = details.get('poster_path') or title.poster_path
            title.backdrop_path = details.get('backdrop_path') or title.backdrop_path
            title.overview = details.get('overview', '') or title.overview
            title.tmdb_rating = details.get('vote_average') or title.tmdb_rating
            title.release_date = (details.get('release_date')
                                  or details.get('first_air_date')
                                  or title.release_date)
            title.tmdb_status = details.get('status') or title.tmdb_status
            db.session.commit()
        except Exception:
            pass

    if title.providers_json:
        providers = json.loads(title.providers_json)
    else:
        try:
            providers = tmdb.get_watch_providers(title.tmdb_id, title.media_type)
            title.providers_json = json.dumps(providers)
            title.providers_updated = datetime.now(timezone.utc)
            db.session.commit()
        except Exception:
            providers = []

    sub_ids = _subscribed_ids()
    providers = _filter_providers(providers, sub_ids)

    family_entries = (WatchlistEntry.query
                      .filter_by(title_id=title_id)
                      .join(User).all())

    family_entry_map = {e.user_id: e for e in family_entries}
    all_users = User.query.order_by(User.username).all()

    return render_template(
        'watchlist/detail.html',
        title=title,
        entry=entry,
        providers=providers,
        family_entries=family_entries,
        family_entry_map=family_entry_map,
        all_users=all_users,
        poster_url=tmdb.poster_url,
        backdrop_url=tmdb.backdrop_url,
    )


@watchlist_bp.route('/add', methods=['POST'])
@login_required
def add():
    data = request.get_json()
    tmdb_id = int(data['tmdb_id'])
    media_type = data['media_type']
    status = data.get('status', 'want')

    title = Title.query.filter_by(tmdb_id=tmdb_id, media_type=media_type).first()
    if not title:
        try:
            details = tmdb.get_details(tmdb_id, media_type)
            genres = details.get('genres', [])
            origin = details.get('origin_country', [])
            category = tmdb.classify_title(media_type, genres, origin)
            title = Title(
                tmdb_id=tmdb_id,
                media_type=media_type,
                category=category,
                title=details.get('title') or details.get('name', ''),
                overview=details.get('overview', ''),
                poster_path=details.get('poster_path'),
                backdrop_path=details.get('backdrop_path'),
                release_date=details.get('release_date') or details.get('first_air_date'),
                tmdb_rating=details.get('vote_average'),
            )
            db.session.add(title)
            db.session.flush()

            providers = tmdb.get_watch_providers(tmdb_id, media_type)
            title.providers_json = json.dumps(providers)
            title.providers_updated = datetime.now(timezone.utc)
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    existing = WatchlistEntry.query.filter_by(
        user_id=current_user.id, title_id=title.id
    ).first()
    if existing:
        existing.status = status
    else:
        entry = WatchlistEntry(user_id=current_user.id, title_id=title.id, status=status)
        db.session.add(entry)

    db.session.commit()
    return jsonify({'ok': True, 'title_id': title.id})


@watchlist_bp.route('/entry/<int:entry_id>/status', methods=['POST'])
@login_required
def update_status(entry_id):
    entry = WatchlistEntry.query.get_or_404(entry_id)
    if entry.user_id != current_user.id:
        abort(403)
    data = request.get_json()
    entry.status = data['status']
    db.session.commit()
    return jsonify({'ok': True})


@watchlist_bp.route('/entry/<int:entry_id>/category', methods=['POST'])
@login_required
def update_category(entry_id):
    entry = WatchlistEntry.query.get_or_404(entry_id)
    if entry.user_id != current_user.id:
        abort(403)
    data = request.get_json()
    new_cat = data.get('category')
    if new_cat not in ('Movie', 'TV Show', 'Anime', None):
        return jsonify({'error': 'invalid category'}), 400
    entry.category_override = new_cat
    db.session.commit()
    return jsonify({'ok': True})


@watchlist_bp.route('/entry/<int:entry_id>/remove', methods=['POST'])
@login_required
def remove(entry_id):
    entry = WatchlistEntry.query.get_or_404(entry_id)
    if entry.user_id != current_user.id:
        abort(403)
    db.session.delete(entry)
    db.session.commit()
    return jsonify({'ok': True})


@watchlist_bp.route('/bulk-status', methods=['POST'])
@login_required
def bulk_status():
    data = request.get_json()
    status = data.get('status')
    entry_ids = data.get('entry_ids', [])
    if status not in ('want', 'watching', 'uptodate', 'watched', 'dropped'):
        return jsonify({'error': 'Invalid status'}), 400
    updated = 0
    for eid in entry_ids:
        entry = WatchlistEntry.query.filter_by(id=eid).first()
        if entry:
            entry.status = status
            updated += 1
    db.session.commit()
    return jsonify({'ok': True, 'updated': updated})


@watchlist_bp.route('/title/<int:title_id>/add-for', methods=['POST'])
@login_required
def add_for_user(title_id):
    title = Title.query.get_or_404(title_id)
    data = request.get_json()
    target = User.query.filter_by(username=data['username']).first()
    if not target:
        return jsonify({'error': 'Unknown user'}), 404
    status = data.get('status', 'want')
    if status not in ('want', 'watching', 'watched'):
        return jsonify({'error': 'Invalid status'}), 400

    entry = WatchlistEntry.query.filter_by(user_id=target.id, title_id=title.id).first()
    if entry:
        entry.status = status
    else:
        db.session.add(WatchlistEntry(user_id=target.id, title_id=title.id, status=status))
    db.session.commit()
    return jsonify({'ok': True})
