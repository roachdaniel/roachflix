import json
from datetime import datetime, timezone
from flask import render_template, redirect, url_for, request, jsonify, abort, flash
from flask_login import login_required, current_user
from app.models import db, Title, WatchlistEntry, User
from app import tmdb
from . import watchlist_bp


@watchlist_bp.route('/')
@login_required
def index():
    tab = request.args.get('tab', 'Movies')
    status = request.args.get('status', 'want')
    user_filter = request.args.get('user', 'all')

    valid_tabs = ('Movies', 'TV Show', 'Anime')
    valid_statuses = ('want', 'watching', 'watched')
    if tab not in valid_tabs:
        tab = 'Movies'
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

    for e in entries:
        if e.title.providers_json:
            e.title._providers = json.loads(e.title.providers_json)
        else:
            e.title._providers = []

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

    family_entries = (WatchlistEntry.query
                      .filter_by(title_id=title_id)
                      .join(User).all())

    return render_template(
        'watchlist/detail.html',
        title=title,
        entry=entry,
        providers=providers,
        family_entries=family_entries,
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
