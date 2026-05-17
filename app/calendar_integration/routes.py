"""Google Calendar integration — add premiere / next episode dates."""
import json
import os
from flask import jsonify, request, current_app, session, redirect, url_for
from flask_login import login_required, current_user
from app.models import Title
from . import calendar_bp

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    GCAL_AVAILABLE = True
except ImportError:
    GCAL_AVAILABLE = False

SCOPES = ['https://www.googleapis.com/auth/calendar.events']


def _get_credentials():
    creds_json = current_app.config.get('GOOGLE_CALENDAR_CREDENTIALS_JSON', '')
    if not creds_json:
        return None
    try:
        creds_data = json.loads(creds_json)
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return creds
    except Exception:
        return None


@calendar_bp.route('/add/<int:title_id>', methods=['POST'])
@login_required
def add_event(title_id):
    if not GCAL_AVAILABLE:
        return jsonify({'error': 'Google Calendar library not installed'}), 503

    title = Title.query.get_or_404(title_id)
    creds = _get_credentials()
    if not creds or not creds.valid:
        return jsonify({'error': 'Google Calendar not configured or credentials expired'}), 503

    event_date = title.next_episode_date or title.release_date
    if not event_date:
        return jsonify({'error': 'No date available for this title'}), 400

    try:
        service = build('calendar', 'v3', credentials=creds)
        event = {
            'summary': title.title,
            'description': title.overview or '',
            'start': {'date': event_date},
            'end': {'date': event_date},
        }
        created = service.events().insert(calendarId='primary', body=event).execute()
        return jsonify({'ok': True, 'event_id': created.get('id')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
