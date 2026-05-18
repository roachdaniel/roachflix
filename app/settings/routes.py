from flask import render_template, request, jsonify
from flask_login import login_required
from app.models import db, SubscribedService
from app import tmdb
from . import settings_bp


@settings_bp.route('/')
@login_required
def index():
    subscribed = SubscribedService.query.order_by(SubscribedService.name).all()
    subscribed_ids = {s.provider_id for s in subscribed}
    all_providers = []
    try:
        all_providers = tmdb.get_all_providers()
    except Exception:
        pass
    return render_template(
        'settings/index.html',
        subscribed=subscribed,
        subscribed_ids=subscribed_ids,
        all_providers=all_providers,
    )


@settings_bp.route('/add', methods=['POST'])
@login_required
def add():
    data = request.get_json()
    provider_id = int(data['provider_id'])
    if SubscribedService.query.filter_by(provider_id=provider_id).first():
        return jsonify({'ok': True})
    svc = SubscribedService(
        provider_id=provider_id,
        name=data['name'],
        logo_url=data.get('logo_url', ''),
    )
    db.session.add(svc)
    db.session.commit()
    return jsonify({'ok': True})


@settings_bp.route('/remove/<int:svc_id>', methods=['POST'])
@login_required
def remove(svc_id):
    svc = SubscribedService.query.get_or_404(svc_id)
    db.session.delete(svc)
    db.session.commit()
    return jsonify({'ok': True})


@settings_bp.route('/sync-statuses', methods=['POST'])
@login_required
def sync_statuses():
    from app.notifications.scheduler import sync_show_statuses
    from flask import current_app
    import threading
    threading.Thread(target=sync_show_statuses, args=[current_app._get_current_object()], daemon=True).start()
    return jsonify({'ok': True, 'message': 'Status sync started — takes a few minutes.'})


@settings_bp.route('/refresh-dates', methods=['POST'])
@login_required
def refresh_dates():
    from app.notifications.scheduler import check_new_episodes, update_want_episode_dates
    from flask import current_app
    import threading
    app = current_app._get_current_object()
    threading.Thread(target=check_new_episodes, args=[app], daemon=True).start()
    threading.Thread(target=update_want_episode_dates, args=[app], daemon=True).start()
    return jsonify({'ok': True, 'message': 'Date refresh started — check back in a moment.'})
