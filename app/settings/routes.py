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
